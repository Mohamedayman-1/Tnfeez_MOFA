from django.core.management.base import BaseCommand
from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowStageInstance, ApprovalAssignment
from user_management.models import XX_UserGroupMembership


class Command(BaseCommand):
    help = 'Fix FAR-0012 - activate skipped Fusion Team stage and assign users'

    def handle(self, *args, **options):
        try:
            transfer = xx_BudgetTransfer.objects.get(code='FAR-0012')
        except xx_BudgetTransfer.DoesNotExist:
            self.stdout.write(self.style.ERROR('FAR-0012 not found'))
            return

        self.stdout.write("=" * 80)
        self.stdout.write(f"FIXING FAR-0012")
        self.stdout.write("=" * 80)

        # Find the far2222 workflow
        far2222_wf = transfer.workflow_instances.filter(template__code='far2222').first()
        
        if not far2222_wf:
            self.stdout.write(self.style.ERROR('far2222 workflow not found'))
            return

        # Find skipped stages
        skipped_stages = far2222_wf.stage_instances.filter(status=ApprovalWorkflowStageInstance.STATUS_SKIPPED)
        
        self.stdout.write(f'\n📋 Found {skipped_stages.count()} skipped stage(s)')
        
        for stage in skipped_stages:
            self.stdout.write(f'\n  🔸 Stage: {stage.stage_template.name}')
            self.stdout.write(f'     Required Role: {stage.stage_template.required_role}')
            
            if not stage.stage_template.required_role:
                self.stdout.write(self.style.WARNING('     ⚠️  No required role - skipping'))
                continue
            
            # Get users from the role's security group
            role_security_group = stage.stage_template.required_role.security_group
            eligible_users = XX_UserGroupMembership.objects.filter(
                security_group=role_security_group,
                assigned_roles=stage.stage_template.required_role,
                is_active=True
            )
            
            self.stdout.write(f'     Eligible Users ({role_security_group.group_name}): {eligible_users.count()}')
            for member in eligible_users:
                self.stdout.write(f'       - {member.user.username}')
            
            if eligible_users.count() == 0:
                self.stdout.write(self.style.WARNING('     ⚠️  No eligible users found'))
                continue
            
            # Activate stage
            stage.status = ApprovalWorkflowStageInstance.STATUS_ACTIVE
            stage.save()
            self.stdout.write(self.style.SUCCESS(f'     ✅ Stage activated'))
            
            # Create assignments
            created_count = 0
            for member in eligible_users:
                assignment, created = ApprovalAssignment.objects.get_or_create(
                    stage_instance=stage,
                    user=member.user,
                    defaults={'status': ApprovalAssignment.STATUS_PENDING}
                )
                if created:
                    created_count += 1
                    self.stdout.write(f'     ✅ Created assignment for: {member.user.username}')
            
            self.stdout.write(self.style.SUCCESS(f'     ✅ Created {created_count} assignment(s)'))

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS('✅ FAR-0012 FIXED!'))
        self.stdout.write("=" * 80)
