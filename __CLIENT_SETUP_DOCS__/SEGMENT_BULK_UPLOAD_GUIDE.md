# Segment Bulk Upload API Guide

## Overview

The system now provides a **unified dynamic bulk upload** endpoint that works with any segment type. This replaces the need for separate upload endpoints for each segment type and includes automatic level calculation and envelope amount support.

---

## Unified Upload Endpoint

### POST `/api/accounts-entities/segments/upload/?segment_type={id|name}`

Upload an Excel file containing multiple segments of any type.

**Query Parameters:**
- `segment_type` (required): Segment type ID or name (e.g., `1`, `Entity`, `Account`, `Project`)

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: Excel file with key `file`

**Excel File Format:**

| Column | Required | Description |
|--------|----------|-------------|
| Code | ✅ Yes | Segment code (unique within segment type) |
| ParentCode | ❌ Optional | Parent segment code (for hierarchy) |
| Alias | ❌ Optional | Display name / description |
| EnvelopeAmount | ❌ Optional | Budget/envelope limit (decimal) |

**Important Notes:**
- ✅ First row can be a header (will be auto-detected and skipped)
- ✅ Empty rows are automatically skipped
- ✅ **Level is calculated automatically** from parent_code
- ✅ EnvelopeAmount column is optional - omit if not needed
- ⚠️ Parent segments must exist before their children (process parents first)

---

## Features

### 1. ✅ Fully Dynamic
- Works with **any segment type** configured in `XX_SegmentType` table
- Not limited to Entity, Account, Project
- Add new segment types without code changes

### 2. ✅ Automatic Level Calculation
- **Root segments** (no parent): `level = 0`
- **Child segments**: `level = parent.level + 1`
- No manual level input needed

### 3. ✅ Envelope Amount Support
- Optional 4th column for budget/limit tracking
- Accepts decimals (e.g., `100000.00`)
- Can be left empty for segments without envelopes
- Validates numeric format

### 4. ✅ Upsert Logic
- **Existing segments**: Updates parent_code, alias, level, envelope_amount
- **New segments**: Creates with all provided data
- Safe to run multiple times (won't create duplicates)

### 5. ✅ Comprehensive Validation
- Checks parent segment exists
- Validates envelope_amount format
- Returns detailed error messages
- Transaction-based (all-or-nothing on critical errors)

---

## Usage Examples

### Example 1: Upload Entities (Cost Centers)

**Excel File** (`entities.xlsx`):
```
Code       | ParentCode | Alias                  | EnvelopeAmount
11000      |            | Finance Division       | 5000000.00
11100      | 11000      | Accounting Department  | 1000000.00
11110      | 11100      | Payroll Section       | 250000.00
12000      |            | Operations Division    | 3000000.00
12100      | 12000      | Logistics Department   | 800000.00
```

**API Call:**
```bash
POST /api/accounts-entities/segments/upload/?segment_type=Entity
Content-Type: multipart/form-data

file: entities.xlsx
```

**Response:**
```json
{
  "status": "ok",
  "message": "Processed 5 Entity segments successfully.",
  "summary": {
    "created": 5,
    "updated": 0,
    "skipped": 0,
    "errors": [],
    "segment_type": "Entity",
    "segment_type_id": 1
  }
}
```

**Result:**
- `11000`: level=0, envelope=5,000,000
- `11100`: level=1 (auto-calculated), envelope=1,000,000
- `11110`: level=2 (auto-calculated), envelope=250,000
- `12000`: level=0, envelope=3,000,000
- `12100`: level=1 (auto-calculated), envelope=800,000

---

### Example 2: Upload Accounts (Without Envelopes)

**Excel File** (`accounts.xlsx`):
```
Code  | ParentCode | Alias
5000  |            | Expenses
5100  | 5000       | Operating Expenses
5110  | 5100       | Salaries
5120  | 5100       | Utilities
6000  |            | Revenue
6100  | 6000       | Sales Revenue
```

**API Call:**
```bash
POST /api/accounts-entities/segments/upload/?segment_type=2
# OR
POST /api/accounts-entities/segments/upload/?segment_type=Account

file: accounts.xlsx
```

**Response:**
```json
{
  "status": "ok",
  "message": "Processed 6 Account segments successfully.",
  "summary": {
    "created": 6,
    "updated": 0,
    "skipped": 0,
    "errors": [],
    "segment_type": "Account",
    "segment_type_id": 2
  }
}
```

**Result:**
- `5000`: level=0, no envelope
- `5100`: level=1, no envelope
- `5110`, `5120`: level=2, no envelope
- `6000`: level=0, no envelope
- `6100`: level=1, no envelope

---

### Example 3: Upload Projects with Budgets

**Excel File** (`projects.xlsx`):
```
Code          | ParentCode    | Alias                    | EnvelopeAmount
PRJ-2025      |               | 2025 All Projects       | 10000000.00
PRJ-2025-Q1   | PRJ-2025      | Q1 2025 Projects        | 2500000.00
PRJ-2025-Q1-A | PRJ-2025-Q1   | Q1 Marketing Campaign   | 500000.00
PRJ-2025-Q1-B | PRJ-2025-Q1   | Q1 IT Infrastructure    | 750000.00
PRJ-2025-Q2   | PRJ-2025      | Q2 2025 Projects        | 3000000.00
```

**API Call:**
```bash
POST /api/accounts-entities/segments/upload/?segment_type=Project

file: projects.xlsx
```

**Response:**
```json
{
  "status": "ok",
  "message": "Processed 5 Project segments successfully.",
  "summary": {
    "created": 5,
    "updated": 0,
    "skipped": 0,
    "errors": [],
    "segment_type": "Project",
    "segment_type_id": 3
  }
}
```

**Result:**
- `PRJ-2025`: level=0, envelope=10,000,000
- `PRJ-2025-Q1`: level=1, envelope=2,500,000
- `PRJ-2025-Q1-A`: level=2, envelope=500,000
- `PRJ-2025-Q1-B`: level=2, envelope=750,000
- `PRJ-2025-Q2`: level=1, envelope=3,000,000

---

### Example 4: Update Existing Segments

**Scenario**: Need to update aliases and envelopes for existing segments

**Excel File** (`updates.xlsx`):
```
Code       | ParentCode | Alias                          | EnvelopeAmount
11100      | 11000      | Accounting Dept (Updated)      | 1200000.00
11110      | 11100      | Payroll Section (Expanded)    | 300000.00
```

**API Call:**
```bash
POST /api/accounts-entities/segments/upload/?segment_type=1

file: updates.xlsx
```

**Response:**
```json
{
  "status": "ok",
  "message": "Processed 2 Entity segments successfully.",
  "summary": {
    "created": 0,
    "updated": 2,
    "skipped": 0,
    "errors": [],
    "segment_type": "Entity",
    "segment_type_id": 1
  }
}
```

**Result:**
- Existing segments updated with new aliases and envelope amounts
- Levels recalculated if parent_code changed

---

## Error Handling

### Error Types

| Error | HTTP Status | When | Solution |
|-------|-------------|------|----------|
| No file uploaded | 400 | File not provided | Include file in request |
| Missing segment_type | 400 | No query parameter | Add `?segment_type=X` |
| Invalid segment_type | 404 | Type not found | Check available types via `/segment-types/` |
| Parent not found | 200 with errors | Parent doesn't exist | Upload parents first |
| Invalid envelope | 200 with errors | Non-numeric value | Fix Excel data |

### Example Error Response

**Scenario**: Parent codes don't exist yet

```json
{
  "status": "ok",
  "message": "Processed 2 Entity segments successfully.",
  "summary": {
    "created": 2,
    "updated": 0,
    "skipped": 2,
    "errors": [
      {
        "code": "11110",
        "error": "Parent code '11100' not found. Process parent rows first."
      },
      {
        "code": "11120",
        "error": "Parent code '11100' not found. Process parent rows first."
      }
    ],
    "segment_type": "Entity",
    "segment_type_id": 1
  }
}
```

**Solution**: Upload parent segments first, then retry children.

---

## Best Practices

### 1. ✅ Process Hierarchies in Order

**Correct Order:**
```
1. Upload root segments (no parents)
2. Upload level-1 children
3. Upload level-2 children
... and so on
```

**OR** include all levels in one file with roots first:
```excel
Code   | ParentCode | Alias
ROOT-1 |            | Root Level 1
ROOT-2 |            | Root Level 2
CHILD-1| ROOT-1     | Child of Root 1
CHILD-2| ROOT-2     | Child of Root 2
GC-1   | CHILD-1    | Grandchild
```

### 2. ✅ Use Consistent Code Format

- No spaces in codes (use dashes or underscores)
- Use consistent case (uppercase or lowercase)
- Avoid special characters except dash (-) and underscore (_)

```
✅ Good: 11000, PRJ-2025, DEPT_HR
❌ Bad: 11 000, PRJ 2025, DEPT/HR
```

### 3. ✅ Validate Excel Data First

Before uploading:
- Check no duplicate codes in the file
- Verify parent codes exist (or are in earlier rows)
- Confirm envelope amounts are numeric
- Remove any extra columns (only 4 max)

### 4. ✅ Use Headers for Clarity

Always include a header row (will be auto-skipped):
```excel
Code | ParentCode | Alias | EnvelopeAmount
```

### 5. ✅ Handle Envelopes Appropriately

- **Projects**: Usually have envelopes (budgets)
- **Entities**: May have envelopes (department budgets)
- **Accounts**: Usually don't have envelopes
- If not using envelopes, omit the 4th column entirely

---

## Legacy Upload Endpoints

### Still Supported (For Backward Compatibility)

The old individual upload endpoints still work but internally use the new unified system:

```bash
# Legacy endpoints (still work)
POST /api/accounts-entities/projects/upload/
POST /api/accounts-entities/accounts/upload/
POST /api/accounts-entities/entities/upload/
```

**Differences:**
- ✅ Now update `XX_Segment` table (unified model)
- ✅ Also update legacy tables (`XX_Project`, `XX_Account`, `XX_Entity`)
- ✅ Support envelope_amount in 4th column
- ✅ Auto-calculate levels

**Recommendation**: Use new unified endpoint for new implementations.

---

## Excel Template

### Template 1: With Envelopes (Projects, Entities)

```excel
Code       | ParentCode | Alias              | EnvelopeAmount
PRJ-001    |            | Main Project       | 1000000.00
PRJ-001-A  | PRJ-001    | Sub-project A      | 250000.00
PRJ-001-B  | PRJ-001    | Sub-project B      | 350000.00
```

### Template 2: Without Envelopes (Accounts)

```excel
Code  | ParentCode | Alias
1000  |            | Assets
1100  | 1000       | Current Assets
1110  | 1100       | Cash
```

### Template 3: Minimal (Code Only)

```excel
Code
CODE-1
CODE-2
CODE-3
```

---

## Quick Reference

```bash
# Discover available segment types
GET /api/accounts-entities/segment-types/

# Upload segments (any type)
POST /api/accounts-entities/segments/upload/?segment_type={id|name}
Content-Type: multipart/form-data
Body: file=<excel_file>

# Upload examples
POST .../segments/upload/?segment_type=1          # By ID
POST .../segments/upload/?segment_type=Entity     # By name
POST .../segments/upload/?segment_type=Account    # By name
POST .../segments/upload/?segment_type=Project    # By name
```

**Excel Columns:**
1. Code (required)
2. ParentCode (optional)
3. Alias (optional)
4. EnvelopeAmount (optional)

**Response Fields:**
- `created`: New segments created
- `updated`: Existing segments updated
- `skipped`: Rows skipped (errors or empty)
- `errors`: List of errors with codes

---

## Troubleshooting

### Issue: "Parent code not found"

**Cause:** Child row processed before parent row.

**Solution:**
1. Sort Excel file so parents come before children
2. OR upload in multiple batches (roots first, then children)

### Issue: "Invalid envelope_amount"

**Cause:** Non-numeric value in EnvelopeAmount column.

**Solution:**
1. Check for text in envelope cells
2. Remove currency symbols ($, €, etc.)
3. Use decimal format: `1000000.00`

### Issue: "segment_type parameter is required"

**Cause:** Missing `?segment_type=X` in URL.

**Solution:**
```bash
# Wrong
POST /api/accounts-entities/segments/upload/

# Correct
POST /api/accounts-entities/segments/upload/?segment_type=Entity
```

### Issue: All rows skipped

**Cause:** Possible header row detection issue or empty data.

**Solution:**
1. Check first row has at least one digit
2. Verify data starts in row 2 (after header)
3. Check for hidden characters in Excel

---

## Migration from Legacy Uploads

### Old Way (3 separate endpoints)

```bash
POST /api/accounts-entities/projects/upload/
POST /api/accounts-entities/accounts/upload/
POST /api/accounts-entities/entities/upload/
```

### New Way (1 unified endpoint)

```bash
POST /api/accounts-entities/segments/upload/?segment_type=Project
POST /api/accounts-entities/segments/upload/?segment_type=Account
POST /api/accounts-entities/segments/upload/?segment_type=Entity
```

**Advantages:**
- ✅ Works with **any segment type** (not just 3)
- ✅ Supports **custom segment types** added to system
- ✅ Handles **envelope amounts**
- ✅ **Auto-calculates levels**
- ✅ More **consistent API**

---

**Last Updated:** November 6, 2025  
**Version:** 1.0 - Unified Dynamic Bulk Upload  
**Status:** ✅ Production Ready
