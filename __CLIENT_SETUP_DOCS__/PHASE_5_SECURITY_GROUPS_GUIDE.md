# Security Group System - Phase 5

## Overview

The Security Group System provides a flexible way to manage user access to segments and roles through organized groups. This is an enhancement over Phase 4's direct user-to-segment assignment.

## Key Concepts

### 1. **Security Group** (`XX_SecurityGroup`)
A named container that holds:
- **Roles** (from `xx_UserLevel` table)
- **Segments** (from required segments only)
- **Users** (with assigned roles)

Example: "Finance Team" group might have:
- Roles: Accountant, Manager
- Segments: Entity 100-199, Account 5000-5999
- Users: User1 (Accountant), User2 (Manager + Accountant)

### 2. **Group Roles** (`XX_SecurityGroupRole`)
Links available roles to a security group. These roles come from your existing `xx_UserLevel` table.

### 3. **Group Segments** (`XX_SecurityGroupSegment`)
Links accessible segments to a security group. **Only required segments** can be added to groups.

### 4. **User Membership** (`XX_UserGroupMembership`)
Assigns users to groups with specific roles:
- User can belong to a group
- User gets **1-2 roles** from the group's available roles
- User sees **only the segments** assigned to that group

## Database Tables Created

```sql
XX_SECURITY_GROUP_XX          -- Security groups
XX_SECURITY_GROUP_ROLE_XX     -- Roles in each group
XX_SECURITY_GROUP_SEGMENT_XX  -- Segments in each group
XX_USER_GROUP_MEMBERSHIP_XX   -- User assignments to groups
```

## API Endpoints

### Security Group Management

#### 1. List All Security Groups
```http
GET /api/auth/security-groups/
```

**Response:**
```json
{
  "total_groups": 2,
  "groups": [
    {
      "group_id": 1,
      "group_name": "Finance Team",
      "description": "Finance department users",
      "is_active": true,
      "total_members": 5,
      "total_roles": 2,
      "total_segments": 10,
      "created_at": "2025-12-10T10:00:00Z",
      "created_by": "admin"
    }
  ]
}
```

#### 2. Create Security Group
```http
POST /api/auth/security-groups/
Content-Type: application/json

{
  "group_name": "Finance Team",
  "description": "Finance department users"
}
```

#### 3. Get Group Details
```http
GET /api/auth/security-groups/{group_id}/
```

**Response:**
```json
{
  "group_id": 1,
  "group_name": "Finance Team",
  "description": "Finance department users",
  "is_active": true,
  "total_members": 5,
  "total_roles": 2,
  "total_segments": 10,
  "roles": [
    {
      "id": 1,
      "role_id": 3,
      "role_name": "Accountant",
      "role_description": "Accounting role",
      "added_at": "2025-12-10T10:00:00Z"
    },
    {
      "id": 2,
      "role_id": 5,
      "role_name": "Manager",
      "role_description": "Management role",
      "added_at": "2025-12-10T10:05:00Z"
    }
  ],
  "segments": [
    {
      "id": 1,
      "segment_type_id": 1,
      "segment_type_name": "Entity",
      "segment_code": "E001",
      "segment_alias": "Finance Entity",
      "added_at": "2025-12-10T10:10:00Z"
    }
  ],
  "members": [
    {
      "membership_id": 1,
      "user_id": 5,
      "username": "john_doe",
      "assigned_roles": ["Accountant", "Manager"],
      "joined_at": "2025-12-10T11:00:00Z"
    }
  ]
}
```

#### 4. Update Security Group
```http
PUT /api/auth/security-groups/{group_id}/
Content-Type: application/json

{
  "group_name": "Finance Department",
  "description": "Updated description",
  "is_active": true
}
```

#### 5. Deactivate Security Group
```http
DELETE /api/auth/security-groups/{group_id}/
```

### Role Management

#### 6. Add Roles to Group
```http
POST /api/auth/security-groups/{group_id}/roles/
Content-Type: application/json

{
  "role_ids": [1, 2, 3]  // IDs from xx_UserLevel table
}
```

#### 7. Remove Role from Group
```http
DELETE /api/auth/security-groups/{group_id}/roles/{role_id}/
```

### Segment Management

#### 8. Add Segments to Group
```http
POST /api/auth/security-groups/{group_id}/segments/
Content-Type: application/json

{
  "segment_assignments": [
    {
      "segment_type_id": 1,
      "segment_codes": ["E001", "E002", "E003"]
    },
    {
      "segment_type_id": 2,
      "segment_codes": ["A100", "A200"]
    }
  ]
}
```

**Response:**
```json
{
  "message": "Added 5 segment(s) to group 'Finance Team'",
  "added_count": 5,
  "errors": []
}
```

#### 9. Remove Segment from Group
```http
DELETE /api/auth/security-groups/{group_id}/segments/{segment_id}/
```

### User Membership Management

#### 10. Assign User to Group
```http
POST /api/auth/security-groups/{group_id}/members/
Content-Type: application/json

{
  "user_id": 5,
  "role_ids": [1, 2],  // IDs of XX_SecurityGroupRole (NOT xx_UserLevel)
  "notes": "Finance team member"
}
```

**Important:** `role_ids` here are the IDs from `XX_SecurityGroupRole` table (the group-role link), NOT the `xx_UserLevel` IDs. You get these IDs from the group details endpoint.

#### 11. Update User's Roles in Group
```http
PUT /api/auth/security-groups/{group_id}/members/{membership_id}/
Content-Type: application/json

{
  "role_ids": [1],  // New role assignment (1-2 roles)
  "notes": "Updated to single role"
}
```

#### 12. Remove User from Group
```http
DELETE /api/auth/security-groups/{group_id}/members/{membership_id}/
```

### User Access Query

#### 13. Get User's Accessible Segments
```http
GET /api/auth/users/{user_id}/accessible-segments/
```

**Response:**
```json
{
  "user_id": 5,
  "username": "john_doe",
  "roles": ["Accountant", "Manager"],
  "accessible_segments": [
    {
      "segment_type_id": 1,
      "segment_type_name": "Entity",
      "segment_count": 3,
      "segments": [
        {
          "code": "E001",
          "alias": "Finance Entity",
          "description": "Finance department entity"
        },
        {
          "code": "E002",
          "alias": "HR Entity",
          "description": "HR department entity"
        }
      ]
    },
    {
      "segment_type_id": 2,
      "segment_type_name": "Account",
      "segment_count": 2,
      "segments": [
        {
          "code": "A100",
          "alias": "Revenue Account",
          "description": "Revenue account"
        }
      ]
    }
  ],
  "total_segment_types": 2
}
```

## Workflow Example

### Scenario: Create Finance Team Group

**Step 1: Create the Group**
```bash
POST /api/auth/security-groups/
{
  "group_name": "Finance Team",
  "description": "Finance department users"
}
# Returns: group_id = 1
```

**Step 2: Add Roles to Group**
```bash
# Assuming you have xx_UserLevel IDs: 
# - ID 3 = "Accountant"
# - ID 5 = "Manager"

POST /api/auth/security-groups/1/roles/
{
  "role_ids": [3, 5]
}
```

**Step 3: Add Segments to Group**
```bash
POST /api/auth/security-groups/1/segments/
{
  "segment_assignments": [
    {
      "segment_type_id": 1,  // Entity
      "segment_codes": ["E001", "E002", "E003"]
    },
    {
      "segment_type_id": 2,  // Account
      "segment_codes": ["A100", "A200", "A300"]
    }
  ]
}
```

**Step 4: Get Group Details to Find Role IDs**
```bash
GET /api/auth/security-groups/1/

# Response includes:
# "roles": [
#   {"id": 101, "role_id": 3, "role_name": "Accountant"},
#   {"id": 102, "role_id": 5, "role_name": "Manager"}
# ]
```

**Step 5: Assign User to Group**
```bash
POST /api/auth/security-groups/1/members/
{
  "user_id": 5,
  "role_ids": [101, 102],  // User gets both Accountant and Manager roles
  "notes": "Senior finance team member"
}
```

**Step 6: Query User's Access**
```bash
GET /api/auth/users/5/accessible-segments/

# Returns all segments from Finance Team group
```

## Validation Rules

### Security Group
- ✅ Group name must be unique
- ✅ Can be activated/deactivated
- ✅ Deactivating group deactivates all memberships

### Group Roles
- ✅ Roles come from `xx_UserLevel` table
- ✅ No duplicate roles in a group
- ✅ Can activate/deactivate roles

### Group Segments
- ✅ **Only required segments** can be added
- ✅ Segment must belong to the specified segment type
- ✅ No duplicate segments in a group
- ✅ Can activate/deactivate segments

### User Membership
- ✅ User must have **1-2 roles** from group's available roles
- ✅ Roles must belong to the security group
- ✅ Roles must be active
- ✅ Group must be active
- ✅ User can belong to multiple groups
- ✅ User sees only segments from their groups

## Manager Class Usage

```python
from user_management.managers.security_group_manager import SecurityGroupManager

# Create group
group = SecurityGroupManager.create_security_group(
    group_name="Finance Team",
    description="Finance department",
    created_by=request.user
)

# Add roles
result = SecurityGroupManager.add_roles_to_group(
    security_group=group,
    role_ids=[1, 2, 3],
    added_by=request.user
)

# Add segments
result = SecurityGroupManager.add_segments_to_group(
    security_group=group,
    segment_assignments=[
        {"segment_type_id": 1, "segment_codes": ["E001", "E002"]},
        {"segment_type_id": 2, "segment_codes": ["A100"]}
    ],
    added_by=request.user
)

# Assign user
result = SecurityGroupManager.assign_user_to_group(
    user=user,
    security_group=group,
    role_ids=[101, 102],  # XX_SecurityGroupRole IDs
    assigned_by=request.user
)

# Get user's accessible segments
segments = SecurityGroupManager.get_user_accessible_segments(user)
# Returns: {1: ["E001", "E002"], 2: ["A100"]}

# Get user's roles
roles = SecurityGroupManager.get_user_roles_from_groups(user)
# Returns: ["Accountant", "Manager"]
```

## Migration Steps

### 1. Create Migration
```bash
python manage.py makemigrations user_management
```

### 2. Review Migration
Check the generated migration file in `user_management/migrations/`

### 3. Apply Migration
```bash
python manage.py migrate user_management
```

### 4. Register URLs
Add to `user_management/urls.py`:

```python
from user_management.views_security_groups import (
    SecurityGroupListCreateView,
    SecurityGroupDetailView,
    SecurityGroupRolesView,
    SecurityGroupSegmentsView,
    SecurityGroupMembersView,
    UserAccessibleSegmentsView,
)

urlpatterns = [
    # ... existing URLs ...
    
    # Security Groups
    path('security-groups/', SecurityGroupListCreateView.as_view(), name='security-group-list'),
    path('security-groups/<int:group_id>/', SecurityGroupDetailView.as_view(), name='security-group-detail'),
    path('security-groups/<int:group_id>/roles/', SecurityGroupRolesView.as_view(), name='security-group-roles'),
    path('security-groups/<int:group_id>/roles/<int:role_id>/', SecurityGroupRolesView.as_view(), name='security-group-role-delete'),
    path('security-groups/<int:group_id>/segments/', SecurityGroupSegmentsView.as_view(), name='security-group-segments'),
    path('security-groups/<int:group_id>/segments/<int:segment_id>/', SecurityGroupSegmentsView.as_view(), name='security-group-segment-delete'),
    path('security-groups/<int:group_id>/members/', SecurityGroupMembersView.as_view(), name='security-group-members'),
    path('security-groups/<int:group_id>/members/<int:membership_id>/', SecurityGroupMembersView.as_view(), name='security-group-member-update'),
    path('users/<int:user_id>/accessible-segments/', UserAccessibleSegmentsView.as_view(), name='user-accessible-segments'),
]
```

## Benefits Over Phase 4

### Phase 4 (Direct Assignment)
- ❌ Assign each user to each segment individually
- ❌ Hard to manage bulk users
- ❌ No role grouping
- ❌ Difficult to maintain consistency

### Phase 5 (Security Groups)
- ✅ Group users by department/team
- ✅ Manage segments once per group
- ✅ Role-based access within groups
- ✅ Easy bulk management
- ✅ Consistent access patterns
- ✅ Flexible 1-2 role assignment

## Use Cases

### 1. Department-Based Access
```
Group: Finance Department
- Roles: Accountant, Manager, Auditor
- Segments: Entity 100-199, Account 5000-5999
- Users: 20 finance staff with different role combinations
```

### 2. Project-Based Access
```
Group: Project Alpha Team
- Roles: Developer, Project Manager
- Segments: Project ALPHA, Entity 300
- Users: 5 team members
```

### 3. Regional Access
```
Group: North Region
- Roles: Regional Manager, Analyst
- Segments: Entity 100-150 (North region entities)
- Users: 15 regional staff
```

## Summary

The Security Group System provides:
1. **Centralized management** of user access
2. **Role-based** permissions within groups
3. **Segment filtering** based on group membership
4. **Flexible 1-2 role** assignment per user
5. **Easy bulk operations** for user management
6. **Audit trail** with created_by, added_by fields
7. **Soft deletes** via is_active flags

All through a clean REST API! 🎉
