"""
Debug script: Check what the API actually returns for adam's pending approvals
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "budget_transfer.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.db.models import Q
from approvals.managers import ApprovalManager
from approvals.models import ApprovalWorkflowStageInstance, ApprovalAssignment
from user_management.models import XX_UserGroupMembership

User = get_user_model()

# Get adam user
try:
    adam = User.objects.get(username='adam')
    print(f"✅ Found user: {adam.username} (ID: {adam.id})")
    print(f"   Role: {adam.role}")
    print(f"   User Level: {adam.user_level}")
except User.DoesNotExist:
    print("❌ User 'adam' not found")
    exit(1)

print("\n" + "="*80)
print("STEP 1: Check user's security group memberships and approval permissions")
print("="*80)

user_memberships = XX_UserGroupMembership.objects.filter(
    user=adam,
    is_active=True
).prefetch_related('assigned_roles')

print(f"\nActive memberships: {user_memberships.count()}")
user_approval_groups = []

for membership in user_memberships:
    print(f"\n📋 Group: {membership.security_group.group_name} (ID: {membership.security_group.id})")
    print(f"   Custom abilities: {membership.custom_abilities}")
    
    # Check custom_abilities first
    if membership.custom_abilities and 'APPROVE' in membership.custom_abilities:
        print(f"   ✅ Has APPROVE via custom_abilities")
        user_approval_groups.append(membership.security_group_id)
        continue
    
    # Check role's default_abilities
    has_approve = False
    for role in membership.assigned_roles.all():
        print(f"   📌 Role: {role.role.name} (ID: {role.role_id})")
        print(f"      Active: {role.is_active}")
        print(f"      Abilities: {role.default_abilities}")
        if role.is_active and role.default_abilities and 'APPROVE' in role.default_abilities:
            print(f"      ✅ Has APPROVE via role abilities")
            has_approve = True
    
    if has_approve:
        user_approval_groups.append(membership.security_group_id)

print(f"\n🔑 User's approval groups: {user_approval_groups}")

if not user_approval_groups:
    print("❌ User has NO APPROVE permissions - API will return 403")
    exit(0)

print("\n" + "="*80)
print("STEP 2: Get pending transfers from ApprovalManager")
print("="*80)

pending_transfers = ApprovalManager.get_user_pending_approvals(adam)
print(f"\nInitial pending transfers: {pending_transfers.count()}")
for transfer in pending_transfers:
    print(f"  - {transfer.code} (ID: {transfer.transaction_id}, Group: {transfer.security_group_id})")

print("\n" + "="*80)
print("STEP 3: Filter by user's security group assignments")
print("="*80)

# Get user's roles in each security group
user_roles_by_group = {}
for membership in user_memberships:
    group_id = membership.security_group_id
    user_roles_by_group[group_id] = list(
        membership.assigned_roles.values_list('role_id', flat=True)
    )

print(f"\nUser's roles by group: {user_roles_by_group}")

# Build list of valid transfer IDs
valid_transfer_ids = []

for transfer in pending_transfers:
    workflow_instance = getattr(transfer, 'workflow_instance', None)
    if not workflow_instance:
        print(f"\n❌ Transfer {transfer.code}: No workflow_instance")
        continue
    
    print(f"\n--- Transfer {transfer.code} (ID: {transfer.transaction_id}) ---")
    
    # Get user's active pending assignments for this transfer
    # NOTE: We don't filter by transfer.security_group_id because multi-stage workflows
    # may have stages requiring different security groups than the transfer's origin group
    user_assignments = ApprovalAssignment.objects.filter(
        user=adam,
        status=ApprovalAssignment.STATUS_PENDING,
        stage_instance__workflow_instance=workflow_instance,
        stage_instance__status=ApprovalWorkflowStageInstance.STATUS_ACTIVE
    ).select_related('stage_instance__stage_template')
    
    print(f"User has {user_assignments.count()} pending assignments")
    for assignment in user_assignments:
        print(f"  📌 Stage: {assignment.stage_instance.stage_template.stage_name}")
        print(f"     Status: {assignment.get_status_display()}")
        print(f"     Stage Status: {assignment.stage_instance.get_status_display()}")
    
    # If user has any pending assignments for this transfer, they can see it
    if user_assignments.exists():
        print(f"✅ User has pending assignment - ALLOWED")
        valid_transfer_ids.append(transfer.transaction_id)
    else:
        print(f"❌ No pending assignments - NOT ALLOWED")

print(f"\n" + "="*80)
print(f"FINAL RESULT: Valid transfer IDs: {valid_transfer_ids}")
print("="*80)

# Final filter
final_pending_transfers = pending_transfers.filter(transaction_id__in=valid_transfer_ids)
print(f"\nFinal pending transfers count: {final_pending_transfers.count()}")
for transfer in final_pending_transfers:
    print(f"  ✅ {transfer.code} - {transfer.request_date}")

if not valid_transfer_ids:
    print("\n⚠️  API WILL RETURN EMPTY LIST FOR ADAM")
else:
    print(f"\n✅ API SHOULD RETURN {len(valid_transfer_ids)} TRANSFER(S)")
