"""
Delete inactive Finance Manger role from Finance Team
(so you can add it fresh via API)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import XX_SecurityGroupRole

print("\n" + "="*80)
print("🗑️  DELETE INACTIVE FINANCE MANGER ROLE")
print("="*80)

# Get the inactive Finance Manger role (XX_SecurityGroupRole ID: 5)
inactive_role = XX_SecurityGroupRole.objects.get(id=5)

print(f"\nRole to delete:")
print(f"  Group: {inactive_role.security_group.group_name}")
print(f"  Role: {inactive_role.role.name}")
print(f"  Active: {inactive_role.is_active}")
print(f"  XX_SecurityGroupRole ID: {inactive_role.id}")

response = input("\n❓ DELETE this role permanently? (yes/no): ")

if response.lower() == 'yes':
    inactive_role.delete()
    print("\n✅ SUCCESS: Inactive Finance Manger role deleted. You can now add it fresh via API.")
else:
    print("\n❌ Operation cancelled.")

print("\n" + "="*80)
