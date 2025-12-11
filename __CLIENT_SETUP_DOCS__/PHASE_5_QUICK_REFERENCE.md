# Security Groups - Quick Reference

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    XX_SecurityGroup                         │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Group Name: "Finance Team"                         │    │
│  │  Description: "Finance department users"            │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────┐  ┌─────────────────┐  ┌────────────┐ │
│  │ Group Roles      │  │ Group Segments  │  │  Members   │ │
│  ├──────────────────┤  ├─────────────────┤  ├────────────┤ │
│  │ • Accountant     │  │ Entity: E001    │  │ User1      │ │
│  │ • Manager        │  │ Entity: E002    │  │ User2      │ │
│  │ • Auditor        │  │ Account: A100   │  │ User3      │ │
│  └──────────────────┘  │ Account: A200   │  └────────────┘ │
│                        │ Project: P001   │                  │
│                        └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘

When User1 joins "Finance Team":
  ↓
Picks 1-2 roles: [Accountant, Manager]
  ↓
User1 sees segments: E001, E002, A100, A200, P001
User1 has roles: Accountant, Manager
```

## Core Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `XX_SECURITY_GROUP_XX` | Groups | group_name, description, is_active |
| `XX_SECURITY_GROUP_ROLE_XX` | Roles in group | security_group, role (FK to xx_UserLevel) |
| `XX_SECURITY_GROUP_SEGMENT_XX` | Segments in group | security_group, segment_type, segment |
| `XX_USER_GROUP_MEMBERSHIP_XX` | User assignments | user, security_group, assigned_roles (M2M) |

## API Quick Commands

### Create Group
```bash
POST /api/auth/security-groups/
{"group_name": "Finance Team", "description": "Finance dept"}
```

### Add Roles (from xx_UserLevel)
```bash
POST /api/auth/security-groups/1/roles/
{"role_ids": [3, 5, 7]}  # xx_UserLevel IDs
```

### Add Segments
```bash
POST /api/auth/security-groups/1/segments/
{
  "segment_assignments": [
    {"segment_type_id": 1, "segment_codes": ["E001", "E002"]},
    {"segment_type_id": 2, "segment_codes": ["A100"]}
  ]
}
```

### Assign User
```bash
# Step 1: Get group details to find role IDs
GET /api/auth/security-groups/1/
# Returns: "roles": [{"id": 101, ...}, {"id": 102, ...}]

# Step 2: Assign user with those role IDs
POST /api/auth/security-groups/1/members/
{
  "user_id": 5,
  "role_ids": [101, 102],  # XX_SecurityGroupRole IDs (NOT xx_UserLevel)
  "notes": "Team member"
}
```

### Query User Access
```bash
GET /api/auth/users/5/accessible-segments/
```

## Key Rules

✅ **User can have 1-2 roles** from group's available roles  
✅ **Only required segments** can be added to groups  
✅ **Group must be active** for memberships to work  
✅ **User sees only group's segments** (subset of all)  
✅ **User can belong to multiple groups** (sees combined segments)

## Common Patterns

### Pattern 1: Department Group
```
Group: IT Department
├─ Roles: Developer, DevOps, Manager
├─ Segments: Entity IT-*, Account 6000-6999
└─ Users: 15 IT staff
```

### Pattern 2: Project Group
```
Group: Project Alpha
├─ Roles: PM, Developer, Tester
├─ Segments: Project ALPHA, Entity PROJ-ALPHA
└─ Users: 8 team members
```

### Pattern 3: Regional Group
```
Group: North Region
├─ Roles: Regional Manager, Analyst
├─ Segments: Entity 100-150 (North entities)
└─ Users: 12 regional staff
```

## Comparison: Phase 4 vs Phase 5

| Feature | Phase 4 (Direct) | Phase 5 (Groups) |
|---------|------------------|------------------|
| Assignment | User → Segment (individual) | User → Group → Segments |
| Roles | Simple access levels | xx_UserLevel roles (1-2 per user) |
| Management | Per-user setup | Bulk via groups |
| Scalability | Hard for many users | Easy bulk management |
| Consistency | Manual per user | Automatic via group |
| Flexibility | High per user | High per group + user roles |

## Migration Checklist

- [ ] Run `python manage.py makemigrations user_management`
- [ ] Run `python manage.py migrate user_management`
- [ ] Add URL patterns to `user_management/urls.py`
- [ ] Test create group endpoint
- [ ] Test add roles endpoint
- [ ] Test add segments endpoint
- [ ] Test assign user endpoint
- [ ] Test query user access endpoint
- [ ] Verify signals are working (role count validation)
- [ ] Update frontend to use new endpoints

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "User must have at least 1 role" | No roles assigned | Assign 1-2 roles |
| "User can have maximum 2 roles" | Too many roles | Limit to 2 roles |
| "Role does not belong to group" | Wrong role ID | Use group's role IDs |
| "Only required segment types" | Non-required segment | Only add required segments |
| "Cannot assign to inactive group" | Group is inactive | Activate group first |

## Django Manager Usage

```python
from user_management.managers.security_group_manager import SecurityGroupManager

# Get user's segments
segments = SecurityGroupManager.get_user_accessible_segments(user)
# {1: ["E001", "E002"], 2: ["A100", "A200"]}

# Get user's roles
roles = SecurityGroupManager.get_user_roles_from_groups(user)
# ["Accountant", "Manager"]

# Get group summary
summary = SecurityGroupManager.get_group_summary(group)
```

## Testing Example

```python
# 1. Create group
group = SecurityGroupManager.create_security_group(
    group_name="Test Group",
    created_by=admin_user
)

# 2. Add roles
SecurityGroupManager.add_roles_to_group(
    security_group=group,
    role_ids=[1, 2],  # xx_UserLevel IDs
    added_by=admin_user
)

# 3. Add segments
SecurityGroupManager.add_segments_to_group(
    security_group=group,
    segment_assignments=[
        {"segment_type_id": 1, "segment_codes": ["E001"]},
    ],
    added_by=admin_user
)

# 4. Assign user
# Get group role IDs first
group_roles = XX_SecurityGroupRole.objects.filter(security_group=group)
role_ids = [gr.id for gr in group_roles[:2]]

SecurityGroupManager.assign_user_to_group(
    user=test_user,
    security_group=group,
    role_ids=role_ids,
    assigned_by=admin_user
)

# 5. Verify
segments = SecurityGroupManager.get_user_accessible_segments(test_user)
assert 1 in segments  # Has Entity segment
assert "E001" in segments[1]  # Has E001
```
