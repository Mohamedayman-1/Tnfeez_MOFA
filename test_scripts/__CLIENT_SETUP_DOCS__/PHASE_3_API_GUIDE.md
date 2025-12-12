# Phase 3 API Guide: Envelope and Mapping Management

## Overview

Phase 3 provides comprehensive REST APIs for managing budget envelopes, segment mappings, and transfer limits using the **new simplified segment format**.

### Key Changes from Phase 2

**SIMPLIFIED SEGMENT FORMAT:**
```json
// ✅ NEW FORMAT (Phase 3)
{
  "segment_combination": {
    "1": "E001",  // Entity code
    "2": "A100",  // Account code
    "3": "P001"   // Project code
  }
}

// ❌ OLD FORMAT (deprecated but still supported)
{
  "segment_combination": {
    "1": {"from_code": "E001", "to_code": "E002"}
  }
}
```

**KEY ARCHITECTURAL CHANGE:**
- `envelope_amount` field **removed** from `XX_Segment` table
- Envelopes now stored in dedicated `XX_SegmentEnvelope` table
- Flexible envelope scopes: single segment, multiple segments, or any combination

---

## 🔵 Envelope Management APIs

### 1. Create Envelope

Create a budget envelope for a specific segment combination.

**Endpoint:** `POST /api/accounts-entities/envelopes/`

**Request Body:**
```json
{
  "segment_combination": {
    "1": "E001",  // Entity
    "2": "A100",  // Account
    "3": "P001"   // Project (optional)
  },
  "envelope_amount": "100000.00",
  "fiscal_year": "FY2025",
  "description": "HR Salaries for AI Initiative - FY2025",
  "is_active": true
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "segment_combination": {
    "1": "E001",
    "2": "A100",
    "3": "P001"
  },
  "envelope_amount": "100000.00",
  "fiscal_year": "FY2025",
  "description": "HR Salaries for AI Initiative - FY2025",
  "is_active": true,
  "created_at": "2025-06-11T10:30:00Z",
  "updated_at": "2025-06-11T10:30:00Z"
}
```

**Validation Rules:**
- `envelope_amount` must be positive
- `fiscal_year` is required
- `segment_combination` must contain valid segment codes
- Duplicate combinations for same fiscal year are not allowed

---

### 2. List Envelopes

Retrieve all envelopes with optional filtering.

**Endpoint:** `GET /api/accounts-entities/envelopes/`

**Query Parameters:**
- `fiscal_year` (optional) - Filter by fiscal year (e.g., `FY2025`)
- `is_active` (optional) - Filter by active status (`true`/`false`)
- `segment_type_id` (optional) - Filter by segment type (e.g., `1` for Entity)
- `segment_code` (optional) - Filter by specific segment code (e.g., `E001`)

**Examples:**

```bash
# Get all envelopes
GET /api/accounts-entities/envelopes/

# Get FY2025 envelopes
GET /api/accounts-entities/envelopes/?fiscal_year=FY2025

# Get envelopes for Entity E001
GET /api/accounts-entities/envelopes/?segment_type_id=1&segment_code=E001

# Get active envelopes only
GET /api/accounts-entities/envelopes/?is_active=true
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "segment_combination": {"1": "E001", "2": "A100", "3": "P001"},
    "envelope_amount": "100000.00",
    "fiscal_year": "FY2025",
    "description": "HR Salaries for AI Initiative",
    "is_active": true
  },
  {
    "id": 2,
    "segment_combination": {"1": "E002", "2": "A200"},
    "envelope_amount": "50000.00",
    "fiscal_year": "FY2025",
    "description": "IT Travel Budget",
    "is_active": true
  }
]
```

---

### 3. Get Envelope Detail

Retrieve detailed information about a specific envelope, including consumption summary.

**Endpoint:** `GET /api/accounts-entities/envelopes/<envelope_id>/`

**Response (200 OK):**
```json
{
  "id": 1,
  "segment_combination": {
    "1": "E001",
    "2": "A100",
    "3": "P001"
  },
  "envelope_amount": "100000.00",
  "consumed_balance": "25000.00",
  "available_balance": "75000.00",
  "fiscal_year": "FY2025",
  "description": "HR Salaries for AI Initiative - FY2025",
  "is_active": true,
  "created_at": "2025-06-11T10:30:00Z",
  "updated_at": "2025-06-11T10:30:00Z"
}
```

**Consumption Calculation:**
- `consumed_balance`: Sum of all approved transfers from this envelope
- `available_balance`: `envelope_amount - consumed_balance`

---

### 4. Update Envelope

Update an existing envelope's amount, description, or active status.

**Endpoint:** `PUT /api/accounts-entities/envelopes/<envelope_id>/`

**Request Body (partial update allowed):**
```json
{
  "envelope_amount": "120000.00",
  "description": "HR Salaries for AI Initiative - FY2025 (Revised)",
  "is_active": true
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "segment_combination": {"1": "E001", "2": "A100", "3": "P001"},
  "envelope_amount": "120000.00",
  "fiscal_year": "FY2025",
  "description": "HR Salaries for AI Initiative - FY2025 (Revised)",
  "is_active": true,
  "updated_at": "2025-06-11T11:45:00Z"
}
```

**Notes:**
- Cannot change `segment_combination` or `fiscal_year` after creation
- Can increase or decrease `envelope_amount`
- Setting `is_active=false` soft-deletes the envelope

---

### 5. Delete Envelope

Delete an envelope (soft delete by default).

**Endpoint:** `DELETE /api/accounts-entities/envelopes/<envelope_id>/`

**Query Parameters:**
- `hard_delete=true` (optional) - Permanently delete instead of soft delete

**Response (204 No Content):**
```
(Empty response body)
```

**Behavior:**
- **Default (soft delete):** Sets `is_active=False`, envelope remains in database
- **Hard delete:** Permanently removes envelope from database (use with caution)
- Cannot delete envelopes with consumed balance (transfers already made)

---

### 6. Check Balance Availability

Validate if sufficient balance is available for a proposed transfer.

**Endpoint:** `POST /api/accounts-entities/envelopes/check-balance/`

**Request Body:**
```json
{
  "segment_combination": {
    "1": "E001",
    "2": "A100",
    "3": "P001"
  },
  "required_amount": "5000.00",
  "fiscal_year": "FY2025"
}
```

**Response (200 OK) - Sufficient Balance:**
```json
{
  "sufficient_balance": true,
  "envelope_amount": "100000.00",
  "consumed_balance": "25000.00",
  "available_balance": "75000.00",
  "required_amount": "5000.00",
  "shortfall": "0.00"
}
```

**Response (200 OK) - Insufficient Balance:**
```json
{
  "sufficient_balance": false,
  "envelope_amount": "100000.00",
  "consumed_balance": "98000.00",
  "available_balance": "2000.00",
  "required_amount": "5000.00",
  "shortfall": "3000.00"
}
```

**Use Cases:**
- Pre-validate transfers before submission
- Display available balance to users
- Prevent overspending

---

## 🟢 Segment Mapping APIs

### 7. Create Mapping

Create a mapping between two segment codes (for consolidation, aliasing, etc.).

**Endpoint:** `POST /api/accounts-entities/mappings/`

**Request Body:**
```json
{
  "segment_type_id": 1,
  "source_code": "E001",
  "target_code": "E002",
  "mapping_type": "CONSOLIDATION",
  "description": "HR consolidates to IT for reporting",
  "is_active": true
}
```

**Mapping Types:**
- `CONSOLIDATION`: Source consolidates to target for reporting
- `ALIAS`: Codes are aliases of each other
- `PARENT_CHILD`: Hierarchical relationship
- `CUSTOM`: User-defined relationship

**Response (201 Created):**
```json
{
  "id": 1,
  "segment_type_id": 1,
  "source_code": "E001",
  "target_code": "E002",
  "mapping_type": "CONSOLIDATION",
  "description": "HR consolidates to IT for reporting",
  "is_active": true,
  "created_at": "2025-06-11T10:30:00Z"
}
```

**Validation:**
- Prevents circular references (A→B, B→A)
- Ensures source and target codes exist
- Duplicate mappings not allowed

---

### 8. List Mappings

Retrieve all mappings with optional filtering.

**Endpoint:** `GET /api/accounts-entities/mappings/`

**Query Parameters:**
- `segment_type_id` (optional) - Filter by segment type
- `mapping_type` (optional) - Filter by mapping type
- `source_code` (optional) - Filter by source code
- `target_code` (optional) - Filter by target code
- `is_active` (optional) - Filter by active status

**Example:**
```bash
# Get all entity mappings
GET /api/accounts-entities/mappings/?segment_type_id=1

# Get consolidation mappings
GET /api/accounts-entities/mappings/?mapping_type=CONSOLIDATION

# Get mappings from E001
GET /api/accounts-entities/mappings/?source_code=E001
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "segment_type_id": 1,
    "source_code": "E001",
    "target_code": "E002",
    "mapping_type": "CONSOLIDATION",
    "description": "HR consolidates to IT",
    "is_active": true
  }
]
```

---

### 9. Lookup Mapping

Lookup targets from a source (forward) or sources from a target (reverse).

**Endpoint:** `GET /api/accounts-entities/mappings/lookup/`

**Query Parameters (Forward Lookup):**
- `segment_type_id` (required) - Segment type ID
- `source_code` (required) - Source code to lookup
- `direction=forward` (required)

**Query Parameters (Reverse Lookup):**
- `segment_type_id` (required) - Segment type ID
- `target_code` (required) - Target code to lookup
- `direction=reverse` (required)

**Example - Forward Lookup:**
```bash
GET /api/accounts-entities/mappings/lookup/?segment_type_id=1&source_code=E001&direction=forward
```

**Response (200 OK):**
```json
{
  "segment_type_id": 1,
  "source_code": "E001",
  "targets": ["E002", "E003"],
  "count": 2,
  "direction": "forward"
}
```

**Example - Reverse Lookup:**
```bash
GET /api/accounts-entities/mappings/lookup/?segment_type_id=1&target_code=E002&direction=reverse
```

**Response (200 OK):**
```json
{
  "segment_type_id": 1,
  "target_code": "E002",
  "sources": ["E001", "E004"],
  "count": 2,
  "direction": "reverse"
}
```

**Use Cases:**
- Find all departments that consolidate to a parent
- Find aliases for a segment code
- Traverse hierarchical relationships

---

## 🟡 Transfer Limit APIs

### 10. Create Transfer Limit

Define transfer permissions and usage limits for a segment combination.

**Endpoint:** `POST /api/accounts-entities/transfer-limits/`

**Request Body:**
```json
{
  "segment_combination": {
    "1": "E001"
  },
  "fiscal_year": "FY2025",
  "is_transfer_allowed_as_source": true,
  "is_transfer_allowed_as_target": true,
  "max_source_transfers": 10,
  "max_target_transfers": 20,
  "description": "HR can make 10 outgoing, receive 20 incoming transfers",
  "is_active": true
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "segment_combination": {"1": "E001"},
  "fiscal_year": "FY2025",
  "is_transfer_allowed_as_source": true,
  "is_transfer_allowed_as_target": true,
  "max_source_transfers": 10,
  "max_target_transfers": 20,
  "source_transfer_count": 0,
  "target_transfer_count": 0,
  "description": "HR can make 10 outgoing, receive 20 incoming transfers",
  "is_active": true
}
```

**Permission Flags:**
- `is_transfer_allowed_as_source`: Can this segment transfer budget OUT?
- `is_transfer_allowed_as_target`: Can this segment receive budget IN?
- `max_source_transfers`: Maximum number of outgoing transfers (null = unlimited)
- `max_target_transfers`: Maximum number of incoming transfers (null = unlimited)

**Use Cases:**
- Lock down segments from making transfers
- Enforce transfer count limits
- Audit transfer activity

---

### 11. Validate Transfer

Validate if a transfer is allowed between two segment combinations.

**Endpoint:** `POST /api/accounts-entities/transfer-limits/validate/`

**Request Body:**
```json
{
  "from_segments": {
    "1": "E001",
    "2": "A100"
  },
  "to_segments": {
    "1": "E002",
    "2": "A100"
  },
  "fiscal_year": "FY2025"
}
```

**Response (200 OK) - Valid Transfer:**
```json
{
  "valid": true,
  "source_allowed": true,
  "target_allowed": true,
  "source_transfer_count": 3,
  "source_transfer_limit": 10,
  "target_transfer_count": 5,
  "target_transfer_limit": 20,
  "reason": "Transfer is allowed"
}
```

**Response (200 OK) - Invalid Transfer:**
```json
{
  "valid": false,
  "source_allowed": true,
  "target_allowed": false,
  "reason": "Target segment is not allowed to receive transfers"
}
```

**Response (200 OK) - Limit Exceeded:**
```json
{
  "valid": false,
  "source_allowed": true,
  "target_allowed": true,
  "source_transfer_count": 10,
  "source_transfer_limit": 10,
  "reason": "Source has reached maximum transfer limit (10/10)"
}
```

**Use Cases:**
- Pre-validate transfers before submission
- Display transfer eligibility to users
- Enforce business rules

---

## 🔴 Error Responses

All endpoints return consistent error responses:

**400 Bad Request:**
```json
{
  "error": "Invalid segment combination",
  "details": {
    "segment_combination": ["Segment code 'E999' does not exist"]
  }
}
```

**404 Not Found:**
```json
{
  "error": "Envelope not found",
  "envelope_id": 999
}
```

**500 Internal Server Error:**
```json
{
  "error": "An unexpected error occurred",
  "message": "Database connection failed"
}
```

---

## 📝 Frontend Integration Examples

### JavaScript (Fetch API)

```javascript
// Create envelope
async function createEnvelope() {
  const response = await fetch('/api/accounts-entities/envelopes/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      segment_combination: { "1": "E001", "2": "A100", "3": "P001" },
      envelope_amount: "100000.00",
      fiscal_year: "FY2025",
      description: "HR Salaries for AI Initiative"
    })
  });
  
  if (response.ok) {
    const envelope = await response.json();
    console.log('Created envelope:', envelope);
  } else {
    const error = await response.json();
    console.error('Error:', error);
  }
}

// Check balance
async function checkBalance(segments, amount, fiscalYear) {
  const response = await fetch('/api/accounts-entities/envelopes/check-balance/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      segment_combination: segments,
      required_amount: amount,
      fiscal_year: fiscalYear
    })
  });
  
  const result = await response.json();
  
  if (result.sufficient_balance) {
    console.log('✓ Sufficient balance:', result.available_balance);
  } else {
    console.error('✗ Insufficient balance. Short by:', result.shortfall);
  }
}

// Lookup mapping
async function lookupMapping(segmentTypeId, sourceCode) {
  const response = await fetch(
    `/api/accounts-entities/mappings/lookup/?segment_type_id=${segmentTypeId}&source_code=${sourceCode}&direction=forward`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  const result = await response.json();
  console.log('Targets:', result.targets);
}
```

### Python (Requests)

```python
import requests

BASE_URL = "http://localhost:8000/api/accounts-entities"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

# Create envelope
def create_envelope():
    response = requests.post(
        f"{BASE_URL}/envelopes/",
        json={
            "segment_combination": {"1": "E001", "2": "A100", "3": "P001"},
            "envelope_amount": "100000.00",
            "fiscal_year": "FY2025",
            "description": "HR Salaries for AI Initiative"
        },
        headers=HEADERS
    )
    
    if response.status_code == 201:
        envelope = response.json()
        print(f"Created envelope: {envelope['id']}")
    else:
        print(f"Error: {response.json()}")

# Check balance
def check_balance(segments, amount, fiscal_year):
    response = requests.post(
        f"{BASE_URL}/envelopes/check-balance/",
        json={
            "segment_combination": segments,
            "required_amount": amount,
            "fiscal_year": fiscal_year
        },
        headers=HEADERS
    )
    
    result = response.json()
    
    if result['sufficient_balance']:
        print(f"✓ Available: ${result['available_balance']}")
    else:
        print(f"✗ Short by: ${result['shortfall']}")

# Validate transfer
def validate_transfer(from_segs, to_segs, fiscal_year):
    response = requests.post(
        f"{BASE_URL}/transfer-limits/validate/",
        json={
            "from_segments": from_segs,
            "to_segments": to_segs,
            "fiscal_year": fiscal_year
        },
        headers=HEADERS
    )
    
    result = response.json()
    print(f"Valid: {result['valid']}")
    if not result['valid']:
        print(f"Reason: {result['reason']}")
```

### cURL

```bash
# Create envelope
curl -X POST http://localhost:8000/api/accounts-entities/envelopes/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "segment_combination": {"1": "E001", "2": "A100", "3": "P001"},
    "envelope_amount": "100000.00",
    "fiscal_year": "FY2025",
    "description": "HR Salaries for AI Initiative"
  }'

# List envelopes for FY2025
curl -X GET "http://localhost:8000/api/accounts-entities/envelopes/?fiscal_year=FY2025" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check balance
curl -X POST http://localhost:8000/api/accounts-entities/envelopes/check-balance/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "segment_combination": {"1": "E001", "2": "A100", "3": "P001"},
    "required_amount": "5000.00",
    "fiscal_year": "FY2025"
  }'

# Lookup mapping (forward)
curl -X GET "http://localhost:8000/api/accounts-entities/mappings/lookup/?segment_type_id=1&source_code=E001&direction=forward" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Validate transfer
curl -X POST http://localhost:8000/api/accounts-entities/transfer-limits/validate/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "from_segments": {"1": "E001", "2": "A100"},
    "to_segments": {"1": "E002", "2": "A100"},
    "fiscal_year": "FY2025"
  }'
```

---

## 🔄 Migration Guide for Existing Clients

### From Phase 2 to Phase 3

**Breaking Changes:**
1. `envelope_amount` field **removed** from `XX_Segment` model
2. All envelope operations now use `XX_SegmentEnvelope` table via APIs

**Migration Steps:**

1. **Update segment format in your code:**
   ```javascript
   // OLD
   const segment = {
     segment_combination: {
       "1": { from_code: "E001", to_code: "E002" }
     }
   };
   
   // NEW
   const segment = {
     segment_combination: {
       "1": "E001"  // Single code, not from/to pair
     }
   };
   ```

2. **Migrate existing envelopes:**
   - Export envelopes from old `XX_Segment.envelope_amount` field
   - Create new envelopes via POST `/api/accounts-entities/envelopes/`

3. **Update balance checking:**
   ```javascript
   // OLD - Direct database query
   const segment = await Segment.findOne({ code: "E001" });
   const balance = segment.envelope_amount;
   
   // NEW - Use API
   const response = await fetch('/api/accounts-entities/envelopes/check-balance/', {
     method: 'POST',
     body: JSON.stringify({
       segment_combination: { "1": "E001" },
       required_amount: "5000.00",
       fiscal_year: "FY2025"
     })
   });
   const result = await response.json();
   const balance = result.available_balance;
   ```

4. **Update transfer validation:**
   - Use new `/transfer-limits/validate/` endpoint
   - Check response `valid` flag before submitting transfers

**Backward Compatibility:**
- Old format with `from_code/to_code` still works in managers
- Gradually migrate to new format at your own pace
- Both formats coexist during transition period

---

## 📊 Best Practices

1. **Always check balance before transfers:**
   ```javascript
   const balanceCheck = await checkBalance(segments, amount, fiscalYear);
   if (balanceCheck.sufficient_balance) {
     // Proceed with transfer
   } else {
     alert(`Insufficient balance. Short by $${balanceCheck.shortfall}`);
   }
   ```

2. **Validate transfers before submission:**
   ```javascript
   const validation = await validateTransfer(fromSegs, toSegs, fiscalYear);
   if (validation.valid) {
     // Submit transfer
   } else {
     alert(validation.reason);
   }
   ```

3. **Use soft deletes instead of hard deletes:**
   ```javascript
   // Preferred - soft delete (reversible)
   await fetch(`/api/accounts-entities/envelopes/${id}/`, { method: 'DELETE' });
   
   // Avoid - hard delete (permanent)
   await fetch(`/api/accounts-entities/envelopes/${id}/?hard_delete=true`, { method: 'DELETE' });
   ```

4. **Filter envelope lists for performance:**
   ```javascript
   // Bad - fetch all envelopes
   const all = await fetch('/api/accounts-entities/envelopes/');
   
   // Good - filter by fiscal year
   const fy2025 = await fetch('/api/accounts-entities/envelopes/?fiscal_year=FY2025');
   ```

5. **Use mappings for consolidation reporting:**
   ```javascript
   // Get all departments that consolidate to IT
   const result = await lookupMapping(1, 'E002', 'reverse');
   const sources = result.sources; // ["E001", "E004", "E007"]
   ```

---

## 🆘 Troubleshooting

### Issue: "Segment code does not exist"

**Cause:** Trying to create envelope with invalid segment code

**Solution:** Ensure segment exists in `XX_Segment` table before creating envelope

```bash
# Check if segment exists
GET /api/accounts-entities/segments/?segment_type_id=1&code=E001
```

### Issue: "Insufficient balance"

**Cause:** Trying to transfer more than available envelope balance

**Solution:** Check balance before transfer

```javascript
const check = await checkBalance(segments, amount, fiscalYear);
if (!check.sufficient_balance) {
  console.log(`Need to increase envelope by $${check.shortfall}`);
}
```

### Issue: "Transfer not allowed"

**Cause:** Segment has transfer limits that prevent the operation

**Solution:** Check transfer limits

```javascript
const validation = await validateTransfer(from, to, fiscalYear);
console.log(validation.reason); // "Source segment is not allowed to transfer"
```

### Issue: "Circular mapping detected"

**Cause:** Trying to create A→B when B→A already exists

**Solution:** Remove existing reverse mapping first

```bash
# Check for reverse mapping
GET /api/accounts-entities/mappings/?source_code=B&target_code=A

# Delete reverse mapping
DELETE /api/accounts-entities/mappings/<mapping_id>/
```

---

## 📚 Related Documentation

- [Phase 1: Segment Types and Values](PHASE_1_SETUP_GUIDE.md)
- [Phase 2: Transaction Segments](PHASE_2_TRANSACTION_GUIDE.md)
- [Phase 4: User Segment Permissions](PHASE_4_USER_SEGMENTS.md)
- [Phase 5: Oracle Integration](PHASE_5_ORACLE_INTEGRATION.md)

---

## 🎯 Summary

**Phase 3 provides 11 REST API endpoints for:**
- ✅ Creating and managing budget envelopes with flexible segment combinations
- ✅ Checking balance availability before transfers
- ✅ Creating and looking up segment mappings (consolidation, aliases, hierarchies)
- ✅ Defining and validating transfer limits with usage tracking

**Key Benefits:**
- 🚀 Simplified segment format (single code per segment type)
- 📦 Flexible envelope scopes (any segment combination)
- 🔒 Transfer permission control (source/target flags, count limits)
- 📊 Real-time balance and consumption tracking
- 🔄 Comprehensive validation before transfers

**Next Steps:**
1. Test all endpoints using `test_phase3_envelope_mapping_NEW.py`
2. Integrate envelope checks into transfer submission flow
3. Set up transfer limits for restricted segments
4. Create segment mappings for reporting consolidation

---

**Last Updated:** Phase 3 - June 11, 2025  
**API Version:** v1.0  
**Format:** NEW SIMPLIFIED (single code per segment)
