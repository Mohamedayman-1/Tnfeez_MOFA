"""
Script to check all security groups and their assigned roles
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import XX_SecurityGroup, XX_SecurityGroupRole, xx_UserLevel

print("\n" + "="*80)
print("🔍 SECURITY GROUP ROLES ANALYSIS")
print("="*80)

# Get all security groups
groups = XX_SecurityGroup.objects.all()

for group in groups:
    print(f"\n📁 Group: {group.group_name} (ID: {group.id})")
    print(f"   Active: {group.is_active}")
    
    # Get all roles for this group
    group_roles = XX_SecurityGroupRole.objects.filter(
        security_group=group,
        is_active=True
    ).select_related('role')
    
    if group_roles.exists():
        print(f"   Total Roles: {group_roles.count()}")
        print("   Assigned Roles:")
        for gr in group_roles:
            print(f"      - {gr.role.name} (Role ID: {gr.role.id}, XX_SecurityGroupRole ID: {gr.id})")
    else:
        print("   ⚠️  No roles assigned to this group")

print("\n" + "="*80)
print("📊 AVAILABLE ROLES IN SYSTEM:")
print("="*80)

all_roles = xx_UserLevel.objects.all()
for role in all_roles:
    print(f"   {role.id}: {role.name}")

print("\n" + "="*80)
