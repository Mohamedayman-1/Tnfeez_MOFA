"""
Quick test script for User Profile API endpoints.
Run this to verify the endpoints are working correctly.

Usage:
    python test_user_profile_api.py
"""

import requests
import json
from pprint import pprint

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/auth"

# Test credentials (update with actual credentials)
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpass123"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "adminpass123"


def login(username, password):
    """Login and get access token."""
    response = requests.post(
        f"{API_BASE}/login/",
        json={"username": username, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        return data.get("access")
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None


def test_get_own_profile(token):
    """Test getting current user's profile."""
    print("\n" + "="*60)
    print("TEST 1: Get Own Profile")
    print("="*60)
    
    response = requests.get(
        f"{API_BASE}/profile/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ SUCCESS - Profile Retrieved")
        print("\nUser Info:")
        pprint(data.get("user_info"))
        print(f"\nTotal Groups: {data['summary']['total_group_memberships']}")
        print(f"Abilities: {', '.join(data['summary']['unique_abilities_from_groups'])}")
        return True
    else:
        print(f"❌ FAILED")
        print(response.text)
        return False


def test_get_simple_profile(token):
    """Test getting simple profile."""
    print("\n" + "="*60)
    print("TEST 2: Get Simple Profile")
    print("="*60)
    
    response = requests.get(
        f"{API_BASE}/profile/simple/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ SUCCESS - Simple Profile Retrieved")
        print(f"\nUsername: {data['username']}")
        print(f"Role: {data['role']}")
        print(f"User Level: {data['user_level']}")
        print(f"Groups: {', '.join([g['group_name'] for g in data['groups']])}")
        print(f"Is Assigned to Groups: {data['is_assigned_to_groups']}")
        return True
    else:
        print(f"❌ FAILED")
        print(response.text)
        return False


def test_get_other_user_profile_as_regular_user(token, user_id=1):
    """Test that regular users cannot view other users' profiles."""
    print("\n" + "="*60)
    print("TEST 3: Regular User Tries to View Other User Profile (Should Fail)")
    print("="*60)
    
    response = requests.get(
        f"{API_BASE}/profile/?user_id={user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 403:
        print("\n✅ SUCCESS - Permission denied as expected")
        print(response.json())
        return True
    else:
        print(f"❌ FAILED - Expected 403, got {response.status_code}")
        print(response.text)
        return False


def test_get_other_user_profile_as_admin(admin_token, user_id=2):
    """Test that admins can view other users' profiles."""
    print("\n" + "="*60)
    print("TEST 4: Admin Views Other User Profile (Should Succeed)")
    print("="*60)
    
    response = requests.get(
        f"{API_BASE}/profile/?user_id={user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ SUCCESS - Admin accessed user profile")
        print(f"\nViewing profile of: {data['user_info']['username']}")
        print(f"Groups: {data['summary']['total_group_memberships']}")
        return True
    else:
        print(f"❌ FAILED")
        print(response.text)
        return False


def test_unauthenticated_access():
    """Test that unauthenticated requests are rejected."""
    print("\n" + "="*60)
    print("TEST 5: Unauthenticated Access (Should Fail)")
    print("="*60)
    
    response = requests.get(f"{API_BASE}/profile/")
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 401:
        print("\n✅ SUCCESS - Unauthorized as expected")
        print(response.json())
        return True
    else:
        print(f"❌ FAILED - Expected 401, got {response.status_code}")
        print(response.text)
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("USER PROFILE API TEST SUITE")
    print("="*60)
    
    # Track results
    results = []
    
    # Test 5: Unauthenticated access (no login needed)
    results.append(("Unauthenticated Access", test_unauthenticated_access()))
    
    # Login as regular user
    print("\n\n" + "="*60)
    print("LOGGING IN AS REGULAR USER")
    print("="*60)
    user_token = login(TEST_USERNAME, TEST_PASSWORD)
    
    if user_token:
        print(f"✅ Login successful")
        
        # Test 1: Get own profile
        results.append(("Get Own Profile", test_get_own_profile(user_token)))
        
        # Test 2: Get simple profile
        results.append(("Get Simple Profile", test_get_simple_profile(user_token)))
        
        # Test 3: Try to view other user's profile (should fail)
        results.append(("Regular User Access Restriction", 
                       test_get_other_user_profile_as_regular_user(user_token)))
    else:
        print("❌ Could not login as regular user. Skipping user tests.")
        results.append(("Get Own Profile", False))
        results.append(("Get Simple Profile", False))
        results.append(("Regular User Access Restriction", False))
    
    # Login as admin
    print("\n\n" + "="*60)
    print("LOGGING IN AS ADMIN")
    print("="*60)
    admin_token = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    
    if admin_token:
        print(f"✅ Login successful")
        
        # Test 4: Admin views other user's profile
        results.append(("Admin Views Other Profile", 
                       test_get_other_user_profile_as_admin(admin_token)))
    else:
        print("❌ Could not login as admin. Skipping admin tests.")
        results.append(("Admin Views Other Profile", False))
    
    # Print summary
    print("\n\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
