from django.core.management.base import BaseCommand
from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowInstance, ApprovalWorkflowStageInstance


class Command(BaseCommand):
    help = 'Check transaction 0008 workflow status'

    def handle(self, *args, **options):
        # Find transaction
        t = xx_BudgetTransfer.objects.filter(code__icontains='0008').first()
        if not t:
            self.stdout.write(self.style.ERROR('Transaction 0008 not found!'))
            return
        
        self.stdout.write("=" * 70)
        self.stdout.write(f"TRANSACTION: {t.code} (ID: {t.transaction_id})")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Status: {t.status}")
        self.stdout.write(f"Type: {t.type}")
        requested_by = getattr(t.requested_by, 'username', t.requested_by) if t.requested_by else 'N/A'
        self.stdout.write(f"Requested by: {requested_by}")
        
        # Check workflows
        workflows = t.workflow_instances.all().order_by('execution_order')
        self.stdout.write(f"\n📋 Workflow Instances: {workflows.count()}")
        
        for wf in workflows:
            self.stdout.write("\n" + "-" * 70)
            self.stdout.write(f"Workflow: {wf.template.code} - {wf.template.name}")
            self.stdout.write(f"Status: {wf.status}")
            self.stdout.write(f"Execution Order: {wf.execution_order}")
            
            # Check stages
            self.stdout.write("\n📊 Stage Instances:")
            stages = wf.stage_instances.all().order_by('stage_template__order_index')
            
            for si in stages:
                self.stdout.write(f"\n  🔹 Stage {si.stage_template.order_index}: {si.stage_template.name}")
                self.stdout.write(f"     Status: {si.status}")
                self.stdout.write(f"     Decision Policy: {si.stage_template.decision_policy}")
                
                # Assignees
                assignments = si.assignments.all()
                if assignments.exists():
                    self.stdout.write(f"     Assignees ({assignments.count()}):")
                    for assign in assignments:
                        self.stdout.write(f"       - {assign.user.username} (ID: {assign.user.id})")
                else:
                    self.stdout.write(self.style.WARNING("     ⚠️  NO ASSIGNEES!"))
                
                # Actions
                actions = si.actions.all().order_by('created_at')
                self.stdout.write(f"     Actions: {actions.count()}")
                for action in actions:
                    self.stdout.write(f"       - {action.user.username}: {action.action} at {action.created_at}")
        
        self.stdout.write("\n" + "=" * 70)
