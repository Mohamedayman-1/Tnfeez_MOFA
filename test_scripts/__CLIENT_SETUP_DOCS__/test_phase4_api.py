"""
Phase 4 API Testing Script - User Segment Access & Abilities

This script tests ALL Phase 4 REST API endpoints using actual HTTP requests.
Tests both user segment access and user segment abilities with the new dynamic structure.

Prerequisites:
1. Server must be running: python manage.py runserver
2. Update JWT_TOKEN with a valid authentication token
3. Ensure test data exists (segment types, segments, users)

Test Coverage:
- User Segment Access: 10 endpoints
- User Segment Abilities: 8 endpoints
- Total: 18 API endpoints tested
"""

import os
import sys
import django

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

import requests
import json
from datetime import datetime
from user_management.models import xx_User, XX_UserSegmentAccess, XX_UserSegmentAbility
from account_and_entitys.models import XX_SegmentType, XX_Segment

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "http://127.0.0.1:8000"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYyNzYxMzEzLCJpYXQiOjE3NjI3NTk1MTMsImp0aSI6IjA4ZTdkOTlmMzVkYzRiZWViMWI0NzhjODMwZTI2YjQwIiwidXNlcl9pZCI6NX0.OcpdB55b_fGLmSr8tTfxtTzHCFcgLahsMYuEEcCypyI"

HEADERS = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "Content-Type": "application/json"
}

# Test results tracking
test_results = []
total_tests = 0
passed_tests = 0
failed_tests = 0

def log_test(test_name, success, details=""):
    """Log test result."""
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    
    if success:
        passed_tests += 1
        status = "[PASS]"
    else:
        failed_tests += 1
        status = "[FAIL]"
    
    result = f"{status} Test {total_tests}: {test_name}"
    if details:
        result += f"\n      {details}"
    
    print(result)
    test_results.append({
        'test_number': total_tests,
        'test_name': test_name,
        'success': success,
        'details': details
    })

def print_summary():
    """Print test summary."""
    print("\n" + "=" * 80)
    print("PHASE 4 API TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests:   {total_tests}")
    print(f"Passed:        {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"Failed:        {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
    print("=" * 80)
    
    if failed_tests > 0:
        print("\nFailed Tests:")
        for result in test_results:
            if not result['success']:
                print(f"  - Test {result['test_number']}: {result['test_name']}")
                if result['details']:
                    print(f"    {result['details']}")

# =============================================================================
# SETUP TEST DATA
# =============================================================================

print("=" * 80)
print("PHASE 4 API TESTING: User Segment Access & Abilities")
print("=" * 80)
print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Base URL: {BASE_URL}")
print(f"Token: {JWT_TOKEN[:20]}..." if len(JWT_TOKEN) > 20 else f"Token: {JWT_TOKEN}")

print("\n[SETUP] Ensuring test data exists...")

# Ensure segment types exist
entity_type, _ = XX_SegmentType.objects.update_or_create(
    segment_id=1,
    defaults={
        'segment_name': 'Entity',
        'segment_type': 'cost_center',
        'oracle_segment_number': 1,
        'is_required': True,
        'has_hierarchy': True,
        'is_active': True
    }
)

account_type, _ = XX_SegmentType.objects.update_or_create(
    segment_id=2,
    defaults={
        'segment_name': 'Account',
        'segment_type': 'account',
        'oracle_segment_number': 2,
        'is_required': True,
        'has_hierarchy': False,
        'is_active': True
    }
)

project_type, _ = XX_SegmentType.objects.update_or_create(
    segment_id=3,
    defaults={
        'segment_name': 'Project',
        'segment_type': 'project',
        'oracle_segment_number': 3,
        'is_required': False,
        'has_hierarchy': True,
        'is_active': True
    }
)

# Create test segments with hierarchy
segments_to_create = [
    (entity_type, 'E001', None, 'HR Department'),
    (entity_type, 'E001-A', 'E001', 'HR Recruitment'),
    (entity_type, 'E001-B', 'E001', 'HR Training'),
    (entity_type, 'E001-A-1', 'E001-A', 'HR Recruitment Local'),
    (entity_type, 'E002', None, 'IT Department'),
    (account_type, 'A100', None, 'Salaries'),
    (account_type, 'A200', None, 'Equipment'),
    (project_type, 'P001', None, 'Project Alpha'),
    (project_type, 'P001-1', 'P001', 'Project Alpha Phase 1'),
    (project_type, 'P002', None, 'Project Beta'),
]

for seg_type, code, parent, alias in segments_to_create:
    XX_Segment.objects.update_or_create(
        segment_type=seg_type,
        code=code,
        defaults={'parent_code': parent, 'alias': alias, 'is_active': True}
    )

# Get or create test users
test_user1, _ = xx_User.objects.get_or_create(
    username='testuser_phase4_1',
    defaults={'role': 'user', 'is_active': True}
)
if not test_user1.is_active:
    test_user1.is_active = True
    test_user1.save()

test_user2, _ = xx_User.objects.get_or_create(
    username='testuser_phase4_2',
    defaults={'role': 'user', 'is_active': True}
)
if not test_user2.is_active:
    test_user2.is_active = True
    test_user2.save()

# Clean up existing test accesses and abilities
XX_UserSegmentAccess.objects.filter(user__in=[test_user1, test_user2]).delete()
XX_UserSegmentAbility.objects.filter(user__in=[test_user1, test_user2]).delete()

print(f"[OK] Test data ready: 3 segment types, 10 segments, 2 test users")
print(f"     Test User 1 ID: {test_user1.id} (username: {test_user1.username})")
print(f"     Test User 2 ID: {test_user2.id} (username: {test_user2.username})")

# =============================================================================
# USER SEGMENT ACCESS API TESTS
# =============================================================================

print("\n" + "=" * 80)
print("TESTING: User Segment Access APIs")
print("=" * 80)

# Test 1: Grant access to Entity E001
print("\n[TEST 1] Grant user access to Entity E001...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/access/grant",
        headers=HEADERS,
        json={
            "user_id": test_user1.id,
            "segment_type_id": 1,
            "segment_code": "E001",
            "access_level": "EDIT",
            "notes": "Test access grant"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('access'):
            log_test("Grant Access", True, f"Access ID: {data['access']['id']}, Level: {data['access']['access_level']}")
        else:
            log_test("Grant Access", False, f"Unexpected response: {data}")
    else:
        log_test("Grant Access", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Grant Access", False, f"Exception: {str(e)}")

# Test 2: Check user has access
print("\n[TEST 2] Check user has access to Entity E001...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/access/check",
        headers=HEADERS,
        json={
            "user_id": test_user1.id,
            "segment_type_id": 1,
            "segment_code": "E001",
            "required_level": "VIEW"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('has_access'):
            log_test("Check Access", True, f"Has access: {data['has_access']}, Level: {data.get('access_level')}")
        else:
            log_test("Check Access", False, f"Access check failed: {data}")
    else:
        log_test("Check Access", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Check Access", False, f"Exception: {str(e)}")

# Test 3: Bulk grant access
print("\n[TEST 3] Bulk grant access to multiple segments...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/access/bulk-grant",
        headers=HEADERS,
        json={
            "user_id": test_user1.id,
            "accesses": [
                {
                    "segment_type_id": 2,
                    "segment_code": "A100",
                    "access_level": "VIEW",
                    "notes": "Salaries view"
                },
                {
                    "segment_type_id": 2,
                    "segment_code": "A200",
                    "access_level": "EDIT",
                    "notes": "Equipment edit"
                },
                {
                    "segment_type_id": 3,
                    "segment_code": "P001",
                    "access_level": "APPROVE",
                    "notes": "Project approval"
                }
            ]
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('granted') == 3:
            log_test("Bulk Grant Access", True, f"Granted: {data['granted']}/{data['total']}")
        else:
            log_test("Bulk Grant Access", False, f"Unexpected result: {data}")
    else:
        log_test("Bulk Grant Access", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Bulk Grant Access", False, f"Exception: {str(e)}")

# Test 4: List all accesses
print("\n[TEST 4] List user's all accesses...")
try:
    response = requests.get(
        f"{BASE_URL}/api/auth/phase4/access/list?user_id={test_user1.id}",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('count') >= 4:
            log_test("List Accesses", True, f"Found {data['count']} accesses")
        else:
            log_test("List Accesses", False, f"Expected >= 4 accesses, got {data.get('count', 0)}")
    else:
        log_test("List Accesses", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("List Accesses", False, f"Exception: {str(e)}")

# Test 5: Get user allowed segments
print("\n[TEST 5] Get user's allowed segments for Entity type...")
try:
    response = requests.get(
        f"{BASE_URL}/api/auth/phase4/access/user-segments?user_id={test_user1.id}&segment_type_id=1",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('count') >= 1:
            log_test("Get User Segments", True, f"Found {data['count']} segments")
        else:
            log_test("Get User Segments", False, f"Expected >= 1 segments, got {data.get('count', 0)}")
    else:
        log_test("Get User Segments", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Get User Segments", False, f"Exception: {str(e)}")

# Test 6: Grant access with children (hierarchical)
print("\n[TEST 6] Grant access to parent with children...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/access/grant-with-children",
        headers=HEADERS,
        json={
            "user_id": test_user2.id,
            "segment_type_id": 1,
            "segment_code": "E001",
            "access_level": "APPROVE",
            "apply_to_children": True,
            "notes": "Department manager with hierarchy"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('children_granted') >= 3:
            log_test("Grant With Children", True, f"Total granted: {data['total_granted']} (parent + {data['children_granted']} children)")
        else:
            log_test("Grant With Children", False, f"Unexpected result: {data}")
    else:
        log_test("Grant With Children", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Grant With Children", False, f"Exception: {str(e)}")

# Test 7: Hierarchical access check
print("\n[TEST 7] Check hierarchical access on child segment...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/access/hierarchical-check",
        headers=HEADERS,
        json={
            "user_id": test_user2.id,
            "segment_type_id": 1,
            "segment_code": "E001-A-1",  # Grandchild
            "required_level": "VIEW"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('has_access'):
            inherited_from = data.get('inherited_from', 'direct')
            log_test("Hierarchical Check", True, f"Has access, inherited from: {inherited_from}")
        else:
            log_test("Hierarchical Check", False, f"Access check failed: {data}")
    else:
        log_test("Hierarchical Check", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Hierarchical Check", False, f"Exception: {str(e)}")

# Test 8: Get effective access level
print("\n[TEST 8] Get effective access level...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/access/effective-level",
        headers=HEADERS,
        json={
            "user_id": test_user2.id,
            "segment_type_id": 1,
            "segment_code": "E001-B"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('access_level'):
            log_test("Get Effective Level", True, f"Level: {data['access_level']}, Source: {data.get('source_segment', 'direct')}")
        else:
            log_test("Get Effective Level", False, f"Unexpected result: {data}")
    else:
        log_test("Get Effective Level", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Get Effective Level", False, f"Exception: {str(e)}")

# Test 9: Get segment users
print("\n[TEST 9] Get users with access to segment...")
try:
    response = requests.get(
        f"{BASE_URL}/api/auth/phase4/access/segment-users?segment_type_id=1&segment_code=E001",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('count') >= 2:
            log_test("Get Segment Users", True, f"Found {data['count']} users")
        else:
            log_test("Get Segment Users", False, f"Expected >= 2 users, got {data.get('count', 0)}")
    else:
        log_test("Get Segment Users", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Get Segment Users", False, f"Exception: {str(e)}")

# Test 10: Revoke access
print("\n[TEST 10] Revoke user access...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/access/revoke",
        headers=HEADERS,
        json={
            "user_id": test_user1.id,
            "segment_type_id": 2,
            "segment_code": "A100",
            "access_level": "VIEW",
            "soft_delete": True
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('revoked_count') >= 1:
            log_test("Revoke Access", True, f"Revoked {data['revoked_count']} access(es)")
        else:
            log_test("Revoke Access", False, f"Unexpected result: {data}")
    else:
        log_test("Revoke Access", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Revoke Access", False, f"Exception: {str(e)}")

# =============================================================================
# USER SEGMENT ABILITY API TESTS
# =============================================================================

print("\n" + "=" * 80)
print("TESTING: User Segment Ability APIs")
print("=" * 80)

# Test 11: Grant ability
print("\n[TEST 11] Grant user ability on segment combination...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/abilities/grant",
        headers=HEADERS,
        json={
            "user_id": test_user1.id,
            "ability_type": "APPROVE",
            "segment_combination": {"1": "E001", "2": "A200"},
            "notes": "Budget approval ability"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('ability'):
            log_test("Grant Ability", True, f"Ability ID: {data['ability']['id']}, Type: {data['ability']['ability_type']}")
        else:
            log_test("Grant Ability", False, f"Unexpected response: {data}")
    else:
        log_test("Grant Ability", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Grant Ability", False, f"Exception: {str(e)}")

# Test 12: Check user has ability
print("\n[TEST 12] Check user has ability...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/abilities/check",
        headers=HEADERS,
        json={
            "user_id": test_user1.id,
            "ability_type": "APPROVE",
            "segment_combination": {"1": "E001", "2": "A200"}
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('has_ability'):
            log_test("Check Ability", True, f"Has ability: {data['has_ability']}")
        else:
            log_test("Check Ability", False, f"Ability check failed: {data}")
    else:
        log_test("Check Ability", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Check Ability", False, f"Exception: {str(e)}")

# Test 13: Bulk grant abilities
print("\n[TEST 13] Bulk grant abilities...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/abilities/bulk-grant",
        headers=HEADERS,
        json={
            "user_id": test_user1.id,
            "abilities": [
                {
                    "ability_type": "EDIT",
                    "segment_combination": {"1": "E002"},
                    "notes": "IT department edit"
                },
                {
                    "ability_type": "TRANSFER",
                    "segment_combination": {"1": "E001", "3": "P001"},
                    "notes": "Transfer between HR and Project"
                }
            ]
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('granted') == 2:
            log_test("Bulk Grant Abilities", True, f"Granted: {data['granted']}/{data['total']}")
        else:
            log_test("Bulk Grant Abilities", False, f"Unexpected result: {data}")
    else:
        log_test("Bulk Grant Abilities", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Bulk Grant Abilities", False, f"Exception: {str(e)}")

# Test 14: List abilities
print("\n[TEST 14] List user's abilities...")
try:
    response = requests.get(
        f"{BASE_URL}/api/auth/phase4/abilities/list?user_id={test_user1.id}",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('count') >= 3:
            log_test("List Abilities", True, f"Found {data['count']} abilities")
        else:
            log_test("List Abilities", False, f"Expected >= 3 abilities, got {data.get('count', 0)}")
    else:
        log_test("List Abilities", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("List Abilities", False, f"Exception: {str(e)}")

# Test 15: Get user abilities with filter
print("\n[TEST 15] Get user abilities with filter...")
try:
    response = requests.get(
        f"{BASE_URL}/api/auth/phase4/abilities/user-abilities?user_id={test_user1.id}&ability_type=APPROVE",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('count') >= 1:
            log_test("Get User Abilities", True, f"Found {data['count']} APPROVE abilities")
        else:
            log_test("Get User Abilities", False, f"Expected >= 1 abilities, got {data.get('count', 0)}")
    else:
        log_test("Get User Abilities", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Get User Abilities", False, f"Exception: {str(e)}")

# Test 16: Validate ability for operation
print("\n[TEST 16] Validate ability for operation...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/abilities/validate-operation",
        headers=HEADERS,
        json={
            "user_id": test_user1.id,
            "operation": "approve_transfer",
            "segment_combination": {"1": "E001", "2": "A200"}
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('allowed'):
            log_test("Validate Operation", True, f"Allowed: {data['allowed']}, Required: {data.get('required_ability')}")
        else:
            log_test("Validate Operation", False, f"Validation failed: {data}")
    else:
        log_test("Validate Operation", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Validate Operation", False, f"Exception: {str(e)}")

# Test 17: Get users with ability
print("\n[TEST 17] Get users with specific ability...")
try:
    response = requests.get(
        f"{BASE_URL}/api/auth/phase4/abilities/users-with-ability?ability_type=APPROVE",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('count') >= 1:
            log_test("Get Users With Ability", True, f"Found {data['count']} users with APPROVE")
        else:
            log_test("Get Users With Ability", False, f"Expected >= 1 users, got {data.get('count', 0)}")
    else:
        log_test("Get Users With Ability", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Get Users With Ability", False, f"Exception: {str(e)}")

# Test 18: Revoke ability
print("\n[TEST 18] Revoke user ability...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/phase4/abilities/revoke",
        headers=HEADERS,
        json={
            "user_id": test_user1.id,
            "ability_type": "EDIT",
            "segment_combination": {"1": "E002"},
            "soft_delete": True
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('revoked_count') >= 1:
            log_test("Revoke Ability", True, f"Revoked {data['revoked_count']} ability(ies)")
        else:
            log_test("Revoke Ability", False, f"Unexpected result: {data}")
    else:
        log_test("Revoke Ability", False, f"HTTP {response.status_code}: {response.text}")
except Exception as e:
    log_test("Revoke Ability", False, f"Exception: {str(e)}")

# =============================================================================
# FINAL SUMMARY
# =============================================================================

print_summary()

print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("\n" + "=" * 80)

# Exit with appropriate code
sys.exit(0 if failed_tests == 0 else 1)
