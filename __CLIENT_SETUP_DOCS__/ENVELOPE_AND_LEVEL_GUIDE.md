# Envelope Amount & Level Handling - Quick Reference

## Overview
The `SegmentCreateView` now properly handles both **automatic level calculation** and **envelope_amount** for segments.

---

## Level Calculation (Automatic)

### How It Works
The system **automatically calculates** the hierarchy level based on the parent_code:

| Scenario | Level Calculation |
|----------|-------------------|
| **No parent_code** | level = 0 (root segment) |
| **Has parent_code** | level = parent.level + 1 |
| **Manual override** | Can provide `level` in request (not recommended) |

### Examples

#### Example 1: Root Segment (No Parent)
```json
POST /segments/create/
{
  "segment_type": 2,
  "code": "5000",
  "alias": "Expenses"
}
```
**Result**: level = 0 (automatically set)

#### Example 2: Child Segment (Has Parent)
```json
POST /segments/create/
{
  "segment_type": 2,
  "code": "5100",
  "parent_code": "5000",
  "alias": "Office Expenses"
}
```
**Result**: level = 1 (parent "5000" has level 0, so 0 + 1 = 1)

#### Example 3: Grandchild Segment
```json
POST /segments/create/
{
  "segment_type": 2,
  "code": "5110",
  "parent_code": "5100",
  "alias": "Printer Supplies"
}
```
**Result**: level = 2 (parent "5100" has level 1, so 1 + 1 = 2)

---

## Envelope Amount (Optional)

### What Is It?
`envelope_amount` is an **optional budget/envelope limit** that can be assigned to any segment. This is commonly used for:
- **Projects**: Project budget envelopes
- **Cost Centers**: Department budget limits
- **Accounts**: Account spending limits

### Field Details
- **Type**: Decimal (30 digits, 2 decimal places)
- **Optional**: Can be `null` or omitted
- **Validation**: Must be a valid number

### Examples

#### Example 1: Project with Envelope
```json
POST /segments/create/
{
  "segment_type": "Project",
  "code": "PRJ-2025-001",
  "alias": "Q1 Marketing Campaign",
  "envelope_amount": 150000.00
}
```
**Result**: Project created with $150,000 budget envelope

#### Example 2: Cost Center with Budget Limit
```json
POST /segments/create/
{
  "segment_type": 1,
  "code": "20000",
  "alias": "IT Department",
  "envelope_amount": 500000.00
}
```
**Result**: Cost center created with $500,000 budget limit

#### Example 3: Account without Envelope
```json
POST /segments/create/
{
  "segment_type": 2,
  "code": "6000",
  "alias": "Revenue"
}
```
**Result**: Account created with envelope_amount = null (no limit)

#### Example 4: Child Project with Envelope
```json
POST /segments/create/
{
  "segment_type": 3,
  "code": "PRJ-2025-001-A",
  "parent_code": "PRJ-2025-001",
  "alias": "Social Media Campaign",
  "envelope_amount": 50000.00
}
```
**Result**: 
- Sub-project with $50,000 envelope
- level = 1 (parent level + 1)

---

## Full Example: Complete Hierarchy with Envelopes

```bash
# Step 1: Create root project
POST /segments/create/
{
  "segment_type": 3,
  "code": "PRJ-2025",
  "alias": "2025 Projects",
  "envelope_amount": 1000000.00
}
# Result: level=0, envelope_amount=1000000.00

# Step 2: Create child project
POST /segments/create/
{
  "segment_type": 3,
  "code": "PRJ-2025-Q1",
  "parent_code": "PRJ-2025",
  "alias": "Q1 Projects",
  "envelope_amount": 250000.00
}
# Result: level=1 (auto-calculated), envelope_amount=250000.00

# Step 3: Create grandchild project
POST /segments/create/
{
  "segment_type": 3,
  "code": "PRJ-2025-Q1-001",
  "parent_code": "PRJ-2025-Q1",
  "alias": "Marketing Campaign",
  "envelope_amount": 100000.00
}
# Result: level=2 (auto-calculated), envelope_amount=100000.00
```

**Hierarchy Created:**
```
PRJ-2025 (2025 Projects) - Level 0 - $1,000,000
└── PRJ-2025-Q1 (Q1 Projects) - Level 1 - $250,000
    └── PRJ-2025-Q1-001 (Marketing Campaign) - Level 2 - $100,000
```

---

## Error Handling

### Invalid Envelope Amount
```json
POST /segments/create/
{
  "segment_type": 2,
  "code": "5000",
  "envelope_amount": "invalid"
}
```

**Response (400 Bad Request):**
```json
{
  "message": "Invalid envelope_amount. Must be a valid number.",
  "error": "..."
}
```

### Parent Not Found (Affects Level Calculation)
```json
POST /segments/create/
{
  "segment_type": 2,
  "code": "5100",
  "parent_code": "9999"  // Doesn't exist
}
```

**Response (400 Bad Request):**
```json
{
  "message": "Parent segment with code '9999' not found for segment type 'Account'."
}
```

---

## Response Format

### Success Response
```json
{
  "message": "Project created successfully.",
  "data": {
    "id": 123,
    "segment_type_name": "Project",
    "code": "PRJ-2025-001",
    "alias": "Marketing Campaign",
    "parent_code": "PRJ-2025",
    "level": 1,
    "envelope_amount": "100000.00",
    "is_active": true
  },
  "segment_type": "Project",
  "segment_type_id": 3
}
```

### Fields Returned
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique segment ID |
| `segment_type_name` | string | Segment type display name |
| `code` | string | Segment code |
| `alias` | string | Display name/description |
| `parent_code` | string/null | Parent segment code |
| `level` | integer | Hierarchy level (0=root) |
| `envelope_amount` | decimal/null | Budget/envelope amount |
| `is_active` | boolean | Active status |

---

## Use Cases

### Use Case 1: Project Budget Management
```json
// Create project with total budget
POST /segments/create/
{
  "segment_type": "Project",
  "code": "INFRA-2025",
  "alias": "Infrastructure Upgrade",
  "envelope_amount": 5000000.00
}

// Create sub-projects with allocated budgets
POST /segments/create/
{
  "segment_type": "Project",
  "code": "INFRA-2025-SERVER",
  "parent_code": "INFRA-2025",
  "alias": "Server Upgrade",
  "envelope_amount": 2000000.00
}

POST /segments/create/
{
  "segment_type": "Project",
  "code": "INFRA-2025-NETWORK",
  "parent_code": "INFRA-2025",
  "alias": "Network Upgrade",
  "envelope_amount": 1500000.00
}
```

### Use Case 2: Department Cost Center Hierarchy
```json
// Create main department
POST /segments/create/
{
  "segment_type": 1,
  "code": "10000",
  "alias": "Operations",
  "envelope_amount": 10000000.00
}

// Create sub-departments
POST /segments/create/
{
  "segment_type": 1,
  "code": "11000",
  "parent_code": "10000",
  "alias": "IT Operations",
  "envelope_amount": 3000000.00
}

POST /segments/create/
{
  "segment_type": 1,
  "code": "12000",
  "parent_code": "10000",
  "alias": "Facilities",
  "envelope_amount": 2000000.00
}
```

### Use Case 3: Account Hierarchy (No Envelopes)
```json
// Accounts typically don't have envelopes
POST /segments/create/
{
  "segment_type": 2,
  "code": "5000",
  "alias": "Expenses"
}

POST /segments/create/
{
  "segment_type": 2,
  "code": "5100",
  "parent_code": "5000",
  "alias": "Operating Expenses"
}
```

---

## Key Features Summary

✅ **Automatic Level Calculation**
- No need to manually calculate hierarchy depth
- Prevents level inconsistencies
- Updates automatically based on parent relationship

✅ **Envelope Amount Support**
- Optional field for budget/limit tracking
- Supports decimal values (30 digits, 2 decimal places)
- Can be assigned to any segment type
- Null/empty if not applicable

✅ **Validation**
- Validates parent existence before creating child
- Validates envelope_amount is a valid number
- Prevents duplicate codes within segment type

✅ **Flexible**
- Works with any segment type (not just 3)
- Can mix segments with/without envelopes
- Manual level override available (not recommended)

---

## Best Practices

1. **Let the system calculate levels** - Don't manually provide `level` unless absolutely necessary
2. **Use envelope_amount for budget tracking** - Projects, cost centers, or any segment that needs budget limits
3. **Create parent before child** - Ensure parent exists before creating child segments
4. **Use meaningful codes** - Easy to identify and maintain
5. **Consistent envelope usage** - If using envelopes, be consistent within a segment type

---

**Last Updated:** November 6, 2025  
**Version:** 2.2 - Level & Envelope Amount Support
