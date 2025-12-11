"""
Check why user 'emad' cannot see transfer FAR-0001
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import xx_User, XX_UserGroupMembership, XX_SecurityGroup
from budget_management.models import xx_BudgetTransfer

print("\n" + "="*80)
print("🔍 INVESTIGATING: Why user 'emad' cannot see FAR-0002")
print("="*80)

# Find user emad
try:
    user = xx_User.objects.get(username='emad')
    print(f"\n✅ User Found: {user.username}")
    print(f"   System Role: {user.role}")
    print(f"   User Level: {user.user_level.name if user.user_level else 'None'}")
    print(f"   Is Active: {user.is_active}")
except xx_User.DoesNotExist:
    print("\n❌ ERROR: User 'emad' not found!")
    exit(1)

# Check user's security group memberships
print("\n" + "-"*80)
print("📋 USER'S SECURITY GROUP MEMBERSHIPS:")
print("-"*80)

memberships = XX_UserGroupMembership.objects.filter(
    user=user,
    is_active=True
).select_related('security_group')

if not memberships.exists():
    print("❌ User has NO active security group memberships!")
else:
    for membership in memberships:
        print(f"\n✅ Group: {membership.security_group.group_name} (ID: {membership.security_group.id})")
        print(f"   Active: {membership.is_active}")
        print(f"   Joined: {membership.joined_at}")
        print(f"   Assigned Roles: {membership.assigned_roles}")

user_security_group_ids = list(memberships.values_list('security_group_id', flat=True))
print(f"\n📌 User's Security Group IDs: {user_security_group_ids}")

# Check transfer FAR-0001
print("\n" + "-"*80)
print("📄 TRANSFER FAR-0001 DETAILS:")
print("-"*80)

try:
    transfer = xx_BudgetTransfer.objects.get(code='FAR-0002')
    print(f"\n✅ Transfer Found: {transfer.code}")
    print(f"   Transaction ID: {transfer.transaction_id}")
    print(f"   Status: {transfer.status}")
    print(f"   User ID: {transfer.user_id}")
    print(f"   Requested By: {transfer.requested_by}")
    print(f"   Security Group ID: {transfer.security_group_id}")
    
    if transfer.security_group_id:
        try:
            security_group = XX_SecurityGroup.objects.get(id=transfer.security_group_id)
            print(f"   Security Group Name: {security_group.group_name}")
            print(f"   Security Group Active: {security_group.is_active}")
        except XX_SecurityGroup.DoesNotExist:
            print(f"   Security Group: ❌ INVALID (ID {transfer.security_group_id} not found)")
    else:
        print(f"   Security Group: ❌ NO SECURITY GROUP ASSIGNED")
        
except xx_BudgetTransfer.DoesNotExist:
    print("\n❌ ERROR: Transfer 'FAR-0002' not found!")
    exit(1)

# Analysis
print("\n" + "="*80)
print("🔎 ANALYSIS:")
print("="*80)

if not user_security_group_ids:
    print("\n❌ PROBLEM: User 'emad' has NO security group memberships")
    print("   SOLUTION: Add user to a security group")
    print("   Command: POST /api/auth/security-groups/<group_id>/members/")
elif transfer.security_group_id is None:
    print("\n⚠️  PROBLEM: Transfer FAR-0002 has NO security group assigned")
    print("   IMPACT: Only SuperAdmin users can see this transfer")
    print("   SOLUTION 1: Assign security group to transfer")
    print("   SOLUTION 2: Auto-assign was implemented - check if it's working")
elif transfer.security_group_id not in user_security_group_ids:
    print(f"\n❌ PROBLEM: Access Control Mismatch")
    print(f"   Transfer is in Security Group ID: {transfer.security_group_id}")
    print(f"   User is in Security Group IDs: {user_security_group_ids}")
    print(f"   SOLUTION: Either:")
    print(f"   1. Add user to Security Group ID {transfer.security_group_id}")
    print(f"   2. Reassign transfer to one of user's groups: {user_security_group_ids}")
else:
    print("\n✅ ACCESS SHOULD BE GRANTED")
    print(f"   User is in Security Group {transfer.security_group_id}")
    print(f"   Transfer is assigned to Security Group {transfer.security_group_id}")
    print("\n⚠️  If user still can't see it, check:")
    print("   1. Frontend API call filters")
    print("   2. Approval workflow stage filtering")
    print("   3. Role-based permissions")

# Check if user is SuperAdmin
if user.role == 'superadmin':
    print("\n💡 NOTE: User is SuperAdmin - should see ALL transfers regardless of security group")

print("\n" + "="*80)
