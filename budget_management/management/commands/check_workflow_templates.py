from django.core.management.base import BaseCommand
from approvals.models import ApprovalWorkflowTemplate, ApprovalWorkflowStageTemplate
from user_management.models import XX_SecurityGroup


class Command(BaseCommand):
    help = 'Check FAR workflow templates configuration'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("CHECKING FAR WORKFLOW TEMPLATES")
        self.stdout.write("=" * 80)

        # Get all FAR-related workflows
        far_workflows = ApprovalWorkflowTemplate.objects.filter(code__icontains='FAR').order_by('code')

        for wf in far_workflows:
            self.stdout.write(f'\n📋 Workflow: {wf.code} - {wf.name}')
            self.stdout.write(f'   Active: {wf.is_active}')
            
            # Get stages
            stages = wf.stages.all().order_by('order_index')
            self.stdout.write(f'   Stages: {stages.count()}')
            
            for stage in stages:
                self.stdout.write(f'\n     🔸 Stage {stage.order_index}: {stage.name}')
                if stage.required_role:
                    self.stdout.write(f'        Required Role: {stage.required_role}')
                    self.stdout.write(f'        Role Security Group: {stage.required_role.security_group.group_name}')
                else:
                    self.stdout.write(self.style.ERROR('        ⚠️  NO REQUIRED ROLE!'))

        # Check Fusion Team security group and roles
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('FUSION TEAM CONFIGURATION')
        self.stdout.write('=' * 80)
        
        fusion_groups = XX_SecurityGroup.objects.filter(group_name__icontains='fusion')
        for group in fusion_groups:
            self.stdout.write(f'\n🔹 Security Group: {group.group_name} (ID: {group.id})')
            
            # Check roles
            roles = group.group_roles.all()
            self.stdout.write(f'   Roles: {roles.count()}')
            for role in roles:
                self.stdout.write(f'     - {role} (ID: {role.id})')

        self.stdout.write('\n' + '=' * 80)
