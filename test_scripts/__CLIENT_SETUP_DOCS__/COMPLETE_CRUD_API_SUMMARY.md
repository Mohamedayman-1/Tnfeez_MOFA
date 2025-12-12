# Complete Dynamic Segment CRUD API - Summary

## Overview

The segment API is now **fully unified** with complete CRUD operations that work dynamically with any segment type. All operations support level auto-calculation and envelope_amount handling.

---

## Complete API Endpoints

| Operation | Endpoint | Method | Description |
|-----------|----------|--------|-------------|
| **Discovery** | `/segment-types/` | GET | List all available segment types |
| **List** | `/segments/?segment_type={id\|name}` | GET | List segments of a specific type |
| **Create** | `/segments/create/` | POST | Create new segment (any type) |
| **Detail** | `/segments/<id>/` | GET | Get segment details by ID |
| **Update** | `/segments/<id>/update/` | PUT | Update segment by ID |
| **Delete** | `/segments/<id>/delete/` | DELETE | Delete segment by ID |

---

## 1. Discovery - Get Available Segment Types

```bash
GET /api/accounts-entities/segment-types/
```

**Returns:**
- List of all configured segment types
- Segment counts
- Example endpoint URLs

---

## 2. List - Query Segments

```bash
GET /api/accounts-entities/segments/?segment_type=2&filter=all&search=5100
```

**Parameters:**
- `segment_type` (required): ID or name
- `filter` (optional): all, root, leaf, exclude_leaf, exclude_root
- `search` (optional): Search by code or alias

**Returns:**
- Filtered list of segments
- Includes: id, code, alias, parent_code, level, envelope_amount, is_active

---

## 3. Create - Add New Segment

```bash
POST /api/accounts-entities/segments/create/
Content-Type: application/json

{
  "segment_type": 2,  // Required - ID or name
  "code": "5150",  // Required - unique within segment type
  "parent_code": "5100",  // Optional - for hierarchy
  "alias": "Office Supplies",  // Optional
  "envelope_amount": 50000.00,  // Optional
  "is_active": true  // Optional (default: true)
}
```

**Features:**
- ✅ Auto-calculates level from parent_code
- ✅ Validates parent existence
- ✅ Prevents duplicate codes
- ✅ Supports envelope_amount for budgets

**Response:**
```json
{
  "message": "Account created successfully.",
  "data": {
    "id": 334,
    "segment_type_name": "Account",
    "code": "5150",
    "alias": "Office Supplies",
    "parent_code": "5100",
    "level": 1,  // Auto-calculated
    "envelope_amount": "50000.00",
    "is_active": true
  },
  "segment_type": "Account",
  "segment_type_id": 2
}
```

---

## 4. Detail - Get Segment Information

```bash
GET /api/accounts-entities/segments/334/
```

**Returns:**
- Full segment details
- Works with any segment type
- Returns 404 if not found

**Response:**
```json
{
  "message": "Account details retrieved successfully.",
  "data": {
    "id": 334,
    "segment_type_name": "Account",
    "code": "5150",
    "alias": "Office Supplies",
    "parent_code": "5100",
    "level": 1,
    "envelope_amount": "50000.00",
    "is_active": true
  },
  "segment_type": "Account",
  "segment_type_id": 2
}
```

---

## 5. Update - Modify Segment

```bash
PUT /api/accounts-entities/segments/334/update/
Content-Type: application/json

{
  "code": "5155",  // Optional - must stay unique
  "parent_code": "5200",  // Optional - triggers level recalc
  "alias": "Updated Office Supplies",  // Optional
  "envelope_amount": 75000.00,  // Optional
  "is_active": false,  // Optional
  "level": 2  // Optional - auto-calculated if parent changes
}
```

**Features:**
- ✅ Auto-recalculates level when parent_code changes
- ✅ Validates new parent existence
- ✅ Prevents duplicate codes
- ✅ Supports partial updates (send only fields to change)
- ✅ Validates envelope_amount format

**Level Recalculation:**
- If `parent_code` changes → level = new_parent.level + 1
- If `parent_code` removed → level = 0 (becomes root)
- Can manually override with `level` parameter

**Response:**
```json
{
  "message": "Account updated successfully.",
  "data": {
    "id": 334,
    "segment_type_name": "Account",
    "code": "5155",
    "alias": "Updated Office Supplies",
    "parent_code": "5200",
    "level": 2,  // Auto-recalculated
    "envelope_amount": "75000.00",
    "is_active": false
  },
  "segment_type": "Account",
  "segment_type_id": 2
}
```

---

## 6. Delete - Remove Segment

```bash
DELETE /api/accounts-entities/segments/334/delete/
```

**Features:**
- ✅ Prevents deletion of parent segments (must delete children first)
- ✅ Works with any segment type
- ✅ Returns friendly error if segment has children

**⚠️ Important:** Cannot delete segments that have children!

**Success Response:**
```json
{
  "message": "Account '5155' deleted successfully."
}
```

**Error - Has Children:**
```json
{
  "message": "Cannot delete segment. It has child segments that depend on it.",
  "suggestion": "Delete child segments first, or remove their parent_code references."
}
```

---

## Complete Workflow Example

### Scenario: Manage Project Hierarchy with Budgets

```bash
# Step 1: Discover available types
GET /api/accounts-entities/segment-types/
# Returns: segment_id=3 is "Project"

# Step 2: Create root project
POST /api/accounts-entities/segments/create/
{
  "segment_type": 3,
  "code": "PRJ-2025",
  "alias": "2025 All Projects",
  "envelope_amount": 5000000.00
}
# Response: id=100, level=0

# Step 3: Create child project
POST /api/accounts-entities/segments/create/
{
  "segment_type": "Project",
  "code": "PRJ-2025-Q1",
  "parent_code": "PRJ-2025",
  "alias": "Q1 Projects",
  "envelope_amount": 1250000.00
}
# Response: id=101, level=1 (auto-calculated)

# Step 4: Create grandchild project
POST /api/accounts-entities/segments/create/
{
  "segment_type": 3,
  "code": "PRJ-2025-Q1-001",
  "parent_code": "PRJ-2025-Q1",
  "alias": "Marketing Campaign",
  "envelope_amount": 300000.00
}
# Response: id=102, level=2 (auto-calculated)

# Step 5: Get project details
GET /api/accounts-entities/segments/102/
# Returns full details including level=2

# Step 6: Update project - increase budget
PUT /api/accounts-entities/segments/102/update/
{
  "envelope_amount": 450000.00,
  "alias": "Extended Marketing Campaign"
}
# Response: Updated successfully, level stays 2

# Step 7: Move project to different parent
PUT /api/accounts-entities/segments/102/update/
{
  "parent_code": "PRJ-2025-Q2"
}
# Response: level recalculated based on new parent

# Step 8: List all Q1 projects
GET /api/accounts-entities/segments/?segment_type=3&search=Q1

# Step 9: Try to delete parent (fails)
DELETE /api/accounts-entities/segments/101/delete/
# Error: "Cannot delete segment. It has child segments..."

# Step 10: Delete child first
DELETE /api/accounts-entities/segments/102/delete/
# Success

# Step 11: Now delete parent
DELETE /api/accounts-entities/segments/101/delete/
# Success
```

---

## Level Handling

### Automatic Level Calculation

| Action | Level Behavior |
|--------|----------------|
| **Create with no parent** | level = 0 (root) |
| **Create with parent** | level = parent.level + 1 |
| **Update parent_code** | level = new_parent.level + 1 |
| **Remove parent_code** | level = 0 (becomes root) |
| **Manual override** | Can provide `level` explicitly |

### Example: Level Changes

```bash
# Initial: PRJ-A (level 0) → PRJ-B (level 1) → PRJ-C (level 2)

# Move PRJ-C to be child of PRJ-A
PUT /segments/PRJ-C/update/
{"parent_code": "PRJ-A"}
# Result: PRJ-C level changes from 2 to 1

# Make PRJ-C a root project
PUT /segments/PRJ-C/update/
{"parent_code": null}
# Result: PRJ-C level changes to 0
```

---

## Envelope Amount Handling

### When to Use Envelope Amount

- ✅ **Projects**: Project budget limits
- ✅ **Cost Centers**: Department spending limits
- ✅ **Accounts**: Account-specific budgets
- ✅ **Any segment**: Any segment that needs budget tracking

### Example: Update Budgets

```bash
# Set initial budget
POST /segments/create/
{
  "segment_type": "Project",
  "code": "PRJ-001",
  "envelope_amount": 100000.00
}

# Increase budget
PUT /segments/123/update/
{
  "envelope_amount": 150000.00
}

# Remove budget limit
PUT /segments/123/update/
{
  "envelope_amount": null
}
```

---

## Error Handling Summary

| Error | Status | When | Solution |
|-------|--------|------|----------|
| Segment not found | 404 | Invalid ID | Check segment exists |
| Duplicate code | 409 | Code already exists | Use different code |
| Parent not found | 400 | Invalid parent_code | Check parent exists |
| Has children | 400 | Delete parent | Delete children first |
| Invalid envelope_amount | 400 | Bad number format | Use valid decimal |
| Missing segment_type | 400 | Create without type | Provide segment_type |

---

## Backward Compatibility

### ❌ Removed Endpoints (Breaking Change)
```bash
POST /api/accounts-entities/accounts/create/
POST /api/accounts-entities/projects/create/
POST /api/accounts-entities/entities/create/
```

### ✅ Still Supported (Legacy)
```bash
# List endpoints still work
GET /api/accounts-entities/accounts/
GET /api/accounts-entities/projects/
GET /api/accounts-entities/entities/

# Detail/Update/Delete still work
GET /api/accounts-entities/accounts/<id>/
PUT /api/accounts-entities/accounts/<id>/update/
DELETE /api/accounts-entities/accounts/<id>/delete/
```

### ⚠️ Migration Required
Use unified endpoints with `segment_type` parameter instead of legacy create endpoints.

---

## Benefits Summary

### 1. ✅ Fully Dynamic
- No hardcoded segment types
- Supports unlimited segment types
- Add new types via database only

### 2. ✅ Complete CRUD
- List, Create, Detail, Update, Delete
- All operations work with any segment type
- Consistent API across all types

### 3. ✅ Smart Level Management
- Auto-calculates hierarchy levels
- Updates on parent changes
- Prevents hierarchy errors

### 4. ✅ Budget Tracking
- Optional envelope_amount field
- Supports any segment type
- Decimal precision for accuracy

### 5. ✅ Data Integrity
- Prevents duplicate codes
- Validates parent existence
- Prevents orphan children

### 6. ✅ Developer Friendly
- Clear error messages
- Consistent response format
- Self-documenting via discovery API

---

## Quick Reference

```bash
# Discovery
GET /segment-types/

# CRUD Operations
GET    /segments/?segment_type={id|name}      # List
POST   /segments/create/                       # Create
GET    /segments/<id>/                         # Detail
PUT    /segments/<id>/update/                  # Update
DELETE /segments/<id>/delete/                  # Delete

# Required Fields
Create: segment_type, code
Update: (all optional)
Delete: (none)

# Auto-Calculated
level: Based on parent_code hierarchy

# Optional Fields
parent_code, alias, envelope_amount, is_active, level (override)
```

---

**Last Updated:** November 6, 2025  
**Version:** 3.0 - Complete Dynamic CRUD Operations  
**Status:** ✅ Production Ready
