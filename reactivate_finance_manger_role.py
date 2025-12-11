"""
Reactivate Finance Manger role in Finance Team
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import XX_SecurityGroupRole

print("\n" + "="*80)
print("🔄 REACTIVATING FINANCE MANGER ROLE IN FINANCE TEAM")
print("="*80)

# Get the inactive Finance Manger role (XX_SecurityGroupRole ID: 5)
inactive_role = XX_SecurityGroupRole.objects.get(id=5)

print(f"\nCurrent Status:")
print(f"  Group: {inactive_role.security_group.group_name}")
print(f"  Role: {inactive_role.role.name}")
print(f"  Active: {inactive_role.is_active}")

response = input("\n❓ Reactivate this role? (yes/no): ")

if response.lower() == 'yes':
    inactive_role.is_active = True
    inactive_role.save()
    print("\n✅ SUCCESS: Finance Manger role has been reactivated in Finance Team!")
else:
    print("\n❌ Operation cancelled.")

print("\n" + "="*80)
