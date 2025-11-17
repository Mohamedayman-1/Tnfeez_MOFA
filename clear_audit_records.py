"""
Clear all budget integration audit records (test data cleanup)
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from budget_management.models import xx_budget_integration_audit

# Delete all audit records
count = xx_budget_integration_audit.objects.count()
print(f"Found {count} audit records")

if count > 0:
    confirmation = input(f"Are you sure you want to delete all {count} audit records? (yes/no): ")
    if confirmation.lower() == 'yes':
        deleted_count, _ = xx_budget_integration_audit.objects.all().delete()
        print(f"✓ Successfully deleted {deleted_count} audit records")
    else:
        print("Cancelled - no records deleted")
else:
    print("No audit records found")
