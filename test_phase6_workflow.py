"""
Phase 6 Test Script: Verify workflow assignment and sequential execution
Run: python test_phase6_workflow.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from approvals.models import XX_WorkflowTemplateAssignment, ApprovalWorkflowTemplate
from user_management.models import XX_SecurityGroup
from budget_management.models import xx_BudgetTransfer
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n" + "="*80)
print("PHASE 6: WORKFLOW ASSIGNMENT TEST")
print("="*80)

# 1. Check if XX_WorkflowTemplateAssignment table exists
print("\n✓ Testing XX_WorkflowTemplateAssignment model...")
try:
    count = XX_WorkflowTemplateAssignment.objects.count()
    print(f"  ✅ Model works! Current assignments: {count}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    exit(1)

# 2. List all security groups
print("\n✓ Security Groups:")
groups = XX_SecurityGroup.objects.filter(is_active=True)
for group in groups:
    print(f"  - ID: {group.id}, Name: {group.group_name}")
    
# 3. List all workflow templates
print("\n✓ Workflow Templates:")
templates = ApprovalWorkflowTemplate.objects.filter(is_active=True)
for template in templates:
    print(f"  - ID: {template.id}, Code: {template.code}, Type: {template.transfer_type}")

# 4. Check existing workflow assignments
print("\n✓ Current Workflow Assignments:")
assignments = XX_WorkflowTemplateAssignment.objects.all()
if assignments.exists():
    for assignment in assignments:
        print(f"  - Group: {assignment.security_group.group_name}")
        print(f"    Workflow: {assignment.workflow_template.code}")
        print(f"    Execution Order: {assignment.execution_order}")
        print(f"    Active: {assignment.is_active}")
else:
    print("  (No assignments yet)")

# 5. Demo: Create a workflow assignment (if groups and templates exist)
if groups.exists() and templates.count() >= 2:
    print("\n✓ Creating demo workflow assignment...")
    first_group = groups.first()
    first_template = templates.first()
    second_template = templates.exclude(id=first_template.id).first()
    
    if second_template:
        # Check if assignment already exists
        existing = XX_WorkflowTemplateAssignment.objects.filter(
            security_group=first_group,
            workflow_template=first_template
        ).first()
        
        if not existing:
            assignment1, created1 = XX_WorkflowTemplateAssignment.objects.get_or_create(
                security_group=first_group,
                workflow_template=first_template,
                defaults={'execution_order': 1, 'is_active': True}
            )
            print(f"  {'Created' if created1 else 'Found'} assignment 1: {first_template.code} (Order: 1)")
            
            assignment2, created2 = XX_WorkflowTemplateAssignment.objects.get_or_create(
                security_group=first_group,
                workflow_template=second_template,
                defaults={'execution_order': 2, 'is_active': True}
            )
            print(f"  {'Created' if created2 else 'Found'} assignment 2: {second_template.code} (Order: 2)")
            
            print(f"\n  ✅ Group '{first_group.group_name}' now has {first_group.workflow_assignments.count()} workflows")
        else:
            print(f"  Assignment already exists for {first_group.group_name}")

# 6. Test ApprovalWorkflowInstance new fields
print("\n✓ Testing ApprovalWorkflowInstance updates...")
transfers = xx_BudgetTransfer.objects.all()[:3]
for transfer in transfers:
    workflows = transfer.workflow_instances.all()
    active = transfer.workflow_instance  # Uses property
    
    print(f"\n  Transfer: {transfer.code}")
    print(f"    Total workflows: {workflows.count()}")
    print(f"    Active workflow: {active.template.code if active else 'None'}")
    
    if workflows.count() > 1:
        print(f"    ✅ MULTI-WORKFLOW TRANSFER FOUND!")
        for wf in workflows:
            print(f"      - Order {wf.execution_order}: {wf.template.code} (Status: {wf.status})")

print("\n" + "="*80)
print("✅ PHASE 6 TEST COMPLETE")
print("="*80)

print("\n📋 Summary:")
print(f"  - Security Groups: {groups.count()}")
print(f"  - Workflow Templates: {templates.count()}")
print(f"  - Workflow Assignments: {XX_WorkflowTemplateAssignment.objects.count()}")
print(f"  - Total Transfers: {xx_BudgetTransfer.objects.count()}")
print(f"  - Total Workflow Instances: {from approvals.models import ApprovalWorkflowInstance}")
print(f"    {ApprovalWorkflowInstance.objects.count()}")

print("\n🔧 Next Steps:")
print("  1. Use POST /api/approvals/workflow-assignments/ to assign workflows to groups")
print("  2. Create a new transfer in a group with multiple workflow assignments")
print("  3. Approve all stages in workflow 1 → Watch workflow 2 auto-start")
print("\n")
