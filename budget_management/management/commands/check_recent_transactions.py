from django.core.management.base import BaseCommand
from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowInstance, ApprovalWorkflowStageInstance, ApprovalAssignment
from user_management.models import XX_UserGroupMembership, XX_SecurityGroup
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Check recent transactions and their approval assignments'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("CHECKING RECENT TRANSACTIONS AND APPROVAL ASSIGNMENTS")
        self.stdout.write("=" * 80)

        # Check Fusion Team groups
        self.stdout.write('\n📋 Fusion Team Security Groups:')
        fusion_groups = XX_SecurityGroup.objects.filter(group_name__icontains='fusion')
        
        if fusion_groups.count() == 0:
            self.stdout.write(self.style.WARNING('  ⚠️  No Fusion Team groups found!'))
        else:
            for group in fusion_groups:
                self.stdout.write(f'\n  🔹 {group.group_name} (ID: {group.id})')
                
                # Check members
                members = XX_UserGroupMembership.objects.filter(security_group=group, is_active=True)
                self.stdout.write(f'     Members: {members.count()}')
                for member in members:
                    roles = member.assigned_roles.all()
                    role_names = [str(r) for r in roles]
                    self.stdout.write(f'       - {member.user.username}: {", ".join(role_names)}')

        # Check recent transactions (last 24 hours or last 10)
        recent_cutoff = timezone.now() - timedelta(hours=24)
        recent_transfers = xx_BudgetTransfer.objects.filter(
            request_date__gte=recent_cutoff
        ).order_by('-transaction_id')[:10]

        if recent_transfers.count() == 0:
            # If no recent ones, just get last 5
            recent_transfers = xx_BudgetTransfer.objects.all().order_by('-transaction_id')[:5]
            self.stdout.write('\n📋 Last 5 Transactions (no new ones in last 24h):')
        else:
            self.stdout.write(f'\n📋 Recent Transactions (last 24h): {recent_transfers.count()}')

        for transfer in recent_transfers:
            self.stdout.write(f'\n  🔸 {transfer.code} (ID: {transfer.transaction_id})')
            self.stdout.write(f'     Security Group: {transfer.security_group.group_name}')
            self.stdout.write(f'     Creator: {transfer.requested_by}')
            self.stdout.write(f'     Status: {transfer.status}')
            self.stdout.write(f'     Created: {transfer.request_date}')
            
            # Check workflows
            workflows = transfer.workflow_instances.all()
            self.stdout.write(f'     Workflows: {workflows.count()}')
            
            for wf in workflows:
                self.stdout.write(f'\n       📊 Workflow: {wf.template.code} - {wf.get_status_display()}')
                
                # Check stages
                stages = wf.stage_instances.all().order_by('stage_template__order_index')
                for stage in stages:
                    role_str = str(stage.stage_template.required_role) if stage.stage_template.required_role else 'No role'
                    self.stdout.write(f'         Stage: {stage.stage_template.name} ({role_str})')
                    self.stdout.write(f'           Status: {stage.get_status_display()}')
                    
                    # Check assignments
                    assignments = stage.assignments.all()
                    if assignments.count() == 0:
                        self.stdout.write(self.style.ERROR('           ⚠️  NO ASSIGNMENTS!'))
                    else:
                        for assignment in assignments:
                            self.stdout.write(f'           ✅ {assignment.user.username}: {assignment.get_status_display()}')

        self.stdout.write("\n" + "=" * 80)
