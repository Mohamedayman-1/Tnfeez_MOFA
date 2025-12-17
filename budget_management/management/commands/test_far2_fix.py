from django.core.management.base import BaseCommand
from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowInstance, ApprovalWorkflowStageInstance
from user_management.models import XX_UserGroupMembership


class Command(BaseCommand):
    help = 'Test the fix - check if newest FAR transaction has proper Fusion Team assignments'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("TESTING FAR-2 WORKFLOW FIX")
        self.stdout.write("=" * 80)

        # Get the most recent FAR transaction
        latest_far = xx_BudgetTransfer.objects.filter(code__startswith='FAR').order_by('-transaction_id').first()

        if not latest_far:
            self.stdout.write(self.style.ERROR('No FAR transactions found'))
            return

        self.stdout.write(f'\n📋 Latest FAR Transaction: {latest_far.code} (ID: {latest_far.transaction_id})')
        self.stdout.write(f'   Creator: {latest_far.requested_by}')
        self.stdout.write(f'   Created: {latest_far.request_date}')

        # Check FAR-2 workflow
        far2_workflows = latest_far.workflow_instances.filter(template__code='FAR-2')

        if not far2_workflows.exists():
            self.stdout.write(self.style.WARNING('\n⚠️  This transaction does not have FAR-2 workflow'))
            self.stdout.write('   Create a NEW FAR transaction to test the fix!')
            return

        far2_wf = far2_workflows.first()
        self.stdout.write(f'\n✅ Found FAR-2 Workflow: {far2_wf.get_status_display()}')

        # Check stages and assignments
        stages = far2_wf.stage_instances.all().order_by('stage_template__order_index')
        
        all_good = True
        for stage in stages:
            self.stdout.write(f'\n  🔸 Stage: {stage.stage_template.name}')
            self.stdout.write(f'     Required Role: {stage.stage_template.required_role}')
            self.stdout.write(f'     Status: {stage.get_status_display()}')
            
            assignments = stage.assignments.all()
            self.stdout.write(f'     Assignments: {assignments.count()}')
            
            if assignments.count() == 0:
                self.stdout.write(self.style.ERROR('       ❌ NO ASSIGNMENTS!'))
                all_good = False
            else:
                for assignment in assignments:
                    self.stdout.write(f'       ✅ {assignment.user.username}: {assignment.get_status_display()}')

        self.stdout.write('\n' + '=' * 80)
        if all_good:
            self.stdout.write(self.style.SUCCESS('✅ SUCCESS! All stages have proper assignments!'))
            self.stdout.write('   The fix is working correctly!')
        else:
            self.stdout.write(self.style.WARNING('⚠️  This transaction was created BEFORE the fix.'))
            self.stdout.write('   Please create a NEW FAR transaction to test the fix!')
        self.stdout.write('=' * 80)

        # Show who should see pending approvals
        self.stdout.write('\n📊 Expected Pending Approvals:')
        
        # Get Fusion Team members
        fusion_members = XX_UserGroupMembership.objects.filter(
            security_group__group_name__icontains='fusion',
            is_active=True
        )
        
        for member in fusion_members:
            roles = [str(r) for r in member.assigned_roles.all()]
            self.stdout.write(f'  - {member.user.username}: {", ".join(roles)}')
