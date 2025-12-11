"""
Debug: Check why adam (unithead) can see FAR-0002
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import xx_User, XX_UserGroupMembership
from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowInstance, ApprovalAssignment, ApprovalWorkflowStageInstance

print("\n" + "="*80)
print("🔍 DEBUGGING ADAM'S ACCESS TO FAR-0002")
print("="*80)

# Get adam user
try:
    adam = xx_User.objects.get(username='adam')
    print(f"\n👤 User: {adam.username}")
    print(f"   Role: {adam.role}")
    print(f"   User Level: {adam.user_level.name if adam.user_level else 'None'}")
except xx_User.DoesNotExist:
    print("\n❌ User 'adam' not found. Searching for users with 'adam' in username...")
    adams = xx_User.objects.filter(username__icontains='adam')
    if adams.exists():
        for u in adams:
            print(f"   Found: {u.username} (ID: {u.id})")
        adam = adams.first()
        print(f"\nUsing: {adam.username}")
    else:
        print("No user found with 'adam' in username")
        exit()

# Get user's security group memberships
memberships = XX_UserGroupMembership.objects.filter(
    user=adam,
    is_active=True
).prefetch_related('assigned_roles')

print(f"\n🔐 Security Group Memberships:")
for membership in memberships:
    print(f"\n   Group: {membership.security_group.group_name} (ID: {membership.security_group_id})")
    print(f"   Custom Abilities: {membership.custom_abilities}")
    
    # Check assigned roles
    print(f"   Assigned Roles:")
    for group_role in membership.assigned_roles.all():
        print(f"      - {group_role.role.name} (Active: {group_role.is_active})")
        print(f"        Default Abilities: {group_role.default_abilities}")

# Check FAR-0002 transfer
print("\n" + "="*80)
print("📄 CHECKING FAR-0002 TRANSFER & WORKFLOW")
print("="*80)

transfer = xx_BudgetTransfer.objects.get(code='FAR-0002')
print(f"\nTransfer: {transfer.code} (ID: {transfer.transaction_id})")
print(f"Status: {transfer.status}")
print(f"Security Group: {transfer.security_group.group_name if transfer.security_group else 'None'} (ID: {transfer.security_group_id})")

# Check workflow instance
workflow = ApprovalWorkflowInstance.objects.filter(budget_transfer=transfer).first()

if not workflow:
    print("\n❌ NO WORKFLOW INSTANCE FOUND")
else:
    print(f"\n🔄 Workflow Instance:")
    print(f"   Status: {workflow.get_status_display()}")
    print(f"   Current Stage: {workflow.current_stage_template.name if workflow.current_stage_template else 'None'}")
    
    # Check ALL stage instances (not just active)
    all_stages = workflow.stage_instances.all().order_by('stage_template__order_index')
    
    print(f"\n📍 All Stage Instances: {all_stages.count()}")
    for stage_inst in all_stages:
        print(f"\n   Stage: {stage_inst.stage_template.name} (Order: {stage_inst.stage_template.order_index})")
        print(f"   Status: {stage_inst.get_status_display()}")
        print(f"   Security Group Required: {stage_inst.stage_template.security_group.group_name if stage_inst.stage_template.security_group else 'None'}")
        
        # Check assignments for this stage
        assignments = stage_inst.assignments.all()
        print(f"   Total Assignments: {assignments.count()}")
        
        adam_assignment = assignments.filter(user=adam).first()
        
        if adam_assignment:
            print(f"   ✅ Adam HAS assignment")
            print(f"      Status: {adam_assignment.get_status_display()}")
            print(f"      Is Mandatory: {adam_assignment.is_mandatory}")
        else:
            print(f"   ❌ Adam has NO assignment in this stage")
        
        print(f"   All assigned users:")
        for asg in assignments:
            print(f"      - {asg.user.username}: {asg.get_status_display()}")

# Check if adam is in transfer's security group
print("\n" + "="*80)
print("🔍 SECURITY GROUP MATCH CHECK")
print("="*80)

user_groups = memberships.values_list('security_group_id', flat=True)
print(f"\nAdam's security groups: {list(user_groups)}")
print(f"Transfer's security group: {transfer.security_group_id}")

if transfer.security_group_id in user_groups:
    print(f"✅ Adam IS in transfer's security group")
else:
    print(f"❌ Adam is NOT in transfer's security group")

# Check using ApprovalManager
print("\n" + "="*80)
print("🔧 TESTING ApprovalManager.get_user_pending_approvals()")
print("="*80)

from approvals.managers import ApprovalManager

pending = ApprovalManager.get_user_pending_approvals(adam)
print(f"\nPending transfers count: {pending.count()}")

far_0002_in_pending = pending.filter(code='FAR-0002').exists()
print(f"FAR-0002 in adam's pending: {far_0002_in_pending}")

if far_0002_in_pending:
    print(f"\n⚠️  ADAM CAN SEE FAR-0002!")
    print(f"This means adam has a pending assignment in an active stage")

print("\n" + "="*80)
