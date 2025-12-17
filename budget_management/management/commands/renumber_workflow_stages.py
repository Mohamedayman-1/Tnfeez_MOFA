from django.core.management.base import BaseCommand
from approvals.models import ApprovalWorkflowTemplate


class Command(BaseCommand):
    help = 'Renumber workflow stages to be sequential (1, 2, 3...) instead of 1, 2, 10000'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("RENUMBERING WORKFLOW STAGES")
        self.stdout.write("=" * 80)

        # Get FAR workflows with stage order issues
        far_workflows = ApprovalWorkflowTemplate.objects.filter(code__icontains='FAR')

        for workflow in far_workflows:
            self.stdout.write(f'\n📋 Workflow: {workflow.code}')
            
            # Get all stages ordered by current order_index
            stages = workflow.stages.all().order_by('order_index')
            
            if stages.count() == 0:
                continue
            
            # Check if renumbering is needed
            needs_renumber = False
            for idx, stage in enumerate(stages, start=1):
                if stage.order_index != idx:
                    needs_renumber = True
                    break
            
            if not needs_renumber:
                self.stdout.write('   ✅ Already sequential - no changes needed')
                continue
            
            self.stdout.write(f'   Current stage orders: {[s.order_index for s in stages]}')
            
            # Renumber stages sequentially
            for idx, stage in enumerate(stages, start=1):
                old_order = stage.order_index
                stage.order_index = idx
                stage.save()
                self.stdout.write(f'   🔸 Stage "{stage.name}": {old_order} → {idx}')
            
            self.stdout.write(self.style.SUCCESS(f'   ✅ Renumbered to: {[s.order_index for s in stages]}'))

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('✅ ALL WORKFLOWS RENUMBERED!'))
        self.stdout.write('=' * 80)
