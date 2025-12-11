"""
Simple check: Does FAR-0002 have a workflow? What stage? What roles required?
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import xx_User, XX_UserGroupMembership
from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowInstance

print("\n" + "="*80)
print("🔍 WORKFLOW CHECK FOR FAR-0002")
print("="*80)

# Get user
user = xx_User.objects.get(username='emad')
membership = XX_UserGroupMembership.objects.get(user=user, security_group_id=1)

print(f"\n👤 User: emad")
print(f"   Assigned Roles in Finance Team:")
for group_role in membership.assigned_roles.all():
    print(f"      - {group_role.role.name} (Role ID: {group_role.role.id})")

# Get transfer
transfer = xx_BudgetTransfer.objects.get(code='FAR-0002')
print(f"\n📄 Transfer: {transfer.code} (ID: {transfer.transaction_id})")
print(f"   Status: {transfer.status}")

# Check workflow
workflow = ApprovalWorkflowInstance.objects.filter(budget_transfer=transfer).first()

if workflow:
    print(f"\n🔄 Workflow Found:")
    print(f"   Template: {workflow.template.name}")
    print(f"   Status: {workflow.get_status_display()}")
    print(f"   Current Stage: {workflow.current_stage_template.name if workflow.current_stage_template else 'None'}")
    
    if workflow.current_stage_template:
        stage = workflow.current_stage_template
        print(f"\n   📍 Stage Details:")
        print(f"      Stage Name: {stage.name}")
        print(f"      Stage Order: {stage.order_index}")
        print(f"      Allowed Roles for this stage:")
        
        # Check security_group and required_user_level
        if stage.security_group:
            print(f"         Security Group: {stage.security_group.group_name}")
        if stage.required_user_level:
            print(f"         Required User Level: {stage.required_user_level.name}")
        if stage.required_role:
            print(f"         Required Role: {stage.required_role}")
        
        # Check permissions
        print(f"\n   🔍 PERMISSION CHECK:")
        print(f"      User's System Role: {user.role}")
        print(f"      User's User Level: {user.user_level.name if user.user_level else 'None'}")
        print(f"      User's Security Group Roles: {[gr.role.name for gr in membership.assigned_roles.all()]}")
        
        # Check if user matches stage requirements
        has_permission = True
        reasons = []
        
        if stage.security_group and stage.security_group.id != membership.security_group.id:
            has_permission = False
            reasons.append(f"Wrong security group (needs {stage.security_group.group_name})")
        
        if stage.required_user_level and (not user.user_level or user.user_level.id != stage.required_user_level.id):
            has_permission = False
            reasons.append(f"Wrong user level (needs {stage.required_user_level.name})")
        
        if stage.required_role and user.role != stage.required_role:
            has_permission = False
            reasons.append(f"Wrong system role (needs {stage.required_role})")
        
        if has_permission:
            print(f"\n   ✅ USER HAS PERMISSION - User should see this transfer!")
            print(f"      Problem is likely in FRONTEND filtering or API query")
        else:
            print(f"\n   ❌ USER MISSING REQUIRED PERMISSIONS")
            print(f"      Reasons: {', '.join(reasons)}")
else:
    print(f"\n⚠️ NO WORKFLOW FOUND")
    print(f"   Transfer might be visible to all users in Finance Team")
    print(f"   Check frontend API call: /api/budget-transfers/")

print("\n" + "="*80)
