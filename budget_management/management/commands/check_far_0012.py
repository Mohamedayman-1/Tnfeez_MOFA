from django.core.management.base import BaseCommand
from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowInstance, ApprovalWorkflowStageInstance, ApprovalAssignment


class Command(BaseCommand):
    help = 'Check FAR-0012 transaction workflows and assignments'

    def handle(self, *args, **options):
        try:
            transfer = xx_BudgetTransfer.objects.get(code='FAR-0012')
        except xx_BudgetTransfer.DoesNotExist:
            self.stdout.write(self.style.ERROR('FAR-0012 not found'))
            return

        self.stdout.write("=" * 80)
        self.stdout.write(f"CHECKING FAR-0012 (NEWLY CREATED)")
        self.stdout.write("=" * 80)
        self.stdout.write(f"\n📋 Transaction: {transfer.code} (ID: {transfer.transaction_id})")
        self.stdout.write(f"   Security Group: {transfer.security_group.group_name}")
        self.stdout.write(f"   Creator: {transfer.requested_by}")
        self.stdout.write(f"   Status: {transfer.status}")
        self.stdout.write(f"   Created: {transfer.request_date}")

        # Check workflows
        workflows = transfer.workflow_instances.all()
        self.stdout.write(f"\n📊 Workflows: {workflows.count()}")

        for wf in workflows:
            self.stdout.write(f"\n  🔹 Workflow: {wf.template.code} - {wf.get_status_display()}")
            
            # Check stages
            stages = wf.stage_instances.all().order_by('stage_template__order_index')
            self.stdout.write(f"     Stages: {stages.count()}")
            
            for stage in stages:
                self.stdout.write(f"\n     📍 Stage {stage.stage_template.order_index}: {stage.stage_template.name}")
                self.stdout.write(f"        Status: {stage.get_status_display()}")
                
                if stage.stage_template.required_role:
                    self.stdout.write(f"        Required Role: {stage.stage_template.required_role}")
                else:
                    self.stdout.write(self.style.WARNING("        ⚠️  NO REQUIRED ROLE"))
                
                # Check assignments
                assignments = stage.assignments.all()
                self.stdout.write(f"        Assignments: {assignments.count()}")
                
                if assignments.count() == 0:
                    self.stdout.write(self.style.ERROR("          ❌ NO ASSIGNMENTS!"))
                else:
                    for assignment in assignments:
                        self.stdout.write(f"          ✅ {assignment.user.username}: {assignment.get_status_display()}")

        self.stdout.write("\n" + "=" * 80)
        
        # Summary
        total_assignments = ApprovalAssignment.objects.filter(
            stage_instance__workflow_instance__budget_transfer=transfer
        ).count()
        
        fusion_assignments = ApprovalAssignment.objects.filter(
            stage_instance__workflow_instance__budget_transfer=transfer,
            stage_instance__stage_template__required_role__security_group__group_name__icontains='fusion'
        ).count()
        
        self.stdout.write(f"\n📊 SUMMARY:")
        self.stdout.write(f"   Total Assignments: {total_assignments}")
        self.stdout.write(f"   Fusion Team Assignments: {fusion_assignments}")
        
        if fusion_assignments > 0:
            self.stdout.write(self.style.SUCCESS("\n✅ SUCCESS! Fusion Team users are assigned!"))
            
            # List Fusion Team assignments
            fusion_asgs = ApprovalAssignment.objects.filter(
                stage_instance__workflow_instance__budget_transfer=transfer,
                stage_instance__stage_template__required_role__security_group__group_name__icontains='fusion'
            )
            self.stdout.write(f"\n📋 Fusion Team Approvers:")
            for asg in fusion_asgs:
                self.stdout.write(f"   - {asg.user.username} (Stage: {asg.stage_instance.stage_template.name})")
        else:
            self.stdout.write(self.style.ERROR("\n❌ PROBLEM! No Fusion Team assignments found!"))
        
        self.stdout.write("\n" + "=" * 80)
