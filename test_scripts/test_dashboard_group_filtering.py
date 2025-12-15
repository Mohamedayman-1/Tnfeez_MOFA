"""
Test script for Dashboard Security Group Filtering.

This script tests that users in the same security group see the same dashboard data.

Usage:
    python test_dashboard_group_filtering.py
"""

import requests
import json
from pprint import pprint

# Configuration
BASE_URL = "http://localhost:8000"
DASHBOARD_URL = f"{BASE_URL}/api/budget/dashboard/"
LOGIN_URL = f"{BASE_URL}/api/auth/login/"

# Test users - update with actual users in the same security group
USER_1 = {"username": "user1", "password": "password1"}
USER_2 = {"username": "user2", "password": "password2"}


def login(username, password):
    """Login and get access token."""
    response = requests.post(
        LOGIN_URL,
        json={"username": username, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        return data.get("access")
    else:
        print(f"❌ Login failed for {username}: {response.status_code}")
        print(response.text)
        return None


def get_dashboard(token, dashboard_type="normal"):
    """Get dashboard data."""
    response = requests.get(
        f"{DASHBOARD_URL}?type={dashboard_type}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Dashboard request failed: {response.status_code}")
        print(response.text)
        return None


def compare_dashboard_data(data1, data2, user1_name, user2_name):
    """Compare dashboard data between two users."""
    print("\n" + "="*70)
    print("DASHBOARD DATA COMPARISON")
    print("="*70)
    
    # Extract normal dashboard data
    normal1 = data1.get("normal", {})
    normal2 = data2.get("normal", {})
    
    # Compare key metrics
    comparisons = [
        ("total_transfers", "Total Transfers"),
        ("approved_transfers", "Approved Transfers"),
        ("rejected_transfers", "Rejected Transfers"),
        ("pending_transfers", "Pending Transfers"),
    ]
    
    all_match = True
    
    for key, label in comparisons:
        val1 = normal1.get(key, 0)
        val2 = normal2.get(key, 0)
        match = val1 == val2
        status = "✅ MATCH" if match else "❌ DIFFERENT"
        
        print(f"\n{label}:")
        print(f"  {user1_name}: {val1}")
        print(f"  {user2_name}: {val2}")
        print(f"  {status}")
        
        if not match:
            all_match = False
    
    print("\n" + "="*70)
    if all_match:
        print("✅ SUCCESS: Both users see the same dashboard data!")
        print("This confirms they are viewing data from the same security group.")
    else:
        print("❌ FAILED: Users see different data.")
        print("This might indicate:")
        print("  1. Users are not in the same security group")
        print("  2. Users have different entity access")
        print("  3. Filtering is not working correctly")
    print("="*70)
    
    return all_match


def test_dashboard_group_filtering():
    """Main test function."""
    print("="*70)
    print("DASHBOARD SECURITY GROUP FILTERING TEST")
    print("="*70)
    
    # Login as User 1
    print(f"\n1️⃣  Logging in as {USER_1['username']}...")
    token1 = login(USER_1['username'], USER_1['password'])
    if not token1:
        print("❌ Cannot proceed without User 1 token")
        return False
    print("✅ Login successful")
    
    # Login as User 2
    print(f"\n2️⃣  Logging in as {USER_2['username']}...")
    token2 = login(USER_2['username'], USER_2['password'])
    if not token2:
        print("❌ Cannot proceed without User 2 token")
        return False
    print("✅ Login successful")
    
    # Get dashboard for User 1
    print(f"\n3️⃣  Getting dashboard for {USER_1['username']}...")
    dashboard1 = get_dashboard(token1)
    if not dashboard1:
        print("❌ Failed to get dashboard for User 1")
        return False
    print("✅ Dashboard retrieved")
    
    # Get dashboard for User 2
    print(f"\n4️⃣  Getting dashboard for {USER_2['username']}...")
    dashboard2 = get_dashboard(token2)
    if not dashboard2:
        print("❌ Failed to get dashboard for User 2")
        return False
    print("✅ Dashboard retrieved")
    
    # Compare the data
    print(f"\n5️⃣  Comparing dashboard data...")
    result = compare_dashboard_data(
        dashboard1,
        dashboard2,
        USER_1['username'],
        USER_2['username']
    )
    
    # Additional details
    if dashboard1.get("normal"):
        print("\n" + "="*70)
        print("ADDITIONAL DETAILS")
        print("="*70)
        
        normal1 = dashboard1["normal"]
        print(f"\nTransfer Breakdown for {USER_1['username']}:")
        print(f"  FAR: {normal1.get('total_transfers_far', 0)}")
        print(f"  AFR: {normal1.get('total_transfers_afr', 0)}")
        print(f"  FAD: {normal1.get('total_transfers_fad', 0)}")
        
        if "pending_transfers_by_level" in normal1:
            print(f"\nPending by Level:")
            for level, count in normal1["pending_transfers_by_level"].items():
                print(f"  {level}: {count}")
    
    return result


def test_smart_dashboard():
    """Test smart dashboard endpoint."""
    print("\n\n" + "="*70)
    print("SMART DASHBOARD TEST")
    print("="*70)
    
    print(f"\n1️⃣  Logging in as {USER_1['username']}...")
    token = login(USER_1['username'], USER_1['password'])
    if not token:
        return False
    
    print(f"\n2️⃣  Getting smart dashboard...")
    dashboard = get_dashboard(token, dashboard_type="smart")
    if not dashboard:
        return False
    
    print("✅ Smart dashboard retrieved")
    
    smart = dashboard.get("smart", {})
    print(f"\nSmart Dashboard Summary:")
    print(f"  Cost Center Groups: {smart.get('performance_metrics', {}).get('cost_center_groups', 0)}")
    print(f"  Account Code Groups: {smart.get('performance_metrics', {}).get('account_code_groups', 0)}")
    print(f"  Total Combinations: {smart.get('performance_metrics', {}).get('total_combinations', 0)}")
    
    return True


def main():
    """Run all tests."""
    try:
        # Test normal dashboard
        test_result = test_dashboard_group_filtering()
        
        # Test smart dashboard
        smart_result = test_smart_dashboard()
        
        # Final summary
        print("\n\n" + "="*70)
        print("FINAL TEST SUMMARY")
        print("="*70)
        print(f"Normal Dashboard: {'✅ PASS' if test_result else '❌ FAIL'}")
        print(f"Smart Dashboard: {'✅ PASS' if smart_result else '❌ FAIL'}")
        print("="*70)
        
        if test_result and smart_result:
            print("\n🎉 All tests passed! Dashboard group filtering is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Please check the output above.")
            
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SETUP INSTRUCTIONS")
    print("="*70)
    print("Before running this test, ensure:")
    print("1. Two users exist and are in the same security group")
    print("2. Update USER_1 and USER_2 credentials in this script")
    print("3. Django server is running on http://localhost:8000")
    print("4. Both users have some budget transfer data")
    print("="*70)
    
    input("\nPress Enter to continue with the test...")
    main()
