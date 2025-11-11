# BREAKING CHANGES - Dynamic Segment API v2.0

## ⚠️ Breaking Change Alert

### Date: November 6, 2025
### Version: 2.0 → 2.1

---

## What Changed

### ❌ Removed Endpoints

The following legacy create endpoints have been **permanently removed**:

```
POST /api/accounts-entities/accounts/create/
POST /api/accounts-entities/projects/create/
POST /api/accounts-entities/entities/create/
```

### ✅ Replacement

Use the new unified endpoint with explicit `segment_type`:

```
POST /api/accounts-entities/segments/create/
```

---

## Why This Change?

The system is now **fully dynamic** and no longer hardcodes segment types. The old endpoints assumed:
- `/accounts/create/` → segment_type = 2 (Account)
- `/projects/create/` → segment_type = 3 (Project)
- `/entities/create/` → segment_type = 1 (Entity)

**Problem:** This hardcoding prevented the system from supporting unlimited segment types and violated the dynamic architecture principle.

**Solution:** Remove hardcoded mappings. Clients must explicitly specify `segment_type` in the request body.

---

## Migration Required

### ❌ Old Code (No Longer Works)

```javascript
// This will return 404 Not Found
fetch('/api/accounts-entities/accounts/create/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    account: '5150',
    parent: '5100',
    alias_default: 'Office Supplies'
  })
})
```

### ✅ New Code (Required)

```javascript
// Use unified endpoint with segment_type
fetch('/api/accounts-entities/segments/create/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    segment_type: 2,  // or "Account"
    code: '5150',
    parent_code: '5100',
    alias: 'Office Supplies'
  })
})
```

---

## Field Name Changes

| Old Field Name | New Field Name | Notes |
|----------------|----------------|-------|
| `account` / `project` / `entity` | `code` | Unified field name |
| `parent` | `parent_code` | Consistent naming |
| `alias_default` | `alias` | Simplified name |
| N/A | `segment_type` | **NEW - Required** |
| N/A | `level` | Auto-calculated (optional) |
| N/A | `envelope_amount` | **NEW - Optional** |

---

## Complete Migration Examples

### Example 1: Create Account

**Before:**
```json
POST /api/accounts-entities/accounts/create/
{
  "account": "5100",
  "parent": "5000",
  "alias_default": "Office Expenses"
}
```

**After:**
```json
POST /api/accounts-entities/segments/create/
{
  "segment_type": 2,
  "code": "5100",
  "parent_code": "5000",
  "alias": "Office Expenses"
}
```

### Example 2: Create Project with Envelope

**Before:**
```json
POST /api/accounts-entities/projects/create/
{
  "project": "PRJ-001",
  "parent": "PRJ",
  "alias_default": "Marketing Campaign"
}
// (No envelope support in old system)
```

**After:**
```json
POST /api/accounts-entities/segments/create/
{
  "segment_type": "Project",
  "code": "PRJ-001",
  "parent_code": "PRJ",
  "alias": "Marketing Campaign",
  "envelope_amount": 150000.00
}
```

### Example 3: Create Entity (Cost Center)

**Before:**
```json
POST /api/accounts-entities/entities/create/
{
  "entity": "11000",
  "parent": "10000",
  "alias_default": "IT Department"
}
```

**After:**
```json
POST /api/accounts-entities/segments/create/
{
  "segment_type": 1,
  "code": "11000",
  "parent_code": "10000",
  "alias": "IT Department",
  "envelope_amount": 500000.00
}
```

---

## What Still Works (No Changes Required)

### ✅ List Endpoints
```bash
GET /api/accounts-entities/accounts/
GET /api/accounts-entities/projects/
GET /api/accounts-entities/entities/
GET /api/accounts-entities/segments/?segment_type=2
```

### ✅ Detail Endpoints
```bash
GET /api/accounts-entities/accounts/<id>/
GET /api/accounts-entities/projects/<id>/
GET /api/accounts-entities/entities/<id>/
```

### ✅ Update Endpoints
```bash
PUT /api/accounts-entities/accounts/<id>/update/
PUT /api/accounts-entities/projects/<id>/update/
PUT /api/accounts-entities/entities/<id>/update/
```

### ✅ Delete Endpoints
```bash
DELETE /api/accounts-entities/accounts/<id>/delete/
DELETE /api/accounts-entities/projects/<id>/delete/
DELETE /api/accounts-entities/entities/<id>/delete/
```

---

## Testing Your Migration

### Step 1: Find All Create Calls
Search your codebase for:
```
/accounts/create/
/projects/create/
/entities/create/
```

### Step 2: Update Each Call
Replace with:
```
/segments/create/
```

And add `segment_type` to request body.

### Step 3: Update Field Names
- `account` / `project` / `entity` → `code`
- `parent` → `parent_code`
- `alias_default` → `alias`
- Add `segment_type` (required)

### Step 4: Test
```bash
# Test account creation
curl -X POST http://localhost:8000/api/accounts-entities/segments/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "segment_type": 2,
    "code": "TEST001",
    "alias": "Test Account"
  }'
```

---

## Benefits of This Change

1. ✅ **Truly Dynamic** - No hardcoded segment type mappings
2. ✅ **Unlimited Types** - Support any number of segment types
3. ✅ **Consistent API** - Single endpoint for all operations
4. ✅ **Better Validation** - Explicit segment_type required
5. ✅ **New Features** - Envelope amount support, auto-level calculation
6. ✅ **Future-Proof** - Ready for multi-dimensional COA

---

## Support

### Discover Available Segment Types
```bash
GET /api/accounts-entities/segment-types/
```

**Response:**
```json
{
  "message": "Available segment types retrieved successfully.",
  "total_types": 3,
  "data": [
    {
      "segment_id": 1,
      "segment_name": "Entity (Cost Center)",
      "total_segments": 59,
      "endpoint_example": "/segments/?segment_type=1"
    },
    {
      "segment_id": 2,
      "segment_name": "Account",
      "total_segments": 333,
      "endpoint_example": "/segments/?segment_type=2"
    },
    {
      "segment_id": 3,
      "segment_name": "Project",
      "total_segments": 1722,
      "endpoint_example": "/segments/?segment_type=3"
    }
  ]
}
```

### Quick Reference

| Segment Type | ID | Name | Old Endpoint | New Endpoint |
|--------------|----|----|--------------|--------------|
| Entity | 1 | Entity (Cost Center) | `/entities/create/` | `/segments/create/` + `"segment_type": 1` |
| Account | 2 | Account | `/accounts/create/` | `/segments/create/` + `"segment_type": 2` |
| Project | 3 | Project | `/projects/create/` | `/segments/create/` + `"segment_type": 3` |

---

## Timeline

- **Now**: Old endpoints return 404 Not Found
- **Action Required**: Update all client code immediately
- **Support**: Legacy read/update/delete endpoints still work
- **Documentation**: Updated guides available in `__CLIENT_SETUP_DOCS__/`

---

## Questions?

1. Check the updated API guide: `DYNAMIC_SEGMENT_API_GUIDE.md`
2. Review migration examples: `SEGMENT_CREATE_MIGRATION.md`
3. Read envelope & level guide: `ENVELOPE_AND_LEVEL_GUIDE.md`

---

**Last Updated:** November 6, 2025  
**Version:** 2.1 - Fully Dynamic (Breaking Changes)  
**Migration Status:** ⚠️ IMMEDIATE ACTION REQUIRED
