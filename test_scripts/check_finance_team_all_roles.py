"""
Check ALL roles (including inactive) in Finance Team
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from user_management.models import XX_SecurityGroup, XX_SecurityGroupRole

print("\n" + "="*80)
print("🔍 ALL ROLES IN FINANCE TEAM (INCLUDING INACTIVE)")
print("="*80)

finance_team = XX_SecurityGroup.objects.get(group_name="Finance Team")

# Get ALL roles (active and inactive)
all_roles = XX_SecurityGroupRole.objects.filter(
    security_group=finance_team
).select_related('role')

print(f"\nTotal roles (active + inactive): {all_roles.count()}\n")

for gr in all_roles:
    status = "✅ ACTIVE" if gr.is_active else "❌ INACTIVE"
    print(f"{status} - {gr.role.name} (Role ID: {gr.role.id}, XX_SecurityGroupRole ID: {gr.id})")

print("\n" + "="*80)
