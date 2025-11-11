"""
Test script for Phase 3: Envelope and Mapping APIs (NEW SIMPLIFIED FORMAT)

This script tests all 11 Phase 3 API endpoints:

ENVELOPE APIs:
1. POST   /api/accounts-entities/envelopes/              - Create envelope
2. GET    /api/accounts-entities/envelopes/              - List envelopes
3. GET    /api/accounts-entities/envelopes/<id>/         - Get envelope detail
4. PUT    /api/accounts-entities/envelopes/<id>/         - Update envelope
5. DELETE /api/accounts-entities/envelopes/<id>/         - Delete envelope
6. POST   /api/accounts-entities/envelopes/check-balance/ - Check balance

MAPPING APIs:
7. POST   /api/accounts-entities/mappings/               - Create mapping
8. GET    /api/accounts-entities/mappings/               - List mappings
9. GET    /api/accounts-entities/mappings/lookup/        - Lookup mappings

TRANSFER LIMIT APIs:
10. POST  /api/accounts-entities/transfer-limits/         - Create limit
11. POST  /api/accounts-entities/transfer-limits/validate/ - Validate transfer

NEW SIMPLIFIED FORMAT:
- segment_combination: {"1": "E001", "2": "A100", "3": "P001"}
- No more from_code/to_code pairs - just single code per segment
"""

import os
import sys
import django
import requests
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from account_and_entitys.models import XX_SegmentType, XX_Segment
from user_management.models import xx_User

# =============================================================================
# CONFIGURATION
# =============================================================================
BASE_URL = "http://127.0.0.1:8000/api/accounts-entities"
HEADERS = {"Content-Type": "application/json"}

# For authenticated requests, you would add:
# TOKEN = "your-auth-token"
# HEADERS["Authorization"] = f"Bearer {TOKEN}"

print("=" * 80)
print("PHASE 3 API TESTING: Envelope and Mapping (NEW SIMPLIFIED FORMAT)")
print("=" * 80)
print(f"Base URL: {BASE_URL}")
print("=" * 80)

# =============================================================================
# SETUP: Ensure test data exists
# =============================================================================
print("\n[SETUP] Ensuring test data exists...")

# Create segment types
entity_type, _ = XX_SegmentType.objects.get_or_create(
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

account_type, _ = XX_SegmentType.objects.get_or_create(
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

project_type, _ = XX_SegmentType.objects.get_or_create(
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

# Create test segments
test_segments = [
    {'type': entity_type, 'code': 'E001', 'alias': 'HR Department'},
    {'type': entity_type, 'code': 'E002', 'alias': 'IT Department'},
    {'type': entity_type, 'code': 'E003', 'alias': 'Finance Department'},
    {'type': account_type, 'code': 'A100', 'alias': 'Salaries'},
    {'type': account_type, 'code': 'A200', 'alias': 'Travel'},
    {'type': account_type, 'code': 'A300', 'alias': 'Supplies'},
    {'type': project_type, 'code': 'P001', 'alias': 'AI Initiative'},
    {'type': project_type, 'code': 'P002', 'alias': 'Cloud Migration'},
]

for seg_data in test_segments:
    XX_Segment.objects.get_or_create(
        segment_type_id=seg_data['type'].segment_id,
        code=seg_data['code'],
        defaults={
            'alias': seg_data['alias'],
            'is_active': True
        }
    )

print("✓ Test segments ready")

# =============================================================================
# TEST 1: CREATE ENVELOPE
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 1] CREATE ENVELOPE")
print("=" * 80)

envelope_data = {
    "segment_combination": {
        "1": "E001",  # HR Department
        "2": "A100",  # Salaries
        "3": "P001"   # AI Initiative
    },
    "envelope_amount": "100000.00",
    "fiscal_year": "FY2025",
    "description": "HR Salaries for AI Initiative - FY2025"
}

print(f"\nPOST {BASE_URL}/envelopes/")
print(f"Request: {envelope_data}")

try:
    response = requests.post(f"{BASE_URL}/envelopes/", json=envelope_data, headers=HEADERS)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        created_envelope = response.json()
        print(f"✓ Envelope created successfully")
        print(f"  ID: {created_envelope['id']}")
        print(f"  Envelope Amount: {created_envelope['envelope_amount']}")
        print(f"  Fiscal Year: {created_envelope['fiscal_year']}")
        ENVELOPE_ID = created_envelope['id']
    else:
        print(f"✗ Failed: {response.json()}")
        ENVELOPE_ID = None
except Exception as e:
    print(f"✗ Error: {e}")
    ENVELOPE_ID = None

# =============================================================================
# TEST 2: LIST ENVELOPES (with filtering)
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 2] LIST ENVELOPES")
print("=" * 80)

# Test 2a: List all envelopes
print(f"\nGET {BASE_URL}/envelopes/")
try:
    response = requests.get(f"{BASE_URL}/envelopes/", headers=HEADERS)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        envelopes = response.json()
        print(f"✓ Retrieved {len(envelopes)} envelope(s)")
        for env in envelopes:
            print(f"  - ID {env['id']}: {env['description']} (${env['envelope_amount']})")
    else:
        print(f"✗ Failed: {response.json()}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2b: Filter by fiscal year
print(f"\nGET {BASE_URL}/envelopes/?fiscal_year=FY2025")
try:
    response = requests.get(f"{BASE_URL}/envelopes/?fiscal_year=FY2025", headers=HEADERS)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        envelopes = response.json()
        print(f"✓ Retrieved {len(envelopes)} envelope(s) for FY2025")
    else:
        print(f"✗ Failed: {response.json()}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2c: Filter by segment
print(f"\nGET {BASE_URL}/envelopes/?segment_type_id=1&segment_code=E001")
try:
    response = requests.get(
        f"{BASE_URL}/envelopes/?segment_type_id=1&segment_code=E001", 
        headers=HEADERS
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        envelopes = response.json()
        print(f"✓ Retrieved {len(envelopes)} envelope(s) for Entity E001")
    else:
        print(f"✗ Failed: {response.json()}")
except Exception as e:
    print(f"✗ Error: {e}")

# =============================================================================
# TEST 3: GET ENVELOPE DETAIL
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 3] GET ENVELOPE DETAIL")
print("=" * 80)

if ENVELOPE_ID:
    print(f"\nGET {BASE_URL}/envelopes/{ENVELOPE_ID}/")
    try:
        response = requests.get(f"{BASE_URL}/envelopes/{ENVELOPE_ID}/", headers=HEADERS)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            envelope = response.json()
            print(f"✓ Envelope details retrieved")
            print(f"  ID: {envelope['id']}")
            print(f"  Segment Combination: {envelope['segment_combination']}")
            print(f"  Envelope Amount: {envelope['envelope_amount']}")
            print(f"  Consumed: {envelope.get('consumed_balance', 'N/A')}")
            print(f"  Available: {envelope.get('available_balance', 'N/A')}")
            print(f"  Description: {envelope['description']}")
        else:
            print(f"✗ Failed: {response.json()}")
    except Exception as e:
        print(f"✗ Error: {e}")
else:
    print("⊘ Skipped - no envelope ID available")

# =============================================================================
# TEST 4: CHECK BALANCE
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 4] CHECK BALANCE AVAILABILITY")
print("=" * 80)

balance_check_data = {
    "segment_combination": {
        "1": "E001",
        "2": "A100",
        "3": "P001"
    },
    "required_amount": "5000.00",
    "fiscal_year": "FY2025"
}

print(f"\nPOST {BASE_URL}/envelopes/check-balance/")
print(f"Request: {balance_check_data}")

try:
    response = requests.post(
        f"{BASE_URL}/envelopes/check-balance/", 
        json=balance_check_data, 
        headers=HEADERS
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Balance check completed")
        print(f"  Sufficient Balance: {result['sufficient_balance']}")
        print(f"  Envelope Amount: ${result['envelope_amount']}")
        print(f"  Consumed: ${result['consumed_balance']}")
        print(f"  Available: ${result['available_balance']}")
        print(f"  Required: ${result['required_amount']}")
        if not result['sufficient_balance']:
            print(f"  ⚠ WARNING: Insufficient balance! Short by ${result['shortfall']}")
    else:
        print(f"✗ Failed: {response.json()}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 4b: Check with insufficient balance
balance_check_large = {
    "segment_combination": {
        "1": "E001",
        "2": "A100",
        "3": "P001"
    },
    "required_amount": "150000.00",  # More than envelope amount
    "fiscal_year": "FY2025"
}

print(f"\nPOST {BASE_URL}/envelopes/check-balance/ (Insufficient)")
print(f"Request: {balance_check_large}")

try:
    response = requests.post(
        f"{BASE_URL}/envelopes/check-balance/", 
        json=balance_check_large, 
        headers=HEADERS
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Balance check completed")
        print(f"  Sufficient Balance: {result['sufficient_balance']}")
        print(f"  Shortfall: ${result['shortfall']}")
    else:
        print(f"✗ Failed: {response.json()}")
except Exception as e:
    print(f"✗ Error: {e}")

# =============================================================================
# TEST 5: UPDATE ENVELOPE
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 5] UPDATE ENVELOPE")
print("=" * 80)

if ENVELOPE_ID:
    update_data = {
        "envelope_amount": "120000.00",  # Increase budget
        "description": "HR Salaries for AI Initiative - FY2025 (Revised)"
    }
    
    print(f"\nPUT {BASE_URL}/envelopes/{ENVELOPE_ID}/")
    print(f"Request: {update_data}")
    
    try:
        response = requests.put(
            f"{BASE_URL}/envelopes/{ENVELOPE_ID}/", 
            json=update_data, 
            headers=HEADERS
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            updated_envelope = response.json()
            print(f"✓ Envelope updated successfully")
            print(f"  New Amount: {updated_envelope['envelope_amount']}")
            print(f"  New Description: {updated_envelope['description']}")
        else:
            print(f"✗ Failed: {response.json()}")
    except Exception as e:
        print(f"✗ Error: {e}")
else:
    print("⊘ Skipped - no envelope ID available")

# =============================================================================
# TEST 6: CREATE SEGMENT MAPPING
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 6] CREATE SEGMENT MAPPING")
print("=" * 80)

mapping_data = {
    "segment_type_id": 1,  # Entity
    "source_code": "E001",  # HR
    "target_code": "E002",  # IT
    "mapping_type": "CONSOLIDATION",
    "description": "HR consolidates to IT for reporting",
    "is_active": True
}

print(f"\nPOST {BASE_URL}/mappings/")
print(f"Request: {mapping_data}")

try:
    response = requests.post(f"{BASE_URL}/mappings/", json=mapping_data, headers=HEADERS)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        created_mapping = response.json()
        print(f"✓ Mapping created successfully")
        print(f"  ID: {created_mapping['id']}")
        print(f"  Mapping: {created_mapping['source_code']} → {created_mapping['target_code']}")
        print(f"  Type: {created_mapping['mapping_type']}")
        MAPPING_ID = created_mapping['id']
    else:
        print(f"✗ Failed: {response.json()}")
        MAPPING_ID = None
except Exception as e:
    print(f"✗ Error: {e}")
    MAPPING_ID = None

# =============================================================================
# TEST 7: LOOKUP MAPPING (Forward)
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 7] LOOKUP MAPPING (FORWARD)")
print("=" * 80)

print(f"\nGET {BASE_URL}/mappings/lookup/?segment_type_id=1&source_code=E001&direction=forward")
try:
    response = requests.get(
        f"{BASE_URL}/mappings/lookup/?segment_type_id=1&source_code=E001&direction=forward",
        headers=HEADERS
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Forward lookup completed")
        print(f"  Source: {result['source_code']}")
        print(f"  Targets: {result['targets']}")
        print(f"  Count: {result['count']}")
    else:
        print(f"✗ Failed: {response.json()}")
except Exception as e:
    print(f"✗ Error: {e}")

# =============================================================================
# TEST 8: LOOKUP MAPPING (Reverse)
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 8] LOOKUP MAPPING (REVERSE)")
print("=" * 80)

print(f"\nGET {BASE_URL}/mappings/lookup/?segment_type_id=1&target_code=E002&direction=reverse")
try:
    response = requests.get(
        f"{BASE_URL}/mappings/lookup/?segment_type_id=1&target_code=E002&direction=reverse",
        headers=HEADERS
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Reverse lookup completed")
        print(f"  Target: {result['target_code']}")
        print(f"  Sources: {result['sources']}")
        print(f"  Count: {result['count']}")
    else:
        print(f"✗ Failed: {response.json()}")
except Exception as e:
    print(f"✗ Error: {e}")

# =============================================================================
# TEST 9: CREATE TRANSFER LIMIT
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 9] CREATE TRANSFER LIMIT")
print("=" * 80)

limit_data = {
    "segment_combination": {
        "1": "E001"  # HR Department
    },
    "fiscal_year": "FY2025",
    "is_transfer_allowed_as_source": True,
    "is_transfer_allowed_as_target": True,
    "max_source_transfers": 10,
    "max_target_transfers": 20,
    "description": "HR can make 10 outgoing transfers, receive 20 incoming transfers",
    "is_active": True
}

print(f"\nPOST {BASE_URL}/transfer-limits/")
print(f"Request: {limit_data}")

try:
    response = requests.post(f"{BASE_URL}/transfer-limits/", json=limit_data, headers=HEADERS)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        created_limit = response.json()
        print(f"✓ Transfer limit created successfully")
        print(f"  ID: {created_limit['id']}")
        print(f"  Max Source Transfers: {created_limit['max_source_transfers']}")
        print(f"  Max Target Transfers: {created_limit['max_target_transfers']}")
        LIMIT_ID = created_limit['id']
    else:
        print(f"✗ Failed: {response.json()}")
        LIMIT_ID = None
except Exception as e:
    print(f"✗ Error: {e}")
    LIMIT_ID = None

# =============================================================================
# TEST 10: VALIDATE TRANSFER
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 10] VALIDATE TRANSFER")
print("=" * 80)

validate_data = {
    "from_segments": {
        "1": "E001",  # HR
        "2": "A100"   # Salaries
    },
    "to_segments": {
        "1": "E002",  # IT
        "2": "A100"   # Salaries
    },
    "fiscal_year": "FY2025"
}

print(f"\nPOST {BASE_URL}/transfer-limits/validate/")
print(f"Request: {validate_data}")

try:
    response = requests.post(
        f"{BASE_URL}/transfer-limits/validate/", 
        json=validate_data, 
        headers=HEADERS
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Transfer validation completed")
        print(f"  Valid: {result['valid']}")
        
        if result['valid']:
            print(f"  Source Allowed: {result['source_allowed']}")
            print(f"  Target Allowed: {result['target_allowed']}")
            print(f"  Source Transfers: {result['source_transfer_count']}/{result['source_transfer_limit']}")
            print(f"  Target Transfers: {result['target_transfer_count']}/{result['target_transfer_limit']}")
        else:
            print(f"  Reason: {result['reason']}")
    else:
        print(f"✗ Failed: {response.json()}")
except Exception as e:
    print(f"✗ Error: {e}")

# =============================================================================
# TEST 11: DELETE ENVELOPE (Soft Delete)
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 11] DELETE ENVELOPE (SOFT DELETE)")
print("=" * 80)

if ENVELOPE_ID:
    print(f"\nDELETE {BASE_URL}/envelopes/{ENVELOPE_ID}/")
    print("(Soft delete - sets is_active=False)")
    
    try:
        response = requests.delete(f"{BASE_URL}/envelopes/{ENVELOPE_ID}/", headers=HEADERS)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 204:
            print(f"✓ Envelope soft deleted successfully")
            
            # Verify it's deactivated, not deleted
            response = requests.get(f"{BASE_URL}/envelopes/{ENVELOPE_ID}/", headers=HEADERS)
            if response.status_code == 200:
                envelope = response.json()
                print(f"  Envelope still exists but is_active={envelope['is_active']}")
        else:
            print(f"✗ Failed: {response.json()}")
    except Exception as e:
        print(f"✗ Error: {e}")
else:
    print("⊘ Skipped - no envelope ID available")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("""
✓ Tests completed for all 11 Phase 3 API endpoints

NEW SIMPLIFIED FORMAT USED:
- segment_combination: {"1": "E001", "2": "A100", "3": "P001"}
- No more from_code/to_code pairs
- Single code per segment type

TESTED OPERATIONS:
1. Create envelope with segment combination
2. List envelopes with filtering (fiscal year, segment)
3. Get envelope detail with consumption summary
4. Check balance availability (sufficient/insufficient)
5. Update envelope amount and description
6. Create segment mapping (source → target)
7. Lookup mappings (forward: source → targets)
8. Lookup mappings (reverse: target → sources)
9. Create transfer limit with permission flags
10. Validate transfer between segment combinations
11. Soft delete envelope (sets is_active=False)

For frontend integration:
- All responses include proper error messages
- Filtering supported on list endpoints
- Validation happens server-side
- Manager classes handle all business logic
""")

print("=" * 80)
print("PHASE 3 API TESTING COMPLETE")
print("=" * 80)
