"""
Fix: Activate the workflow stages for FAR-0002
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from budget_management.models import xx_BudgetTransfer
from approvals.managers import ApprovalManager

print("\n" + "="*80)
print("🔧 ACTIVATING WORKFLOW FOR FAR-0002")
print("="*80)

transfer = xx_BudgetTransfer.objects.get(code='FAR-0002')
print(f"\nTransfer: {transfer.code} (ID: {transfer.transaction_id})")
print(f"Status: {transfer.status}")

workflow = transfer.workflow_instance

if not workflow:
    print("\n❌ No workflow instance found!")
    print("Creating workflow...")
    # Initialize workflow
    result = ApprovalManager.initiate_workflow(transfer)
    print(f"Workflow creation result: {result}")
else:
    print(f"\n✅ Workflow exists: {workflow.template.name}")
    print(f"   Status: {workflow.get_status_display()}")
    print(f"   Current Stage: {workflow.current_stage_template.name if workflow.current_stage_template else 'None'}")
    
    # Check stage instances
    stage_instances = workflow.stage_instances.all()
    print(f"\n📍 Stage Instances: {stage_instances.count()}")
    
    for si in stage_instances:
        print(f"\n   Stage: {si.stage_template.name}")
        print(f"   Status: {si.get_status_display()}")
        print(f"   Order: {si.stage_template.order_index}")
        
        # Check assignments
        assignments = si.assignments.all()
        print(f"   Assignments: {assignments.count()}")
        for asg in assignments:
            print(f"      - {asg.user.username}: {asg.get_status_display()}")
    
    # If no active stages, activate the first one
    active_count = stage_instances.filter(status='active').count()
    if active_count == 0:
        print(f"\n⚠️  No active stages! Activating first stage...")
        try:
            ApprovalManager._activate_next_stage_internal(transfer, workflow)
            print("✅ First stage activated!")
            
            # Refresh and show status
            workflow.refresh_from_db()
            print(f"\nUpdated Status:")
            print(f"   Current Stage: {workflow.current_stage_template.name if workflow.current_stage_template else 'None'}")
            
            active_stages = workflow.stage_instances.filter(status='active')
            print(f"   Active Stages: {active_stages.count()}")
            for si in active_stages:
                print(f"      - {si.stage_template.name}")
                assignments = si.assignments.filter(status='pending')
                print(f"        Pending Assignments: {assignments.count()}")
                for asg in assignments:
                    print(f"           * {asg.user.username}")
        except Exception as e:
            print(f"❌ Error activating stage: {e}")
            import traceback
            traceback.print_exc()

print("\n" + "="*80)
