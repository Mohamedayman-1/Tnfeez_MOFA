"""
Debug: Check why emad can't see FAR-0002 in pending approvals
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import xx_User, XX_UserGroupMembership
from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowInstance, ApprovalAssignment, ApprovalWorkflowStageInstance

print("\n" + "="*80)
print("🔍 DEBUGGING EMAD'S PENDING APPROVALS ACCESS")
print("="*80)

# Get user
user = xx_User.objects.get(username='emad')
print(f"\n👤 User: {user.username}")
print(f"   Role: {user.role}")

# Get user's security group memberships
memberships = XX_UserGroupMembership.objects.filter(
    user=user,
    is_active=True
).prefetch_related('assigned_roles')

print(f"\n🔐 Security Group Memberships:")
user_approval_groups = []
for membership in memberships:
    print(f"\n   Group: {membership.security_group.group_name} (ID: {membership.security_group_id})")
    print(f"   Custom Abilities: {membership.custom_abilities}")
    
    # Check for APPROVE permission
    has_approve = False
    if membership.custom_abilities and 'APPROVE' in membership.custom_abilities:
        has_approve = True
        print(f"   ✅ Has APPROVE in custom_abilities")
    
    # Check assigned roles
    print(f"   Assigned Roles:")
    for group_role in membership.assigned_roles.all():
        print(f"      - {group_role.role.name} (Active: {group_role.is_active})")
        print(f"        Default Abilities: {group_role.default_abilities}")
        if group_role.is_active and group_role.default_abilities and 'APPROVE' in group_role.default_abilities:
            has_approve = True
            print(f"        ✅ Has APPROVE in role abilities")
    
    if has_approve:
        user_approval_groups.append(membership.security_group_id)

print(f"\n📋 User's Approval Groups: {user_approval_groups}")

if not user_approval_groups:
    print("\n❌ PROBLEM: User has NO approval permissions!")
    print("   Solution: Grant APPROVE ability to user's role in security group")
else:
    print(f"\n✅ User has approval access in {len(user_approval_groups)} group(s)")

# Check FAR-0002 transfer
print("\n" + "="*80)
print("📄 CHECKING FAR-0002 TRANSFER")
print("="*80)

transfer = xx_BudgetTransfer.objects.get(code='FAR-0002')
print(f"\nTransfer: {transfer.code} (ID: {transfer.transaction_id})")
print(f"Status: {transfer.status}")
print(f"Security Group: {transfer.security_group.group_name if transfer.security_group else 'None'} (ID: {transfer.security_group_id})")

# Check if transfer's security group matches user's approval groups
if transfer.security_group_id in user_approval_groups:
    print(f"✅ Transfer's security group MATCHES user's approval groups")
else:
    print(f"❌ Transfer's security group NOT in user's approval groups")
    print(f"   Transfer group: {transfer.security_group_id}")
    print(f"   User groups: {user_approval_groups}")

# Check workflow instance
workflow = ApprovalWorkflowInstance.objects.filter(budget_transfer=transfer).first()

if not workflow:
    print("\n❌ NO WORKFLOW INSTANCE FOUND")
else:
    print(f"\n🔄 Workflow Instance:")
    print(f"   Status: {workflow.get_status_display()}")
    print(f"   Current Stage: {workflow.current_stage_template.name if workflow.current_stage_template else 'None'}")
    
    # Check active stage instances
    active_stages = ApprovalWorkflowStageInstance.objects.filter(
        workflow_instance=workflow,
        status=ApprovalWorkflowStageInstance.STATUS_ACTIVE
    )
    
    print(f"\n📍 Active Stage Instances: {active_stages.count()}")
    for stage_inst in active_stages:
        print(f"\n   Stage: {stage_inst.stage_template.name}")
        print(f"   Security Group Required: {stage_inst.stage_template.security_group.group_name if stage_inst.stage_template.security_group else 'None'}")
        
        # Check assignments for this stage
        assignments = ApprovalAssignment.objects.filter(
            stage_instance=stage_inst
        ).select_related('user')
        
        print(f"   Total Assignments: {assignments.count()}")
        
        emad_assignment = assignments.filter(user=user).first()
        
        if emad_assignment:
            print(f"   ✅ Emad HAS assignment")
            print(f"      Status: {emad_assignment.get_status_display()}")
            print(f"      Is Mandatory: {emad_assignment.is_mandatory}")
        else:
            print(f"   ❌ Emad has NO assignment in this stage")
            print(f"\n   All assigned users:")
            for asg in assignments:
                print(f"      - {asg.user.username} (Status: {asg.get_status_display()})")

# Check using ApprovalManager
print("\n" + "="*80)
print("🔧 TESTING ApprovalManager.get_user_pending_approvals()")
print("="*80)

from approvals.managers import ApprovalManager

pending = ApprovalManager.get_user_pending_approvals(user)
print(f"\nPending transfers count: {pending.count()}")

far_0002_in_pending = pending.filter(code='FAR-0002').exists()
print(f"FAR-0002 in pending: {far_0002_in_pending}")

if not far_0002_in_pending and pending.count() > 0:
    print(f"\nOther pending transfers:")
    for t in pending[:5]:
        print(f"   - {t.code} (ID: {t.transaction_id})")

print("\n" + "="*80)
