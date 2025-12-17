from django.core.management.base import BaseCommand
from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowStageInstance, ApprovalAssignment
from user_management.models import XX_UserGroupMembership


class Command(BaseCommand):
    help = 'Fix FAR-0009 Fusion Team stage - activate and assign eligible users'

    def handle(self, *args, **options):
        try:
            transfer = xx_BudgetTransfer.objects.get(code='FAR-0009')
        except xx_BudgetTransfer.DoesNotExist:
            self.stdout.write(self.style.ERROR('FAR-0009 not found'))
            return

        self.stdout.write("=" * 80)
        self.stdout.write(f"Fixing Transaction: {transfer.code} (ID: {transfer.transaction_id})")
        self.stdout.write("=" * 80)

        # Find the skipped Fusion Team stage
        # The FAR-2 workflow has a stage for Fusion Team that was skipped
        all_stages = ApprovalWorkflowStageInstance.objects.filter(
            workflow_instance__budget_transfer=transfer,
            stage_template__name='Finance Manager'
        )
        
        self.stdout.write(f"\n📋 Found {all_stages.count()} Finance Manager stages")
        for stage in all_stages:
            role_str = str(stage.stage_template.required_role) if stage.stage_template.required_role else 'No role'
            self.stdout.write(f"  - {role_str}: {stage.get_status_display()}")
        
        # Find the one for Fusion Team (look for 'fusion' in the role string)
        fusion_stage = None
        for stage in all_stages:
            if stage.stage_template.required_role:
                role_str = str(stage.stage_template.required_role).lower()
                if 'fusion' in role_str:
                    fusion_stage = stage
                    break

        if not fusion_stage:
            self.stdout.write(self.style.ERROR('\nNo Fusion Team Finance Manager stage found'))
            return
        self.stdout.write(f"\n📋 Found Stage: {fusion_stage.stage_template.name}")
        self.stdout.write(f"   Current Status: {fusion_stage.get_status_display()}")
        self.stdout.write(f"   Required Role: {fusion_stage.stage_template.required_role}")

        # Get eligible users (users with Fusion Team - Finance Manager role)
        eligible_users = XX_UserGroupMembership.objects.filter(
            security_group__group_name__icontains='fusion',
            assigned_roles=fusion_stage.stage_template.required_role,
            is_active=True
        )

        self.stdout.write(f"\n🔍 Eligible Users: {eligible_users.count()}")
        if eligible_users.count() == 0:
            self.stdout.write(self.style.WARNING('⚠️  No users assigned to Fusion Team - Finance Manager role!'))
            self.stdout.write('   Please assign users to this role in Django Admin first:')
            self.stdout.write('   1. Go to User Management → XX_UserGroupMembership')
            self.stdout.write('   2. Find/create memberships for Fusion Team security group')
            self.stdout.write('   3. Assign "fusion team - Finance Manger" role')
            return

        for membership in eligible_users:
            self.stdout.write(f"   - {membership.user.username} (Group: {membership.security_group.group_name})")

        # Confirm before proceeding
        confirm = input('\nProceed with fixing this stage? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('Cancelled')
            return

        # Change stage status to ACTIVE
        fusion_stage.status = ApprovalWorkflowStageInstance.STATUS_ACTIVE
        fusion_stage.save()
        self.stdout.write(self.style.SUCCESS(f'\n✅ Stage status changed to: {fusion_stage.get_status_display()}'))

        # Create assignments for eligible users
        created_count = 0
        for membership in eligible_users:
            assignment, created = ApprovalAssignment.objects.get_or_create(
                stage_instance=fusion_stage,
                user=membership.user,
                defaults={
                    'status': ApprovalAssignment.STATUS_PENDING
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'✅ Created assignment for: {membership.user.username}')
            else:
                self.stdout.write(f'ℹ️  Assignment already exists for: {membership.user.username}')

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS(f'✅ FIXED: Created {created_count} new assignments'))
        self.stdout.write("=" * 80)
        self.stdout.write('\nNow Fusion Team users should see FAR-0009 in their pending approval list!')
