from django.core.management.base import BaseCommand
from django.db.models import Q
from user_management.models import xx_User, XX_UserGroupMembership, XX_SecurityGroup, XX_SecurityGroupRole
from approvals.models import ApprovalAssignment, ApprovalWorkflowStageInstance


class Command(BaseCommand):
    help = 'Test multi-group multi-role user scenario'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to test')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = xx_User.objects.get(username=username)
        except xx_User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User {username} not found!'))
            return
        
        self.stdout.write("=" * 80)
        self.stdout.write(f"MULTI-GROUP/MULTI-ROLE TEST FOR USER: {user.username}")
        self.stdout.write("=" * 80)
        
        # Check group memberships
        memberships = XX_UserGroupMembership.objects.filter(
            user=user,
            is_active=True
        ).select_related('security_group')
        
        self.stdout.write(f"\n📋 Security Group Memberships: {memberships.count()}")
        
        for membership in memberships:
            self.stdout.write(f"\n  🔹 Group: {membership.security_group.group_name}")
            
            # Show assigned roles in this group
            assigned_roles = membership.assigned_roles.all()
            if assigned_roles.exists():
                self.stdout.write(f"     Roles ({assigned_roles.count()}):")
                for role in assigned_roles:
                    role_name = getattr(role, 'role_name', getattr(role, 'name', str(role)))
                    self.stdout.write(f"       - {role_name}")
            else:
                self.stdout.write(self.style.WARNING("     ⚠️  NO ROLES ASSIGNED!"))
        
        # Check approval assignments across all groups
        self.stdout.write("\n\n📊 Approval Assignments:")
        
        all_assignments = ApprovalAssignment.objects.filter(
            user=user
        ).select_related(
            'stage_instance__workflow_instance__budget_transfer',
            'stage_instance__stage_template'
        ).order_by('-created_at')[:20]  # Last 20 assignments
        
        if not all_assignments.exists():
            self.stdout.write(self.style.WARNING("  ⚠️  No approval assignments found!"))
        else:
            self.stdout.write(f"  Total: {all_assignments.count()} recent assignments\n")
            
            for assign in all_assignments:
                transfer = assign.stage_instance.workflow_instance.budget_transfer
                stage = assign.stage_instance.stage_template
                workflow = assign.stage_instance.workflow_instance
                
                self.stdout.write(f"  🔸 Transfer: {transfer.code}")
                self.stdout.write(f"     Security Group: {transfer.security_group.group_name if transfer.security_group else 'None'}")
                self.stdout.write(f"     Workflow: {workflow.template.name}")
                self.stdout.write(f"     Stage: {stage.name}")
                self.stdout.write(f"     Required Role: {stage.required_role if stage.required_role else 'None'}")
                self.stdout.write(f"     Assignment Status: {assign.status}")
                self.stdout.write("")
        
        # Test dashboard filtering logic
        self.stdout.write("\n🎯 Dashboard Filtering Test:")
        
        from budget_management.models import xx_BudgetTransfer
        from approvals.models import ApprovalWorkflowInstance
        
        # Check if user is SuperAdmin
        if user.role == 1:
            self.stdout.write("  User is SuperAdmin - sees ALL transfers")
            all_transfers = xx_BudgetTransfer.objects.all()
            self.stdout.write(f"  Total transfers in system: {all_transfers.count()}")
        else:
            # Simulate the dashboard query - approval assignments
            user_assigned_transfer_ids = set(ApprovalAssignment.objects.filter(
                user=user,
                stage_instance__workflow_instance__budget_transfer__isnull=False
            ).filter(
                Q(status=ApprovalAssignment.STATUS_PENDING) |
                Q(stage_instance__workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS)
            ).values_list('stage_instance__workflow_instance__budget_transfer_id', flat=True).distinct())
            
            # Get transfers created by user
            user_created_transfer_ids = set(xx_BudgetTransfer.objects.filter(
                requested_by=user.username
            ).values_list('transaction_id', flat=True))
            
            # Combine both
            visible_transfer_ids = user_assigned_transfer_ids | user_created_transfer_ids
            
            self.stdout.write(f"  Assigned to approve: {len(user_assigned_transfer_ids)} transfers")
            self.stdout.write(f"  Created by user: {len(user_created_transfer_ids)} transfers")
            self.stdout.write(f"  Total visible: {len(visible_transfer_ids)} transfers")
        
            if visible_transfer_ids:
                transfers = xx_BudgetTransfer.objects.filter(transaction_id__in=visible_transfer_ids)
                self.stdout.write(f"\n  📋 Visible Transfers:")
                for transfer in transfers[:10]:  # Show first 10
                    creator = transfer.requested_by
                    group = transfer.security_group.group_name if transfer.security_group else 'None'
                    self.stdout.write(f"    - {transfer.code} (Creator: {creator}, Group: {group}, Status: {transfer.status})")
            else:
                self.stdout.write(self.style.WARNING("  ⚠️  No visible transfers!"))
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("✅ TEST COMPLETE")
        self.stdout.write("=" * 80)
