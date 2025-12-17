from django.core.management.base import BaseCommand
from approvals.models import ApprovalWorkflowTemplate


class Command(BaseCommand):
    help = 'Check all FAR workflow templates and their stages'

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write("FAR WORKFLOW TEMPLATES")
        self.stdout.write("=" * 70)
        
        far_workflows = ApprovalWorkflowTemplate.objects.filter(code__istartswith='FAR').order_by('code')
        
        for wf in far_workflows:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write(f"Workflow: {wf.code} - {wf.name}")
            self.stdout.write(f"Active: {wf.is_active}")
            
            stages = wf.stages.all().order_by('order_index')
            self.stdout.write(f"\nStages: {stages.count()}")
            
            for stage in stages:
                self.stdout.write(f"\n  🔹 Stage {stage.order_index}: {stage.name}")
                self.stdout.write(f"     Decision Policy: {stage.decision_policy}")
                
                # Check required role
                if stage.required_role:
                    role_name = getattr(stage.required_role, 'role_name', getattr(stage.required_role, 'name', str(stage.required_role)))
                    self.stdout.write(f"     Required Role: {role_name}")
                    # Get users with this role in any security group
                    role_members = getattr(stage.required_role, 'members', None)
                    if role_members:
                        role_assignments = role_members.all()
                        if role_assignments.exists():
                            users = [assignment.user.username for assignment in role_assignments if hasattr(assignment, 'user')]
                            self.stdout.write(f"     Users with this role: {users}")
                        else:
                            self.stdout.write(self.style.WARNING("     ⚠️  NO USERS ASSIGNED TO THIS ROLE!"))
                    else:
                        self.stdout.write(self.style.WARNING("     ⚠️  Role has no members relation"))
                else:
                    self.stdout.write(self.style.WARNING("     ⚠️  NO REQUIRED ROLE!"))
        
        self.stdout.write("\n" + "=" * 70)
