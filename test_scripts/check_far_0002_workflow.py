"""
Deep dive into FAR-0002 workflow and emad's permissions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import xx_User, XX_UserGroupMembership, XX_SecurityGroupRole
from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowInstance, ApprovalWorkflowStageInstance
from django.contrib.contenttypes.models import ContentType

print("\n" + "="*80)
print("🔍 DEEP DIVE: FAR-0002 WORKFLOW ANALYSIS")
print("="*80)

# Get user and transfer
user = xx_User.objects.get(username='emad')
transfer = xx_BudgetTransfer.objects.get(code='FAR-0002')

print(f"\n👤 User: {user.username}")
print(f"   Role: {user.role}")
print(f"   User Level: {user.user_level.name if user.user_level else 'None'}")

# Get membership with roles
membership = XX_UserGroupMembership.objects.filter(
    user=user, 
    security_group_id=1,
    is_active=True
).first()

if membership:
    print(f"\n🔐 Security Group Membership:")
    print(f"   Group: {membership.security_group.group_name}")
    print(f"   Membership ID: {membership.id}")
    
    # Get assigned roles properly
    assigned_role_ids = membership.assigned_roles.all()
    print(f"   Assigned Roles:")
    for group_role in assigned_role_ids:
        print(f"      - {group_role.role.name} (ID: {group_role.id}, Active: {group_role.is_active})")

print(f"\n📄 Transfer: {transfer.code}")
print(f"   Transaction ID: {transfer.transaction_id}")
print(f"   Status: {transfer.status}")
print(f"   Security Group: {transfer.security_group.group_name if transfer.security_group else 'None'}")

# Check workflow instance
content_type = ContentType.objects.get_for_model(xx_BudgetTransfer)
workflow_instances = ApprovalWorkflowInstance.objects.filter(
    content_type=content_type,
    object_id=transfer.transaction_id
)

print(f"\n🔄 Workflow Instances: {workflow_instances.count()}")
for instance in workflow_instances:
    print(f"\n   Instance ID: {instance.id}")
    print(f"   Template: {instance.workflow_template.template_name}")
    print(f"   Status: {instance.get_status_display()}")
    print(f"   Current Stage: {instance.current_stage.stage_name if instance.current_stage else 'None'}")
    
    if instance.current_stage:
        stage = instance.current_stage
        print(f"\n   📍 Current Stage Details:")
        print(f"      Stage Name: {stage.stage_name}")
        print(f"      Stage Order: {stage.stage_order}")
        print(f"      Allowed Roles:")
        
        # Get allowed roles for this stage
        for role in stage.allowed_roles.all():
            print(f"         - {role.name} (ID: {role.id})")
        
        # Check if user's roles match
        user_role_ids = [gr.role.id for gr in assigned_role_ids]
        stage_role_ids = [r.id for r in stage.allowed_roles.all()]
        
        print(f"\n   🔍 Role Matching:")
        print(f"      User's Role IDs: {user_role_ids}")
        print(f"      Stage Required Role IDs: {stage_role_ids}")
        
        has_permission = any(role_id in stage_role_ids for role_id in user_role_ids)
        print(f"      ✅ HAS PERMISSION: {has_permission}")
        
        if not has_permission:
            print(f"\n   ❌ USER DOES NOT HAVE REQUIRED ROLE FOR THIS STAGE")
            print(f"      User needs one of: {[r.name for r in stage.allowed_roles.all()]}")
            print(f"      User has: {[gr.role.name for gr in assigned_role_ids]}")

print("\n" + "="*80)
print("💡 SUMMARY")
print("="*80)

if workflow_instances.exists():
    instance = workflow_instances.first()
    if instance.current_stage:
        user_role_ids = [gr.role.id for gr in membership.assigned_roles.all()]
        stage_role_ids = [r.id for r in instance.current_stage.allowed_roles.all()]
        has_permission = any(role_id in stage_role_ids for role_id in user_role_ids)
        
        if has_permission:
            print("✅ User SHOULD be able to see this transfer")
            print("   Problem might be in frontend filtering or API query")
        else:
            print("❌ User CANNOT see this transfer")
            print("   Reason: User's role not in current workflow stage's allowed roles")
    else:
        print("⚠️ No current stage set - check workflow configuration")
else:
    print("⚠️ No workflow instance found - transfer might be visible to all in security group")

print("="*80 + "\n")
