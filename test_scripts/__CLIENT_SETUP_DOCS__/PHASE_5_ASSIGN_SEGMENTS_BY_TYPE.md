# Member Segment Assignment - Simplified Guide

## Understanding Segment Organization

Segments are organized by **Segment Type**:

```
Segment Type 1: Entity
├─ E001 (Finance Department)
├─ E002 (HR Department)
├─ E005 (IT Department)
└─ E009 (Operations)

Segment Type 2: Account
├─ A100 (Salaries)
├─ A200 (Travel)
├─ A300 (Equipment)
└─ A400 (Training)

Segment Type 3: Project
├─ P001 (Project Alpha)
├─ P005 (Project Beta)
├─ P011 (Project Gamma)
└─ P015 (Project Delta)
```

## Example Scenario

**Group Setup:**
- Security Group: "Finance Team"
- Group has these segments assigned:
  - **Entity (Type 1)**: E001, E002, E005, E009
  - **Account (Type 2)**: A100, A200, A300
  - **Project (Type 3)**: P001, P005, P011

**Members:**
- Manager → Sees ALL segments (no restriction)
- Accountant #1 → Should only see: E005, E009, A100, P005
- Accountant #2 → Should only see: E001, A200, A300, P011

## API Usage (RECOMMENDED FORMAT)

### Assign Segments by Type and Code

This is the **clearest and easiest** way:

```bash
POST /api/auth/security-groups/1/members/2/segments/
Content-Type: application/json

{
  "segments": {
    "1": ["E005", "E009"],      // Entity: segments 5 and 9
    "2": ["A100"],              // Account: segment 100
    "3": ["P005"]               // Project: segment 5
  }
}
```

**Response:**
```json
{
  "message": "Assigned 4 specific segments to member 'john.doe'",
  "assigned_count": 4,
  "access_mode": "restricted"
}
```

Now **Accountant #1** only sees:
- Entity: E005, E009
- Account: A100
- Project: P005

### Another Member with Different Segments

```bash
POST /api/auth/security-groups/1/members/3/segments/
Content-Type: application/json

{
  "segments": {
    "1": ["E001"],              // Entity: segment 1
    "2": ["A200", "A300"],      // Account: segments 200 and 300
    "3": ["P011"]               // Project: segment 11
  }
}
```

Now **Accountant #2** only sees:
- Entity: E001
- Account: A200, A300
- Project: P011

## Understanding Segment Type IDs

Your segment types are numbered (usually 1, 2, 3, etc.):

```bash
# Check your segment type IDs
GET /api/account-entitys/segments/types/

Response:
[
  {
    "segment_id": 1,
    "segment_name": "Entity",
    "is_required": true
  },
  {
    "segment_id": 2,
    "segment_name": "Account", 
    "is_required": true
  },
  {
    "segment_id": 3,
    "segment_name": "Project",
    "is_required": false
  }
]
```

## Real-World Examples

### Example 1: Regional Team

Group has 5 regions, assign each member to specific regions:

```bash
# Member handles only North and South regions
POST /api/auth/security-groups/1/members/5/segments/
{
  "segments": {
    "1": ["REGION_NORTH", "REGION_SOUTH"]
  }
}

# Another member handles East and West
POST /api/auth/security-groups/1/members/6/segments/
{
  "segments": {
    "1": ["REGION_EAST", "REGION_WEST"]
  }
}
```

### Example 2: Multi-Type Restriction

```bash
# Member can only work with:
# - Finance Entity (E001)
# - Salary and Travel Accounts (A100, A200)
# - Alpha and Beta Projects (P001, P005)

POST /api/auth/security-groups/1/members/7/segments/
{
  "segments": {
    "1": ["E001"],
    "2": ["A100", "A200"],
    "3": ["P001", "P005"]
  }
}
```

### Example 3: Single Segment Type

```bash
# Group only uses one segment type (e.g., departments)
# Member should only see Finance and HR departments

POST /api/auth/security-groups/1/members/8/segments/
{
  "segments": {
    "1": ["DEPT_FINANCE", "DEPT_HR"]
  }
}
```

## Verification

Check what segments a member can see:

```bash
GET /api/auth/security-groups/1/members/2/segments/

Response:
{
  "membership_id": 2,
  "user": "john.doe",
  "has_specific_assignments": true,
  "access_mode": "restricted",
  "accessible_segments": [
    {
      "segment_type_id": 1,
      "segment_type_name": "Entity",
      "segment_count": 2,
      "segments": [
        {"code": "E005", "alias": "IT Department"},
        {"code": "E009", "alias": "Operations"}
      ]
    },
    {
      "segment_type_id": 2,
      "segment_type_name": "Account",
      "segment_count": 1,
      "segments": [
        {"code": "A100", "alias": "Salaries"}
      ]
    },
    {
      "segment_type_id": 3,
      "segment_type_name": "Project",
      "segment_count": 1,
      "segments": [
        {"code": "P005", "alias": "Project Beta"}
      ]
    }
  ]
}
```

## Remove Restrictions

Give member full group access again:

```bash
DELETE /api/auth/security-groups/1/members/2/segments/

Response:
{
  "message": "Removed 4 specific segment assignments. Member now has full group access.",
  "removed_count": 4,
  "access_mode": "full_group_access"
}

# Now member sees ALL group segments again ✅
```

## Legacy Format (Still Supported)

If you need to use SecurityGroupSegment IDs directly:

```bash
# First, get the group details to see segment IDs
GET /api/auth/security-groups/1/

# Then use IDs in the request
POST /api/auth/security-groups/1/members/2/segments/
{
  "segment_assignment_ids": [14, 15, 18, 22]
}
```

## Quick Reference

### Assign Segments (Recommended)
```bash
POST /api/auth/security-groups/{group_id}/members/{membership_id}/segments/
{
  "segments": {
    "{segment_type_id}": ["code1", "code2"],
    "{segment_type_id}": ["code3"]
  }
}
```

### View Member Segments
```bash
GET /api/auth/security-groups/{group_id}/members/{membership_id}/segments/
```

### Remove Restrictions
```bash
DELETE /api/auth/security-groups/{group_id}/members/{membership_id}/segments/
```

## Error Handling

### Segment Not in Group
```bash
POST /api/auth/security-groups/1/members/2/segments/
{
  "segments": {
    "1": ["E999"]  // Not in group
  }
}

Response (400):
{
  "errors": [
    "Segment Type 1, Code 'E999' not found in group or not active"
  ]
}
```

### Invalid Segment Type
```bash
POST /api/auth/security-groups/1/members/2/segments/
{
  "segments": {
    "99": ["E001"]  // Type 99 doesn't exist
  }
}

Response (400):
{
  "errors": [
    "Segment Type 99, Code 'E001' not found in group or not active"
  ]
}
```

## Summary

✅ **Use segment type ID + code** - Clear and intuitive  
✅ **Required segments only** - Only segments already in group  
✅ **Multi-type support** - Assign across all segment types  
✅ **Flexible changes** - Update anytime  
✅ **Clear errors** - Validation tells you exactly what's wrong  

**Your Question Answered:**
> "The segments are known from segment type right? Like segment 5 and 9 and 11 are the required ones"

**Answer:** Yes! Use:
```json
{
  "segments": {
    "1": ["E005", "E009", "E011"]  // Segments 5, 9, 11 from Type 1
  }
}
```

Much clearer than using database IDs! 🎯
