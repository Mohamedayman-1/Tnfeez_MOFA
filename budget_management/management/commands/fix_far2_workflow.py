from django.core.management.base import BaseCommand
from approvals.models import ApprovalWorkflowTemplate
from user_management.models import XX_SecurityGroup, XX_SecurityGroupRole


class Command(BaseCommand):
    help = 'Fix FAR-2 workflow template by adding required roles to stages'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("FIXING FAR-2 WORKFLOW TEMPLATE")
        self.stdout.write("=" * 80)

        try:
            far2_workflow = ApprovalWorkflowTemplate.objects.get(code='FAR-2')
        except ApprovalWorkflowTemplate.DoesNotExist:
            self.stdout.write(self.style.ERROR('FAR-2 workflow not found'))
            return

        self.stdout.write(f'\n📋 Workflow: {far2_workflow.code} - {far2_workflow.name}')

        # Get Fusion Team security group
        try:
            fusion_group = XX_SecurityGroup.objects.get(group_name__iexact='Fusion tam')
            self.stdout.write(f'✅ Found Fusion Team group: {fusion_group.group_name}')
        except XX_SecurityGroup.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ Fusion Team security group not found!'))
            self.stdout.write('   Please create "Fusion tam" security group first')
            return

        # Get roles
        all_roles = XX_SecurityGroupRole.objects.filter(security_group=fusion_group)
        
        finance_manager_role = None
        unit_head_role = None
        
        for role in all_roles:
            role_str = str(role).lower()
            if 'finance' in role_str or 'manger' in role_str:
                finance_manager_role = role
            elif 'unit' in role_str or 'head' in role_str:
                unit_head_role = role
        
        if not finance_manager_role:
            self.stdout.write(self.style.ERROR('❌ Fusion Team Finance Manager role not found!'))
            return
        if not unit_head_role:
            self.stdout.write(self.style.ERROR('❌ Fusion Team Unit Head role not found!'))
            return
            
        self.stdout.write(f'✅ Found Finance Manager role: {finance_manager_role}')
        self.stdout.write(f'✅ Found Unit Head role: {unit_head_role}')

        # Fix stages
        self.stdout.write('\n📊 Fixing Stages:')
        stages = far2_workflow.stages.all().order_by('order_index')
        
        for stage in stages:
            self.stdout.write(f'\n  🔸 Stage {stage.order_index}: {stage.name}')
            self.stdout.write(f'     Current Required Role: {stage.required_role or "None"}')
            
            # Assign roles based on stage name
            if 'finance' in stage.name.lower():
                stage.required_role = finance_manager_role
                stage.save()
                self.stdout.write(self.style.SUCCESS(f'     ✅ Updated to: {finance_manager_role}'))
            elif 'unit' in stage.name.lower():
                stage.required_role = unit_head_role
                stage.save()
                self.stdout.write(self.style.SUCCESS(f'     ✅ Updated to: {unit_head_role}'))
            else:
                self.stdout.write(self.style.WARNING(f'     ⚠️  Unknown stage type - please update manually'))

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('✅ FAR-2 WORKFLOW FIXED!'))
        self.stdout.write('=' * 80)
        self.stdout.write('\nNow new FAR transactions will correctly assign Fusion Team users!')
