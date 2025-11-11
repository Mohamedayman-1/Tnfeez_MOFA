# Dynamic Segment API Guide

## Overview

The system now uses a **fully dynamic segment architecture** that supports any number of segment types (not limited to Entity, Account, Project). All segment types are configured in the `XX_SegmentType` table and can be extended without code changes.

## Key Improvements

### ✅ Before (Old System)
- **Hard-coded**: Only 3 segment types (Entity, Account, Project)
- **Separate views**: AccountListView, ProjectListView, EntityListView + separate create/upload views
- **Limited**: Cannot add new segment types without code changes
- **Rigid**: Hard-coded validation (must be 1, 2, or 3)
- **No level support**: Manual level management
- **No envelope support**: Separate envelope tables

### ✨ After (New Dynamic System)
- **Dynamic**: Any number of segment types from database
- **Unified views**: Single views for all types (List, Create, Detail, Update, Delete, Upload)
- **Extensible**: Add new segment types via database only
- **Flexible**: Query by ID or name (e.g., `segment_type=Account`)
- **Auto-level calculation**: Hierarchy levels calculated automatically
- **Envelope support**: Optional envelope_amount field for budgets

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
| **Bulk Upload** | `/segments/upload/?segment_type={id\|name}` | POST | Upload Excel file with multiple segments |

---

## API Endpoints

### 1. **Discover Available Segment Types**
```
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
      "description": null,
      "total_segments": 59,
      "endpoint_example": "/api/accounts-entities/segments/?segment_type=1",
      "endpoint_by_name": "/api/accounts-entities/segments/?segment_type=Entity (Cost Center)"
    },
    {
      "segment_id": 2,
      "segment_name": "Account",
      "description": null,
      "total_segments": 333,
      "endpoint_example": "/api/accounts-entities/segments/?segment_type=2",
      "endpoint_by_name": "/api/accounts-entities/segments/?segment_type=Account"
    },
    {
      "segment_id": 3,
      "segment_name": "Project",
      "description": null,
      "total_segments": 1722,
      "endpoint_example": "/api/accounts-entities/segments/?segment_type=3",
      "endpoint_by_name": "/api/accounts-entities/segments/?segment_type=Project"
    }
  ]
}
```

---

### 2. **List Segments (Unified Endpoint)**

```
GET /api/accounts-entities/segments/?segment_type={id_or_name}
```

#### **Required Parameters:**
- `segment_type` - Segment type ID (e.g., `1`, `2`, `3`) OR name (e.g., `Account`, `Project`)

#### **Optional Parameters:**
- `filter` - Filter type (default: `all`)
  - `all` - All segments (default)
  - `root` or `zero_level` - Only root segments (level=0)
  - `leaf` or `children` - Only leaf segments (no children)
  - `exclude_leaf` - All except leaf segments (only parents)
  - `exclude_root` - All except root segments (non-root only)
- `search` - Search by code or alias (case-insensitive)

---

### 3. **Create Segment (Unified Endpoint)**

```
POST /api/accounts-entities/segments/create/
```

#### **Request Body:**
```json
{
  "segment_type": 2,  // or "Account"
  "code": "5100",
  "parent_code": "5000",  // optional - auto-calculates level
  "alias": "Office Supplies",  // optional
  "envelope_amount": 50000.00,  // optional - budget/envelope limit
  "is_active": true  // optional, defaults to true
}
```

#### **Required Fields:**
- `segment_type` - Segment type ID or name (e.g., `2` or `"Account"`)
- `code` - Segment code (must be unique within segment type)

#### **Optional Fields:**
- `parent_code` - Parent segment code (for hierarchy, auto-calculates level)
- `alias` - Display name/alias for the segment
- `envelope_amount` - Budget/envelope amount for this segment (e.g., project budgets)
- `level` - Hierarchy level (auto-calculated from parent, manual override not recommended)
- `is_active` - Active status (defaults to `true`)

#### **Level Calculation (Automatic):**
- **No parent**: level = 0 (root)
- **Has parent**: level = parent.level + 1 (auto-calculated)
- **Manual override**: Can be provided, but not recommended

#### **Response (201 Created):**
```json
{
  "message": "Account created successfully.",
  "data": {
    "id": 334,
    "segment_type_name": "Account",
    "code": "5100",
    "parent_code": "5000",
    "alias": "Office Supplies",
    "level": 1,
    "envelope_amount": "50000.00",
    "is_active": true
  },
  "segment_type": "Account",
  "segment_type_id": 2
}
```

#### **Error Responses:**

**Missing segment_type (400 Bad Request):**
```json
{
  "message": "segment_type is required in request body.",
  "available_segment_types": [
    "1=Entity (Cost Center)",
    "2=Account",
    "3=Project"
  ]
}
```

**Invalid segment_type (404 Not Found):**
```json
{
  "message": "Invalid segment_type '99'. Not found in configured segment types.",
  "available_segment_types": [
    "1=Entity (Cost Center)",
    "2=Account",
    "3=Project"
  ]
}
```

**Missing code (400 Bad Request):**
```json
{
  "message": "code is required in request body."
}
```

**Duplicate code (409 Conflict):**
```json
{
  "message": "Segment with code '5100' already exists for segment type 'Account'.",
  "existing_segment": {
    "id": 334,
    "code": "5100",
    "alias": "Office Supplies",
    "level": 1
  }
}
```

**Parent not found (400 Bad Request):**
```json
{
  "message": "Parent segment with code '9999' not found for segment type 'Account'."
}
```

---

### 4. **Get Segment Details (Unified Endpoint)**

```
GET /api/accounts-entities/segments/<id>/
```

Retrieve full details of a specific segment by its ID. Works with any segment type.

**Response (200 OK):**
```json
{
  "message": "Account details retrieved successfully.",
  "data": {
    "id": 334,
    "segment_type_name": "Account",
    "code": "5100",
    "alias": "Office Supplies",
    "parent_code": "5000",
    "level": 1,
    "envelope_amount": "50000.00",
    "is_active": true
  },
  "segment_type": "Account",
  "segment_type_id": 2
}
```

**Error (404 Not Found):**
```json
{
  "message": "Segment not found."
}
```

---

### 5. **Update Segment (Unified Endpoint)**

```
PUT /api/accounts-entities/segments/<id>/update/
```

Update an existing segment. Supports updating all fields including auto-recalculating level when parent_code changes.

**Request Body (all fields optional):**
```json
{
  "code": "5150",  // Must remain unique within segment type
  "parent_code": "5100",  // Auto-recalculates level
  "alias": "Updated Office Supplies",
  "envelope_amount": 75000.00,
  "is_active": true,
  "level": 2  // Optional override (auto-calculated if parent_code changes)
}
```

**Response (200 OK):**
```json
{
  "message": "Account updated successfully.",
  "data": {
    "id": 334,
    "segment_type_name": "Account",
    "code": "5150",
    "alias": "Updated Office Supplies",
    "parent_code": "5100",
    "level": 2,
    "envelope_amount": "75000.00",
    "is_active": true
  },
  "segment_type": "Account",
  "segment_type_id": 2
}
```

**Error Responses:**

**Segment not found (404):**
```json
{
  "message": "Segment not found."
}
```

**Duplicate code (409 Conflict):**
```json
{
  "message": "Segment with code '5150' already exists for segment type 'Account'."
}
```

**Parent not found (400 Bad Request):**
```json
{
  "message": "Parent segment with code '9999' not found for segment type 'Account'."
}
```

**Invalid envelope_amount (400 Bad Request):**
```json
{
  "message": "Invalid envelope_amount. Must be a valid number.",
  "error": "..."
}
```

---

### 6. **Delete Segment (Unified Endpoint)**

```
DELETE /api/accounts-entities/segments/<id>/delete/
```

Delete a segment by its ID. Works with any segment type.

**⚠️ Important:** Cannot delete segments that have children. Delete child segments first.

**Response (200 OK):**
```json
{
  "message": "Account '5150' deleted successfully."
}
```

**Error Responses:**

**Segment not found (404):**
```json
{
  "message": "Segment not found."
}
```

**Has children (400 Bad Request):**
```json
{
  "message": "Cannot delete segment. It has child segments that depend on it.",
  "suggestion": "Delete child segments first, or remove their parent_code references."
}
```

---

## Complete CRUD Examples

### Example 1: Full Account Lifecycle

```bash
# 1. Create account
POST /api/accounts-entities/segments/create/
{
  "segment_type": 2,
  "code": "6000",
  "alias": "New Expense Category",
  "envelope_amount": 100000.00
}

# 2. Get account details
GET /api/accounts-entities/segments/334/

# 3. Update account
PUT /api/accounts-entities/segments/334/update/
{
  "alias": "Updated Expense Category",
  "envelope_amount": 150000.00
}

# 4. Delete account
DELETE /api/accounts-entities/segments/334/delete/
```

### Example 2: Project with Children

```bash
# 1. Create parent project
POST /api/accounts-entities/segments/create/
{
  "segment_type": "Project",
  "code": "PRJ-2025",
  "alias": "2025 Projects",
  "envelope_amount": 1000000.00
}

# 2. Create child project
POST /api/accounts-entities/segments/create/
{
  "segment_type": "Project",
  "code": "PRJ-2025-Q1",
  "parent_code": "PRJ-2025",
  "alias": "Q1 Projects",
  "envelope_amount": 250000.00
}

# 3. Update child project - change parent
PUT /api/accounts-entities/segments/456/update/
{
  "parent_code": "PRJ-2025-NEW",  // Level auto-recalculated
  "envelope_amount": 300000.00
}

# 4. Try to delete parent (will fail if has children)
DELETE /api/accounts-entities/segments/455/delete/
# Returns: "Cannot delete segment. It has child segments..."

# 5. Delete child first
DELETE /api/accounts-entities/segments/456/delete/

# 6. Now can delete parent
DELETE /api/accounts-entities/segments/455/delete/
```

---

## Usage Examples

### Example 1: Get All Accounts
```bash
GET /api/accounts-entities/segments/?segment_type=2
# OR
GET /api/accounts-entities/segments/?segment_type=Account
```

**Response:**
```json
{
  "message": "Account retrieved successfully.",
  "data": [...],
  "segment_type": "Account",
  "segment_type_id": 2,
  "filter_applied": "all",
  "total_count": 333
}
```

### Example 2: Create a New Account
```bash
POST /api/accounts-entities/segments/create/
Content-Type: application/json

{
  "segment_type": 2,
  "code": "5150",
  "parent_code": "5100",
  "alias": "Printer Supplies"
}
```

### Example 3: Create a Project with Envelope Amount
```bash
POST /api/accounts-entities/segments/create/
Content-Type: application/json

{
  "segment_type": "Project",
  "code": "PRJ-2025-001",
  "parent_code": "PRJ-2025",
  "alias": "Q1 Marketing Campaign",
  "envelope_amount": 150000.00,
  "is_active": true
}
```

### Example 4: Create a Root Entity (No Parent)
```bash
POST /api/accounts-entities/segments/create/
Content-Type: application/json

{
  "segment_type": "Entity (Cost Center)",
  "code": "20000",
  "alias": "New Department",
  "envelope_amount": 500000.00
}
```

### Example 5: Get Root Entities Only
```bash
GET /api/accounts-entities/segments/?segment_type=1&filter=root
```

### Example 6: Get Leaf Projects (No Children)
```bash
GET /api/accounts-entities/segments/?segment_type=3&filter=leaf
```

### Example 7: Search Accounts
```bash
GET /api/accounts-entities/segments/?segment_type=2&search=5100
```

### Example 8: Get Non-Root Entities (Exclude Roots)
```bash
GET /api/accounts-entities/segments/?segment_type=1&filter=exclude_root
```

### Example 9: Get Parent Accounts Only (Exclude Leaf)
```bash
GET /api/accounts-entities/segments/?segment_type=2&filter=exclude_leaf
```

---

## Backward Compatibility

### ⚠️ Important: Create Endpoints Changed

**Legacy create endpoints have been REMOVED** because the system is now fully dynamic:
```bash
# ❌ REMOVED - No longer available
POST /api/accounts-entities/accounts/create/
POST /api/accounts-entities/projects/create/
POST /api/accounts-entities/entities/create/
```

**Why removed?** The dynamic system doesn't know which segment_type corresponds to "accounts", "projects", or "entities" anymore. You must use the unified endpoint with explicit segment_type.

**✅ Use this instead:**
```bash
# NEW unified endpoint (REQUIRED)
POST /api/accounts-entities/segments/create/
Content-Type: application/json

{
  "segment_type": 2,  # or "Account"
  "code": "5150",
  "alias": "Office Supplies"
}
```

### Legacy List/Detail/Update/Delete Endpoints (Still Work)

These legacy endpoints are **still supported** for reading, updating, and deleting:

```bash
# List (still supported - redirects to unified view)
GET /api/accounts-entities/accounts/
GET /api/accounts-entities/projects/
GET /api/accounts-entities/entities/

# Detail/Update/Delete (still supported)
GET /api/accounts-entities/accounts/<id>/
PUT /api/accounts-entities/accounts/<id>/update/
DELETE /api/accounts-entities/accounts/<id>/delete/

GET /api/accounts-entities/projects/<id>/
PUT /api/accounts-entities/projects/<id>/update/
DELETE /api/accounts-entities/projects/<id>/delete/

GET /api/accounts-entities/entities/<id>/
PUT /api/accounts-entities/entities/<id>/update/
DELETE /api/accounts-entities/entities/<id>/delete/
```

### Migration Path for Clients

**Old code (no longer works):**
```javascript
// ❌ This will fail with 404
POST /api/accounts-entities/accounts/create/
{
  "account": "5150",
  "parent": "5100",
  "alias_default": "Office Supplies"
}
```

**New code (required):**
```javascript
// ✅ Use this instead
POST /api/accounts-entities/segments/create/
{
  "segment_type": 2,  // or "Account"
  "code": "5150",
  "parent_code": "5100",
  "alias": "Office Supplies"
}
```

---

## Adding New Segment Types

To add a new segment type (e.g., "Department", "Location"):

1. **Insert into database:**
```sql
INSERT INTO XX_SEGMENTTYPE_XX (segment_id, segment_name, description, created_at, updated_at)
VALUES (4, 'Department', 'Organizational departments', NOW(), NOW());
```

2. **Create segments via API:**
```bash
POST /api/accounts-entities/segments/create/
Content-Type: application/json

{
  "segment_type": 4,
  "code": "DEPT001",
  "alias": "HR Department"
}
```

3. **Query immediately:**
```bash
GET /api/accounts-entities/segments/?segment_type=4
# OR
GET /api/accounts-entities/segments/?segment_type=Department
```

**No code changes required!** ✨

---

## Hierarchy Management

The system **automatically calculates hierarchy levels** when creating segments:

- **Root segments** (no parent): level = 0
- **Child segments**: level = parent.level + 1

**Example:**
```bash
# Create root account (level 0)
POST /segments/create/
{"segment_type": 2, "code": "5000", "alias": "Expenses"}

# Create child account (level 1) - level auto-calculated
POST /segments/create/
{"segment_type": 2, "code": "5100", "parent_code": "5000", "alias": "Office Expenses"}

# Create grandchild account (level 2) - level auto-calculated
POST /segments/create/
{"segment_type": 2, "code": "5110", "parent_code": "5100", "alias": "Printer Supplies"}

# Create project with envelope
POST /segments/create/
{"segment_type": 3, "code": "PRJ-001", "alias": "Project A", "envelope_amount": 100000.00}
```

Result:
- `5000` → level 0 (root)
- `5100` → level 1 (child of 5000, auto-calculated)
- `5110` → level 2 (child of 5100, auto-calculated)
- `PRJ-001` → level 0 (root) with envelope_amount = 100000.00

---

## Error Handling

### Missing segment_type Parameter (GET)
```bash
GET /api/accounts-entities/segments/
```

**Response (400 Bad Request):**
```json
{
  "message": "segment_type parameter is required.",
  "available_segment_types": [
    "1=Entity (Cost Center)",
    "2=Account",
    "3=Project"
  ],
  "data": []
}
```

### Invalid segment_type (GET)
```bash
GET /api/accounts-entities/segments/?segment_type=99
```

**Response (404 Not Found):**
```json
{
  "message": "Invalid segment_type '99'. Not found in configured segment types.",
  "available_segment_types": [
    "1=Entity (Cost Center)",
    "2=Account",
    "3=Project"
  ],
  "data": []
}
```

---

## Benefits

1. ✅ **Extensibility**: Add unlimited segment types without code changes
2. ✅ **Consistency**: Single unified API for all segment types (list + create)
3. ✅ **Flexibility**: Query by ID or name
4. ✅ **Discovery**: Built-in endpoint to discover available types
5. ✅ **Maintainability**: One view instead of multiple separate views
6. ✅ **Future-proof**: Ready for multi-dimensional chart of accounts
7. ✅ **Backward compatible**: Legacy endpoints still work
8. ✅ **Automatic hierarchy**: Levels calculated automatically based on parent
9. ✅ **Validation**: Prevents duplicates and validates parent existence

---

## Migration Notes

### What Changed
- ✅ Removed hard-coded segment type validation (1, 2, 3)
- ✅ Removed separate AccountCreateView, ProjectCreateView, EntityCreateView classes
- ✅ Added unified `SegmentCreateView` with dynamic segment type support
- ✅ Added dynamic segment type lookup from database
- ✅ Added segment type name support (not just IDs)
- ✅ Added automatic level calculation based on parent_code
- ✅ Added duplicate code validation
- ✅ Added parent existence validation
- ✅ Added envelope_amount support for budget tracking
- ✅ Added unified bulk upload endpoint for all segment types

### What Stayed
- ✅ All filtering options (root, leaf, exclude_leaf, exclude_root, all)
- ✅ Search functionality (code and alias)
- ✅ Response format
- ✅ Pagination support
- ✅ Legacy endpoint URLs (backward compatible)
- ✅ Authentication requirements

---

## 7. Bulk Upload Segments

Upload multiple segments at once via Excel file.

### Endpoint
```
POST /api/accounts-entities/segments/upload/?segment_type={id|name}
Content-Type: multipart/form-data
```

### Query Parameters
- `segment_type` (required): Segment type ID or name

### Request Body
- **File**: Excel file with key `file`

### Excel File Format

| Column | Required | Description |
|--------|----------|-------------|
| Code | ✅ Yes | Segment code |
| ParentCode | ❌ Optional | Parent segment code |
| Alias | ❌ Optional | Display name |
| EnvelopeAmount | ❌ Optional | Budget/envelope amount |

**Example Excel:**
```excel
Code       | ParentCode | Alias              | EnvelopeAmount
11000      |            | Finance Division   | 5000000.00
11100      | 11000      | Accounting Dept    | 1000000.00
11110      | 11100      | Payroll Section    | 250000.00
```

### Features
- ✅ Auto-calculates hierarchy levels
- ✅ Supports optional envelope amounts
- ✅ Upserts (creates new, updates existing)
- ✅ Validates parent existence
- ✅ Returns detailed summary

### Example Request
```bash
POST /api/accounts-entities/segments/upload/?segment_type=Entity
Content-Type: multipart/form-data

file: entities.xlsx
```

### Success Response
```json
{
  "status": "ok",
  "message": "Processed 3 Entity segments successfully.",
  "summary": {
    "created": 3,
    "updated": 0,
    "skipped": 0,
    "errors": [],
    "segment_type": "Entity",
    "segment_type_id": 1
  }
}
```

### Error Response
```json
{
  "status": "ok",
  "message": "Processed 2 Entity segments successfully.",
  "summary": {
    "created": 2,
    "updated": 0,
    "skipped": 1,
    "errors": [
      {
        "code": "11110",
        "error": "Parent code '11100' not found. Process parent rows first."
      }
    ],
    "segment_type": "Entity",
    "segment_type_id": 1
  }
}
```

### Notes
- ⚠️ Parent segments must exist before children (upload parents first)
- ✅ First row auto-detected as header (will be skipped)
- ✅ Empty rows automatically skipped
- ✅ EnvelopeAmount column optional (omit if not needed)
- ✅ Works with any segment type

**See full documentation:** `SEGMENT_BULK_UPLOAD_GUIDE.md`

---

## Technical Details

### Database Schema
```
XX_SEGMENTTYPE_XX (Segment Type Configuration)
├── segment_id (PK) - Unique identifier
├── segment_name - Display name (e.g., "Account", "Project")
└── description - Optional description

XX_SEGMENT_XX (Segment Values - All Types)
├── id (PK)
├── segment_type_id (FK) - References XX_SegmentType
├── code - Segment code (unique per segment type)
├── parent_code - Parent segment (for hierarchy)
├── alias - Display name
├── level - Hierarchy level (0=root, 1=child, etc.)
├── envelope_amount - Budget/envelope limit (optional)
└── is_active - Active status
```

### Hierarchy Levels
- Calculated automatically during creation and bulk upload
- Level 0: Root nodes (no parent)
- Level N: Parent at level N-1
- Supports unlimited depth

### Envelope Amounts
- Optional decimal field (30 digits, 2 decimal places)
- Used for budget/limit tracking
- Supported in all CRUD operations and bulk upload
- Can be null for segments without budgets
- Can be corrected using: `python manage.py fix_segment_levels`

---

## Support

For questions or issues:
1. Check available segment types: `GET /api/accounts-entities/segment-types/`
2. Verify segment type exists in `XX_SEGMENTTYPE_XX` table
3. Run level correction: `python manage.py fix_segment_levels`
4. Check segment data in `XX_SEGMENT_XX` table

---

**Last Updated:** November 6, 2025  
**Version:** 2.1 - Dynamic Segment Architecture with Unified Create

