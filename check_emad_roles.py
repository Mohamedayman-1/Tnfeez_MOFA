"""
Check emad's role assignments in Finance Team
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import xx_User, XX_UserGroupMembership, XX_SecurityGroupRole

print("\n" + "="*80)
print("🔍 CHECKING EMAD'S ROLE ASSIGNMENTS")
print("="*80)

user = xx_User.objects.get(username='emad')
membership = XX_UserGroupMembership.objects.get(user=user, security_group_id=1)

print(f"\nUser: {user.username}")
print(f"Security Group: {membership.security_group.group_name}")
print(f"Membership ID: {membership.id}")
print(f"assigned_roles (raw): {membership.assigned_roles}")
print(f"assigned_roles type: {type(membership.assigned_roles)}")

# Check what roles are available in the group
available_roles = XX_SecurityGroupRole.objects.filter(
    security_group_id=1,
    is_active=True
).select_related('role')

print(f"\n📋 Available Roles in Finance Team:")
for role in available_roles:
    print(f"   - {role.role.name} (XX_SecurityGroupRole ID: {role.id}, Role ID: {role.role.id})")

# Try to get assigned roles if they exist
if membership.assigned_roles:
    print(f"\n✅ User HAS assigned roles: {membership.assigned_roles}")
    if isinstance(membership.assigned_roles, list):
        for role_id in membership.assigned_roles:
            try:
                group_role = XX_SecurityGroupRole.objects.get(id=role_id)
                print(f"   - {group_role.role.name}")
            except XX_SecurityGroupRole.DoesNotExist:
                print(f"   - ❌ Invalid role ID: {role_id}")
else:
    print(f"\n❌ User has NO assigned roles (assigned_roles is NULL or empty)")
    print("\nSOLUTION: Assign roles to user via:")
    print(f"PATCH /api/auth/security-groups/1/members/{membership.id}/")
    print(f'Body: {{"assigned_roles": [1]}}  # Use XX_SecurityGroupRole IDs')

print("\n" + "="*80)
