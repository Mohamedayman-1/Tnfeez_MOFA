from django.core.management.base import BaseCommand
from approvals.models import ApprovalWorkflowTemplate


class Command(BaseCommand):
    help = 'Fix duplicate workflow stages in FAR workflow'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("FIXING DUPLICATE WORKFLOW STAGES")
        self.stdout.write("=" * 60)
        
        # Get FAR workflow
        try:
            far = ApprovalWorkflowTemplate.objects.get(code='FAR')
        except ApprovalWorkflowTemplate.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ FAR workflow not found!'))
            return
        
        # Show current stages
        self.stdout.write("\n📋 Current FAR workflow stages:")
        stages = far.stages.all().order_by('order_index')
        for stage in stages:
            self.stdout.write(f"  • Order {stage.order_index}: {stage.name} (ID: {stage.id})")
        
        # Check which stages are used
        from approvals.models import ApprovalWorkflowStageInstance
        
        self.stdout.write("\n📊 Stage usage:")
        for stage in stages:
            usage_count = ApprovalWorkflowStageInstance.objects.filter(stage_template_id=stage.id).count()
            self.stdout.write(f"  • Order {stage.order_index} ({stage.name}, ID:{stage.id}): {usage_count} instances")
        
        # Find unused stages with low order_index (the newly created duplicates)
        unused_stages = []
        for stage in stages:
            if stage.order_index < 10 and ApprovalWorkflowStageInstance.objects.filter(stage_template_id=stage.id).count() == 0:
                unused_stages.append(stage)
        
        if not unused_stages:
            self.stdout.write(self.style.SUCCESS('\n✅ No unused duplicate stages found!'))
            # Check if we need to rename high order_index stages
            high_order_stages = far.stages.filter(order_index__gte=10000).order_by('order_index')
            if high_order_stages.exists():
                self.stdout.write("\n⚠️  However, stages with high order_index need renaming:")
                for idx, stage in enumerate(high_order_stages, start=1):
                    self.stdout.write(f"  Renaming Order {stage.order_index} to Order {idx}")
                    stage.order_index = idx
                    stage.save()
                self.stdout.write(self.style.SUCCESS(f'\n✅ Renamed {high_order_stages.count()} stages!'))
            return
        
        self.stdout.write(f"\n⚠️  Found {len(unused_stages)} unused duplicate stages to delete:")
        for stage in unused_stages:
            self.stdout.write(f"  • Order {stage.order_index}: {stage.name} (ID: {stage.id})")
        
        # Delete unused stages
        deleted_count = 0
        for stage in unused_stages:
            stage.delete()
            deleted_count += 1
        self.stdout.write(self.style.SUCCESS(f'\n✅ Deleted {deleted_count} unused stages!'))
        
        # Now rename the remaining high order_index stages to correct order
        high_order_stages = far.stages.filter(order_index__gte=10000).order_by('order_index')
        if high_order_stages.exists():
            self.stdout.write(f"\n🔄 Renaming {high_order_stages.count()} stages to correct order:")
            for idx, stage in enumerate(high_order_stages, start=1):
                old_order = stage.order_index
                stage.order_index = idx
                stage.save()
                self.stdout.write(f"  • {stage.name}: Order {old_order} → Order {idx}")
            self.stdout.write(self.style.SUCCESS(f'\n✅ Renamed {high_order_stages.count()} stages!'))
        
        # Show final stages
        self.stdout.write(f"\n📋 Final FAR workflow stages:")
        final_stages = far.stages.all().order_by('order_index')
        for stage in final_stages:
            self.stdout.write(f"  • Order {stage.order_index}: {stage.name} (ID: {stage.id})")
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS('✅ FIX COMPLETE!'))
        self.stdout.write("=" * 60)
