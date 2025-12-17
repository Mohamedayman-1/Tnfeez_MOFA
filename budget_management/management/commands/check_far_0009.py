from django.core.management.base import BaseCommand
from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowInstance, ApprovalWorkflowStageInstance, ApprovalAssignment
from user_management.models import XX_UserGroupMembership


class Command(BaseCommand):
    help = 'Check FAR-0009 transaction workflow and assignments'

    def handle(self, *args, **options):
        try:
            transfer = xx_BudgetTransfer.objects.get(code='FAR-0009')
        except xx_BudgetTransfer.DoesNotExist:
            self.stdout.write(self.style.ERROR('FAR-0009 not found'))
            return

        self.stdout.write("=" * 80)
        self.stdout.write(f"Transaction: {transfer.code} (ID: {transfer.transaction_id})")
        self.stdout.write(f"Security Group: {transfer.security_group.group_name}")
        self.stdout.write(f"Creator: {transfer.requested_by}")
        self.stdout.write(f"Status: {transfer.status}")
        self.stdout.write("=" * 80)

        # Check workflows
        workflows = transfer.workflow_instances.all()
        self.stdout.write(f"\n📋 Workflows: {workflows.count()}")
        for wf in workflows:
            self.stdout.write(f"  - {wf.template.code}: {wf.get_status_display()}")

        # Check stage instances
        self.stdout.write(f"\n📊 Stage Instances:")
        stages = ApprovalWorkflowStageInstance.objects.filter(
            workflow_instance__budget_transfer=transfer
        ).order_by('stage_template__order_index')

        for stage in stages:
            self.stdout.write(f"\n  🔹 Stage {stage.stage_template.order_index}: {stage.stage_template.name}")
            self.stdout.write(f"     Status: {stage.get_status_display()}")
            
            if stage.stage_template.required_role:
                role_display = str(stage.stage_template.required_role)
                self.stdout.write(f"     Required Role: {role_display}")
                
                # Check who SHOULD be assigned (users with this role in this security group)
                eligible_users = XX_UserGroupMembership.objects.filter(
                    security_group=transfer.security_group,
                    assigned_roles=stage.stage_template.required_role,
                    is_active=True
                )
                self.stdout.write(f"     Eligible Users: {eligible_users.count()}")
                for membership in eligible_users:
                    self.stdout.write(f"       - {membership.user.username}")
            else:
                self.stdout.write(f"     Required Role: None")

            # Check actual assignments
            assignments = stage.assignments.all()
            self.stdout.write(f"     Actual Assignments: {assignments.count()}")
            if assignments.count() == 0:
                self.stdout.write(self.style.ERROR("       ⚠️  NO ASSIGNMENTS!"))
            else:
                for assignment in assignments:
                    self.stdout.write(f"       - {assignment.user.username}: {assignment.get_status_display()}")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("✅ CHECK COMPLETE")
        self.stdout.write("=" * 80)
