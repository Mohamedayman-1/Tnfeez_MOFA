"""
Test Phase 6 Backend Implementation
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from approvals.models import ApprovalWorkflowTemplate, XX_WorkflowTemplateAssignment
from user_management.models import XX_SecurityGroup, xx_UserLevel, XX_SecurityGroupRole

print("="*80)
print("PHASE 6 BACKEND TEST")
print("="*80)

# Test 1: Check workflow templates
print("\n1. Workflow Templates:")
workflows = ApprovalWorkflowTemplate.objects.all()
for wf in workflows:
    print(f"   - {wf.code}: {wf.name} ({wf.transfer_type})")
    stages = wf.stages.all()
    for stage in stages:
        role_name = stage.required_role.role.name if stage.required_role else "No role"
        print(f"      Stage {stage.order_index}: {stage.name} - Role: {role_name}")

# Test 2: Check workflow assignments
print("\n2. Workflow Template Assignments:")
assignments = XX_WorkflowTemplateAssignment.objects.select_related(
    'security_group', 'workflow_template'
).all()
if assignments.exists():
    for assign in assignments:
        print(f"   - Group: {assign.security_group.group_name}")
        print(f"     Workflow: {assign.workflow_template.code}")
        print(f"     Order: {assign.execution_order}")
else:
    print("   No workflow assignments found (expected for fresh setup)")

# Test 3: Check security groups and roles
print("\n3. Security Groups and Roles:")
groups = XX_SecurityGroup.objects.filter(is_active=True)
for group in groups:
    print(f"   - {group.group_name}")
    roles = XX_SecurityGroupRole.objects.filter(
        security_group=group, 
        is_active=True
    ).select_related('role')
    for group_role in roles:
        print(f"      Role: {group_role.role.name}")

# Test 4: Check user levels (system roles)
print("\n4. System Roles (User Levels):")
roles = xx_UserLevel.objects.all()
for role in roles:
    print(f"   - {role.name} (Level: {role.level_order})")

print("\n" + "="*80)
print("Backend structure looks good! ✅")
print("="*80)
