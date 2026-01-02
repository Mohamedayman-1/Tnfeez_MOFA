"""
Test script to verify audit logging system is working correctly.

Run this after the server is started to test audit functionality.
"""
import requests
import json

# Configuration
BASE_URL = "http://127.0.0.1:8000"
USERNAME = "admin"  # Change to your admin username
PASSWORD = "your_password"  # Change to your admin password


def test_audit_system():
    """Test the audit logging system."""
    
    print("=" * 60)
    print("AUDIT LOGGING SYSTEM - VERIFICATION TESTS")
    print("=" * 60)
    
    # Test 1: Login (should create audit logs)
    print("\n1. Testing Login (creates audit log)...")
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login/",
        json={
            "username": USERNAME,
            "password": PASSWORD
        }
    )
    
    if login_response.status_code == 200:
        print("   ✅ Login successful")
        token = login_response.json()['token']
        headers = {"Authorization": f"Bearer {token}"}
    else:
        print(f"   ❌ Login failed: {login_response.text}")
        return
    
    # Test 2: Check if audit log was created for login
    print("\n2. Checking if login was logged...")
    my_activity_response = requests.get(
        f"{BASE_URL}/api/auth/audit/logs/my_activity/",
        headers=headers
    )
    
    if my_activity_response.status_code == 200:
        activity = my_activity_response.json()
        print(f"   ✅ Retrieved {len(activity)} recent activities")
        if activity:
            latest = activity[0]
            print(f"   Latest action: {latest['action_type']} - {latest['action_description']}")
    else:
        print(f"   ❌ Failed to retrieve activity: {my_activity_response.text}")
    
    # Test 3: Check login history
    print("\n3. Checking login history...")
    login_history_response = requests.get(
        f"{BASE_URL}/api/auth/audit/login-history/my_history/",
        headers=headers
    )
    
    if login_history_response.status_code == 200:
        history = login_history_response.json()
        print(f"   ✅ Retrieved {len(history)} login records")
        if history:
            latest = history[0]
            print(f"   Latest login: {latest['login_type']} at {latest['timestamp']}")
            print(f"   IP: {latest.get('ip_address', 'N/A')}")
    else:
        print(f"   ❌ Failed to retrieve login history: {login_history_response.text}")
    
    # Test 4: Get statistics (admin only)
    print("\n4. Getting audit statistics (admin only)...")
    stats_response = requests.get(
        f"{BASE_URL}/api/auth/audit/logs/statistics/?days=30",
        headers=headers
    )
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"   ✅ Statistics retrieved")
        print(f"   Total actions: {stats['total_actions']}")
        print(f"   Actions by type: {stats['actions_by_type']}")
    elif stats_response.status_code == 403:
        print("   ⚠️  Permission denied (user not admin)")
    else:
        print(f"   ❌ Failed to retrieve statistics: {stats_response.text}")
    
    # Test 5: List action types
    print("\n5. Getting available action types...")
    action_types_response = requests.get(
        f"{BASE_URL}/api/auth/audit/logs/action_types/",
        headers=headers
    )
    
    if action_types_response.status_code == 200:
        action_types = action_types_response.json()
        print(f"   ✅ Retrieved action types: {action_types['action_types']}")
    else:
        print(f"   ❌ Failed to retrieve action types: {action_types_response.text}")
    
    # Test 6: List modules
    print("\n6. Getting available modules...")
    modules_response = requests.get(
        f"{BASE_URL}/api/auth/audit/logs/modules/",
        headers=headers
    )
    
    if modules_response.status_code == 200:
        modules = modules_response.json()
        print(f"   ✅ Retrieved modules: {modules['modules']}")
    else:
        print(f"   ❌ Failed to retrieve modules: {modules_response.text}")
    
    # Test 7: Filter by action type
    print("\n7. Testing filters (action_type=LOGIN)...")
    filter_response = requests.get(
        f"{BASE_URL}/api/auth/audit/logs/?action_type=LOGIN",
        headers=headers
    )
    
    if filter_response.status_code == 200:
        results = filter_response.json().get('results', [])
        print(f"   ✅ Retrieved {len(results)} LOGIN actions")
    else:
        print(f"   ❌ Failed to filter: {filter_response.text}")
    
    # Test 8: Test logout (should create audit log)
    print("\n8. Testing Logout (creates audit log)...")
    logout_response = requests.post(
        f"{BASE_URL}/api/auth/logout/",
        headers=headers,
        json={
            "refresh": login_response.json().get('refresh'),
            "access": token
        }
    )
    
    if logout_response.status_code in [200, 205]:
        print("   ✅ Logout successful")
    else:
        print(f"   ❌ Logout failed: {logout_response.text}")
    
    print("\n" + "=" * 60)
    print("AUDIT LOGGING VERIFICATION COMPLETE")
    print("=" * 60)
    print("\nCheck Django admin at: http://127.0.0.1:8000/admin/")
    print("  - user_management/XX_AuditLog")
    print("  - user_management/XX_AuditLoginHistory")


def test_programmatic_logging():
    """
    Test programmatic logging (requires Django shell or integration).
    This is just example code showing what could be tested.
    """
    print("\n" + "=" * 60)
    print("PROGRAMMATIC LOGGING EXAMPLES")
    print("=" * 60)
    
    print("""
To test programmatic logging, run in Django shell:

python manage.py shell

Then execute:

from user_management.audit_utils import AuditLogger
from user_management.models import xx_User

user = xx_User.objects.first()

# Test log action
AuditLogger.log_action(
    user=user,
    action_type='TEST',
    action_description='Testing audit logging system',
    severity='INFO',
    status='SUCCESS',
    metadata={'test': True}
)

# Check if it was created
from user_management.audit_models import XX_AuditLog
latest = XX_AuditLog.objects.latest('timestamp')
print(f"Latest log: {latest.action_description}")
""")


if __name__ == "__main__":
    print("\nBefore running this test:")
    print("1. Make sure the Django server is running (python manage.py runserver)")
    print("2. Update USERNAME and PASSWORD in this script")
    print("3. Run: python test_audit_system.py\n")
    
    response = input("Do you want to run the tests now? (y/n): ")
    if response.lower() == 'y':
        test_audit_system()
        test_programmatic_logging()
    else:
        print("\nUpdate the script configuration and run again.")
