"""
Script to check Finance Manager user's role and user_level
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import xx_User, xx_UserLevel, XX_UserGroupMembership

print("\n=== CHECKING FINANCE MANAGER ROLE ===\n")

# Find Finance Manager user_level
fm_levels = xx_UserLevel.objects.filter(name__icontains='finance')
print(f"User Levels containing 'finance': {fm_levels.count()}")
for level in fm_levels:
    print(f"  - ID: {level.id}, Name: '{level.name}', Order: {level.level_order}")

# Find users with Finance Manager user_level
if fm_levels.exists():
    fm_level = fm_levels.first()
    users = xx_User.objects.filter(user_level=fm_level)
    print(f"\nUsers with user_level '{fm_level.name}' (ID: {fm_level.id}):")
    for user in users:
        print(f"  - Username: {user.username}")
        print(f"    System role: {user.role}")
        print(f"    User level: {user.user_level.name if user.user_level else 'None'}")
        
        # Check security group memberships
        memberships = XX_UserGroupMembership.objects.filter(user=user, is_active=True)
        print(f"    Security Groups: {memberships.count()}")
        for m in memberships:
            roles = m.assigned_roles.all()
            role_names = [r.role.name for r in roles]
            print(f"      - Group: {m.security_group.group_name}")
            print(f"        Assigned roles: {role_names}")
            print(f"        Custom abilities: {m.custom_abilities}")
        print()

# Also check all user_levels
print("\n=== ALL USER LEVELS ===")
all_levels = xx_UserLevel.objects.all().order_by('level_order')
for level in all_levels:
    user_count = xx_User.objects.filter(user_level=level).count()
    print(f"ID: {level.id}, Order: {level.level_order}, Name: '{level.name}', Users: {user_count}")
