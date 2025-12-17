from django.core.management.base import BaseCommand
from approvals.models import ApprovalWorkflowTemplate
from user_management.models import XX_SecurityGroup, XX_SecurityGroupRole


class Command(BaseCommand):
    help = 'Fix far2222 workflow Stage 10000 - change from Finance Team to Fusion Team role'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("FIXING far2222 WORKFLOW")
        self.stdout.write("=" * 80)

        try:
            far2222_workflow = ApprovalWorkflowTemplate.objects.get(code='far2222')
        except ApprovalWorkflowTemplate.DoesNotExist:
            self.stdout.write(self.style.ERROR('far2222 workflow not found'))
            return

        self.stdout.write(f'\n📋 Workflow: {far2222_workflow.code}')

        # Get Fusion Team Finance Manager role
        try:
            fusion_group = XX_SecurityGroup.objects.get(group_name__iexact='Fusion tam')
            fusion_roles = XX_SecurityGroupRole.objects.filter(security_group=fusion_group)
            
            fusion_finance_manager = None
            for role in fusion_roles:
                if 'finance' in str(role).lower() or 'manger' in str(role).lower():
                    fusion_finance_manager = role
                    break
            
            if not fusion_finance_manager:
                self.stdout.write(self.style.ERROR('Fusion Team Finance Manager role not found'))
                return
                
            self.stdout.write(f'✅ Found role: {fusion_finance_manager}')
        except XX_SecurityGroup.DoesNotExist:
            self.stdout.write(self.style.ERROR('Fusion Team security group not found'))
            return

        # Fix Stage 10000
        stage_10000 = far2222_workflow.stages.filter(order_index=10000).first()
        
        if not stage_10000:
            self.stdout.write(self.style.WARNING('Stage 10000 not found in far2222 workflow'))
            return

        self.stdout.write(f'\n🔸 Stage 10000: {stage_10000.name}')
        self.stdout.write(f'   Current Role: {stage_10000.required_role}')
        
        stage_10000.required_role = fusion_finance_manager
        stage_10000.save()
        
        self.stdout.write(self.style.SUCCESS(f'   ✅ Updated to: {fusion_finance_manager}'))

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('✅ far2222 WORKFLOW FIXED!'))
        self.stdout.write('=' * 80)
