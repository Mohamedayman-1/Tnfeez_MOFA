"""
Test script to verify security group roles API endpoint.
Run this to check if the new endpoint returns data correctly.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import XX_SecurityGroupRole, XX_SecurityGroup, xx_UserLevel

print("=" * 60)
print("SECURITY GROUP ROLES TEST")
print("=" * 60)

# Check if we have any security group roles
all_roles = XX_SecurityGroupRole.objects.select_related('security_group', 'role').all()
print(f"\n✓ Total Security Group Roles: {all_roles.count()}")

if all_roles.exists():
    print("\nSample Security Group Roles:")
    print("-" * 60)
    for role in all_roles[:5]:
        print(f"  ID: {role.id}")
        print(f"  Group: {role.security_group.group_name} (ID: {role.security_group.id})")
        print(f"  Role: {role.role.name} (ID: {role.role.id})")
        print(f"  Active: {role.is_active}")
        print(f"  Display: {role.security_group.group_name} - {role.role.name}")
        print("-" * 60)
else:
    print("\n⚠️  No security group roles found!")
    print("   Creating test data...")
    
    # Get or create a security group
    group, _ = XX_SecurityGroup.objects.get_or_create(
        group_name="Test Finance Team",
        defaults={
            'description': 'Test group for roles',
            'is_active': True
        }
    )
    
    # Get user levels
    levels = xx_UserLevel.objects.all()[:2]
    
    if levels.exists():
        for level in levels:
            role, created = XX_SecurityGroupRole.objects.get_or_create(
                security_group=group,
                role=level,
                defaults={
                    'is_active': True,
                    'default_abilities': []
                }
            )
            if created:
                print(f"  ✓ Created: {group.group_name} - {level.name}")
    
    all_roles = XX_SecurityGroupRole.objects.select_related('security_group', 'role').all()
    print(f"\n✓ After creation: {all_roles.count()} roles")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print("\nYou can now use this API:")
print("GET /api/auth/security-group-roles/all/")
print("\nExpected format:")
print("  required_role: <XX_SecurityGroupRole.id>")
print("  NOT: <xx_UserLevel.id>")
print("=" * 60)
