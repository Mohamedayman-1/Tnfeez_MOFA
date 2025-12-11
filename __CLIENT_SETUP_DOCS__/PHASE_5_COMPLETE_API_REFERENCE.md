# Phase 5 Security Groups - Complete API Reference

## Overview
Complete REST API endpoints for Security Groups management with full CRUD operations for groups, members, segments, roles, and abilities.

---

## 1. Security Groups Management

### List/Create Groups
```
GET  /api/auth/security-groups/
POST /api/auth/security-groups/
```

**GET Response:**
```json
{
  "total_groups": 3,
  "groups": [
    {
      "id": 1,
      "group_name": "Finance Team",
      "description": "Finance department access",
      "is_active": true,
      "total_members": 5,
      "total_roles": 2,
      "total_segments": 8,
      "created_at": "2025-12-10T10:00:00Z",
      "created_by": "admin"
    }
  ]
}
```

**POST Body:**
```json
{
  "group_name": "Finance Team",
  "description": "Finance department access",
  "is_active": true
}
```

### Get/Update/Delete Single Group
```
GET    /api/auth/security-groups/<group_id>/
PUT    /api/auth/security-groups/<group_id>/
DELETE /api/auth/security-groups/<group_id>/
```

---

## 2. Group Members Management

### List/Add Members
```
GET  /api/auth/security-groups/<group_id>/members/
POST /api/auth/security-groups/<group_id>/members/
```

**GET Response:**
```json
{
  "group_id": 1,
  "group_name": "Finance Team",
  "total_members": 3,
  "members": [
    {
      "membership_id": 1,
      "user_id": 5,
      "username": "john.doe",
      "user_role": 3,
      "assigned_roles": [
        {"role_id": 1, "role_name": "Planner"}
      ],
      "effective_abilities": ["VIEW", "TRANSFER", "APPROVE"],
      "has_custom_abilities": false,
      "access_mode": "all_group_segments",
      "specific_segments_count": 0,
      "joined_at": "2025-12-10T12:00:00Z",
      "notes": "Department manager"
    }
  ]
}
```

**POST Body - Add Member:**
```json
{
  "user_id": 10,
  "role_ids": [1, 2],
  "access_mode": "restricted_segments",
  "specific_segment_ids": [5, 10, 15],
  "notes": "Limited access - accounting only"
}
```

### Update/Remove Member
```
PATCH  /api/auth/security-groups/<group_id>/members/<membership_id>/
DELETE /api/auth/security-groups/<group_id>/members/<membership_id>/
```

**PATCH Body - Update Member:**
```json
{
  "role_ids": [1, 3],
  "access_mode": "all_group_segments",
  "specific_segment_ids": [],
  "notes": "Promoted to full access",
  "is_active": true
}
```

### Get Available Users (Not in Group)
```
GET /api/auth/security-groups/<group_id>/available-users/?search=john
```

**Response:**
```json
{
  "group_id": 1,
  "group_name": "Finance Team",
  "total_available": 25,
  "users": [
    {
      "id": 15,
      "username": "john.smith",
      "email": "john@example.com",
      "role": 3,
      "role_name": "Planner"
    }
  ]
}
```

---

## 3. Group Segments Management

### List/Add Segments
```
GET  /api/auth/security-groups/<group_id>/segments/
POST /api/auth/security-groups/<group_id>/segments/
```

**GET Response:**
```json
{
  "group_id": 1,
  "group_name": "Finance Team",
  "total_segments": 8,
  "segments": [
    {
      "id": 1,
      "segment_type_id": 5,
      "segment_type_name": "الموقع الجغرافي",
      "segment_code": "2760000",
      "segment_name": "ألمانيا",
      "is_active": true,
      "added_at": "2025-12-10T14:03:39Z"
    }
  ]
}
```

**POST Body - Add Segments:**
```json
{
  "segment_assignments": [
    {
      "segment_type_id": 5,
      "segment_codes": ["2760000", "27601011", "68201011"]
    },
    {
      "segment_type_id": 9,
      "segment_codes": ["013800000000"]
    }
  ]
}
```

### Remove Segment
```
DELETE /api/auth/security-groups/<group_id>/segments/<segment_id>/
```

### Get Available Segments (Not in Group)
```
GET /api/auth/security-groups/<group_id>/available-segments/?segment_type_id=5
```

**Response:**
```json
{
  "group_id": 1,
  "group_name": "Finance Team",
  "segment_types": [
    {
      "segment_type_id": 5,
      "segment_type_name": "الموقع الجغرافي",
      "segments": [
        {
          "id": 25,
          "segment_type_id": 5,
          "segment_type_name": "الموقع الجغرافي",
          "code": "2770000",
          "alias": "فرنسا",
          "is_active": true
        }
      ]
    }
  ]
}
```

---

## 4. Group Roles Management

### List/Add Roles
```
GET  /api/auth/security-groups/<group_id>/roles/
POST /api/auth/security-groups/<group_id>/roles/
```

**GET Response:**
```json
{
  "group_id": 1,
  "group_name": "Finance Team",
  "total_roles": 2,
  "roles": [
    {
      "id": 1,
      "role_id": 1,
      "role_name": "Planner",
      "is_active": true,
      "added_at": "2025-12-10T10:00:00Z"
    }
  ],
  "note": "Use the 'id' field for deletion"
}
```

**POST Body - Add Role:**
```json
{
  "role_id": 2,
  "is_active": true
}
```

### Update/Delete Role
```
PUT    /api/auth/security-groups/<group_id>/roles/<role_id>/
DELETE /api/auth/security-groups/<group_id>/roles/<role_id>/
```

### Get System Roles (All Available)
```
GET /api/auth/roles/
```

**Response:**
```json
{
  "roles": [
    {
      "role_id": 1,
      "role_name": "Planner",
      "description": "Budget planning and preparation",
      "default_abilities": ["VIEW", "TRANSFER", "SUBMIT"]
    },
    {
      "role_id": 2,
      "role_name": "Approver",
      "description": "Budget approval authority",
      "default_abilities": ["VIEW", "APPROVE", "REJECT"]
    }
  ]
}
```

---

## 5. Member-Specific Segment Restrictions

### Manage Member Segments
```
GET    /api/auth/security-groups/<group_id>/members/<membership_id>/segments/
POST   /api/auth/security-groups/<group_id>/members/<membership_id>/segments/
DELETE /api/auth/security-groups/<group_id>/members/<membership_id>/segments/
```

**POST Body - Assign Limited Segments to Member:**
```json
{
  "segment_ids": [5, 10, 15],
  "access_mode": "restricted"
}
```

**Response:**
```json
{
  "message": "Member restricted to 3 specific segments",
  "membership_id": 1,
  "user": "john.doe",
  "access_mode": "restricted_segments",
  "segment_count": 3,
  "segments": [
    {
      "segment_id": 5,
      "segment_code": "2760000",
      "segment_name": "ألمانيا"
    }
  ]
}
```

---

## 6. Member-Specific Ability Overrides

### Manage Member Abilities
```
GET    /api/auth/security-groups/<group_id>/members/<membership_id>/abilities/
PUT    /api/auth/security-groups/<group_id>/members/<membership_id>/abilities/
DELETE /api/auth/security-groups/<group_id>/members/<membership_id>/abilities/
```

**GET Response:**
```json
{
  "membership_id": 1,
  "user": "john.doe",
  "group": "Finance Team",
  "has_custom_abilities": true,
  "effective_abilities": ["VIEW", "TRANSFER", "APPROVE", "DELETE"],
  "custom_abilities": ["DELETE"],
  "role_default_abilities": {
    "Planner": ["VIEW", "TRANSFER", "APPROVE"]
  },
  "note": "Effective abilities = custom_abilities if set, otherwise aggregated from role defaults"
}
```

**PUT Body - Set Custom Abilities:**
```json
{
  "abilities": ["VIEW", "TRANSFER", "APPROVE", "DELETE"]
}
```

**DELETE** - Removes custom abilities, reverts to role defaults.

---

## 7. Transaction Security Group Assignment

### Get/Assign/Remove Transaction Group
```
GET    /api/budget-management/transfers/<transaction_id>/security-group/
PUT    /api/budget-management/transfers/<transaction_id>/security-group/
DELETE /api/budget-management/transfers/<transaction_id>/security-group/
```

**GET Response:**
```json
{
  "transaction_id": 123,
  "security_group": {
    "group_id": 1,
    "group_name": "Finance Team",
    "description": "Finance department access",
    "is_active": true
  },
  "is_restricted": true
}
```

**PUT Body - Assign Transaction:**
```json
{
  "security_group_id": 1
}
```

**DELETE Response:**
```json
{
  "message": "Security group restriction removed. Transaction 123 is now accessible to all users",
  "transaction_id": 123,
  "previous_group": "Finance Team"
}
```

---

## 8. User Access Query Endpoints

### Get User's Accessible Segments
```
GET /api/auth/users/<user_id>/accessible-segments/
```

**Response:**
```json
{
  "user_id": 5,
  "username": "john.doe",
  "groups": [
    {
      "group_id": 1,
      "group_name": "Finance Team",
      "access_mode": "restricted_segments",
      "accessible_segments": [
        {
          "segment_type_name": "الموقع الجغرافي",
          "segments": [
            {"code": "2760000", "name": "ألمانيا"}
          ]
        }
      ]
    }
  ]
}
```

### Get User's Group Memberships
```
GET /api/auth/users/<user_id>/memberships/
```

**Response:**
```json
{
  "user_id": 5,
  "username": "john.doe",
  "total_groups": 2,
  "memberships": [
    {
      "group_id": 1,
      "group_name": "Finance Team",
      "roles": ["Planner", "Approver"],
      "effective_abilities": ["VIEW", "TRANSFER", "APPROVE"],
      "access_mode": "all_group_segments"
    }
  ]
}
```

---

## Frontend Hooks (RTK Query)

### Groups
- `useGetSecurityGroupsQuery()` - List all groups
- `useGetSecurityGroupQuery(groupId)` - Get single group
- `useCreateSecurityGroupMutation()` - Create new group
- `useUpdateSecurityGroupMutation()` - Update group
- `useDeleteSecurityGroupMutation()` - Delete group

### Members
- `useGetGroupMembersQuery(groupId)` - List members
- `useAddGroupMemberMutation()` - Add member with roles & segment restrictions
- `useUpdateGroupMemberMutation()` - Update member roles/segments/notes
- `useRemoveGroupMemberMutation()` - Remove member
- `useGetAvailableUsersQuery({groupId, search})` - Get users not in group

### Segments
- `useGetGroupSegmentsQuery(groupId)` - List segments (grouped by type)
- `useAddGroupSegmentsMutation()` - Bulk add segments
- `useRemoveGroupSegmentMutation()` - Remove segment
- `useGetAvailableSegmentsQuery({groupId, segmentTypeId})` - Get unassigned segments

### Roles
- `useGetGroupRolesQuery(groupId)` - List roles
- `useCreateGroupRoleMutation()` - Add role to group
- `useUpdateGroupRoleMutation()` - Update role
- `useDeleteGroupRoleMutation()` - Remove role
- `useGetSystemRolesQuery()` - Get all available system roles

### Member Abilities
- `useGetMemberAbilitiesQuery({groupId, membershipId})` - Get member abilities
- `useUpdateMemberAbilitiesMutation()` - Set custom abilities
- `useRemoveMemberAbilitiesMutation()` - Revert to role defaults

### Transactions
- `useGetTransactionSecurityGroupQuery(transactionId)` - Get transaction's group
- `useAssignTransactionToGroupMutation()` - Assign transaction to group
- `useRemoveTransactionFromGroupMutation()` - Remove restriction

---

## Key Concepts

### Access Modes
1. **all_group_segments** - Member sees ALL segments assigned to group
2. **restricted_segments** - Member sees only SPECIFIC segments (subset of group segments)

### Ability Hierarchy
1. Custom abilities (if set) - OVERRIDES role defaults
2. Role default abilities - Aggregated from all assigned roles
3. If no custom abilities set, user gets combined abilities from all their roles

### Segment Grouping
- Segments grouped by `segment_type_id` for better UX
- Each segment type (e.g., "الموقع الجغرافي", "مراكز التكلفة") displayed separately

### Permission Model
- **SuperAdmin**: Full access to all operations
- **Admin**: Can manage groups, members, segments
- **Group Members**: Can view their own membership details
- **Transaction Access**: Determined by group membership + segment restrictions

---

## Example Workflows

### Add Member with Limited Access
```javascript
// 1. Get available users
const { data: users } = useGetAvailableUsersQuery({ groupId: 1, search: 'john' });

// 2. Get available segments for selection
const { data: segments } = useGetAvailableSegmentsQuery({ groupId: 1 });

// 3. Add member with restricted segments
await addMember({
  groupId: 1,
  data: {
    user_id: 15,
    role_ids: [1], // Planner
    access_mode: 'restricted_segments',
    specific_segment_ids: [5, 10, 15], // Only 3 specific segments
    notes: 'Accounting department only'
  }
});
```

### Add Multiple Segments to Group
```javascript
await addSegments({
  groupId: 1,
  data: {
    segment_assignments: [
      {
        segment_type_id: 5, // Location
        segment_codes: ['2760000', '27601011', '68201011']
      },
      {
        segment_type_id: 9, // Cost Center
        segment_codes: ['013800000000']
      }
    ]
  }
});
```

### Grant Custom Abilities to Member
```javascript
// Member gets custom abilities instead of role defaults
await updateMemberAbilities({
  groupId: 1,
  membershipId: 5,
  data: {
    abilities: ['VIEW', 'TRANSFER', 'APPROVE', 'DELETE', 'ADMIN']
  }
});
```

---

## Status: ✅ **PRODUCTION READY**

All endpoints implemented and tested. Frontend integration complete with modern React components and RTK Query hooks.
