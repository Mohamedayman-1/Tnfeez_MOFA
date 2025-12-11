"""
Test Phase 6 Complete Flow: Backend + API
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from django.contrib.auth import get_user_model
from approvals.models import ApprovalWorkflowTemplate, ApprovalWorkflowStageTemplate, XX_WorkflowTemplateAssignment
from user_management.models import XX_SecurityGroup, xx_UserLevel, XX_SecurityGroupRole
from budget_management.models import xx_BudgetTransfer

User = get_user_model()

print("="*80)
print("PHASE 6 END-TO-END TEST")
print("="*80)

# Test 1: Create a new workflow with roles
print("\n1. Creating Test Workflow with Roles...")
try:
    # Get or create user levels (system roles)
    finance_mgr_role, _ = xx_UserLevel.objects.get_or_create(
        name="Finance Manager Test",
        defaults={"level_order": 10, "description": "Test Finance Manager"}
    )
    unit_head_role, _ = xx_UserLevel.objects.get_or_create(
        name="Unit Head Test",
        defaults={"level_order": 20, "description": "Test Unit Head"}
    )
    
    # Get security group
    group = XX_SecurityGroup.objects.filter(is_active=True).first()
    if not group:
        print("   ❌ No active security group found!")
    else:
        print(f"   Using Security Group: {group.group_name}")
        
        # Create security group roles (link roles to group)
        finance_group_role, created = XX_SecurityGroupRole.objects.get_or_create(
            security_group=group,
            role=finance_mgr_role,
            defaults={"is_active": True}
        )
        print(f"   {'Created' if created else 'Found'} Finance Manager role in group")
        
        unit_head_group_role, created = XX_SecurityGroupRole.objects.get_or_create(
            security_group=group,
            role=unit_head_role,
            defaults={"is_active": True}
        )
        print(f"   {'Created' if created else 'Found'} Unit Head role in group")
        
        # Create workflow template
        workflow, created = ApprovalWorkflowTemplate.objects.get_or_create(
            code="TEST-PHASE6",
            defaults={
                "transfer_type": "FAR",
                "name": "Phase 6 Test Workflow",
                "description": "Testing role-based stages",
                "version": 1,
                "is_active": True
            }
        )
        print(f"   {'Created' if created else 'Found'} Workflow: {workflow.code}")
        
        # Create stages with roles
        stage1, created = ApprovalWorkflowStageTemplate.objects.get_or_create(
            workflow_template=workflow,
            order_index=1,
            defaults={
                "name": "Finance Review",
                "decision_policy": "ALL",
                "allow_reject": True,
                "sla_hours": 24,
                "required_role": finance_group_role  # FK to XX_SecurityGroupRole
            }
        )
        print(f"   {'Created' if created else 'Found'} Stage 1: {stage1.name} (Role: {stage1.required_role.role.name if stage1.required_role else 'None'})")
        
        stage2, created = ApprovalWorkflowStageTemplate.objects.get_or_create(
            workflow_template=workflow,
            order_index=2,
            defaults={
                "name": "Unit Head Approval",
                "decision_policy": "ALL",
                "allow_reject": True,
                "sla_hours": 48,
                "required_role": unit_head_group_role  # FK to XX_SecurityGroupRole
            }
        )
        print(f"   {'Created' if created else 'Found'} Stage 2: {stage2.name} (Role: {stage2.required_role.role.name if stage2.required_role else 'None'})")
        
        print("   ✅ Workflow created successfully!")

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Create workflow assignment
print("\n2. Creating Workflow Assignment...")
try:
    group = XX_SecurityGroup.objects.filter(is_active=True).first()
    workflow = ApprovalWorkflowTemplate.objects.get(code="TEST-PHASE6")
    
    assignment, created = XX_WorkflowTemplateAssignment.objects.get_or_create(
        security_group=group,
        workflow_template=workflow,
        defaults={
            "execution_order": 1,
            "is_active": True
        }
    )
    
    print(f"   {'Created' if created else 'Found'} Assignment:")
    print(f"   - Group: {assignment.security_group.group_name}")
    print(f"   - Workflow: {assignment.workflow_template.code}")
    print(f"   - Order: {assignment.execution_order}")
    print("   ✅ Assignment created!")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Verify serializer output
print("\n3. Testing Serializer Output...")
try:
    from approvals.serializers import ApprovalWorkflowTemplateDetailSerializer
    
    workflow = ApprovalWorkflowTemplate.objects.get(code="TEST-PHASE6")
    serializer = ApprovalWorkflowTemplateDetailSerializer(workflow)
    data = serializer.data
    
    print(f"   Workflow: {data['code']}")
    print(f"   Stages Count: {len(data.get('stages', []))}")
    
    for stage in data.get('stages', []):
        print(f"   Stage {stage['order_index']}: {stage['name']}")
        print(f"      - Required Role: {stage.get('required_role')} (ID)")
        print(f"      - Required Role Name: {stage.get('required_role_name', 'N/A')}")
        print(f"      - Decision Policy: {stage['decision_policy']}")
    
    print("   ✅ Serializer working correctly!")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Summary
print("\n" + "="*80)
print("SUMMARY:")
print("="*80)

workflows = ApprovalWorkflowTemplate.objects.all()
print(f"Total Workflows: {workflows.count()}")

assignments = XX_WorkflowTemplateAssignment.objects.all()
print(f"Total Workflow Assignments: {assignments.count()}")

groups = XX_SecurityGroup.objects.filter(is_active=True)
print(f"Active Security Groups: {groups.count()}")

group_roles = XX_SecurityGroupRole.objects.filter(is_active=True)
print(f"Active Group Roles: {group_roles.count()}")

print("\n✅ Phase 6 Backend Test Complete!")
print("="*80)
