# Phase 3 API Quick Reference Card

## 🎯 NEW SIMPLIFIED FORMAT
```json
{
  "segment_combination": {
    "1": "E001",  // Just code, no from/to pairs
    "2": "A100",
    "3": "P001"
  }
}
```

---

## 📋 All 11 Endpoints

### 🔵 ENVELOPES (Budget Management)

#### 1. Create Envelope
```http
POST /api/accounts-entities/envelopes/
Content-Type: application/json

{
  "segment_combination": {"1": "E001", "2": "A100"},
  "envelope_amount": "100000.00",
  "fiscal_year": "FY2025",
  "description": "HR Salaries Budget"
}

→ 201 Created: {id, segment_combination, envelope_amount, ...}
```

#### 2. List Envelopes
```http
GET /api/accounts-entities/envelopes/
GET /api/accounts-entities/envelopes/?fiscal_year=FY2025
GET /api/accounts-entities/envelopes/?segment_type_id=1&segment_code=E001

→ 200 OK: [{id, segment_combination, envelope_amount, ...}, ...]
```

#### 3. Get Envelope Detail
```http
GET /api/accounts-entities/envelopes/<id>/

→ 200 OK: {
  id, segment_combination, envelope_amount,
  consumed_balance, available_balance,
  fiscal_year, description, ...
}
```

#### 4. Update Envelope
```http
PUT /api/accounts-entities/envelopes/<id>/
Content-Type: application/json

{
  "envelope_amount": "120000.00",
  "description": "Updated budget"
}

→ 200 OK: {id, envelope_amount, ...}
```

#### 5. Delete Envelope
```http
DELETE /api/accounts-entities/envelopes/<id>/
DELETE /api/accounts-entities/envelopes/<id>/?hard_delete=true

→ 204 No Content
```

#### 6. Check Balance
```http
POST /api/accounts-entities/envelopes/check-balance/
Content-Type: application/json

{
  "segment_combination": {"1": "E001", "2": "A100"},
  "required_amount": "5000.00",
  "fiscal_year": "FY2025"
}

→ 200 OK: {
  sufficient_balance: true/false,
  envelope_amount, consumed_balance, available_balance,
  required_amount, shortfall
}
```

---

### 🟢 MAPPINGS (Consolidation, Aliases, Hierarchies)

#### 7. Create Mapping
```http
POST /api/accounts-entities/mappings/
Content-Type: application/json

{
  "segment_type_id": 1,
  "source_code": "E001",
  "target_code": "E002",
  "mapping_type": "CONSOLIDATION",
  "description": "HR consolidates to IT"
}

→ 201 Created: {id, segment_type_id, source_code, target_code, ...}
```

#### 8. List Mappings
```http
GET /api/accounts-entities/mappings/
GET /api/accounts-entities/mappings/?segment_type_id=1
GET /api/accounts-entities/mappings/?mapping_type=CONSOLIDATION
GET /api/accounts-entities/mappings/?source_code=E001

→ 200 OK: [{id, segment_type_id, source_code, target_code, ...}, ...]
```

#### 9. Lookup Mapping
```http
# Forward: Get targets from source
GET /api/accounts-entities/mappings/lookup/?segment_type_id=1&source_code=E001&direction=forward

→ 200 OK: {
  segment_type_id, source_code,
  targets: ["E002", "E003"],
  count: 2
}

# Reverse: Get sources from target
GET /api/accounts-entities/mappings/lookup/?segment_type_id=1&target_code=E002&direction=reverse

→ 200 OK: {
  segment_type_id, target_code,
  sources: ["E001", "E004"],
  count: 2
}
```

---

### 🟡 TRANSFER LIMITS (Permissions & Usage Tracking)

#### 10. Create Transfer Limit
```http
POST /api/accounts-entities/transfer-limits/
Content-Type: application/json

{
  "segment_combination": {"1": "E001"},
  "fiscal_year": "FY2025",
  "is_transfer_allowed_as_source": true,
  "is_transfer_allowed_as_target": true,
  "max_source_transfers": 10,
  "max_target_transfers": 20,
  "description": "10 outgoing, 20 incoming"
}

→ 201 Created: {
  id, segment_combination, fiscal_year,
  is_transfer_allowed_as_source, is_transfer_allowed_as_target,
  max_source_transfers, max_target_transfers,
  source_transfer_count, target_transfer_count, ...
}
```

#### 11. Validate Transfer
```http
POST /api/accounts-entities/transfer-limits/validate/
Content-Type: application/json

{
  "from_segments": {"1": "E001", "2": "A100"},
  "to_segments": {"1": "E002", "2": "A100"},
  "fiscal_year": "FY2025"
}

→ 200 OK: {
  valid: true/false,
  source_allowed, target_allowed,
  source_transfer_count, source_transfer_limit,
  target_transfer_count, target_transfer_limit,
  reason: "..."
}
```

---

## 🚀 Common Use Cases

### 1. Create Budget Envelope
```javascript
await fetch('/api/accounts-entities/envelopes/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    segment_combination: { "1": "E001", "2": "A100" },
    envelope_amount: "100000.00",
    fiscal_year: "FY2025",
    description: "HR Salaries"
  })
});
```

### 2. Check if Balance is Sufficient
```javascript
const response = await fetch('/api/accounts-entities/envelopes/check-balance/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    segment_combination: { "1": "E001", "2": "A100" },
    required_amount: "5000.00",
    fiscal_year: "FY2025"
  })
});

const result = await response.json();
if (!result.sufficient_balance) {
  alert(`Insufficient! Short by $${result.shortfall}`);
}
```

### 3. Find What E001 Consolidates To
```javascript
const response = await fetch(
  '/api/accounts-entities/mappings/lookup/?segment_type_id=1&source_code=E001&direction=forward'
);

const result = await response.json();
console.log('E001 consolidates to:', result.targets); // ["E002", "E003"]
```

### 4. Validate Transfer Before Submission
```javascript
const response = await fetch('/api/accounts-entities/transfer-limits/validate/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    from_segments: { "1": "E001", "2": "A100" },
    to_segments: { "1": "E002", "2": "A100" },
    fiscal_year: "FY2025"
  })
});

const result = await response.json();
if (!result.valid) {
  alert(result.reason); // "Source has reached maximum transfer limit"
}
```

### 5. Get All FY2025 Envelopes for Entity E001
```javascript
const response = await fetch(
  '/api/accounts-entities/envelopes/?fiscal_year=FY2025&segment_type_id=1&segment_code=E001'
);

const envelopes = await response.json();
envelopes.forEach(env => {
  console.log(`${env.description}: $${env.envelope_amount}`);
});
```

---

## 🎨 Python Examples

```python
import requests

BASE_URL = "http://localhost:8000/api/accounts-entities"

# Create envelope
requests.post(
    f"{BASE_URL}/envelopes/",
    json={
        "segment_combination": {"1": "E001", "2": "A100"},
        "envelope_amount": "100000.00",
        "fiscal_year": "FY2025",
        "description": "HR Salaries"
    }
)

# Check balance
response = requests.post(
    f"{BASE_URL}/envelopes/check-balance/",
    json={
        "segment_combination": {"1": "E001", "2": "A100"},
        "required_amount": "5000.00",
        "fiscal_year": "FY2025"
    }
)
result = response.json()
print(f"Available: ${result['available_balance']}")

# Lookup mapping
response = requests.get(
    f"{BASE_URL}/mappings/lookup/",
    params={
        "segment_type_id": 1,
        "source_code": "E001",
        "direction": "forward"
    }
)
result = response.json()
print(f"Targets: {result['targets']}")

# Validate transfer
response = requests.post(
    f"{BASE_URL}/transfer-limits/validate/",
    json={
        "from_segments": {"1": "E001", "2": "A100"},
        "to_segments": {"1": "E002", "2": "A100"},
        "fiscal_year": "FY2025"
    }
)
result = response.json()
print(f"Valid: {result['valid']}, Reason: {result['reason']}")
```

---

## 🔴 Common Errors

| Status | Error | Cause | Solution |
|--------|-------|-------|----------|
| 400 | "Invalid segment combination" | Segment code doesn't exist | Check segments exist first |
| 400 | "Insufficient balance" | Not enough budget | Increase envelope or reduce amount |
| 400 | "Circular mapping detected" | A→B when B→A exists | Remove reverse mapping |
| 404 | "Envelope not found" | Invalid envelope ID | Check ID is correct |
| 403 | "Transfer not allowed" | Segment has restrictions | Check transfer limits |

---

## 💡 Pro Tips

1. **Always check balance before transfers:**
   ```javascript
   const check = await checkBalance(segments, amount);
   if (check.sufficient_balance) submitTransfer();
   ```

2. **Use soft deletes (reversible):**
   ```javascript
   DELETE /api/accounts-entities/envelopes/<id>/  // Good
   // Avoid: ?hard_delete=true (permanent)
   ```

3. **Filter lists for performance:**
   ```javascript
   // Good: /envelopes/?fiscal_year=FY2025
   // Bad:  /envelopes/ (returns everything)
   ```

4. **Validate transfers before submission:**
   ```javascript
   const valid = await validateTransfer(from, to, fy);
   if (valid.valid) submitTransfer();
   ```

5. **Use mappings for consolidation:**
   ```javascript
   const targets = await lookupMapping(1, "E001", "forward");
   // Returns all entities E001 consolidates to
   ```

---

## 📦 Response Fields

### Envelope Object
```javascript
{
  id: 1,
  segment_combination: {"1": "E001", "2": "A100"},
  envelope_amount: "100000.00",
  consumed_balance: "25000.00",      // Calculated
  available_balance: "75000.00",     // Calculated
  fiscal_year: "FY2025",
  description: "...",
  is_active: true,
  created_at: "2025-06-11T10:30:00Z",
  updated_at: "2025-06-11T10:30:00Z"
}
```

### Mapping Object
```javascript
{
  id: 1,
  segment_type_id: 1,
  source_code: "E001",
  target_code: "E002",
  mapping_type: "CONSOLIDATION",  // or "ALIAS", "PARENT_CHILD", "CUSTOM"
  description: "...",
  is_active: true,
  created_at: "2025-06-11T10:30:00Z"
}
```

### Transfer Limit Object
```javascript
{
  id: 1,
  segment_combination: {"1": "E001"},
  fiscal_year: "FY2025",
  is_transfer_allowed_as_source: true,
  is_transfer_allowed_as_target: true,
  max_source_transfers: 10,        // null = unlimited
  max_target_transfers: 20,        // null = unlimited
  source_transfer_count: 3,        // Current usage
  target_transfer_count: 5,        // Current usage
  description: "...",
  is_active: true
}
```

---

## 🔗 Related Docs

- **Full API Guide:** [PHASE_3_API_GUIDE.md](PHASE_3_API_GUIDE.md)
- **Test Script:** [test_phase3_envelope_mapping_NEW.py](test_phase3_envelope_mapping_NEW.py)
- **Phase 2:** [PHASE_2_TRANSACTION_GUIDE.md](PHASE_2_TRANSACTION_GUIDE.md)
- **Phase 4:** [PHASE_4_USER_SEGMENTS.md](PHASE_4_USER_SEGMENTS.md)

---

**API Version:** v1.0 | **Format:** NEW SIMPLIFIED (single code)  
**Base URL:** `/api/accounts-entities/` | **Auth:** Bearer Token Required
