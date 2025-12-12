# Phase 5: Member-Specific Segment Filtering

## Overview

This feature allows **group managers to restrict individual members' access to specific segments** within a security group. Instead of all members seeing all group segments, you can now:

- Group has 10 segments (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
- Member #1 sees segments 1, 2, 3 (restricted)
- Member #2 sees segments 5, 6 (restricted)
- Member #3 sees ALL 10 segments (no restriction)

## How It Works

### Default Behavior (No Restrictions)

When a user is added to a security group **WITHOUT specific segment assignments**, they see **ALL segments** assigned to the group:

```
Security Group: "Finance Team"
├─ Group Segments: E001, E002, E003, A100, A200
├─ Member: User1 (Accountant)
│  └─ assigned_segments: EMPTY
│  └─ Sees: E001, E002, E003, A100, A200 ✅ (ALL group segments)
```

### Restricted Access (With Specific Assignments)

When a group manager assigns **specific segments to a member**, that member sees **ONLY those segments**:

```
Security Group: "Finance Team"
├─ Group Segments: E001, E002, E003, A100, A200
├─ Member: User2 (Manager)
│  └─ assigned_segments: [E001, A100]
│  └─ Sees: E001, A100 ✅ (ONLY assigned segments)
```

## Database Model Changes

### XX_UserGroupMembership Model

Added new ManyToMany field:

```python
class XX_UserGroupMembership(models.Model):
    user = models.ForeignKey(xx_User, ...)
    security_group = models.ForeignKey(XX_SecurityGroup, ...)
    assigned_roles = models.ManyToManyField(XX_SecurityGroupRole, ...)
    
    # NEW: Member-specific segment restrictions
    assigned_segments = models.ManyToManyField(
        'XX_SecurityGroupSegment',
        related_name='member_assignments',
        blank=True,
        help_text="Specific segments this member can access. If empty, member sees all group segments."
    )
```

### Validation Rules

1. **Segments must belong to the group**: Can't assign segment from Group A to member of Group B
2. **Empty = Full Access**: If `assigned_segments` is empty, member sees all group segments
3. **Non-empty = Restricted**: If `assigned_segments` has values, member sees ONLY those segments

## API Endpoints

### 1. Get Member's Segments

```http
GET /api/auth/security-groups/{group_id}/members/{membership_id}/segments/
```

**Response:**
```json
{
  "membership_id": 5,
  "user": "john.doe",
  "group": "Finance Team",
  "has_specific_assignments": true,
  "access_mode": "restricted",  // or "full_group_access"
  "accessible_segments": [
    {
      "segment_type_id": 1,
      "segment_type_name": "Entity",
      "segment_count": 2,
      "segments": [
        {"code": "E001", "alias": "Finance Dept", "description": "..."},
        {"code": "E002", "alias": "HR Dept", "description": "..."}
      ]
    }
  ],
  "total_segment_types": 1
}
```

### 2. Assign Specific Segments to Member (Restrict Access)

```http
POST /api/auth/security-groups/{group_id}/members/{membership_id}/segments/
Content-Type: application/json

{
  "segment_assignment_ids": [12, 15, 18]  // XX_SecurityGroupSegment IDs
}
```

**Response:**
```json
{
  "message": "Assigned 3 specific segments to member 'john.doe'",
  "assigned_count": 3,
  "access_mode": "restricted"
}
```

### 3. Remove Restrictions (Give Full Group Access)

```http
DELETE /api/auth/security-groups/{group_id}/members/{membership_id}/segments/
```

**Response:**
```json
{
  "message": "Removed 3 specific segment assignments. Member now has full group access.",
  "removed_count": 3,
  "access_mode": "full_group_access"
}
```

## Real-World Examples

### Example 1: Department with Regional Restrictions

**Scenario**: Finance department has 5 regions, but each accountant only handles 2 regions.

```bash
# Group Setup
POST /api/auth/security-groups/
{
  "group_name": "Finance Department",
  "description": "All finance staff"
}

# Add segments (all 5 regions to group)
POST /api/auth/security-groups/1/segments/
{
  "segment_assignments": [
    {
      "segment_type_id": 1,
      "segment_codes": ["REGION_NORTH", "REGION_SOUTH", "REGION_EAST", "REGION_WEST", "REGION_CENTRAL"]
    }
  ]
}

# Add member (default: sees all regions)
POST /api/auth/security-groups/1/members/
{
  "user_id": 10,
  "role_ids": [2]
}
# Result: membership_id = 5

# Restrict member to only North & South regions
POST /api/auth/security-groups/1/members/5/segments/
{
  "segment_assignment_ids": [1, 2]  // IDs for REGION_NORTH and REGION_SOUTH
}
# Now User10 sees ONLY North & South regions ✅
```

### Example 2: Project Team with Task-Based Access

**Scenario**: Project team with 10 work packages, assign specific packages to each member.

```bash
# Group has 10 work packages (WP1-WP10)
# Member assignments:
# - Project Manager: ALL 10 packages (no restriction)
# - Developer A: WP1, WP2, WP3
# - Developer B: WP5, WP6

# Assign to Developer A (restricted)
POST /api/auth/security-groups/2/members/10/segments/
{
  "segment_assignment_ids": [5, 6, 7]  // WP1, WP2, WP3 segment IDs
}

# Assign to Developer B (restricted)
POST /api/auth/security-groups/2/members/11/segments/
{
  "segment_assignment_ids": [9, 10]  // WP5, WP6 segment IDs
}

# Project Manager (full access - no restriction needed)
# Just assign to group, don't call segment assignment endpoint
POST /api/auth/security-groups/2/members/
{
  "user_id": 5,
  "role_ids": [1]  // Manager role
}
# Manager sees ALL 10 work packages ✅
```

### Example 3: Multi-Level Access

**Scenario**: Group has Entity + Account segments, restrict both.

```bash
# Group Segments:
# - Entity: E001, E002, E003, E004, E005
# - Account: A100, A200, A300, A400

# Get segment assignment IDs first
GET /api/auth/security-groups/3/
# Response includes group_segments with their IDs:
# [
#   {id: 20, segment_type: "Entity", segment_code: "E001"},
#   {id: 21, segment_type: "Entity", segment_code: "E002"},
#   ...
#   {id: 28, segment_type: "Account", segment_code: "A100"},
#   {id: 29, segment_type: "Account", segment_code: "A200"},
#   ...
# ]

# Assign Member to E001, E002 (Entity) + A100 (Account)
POST /api/auth/security-groups/3/members/15/segments/
{
  "segment_assignment_ids": [20, 21, 28]  // E001, E002, A100
}
# Member sees: Entity=[E001, E002], Account=[A100] ✅
```

## Manager Class Methods

### SecurityGroupManager.assign_segments_to_member()

```python
from user_management.managers import SecurityGroupManager

# Get membership
membership = XX_UserGroupMembership.objects.get(pk=5)

# Assign specific segments
result = SecurityGroupManager.assign_segments_to_member(
    membership=membership,
    segment_assignment_ids=[12, 15, 18],  # XX_SecurityGroupSegment IDs
    assigned_by=request.user
)

if result['success']:
    print(f"Assigned {result['assigned']} segments")
else:
    print(f"Errors: {result['errors']}")
```

### SecurityGroupManager.get_member_segments()

```python
# Get segments for a specific member
member_segments = SecurityGroupManager.get_member_segments(membership)

# Returns: {segment_type_id: [segment_codes]}
# Example: {1: ["E001", "E002"], 2: ["A100"]}
```

### SecurityGroupManager.get_user_accessible_segments()

```python
# Get ALL segments user can access across ALL their groups
# (respects member-specific restrictions)
user_segments = SecurityGroupManager.get_user_accessible_segments(user)

# Returns: {segment_type_id: [segment_codes]}
# Aggregates segments from all user's group memberships
```

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY GROUP                           │
│                  "Finance Department"                       │
│                                                              │
│  Group Segments (10 total):                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ E001, E002, E003, E004, E005                         │  │
│  │ A100, A200, A300, A400, A500                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Members:                                                   │
│  ┌────────────────────────────────────────────────────────┐│
│  │ Manager (User1) - assigned_segments: EMPTY             ││
│  │ ├─> Sees: ALL 10 segments ✅                           ││
│  │                                                         ││
│  │ Accountant A (User2) - assigned_segments: [E001, A100] ││
│  │ ├─> Sees: E001, A100 ONLY ✅                           ││
│  │                                                         ││
│  │ Accountant B (User3) - assigned_segments: [E002, A200] ││
│  │ ├─> Sees: E002, A200 ONLY ✅                           ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Testing Examples

### Test 1: Default Full Access

```bash
# Create group and add segments
POST /api/auth/security-groups/
{"group_name": "Test Group"}
# group_id = 1

POST /api/auth/security-groups/1/segments/
{
  "segment_assignments": [
    {"segment_type_id": 1, "segment_codes": ["S1", "S2", "S3"]}
  ]
}

# Add member (no specific segment assignment)
POST /api/auth/security-groups/1/members/
{"user_id": 10, "role_ids": [1]}
# membership_id = 5

# Check member's access
GET /api/auth/security-groups/1/members/5/segments/
# Expected: has_specific_assignments=false, sees S1, S2, S3
```

### Test 2: Restricted Access

```bash
# Get group segment IDs
GET /api/auth/security-groups/1/
# Response shows: segment assignments with IDs [1, 2, 3] for S1, S2, S3

# Restrict member to S1 only
POST /api/auth/security-groups/1/members/5/segments/
{"segment_assignment_ids": [1]}

# Check member's access
GET /api/auth/security-groups/1/members/5/segments/
# Expected: has_specific_assignments=true, sees S1 ONLY
```

### Test 3: Remove Restriction

```bash
# Remove restrictions
DELETE /api/auth/security-groups/1/members/5/segments/

# Check member's access
GET /api/auth/security-groups/1/members/5/segments/
# Expected: has_specific_assignments=false, sees S1, S2, S3 again
```

### Test 4: Validation (Should Fail)

```bash
# Try assigning segment from different group (should fail)
POST /api/auth/security-groups/1/members/5/segments/
{"segment_assignment_ids": [99]}  // Segment from Group 2

# Expected error:
# "Segment assignment ID 99 does not belong to security group 'Test Group' or is inactive"
```

## Database Query Examples

### Get all restricted members in a group

```python
# Find members with specific segment restrictions
restricted_members = XX_UserGroupMembership.objects.filter(
    security_group_id=1,
    assigned_segments__isnull=False
).distinct()

for member in restricted_members:
    segment_count = member.assigned_segments.count()
    print(f"{member.user.username}: {segment_count} assigned segments")
```

### Get all members with full access

```python
# Find members without restrictions (see all group segments)
full_access_members = XX_UserGroupMembership.objects.filter(
    security_group_id=1,
    is_active=True
).annotate(
    segment_count=models.Count('assigned_segments')
).filter(segment_count=0)

print(f"Members with full group access: {full_access_members.count()}")
```

### Audit member access changes

```python
# Track who has restricted access
from django.db.models import Q

memberships = XX_UserGroupMembership.objects.filter(
    security_group_id=1
).annotate(
    restricted=models.Case(
        models.When(assigned_segments__isnull=False, then=True),
        default=False,
        output_field=models.BooleanField()
    )
)

print("Access Report:")
for m in memberships:
    access_type = "RESTRICTED" if m.restricted else "FULL"
    print(f"- {m.user.username}: {access_type}")
```

## Best Practices

### 1. Default to Full Access

**Don't** assign specific segments unless needed. Members without restrictions automatically get full group access.

```python
# ✅ Good: Default behavior
POST /api/auth/security-groups/1/members/
{"user_id": 10, "role_ids": [1]}
# Member sees all group segments

# ❌ Avoid: Unnecessary restriction when you want full access
POST /api/auth/security-groups/1/members/
{"user_id": 10, "role_ids": [1]}
# Then immediately:
POST /api/auth/security-groups/1/members/5/segments/
{"segment_assignment_ids": [1,2,3,4,5,6,7,8,9,10]}  # All segments anyway
```

### 2. Use for Granular Access Control

Best use cases:
- Regional teams (each member handles specific regions)
- Project assignments (each member works on specific work packages)
- Department sub-teams (each sub-team handles specific accounts)
- Role-based data segregation (junior staff see subset of data)

### 3. Document Restrictions

Add notes when restricting access:

```python
# Update membership with notes about restrictions
PUT /api/auth/security-groups/1/members/5/
{
  "notes": "Restricted to North & South regions only - assigned territories"
}
```

### 4. Review Access Regularly

```bash
# Audit who has restrictions
GET /api/auth/security-groups/1/
# Review members with assigned_segments_count > 0
```

## Migration Considerations

### Existing Memberships

All existing `XX_UserGroupMembership` records will have **empty** `assigned_segments`:
- **No migration needed** - they automatically get full group access ✅
- Behavior unchanged from before this feature

### Database Migration

After adding the `assigned_segments` field:

```bash
python manage.py makemigrations user_management
python manage.py migrate user_management
```

The new M2M table will be created: `XX_USER_GROUP_MEMBERSHIP_ASSIGNED_SEGMENTS_XX`

## Summary

**Member-Specific Segment Filtering** provides:

✅ **Granular access control** within groups  
✅ **Flexible restrictions** per member  
✅ **Default full access** when no restrictions set  
✅ **API endpoints** for managing restrictions  
✅ **Automatic validation** via signals  
✅ **Backward compatible** with existing memberships  

Use this feature when you need **fine-grained control over which segments each group member can access**, while maintaining the convenience of group-based management.
