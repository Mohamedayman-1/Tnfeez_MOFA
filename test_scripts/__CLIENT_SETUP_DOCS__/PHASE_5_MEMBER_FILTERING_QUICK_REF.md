# Member-Specific Segment Filtering - Quick Reference

## What's New

✅ **Individual member access control** - Restrict each member to specific segments within a group

## How It Works

```
Security Group: Has 10 segments (1-10)
├─ Member #1: assigned_segments = EMPTY → Sees ALL 10 segments
├─ Member #2: assigned_segments = [5, 6] → Sees ONLY segments 5, 6
└─ Member #3: assigned_segments = [1, 2, 3, 8] → Sees ONLY segments 1, 2, 3, 8
```

## Quick API Commands

### 1. Check Member's Access

```bash
GET /api/auth/security-groups/{group_id}/members/{membership_id}/segments/
```

**Response shows:**
- `has_specific_assignments`: true/false
- `access_mode`: "restricted" or "full_group_access"
- `accessible_segments`: List of segments they can see

### 2. Restrict Member Access

```bash
POST /api/auth/security-groups/{group_id}/members/{membership_id}/segments/
{
  "segment_assignment_ids": [12, 15, 18]  # XX_SecurityGroupSegment IDs
}
```

**Effect:** Member now sees ONLY segments 12, 15, 18 (not all group segments)

### 3. Remove Restriction (Full Access)

```bash
DELETE /api/auth/security-groups/{group_id}/members/{membership_id}/segments/
```

**Effect:** Member now sees ALL group segments again

## Real Example

**Scenario:** Finance team has 5 regions, accountants handle 2 regions each

```bash
# Step 1: Get group segment IDs
GET /api/auth/security-groups/1/
# Response shows segment_assignments with IDs:
# [
#   {id: 1, segment_code: "REGION_NORTH"},
#   {id: 2, segment_code: "REGION_SOUTH"},
#   {id: 3, segment_code: "REGION_EAST"},
#   {id: 4, segment_code: "REGION_WEST"},
#   {id: 5, segment_code: "REGION_CENTRAL"}
# ]

# Step 2: Assign Accountant A to North & South only
POST /api/auth/security-groups/1/members/10/segments/
{
  "segment_assignment_ids": [1, 2]  # North & South
}
# ✅ Accountant A now sees ONLY North & South regions

# Step 3: Assign Accountant B to East & West only
POST /api/auth/security-groups/1/members/11/segments/
{
  "segment_assignment_ids": [3, 4]  # East & West
}
# ✅ Accountant B now sees ONLY East & West regions

# Step 4: Manager gets full access (no restriction)
POST /api/auth/security-groups/1/members/
{
  "user_id": 5,
  "role_ids": [1]
}
# ✅ Manager sees ALL 5 regions (no segment assignment needed)
```

## Key Points

### Default Behavior
- **No assigned_segments** = Member sees **ALL group segments** ✅
- This is automatic - don't need to do anything

### Restricted Access
- **Has assigned_segments** = Member sees **ONLY those specific segments** 🔒
- Must explicitly assign via API

### Validation
- Can only assign segments that belong to the group
- Signal automatically validates on save
- Invalid assignments are rejected

## Code Examples

### Python Manager Usage

```python
from user_management.managers import SecurityGroupManager

# Get membership
membership = XX_UserGroupMembership.objects.get(pk=5)

# Assign specific segments
result = SecurityGroupManager.assign_segments_to_member(
    membership=membership,
    segment_assignment_ids=[1, 2, 3],
    assigned_by=request.user
)

# Get member's segments
segments = SecurityGroupManager.get_member_segments(membership)
# Returns: {1: ["E001", "E002"], 2: ["A100"]}
```

### Query User's Total Access

```python
# Get all segments user can see across all groups
user_segments = SecurityGroupManager.get_user_accessible_segments(user)
# Returns: {segment_type_id: [segment_codes]}
# Respects member-specific restrictions automatically
```

## Database Changes

### New Field

```python
XX_UserGroupMembership:
    assigned_segments = ManyToManyField(
        'XX_SecurityGroupSegment',
        blank=True,
        help_text="Specific segments this member can access"
    )
```

### New M2M Table

```
XX_USER_GROUP_MEMBERSHIP_ASSIGNED_SEGMENTS_XX
├─ usergroupmembership_id
├─ securitygroupsegment_id
└─ (Links members to specific segments)
```

## Migration Steps

```bash
# 1. Create migration
python manage.py makemigrations user_management

# 2. Apply migration
python manage.py migrate user_management

# 3. Test with existing members (should work - empty assigned_segments = full access)
GET /api/auth/security-groups/1/members/5/segments/
# Should show: "access_mode": "full_group_access"
```

## Best Practices

✅ **DO:**
- Use restrictions for regional/project-based access
- Document why member is restricted (add notes)
- Review restrictions regularly

❌ **DON'T:**
- Assign all segments individually when you want full access (just leave empty)
- Forget to validate segment IDs belong to the group
- Restrict without business justification

## Use Cases

### 1. Regional Teams
```
Group: Sales Team (5 regions)
├─ Sales Manager: ALL regions (no restriction)
├─ Salesperson A: North region only
└─ Salesperson B: South region only
```

### 2. Project Assignments
```
Group: Development Team (10 work packages)
├─ Project Manager: ALL packages (no restriction)
├─ Developer A: WP1, WP2, WP3
└─ Developer B: WP5, WP6, WP7
```

### 3. Department Sub-Teams
```
Group: Finance Dept (20 accounts)
├─ CFO: ALL accounts (no restriction)
├─ Sub-Team A: Accounts 1-10
└─ Sub-Team B: Accounts 11-20
```

## Troubleshooting

### Issue: Member still sees all segments after assignment

**Check:**
```bash
GET /api/auth/security-groups/{group_id}/members/{membership_id}/segments/
```

Look for:
- `has_specific_assignments`: Should be `true`
- `assigned_count`: Should be > 0

**Fix:** Verify segment_assignment_ids are valid XX_SecurityGroupSegment IDs

### Issue: Assignment fails with validation error

**Error:** "Segment does not belong to security group"

**Fix:** Get correct segment IDs from:
```bash
GET /api/auth/security-groups/{group_id}/
# Use IDs from "group_segments" section
```

### Issue: Want to reset to full access

**Solution:**
```bash
DELETE /api/auth/security-groups/{group_id}/members/{membership_id}/segments/
```

This clears all restrictions → member sees all group segments again ✅

## Summary

**Member-Specific Segment Filtering** provides:

| Feature | Description |
|---------|-------------|
| **Default** | Empty assigned_segments = Full group access |
| **Restricted** | Assigned segments = ONLY those segments visible |
| **Flexible** | Can change anytime via API |
| **Validated** | Signals ensure segments belong to group |
| **API** | GET/POST/DELETE endpoints for management |

Perfect for granular access control within security groups! 🎯
