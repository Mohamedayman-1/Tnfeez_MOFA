# User Profile API - Architecture & Data Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ User         │  │ Admin        │  │ UI           │          │
│  │ Dashboard    │  │ Panel        │  │ Components   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          │   GET /api/auth/profile/            │
          │   GET /api/auth/profile/simple/     │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API LAYER (Django REST)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  UserProfileView                                          │  │
│  │  - Authentication Check                                   │  │
│  │  - Permission Validation (own profile vs other users)    │  │
│  │  - Data Aggregation                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  UserProfileSimpleView (Lightweight)                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────┬───────────────────────────────────────────────────────┘
          │
          │ Queries with prefetch_related/select_related
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATABASE LAYER                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ xx_User     │  │ XX_Security  │  │ XX_Segment   │          │
│  │             │  │ Group        │  │ Access       │          │
│  └─────────────┘  └──────────────┘  └──────────────┘          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ XX_User     │  │ XX_Security  │  │ XX_User      │          │
│  │ Group       │  │ GroupRole    │  │ Segment      │          │
│  │ Membership  │  │              │  │ Ability      │          │
│  └─────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow - Comprehensive Profile

```
User Request
    │
    ├── Authentication Check (JWT Token)
    │   └── ✅ Valid → Continue
    │   └── ❌ Invalid → 401 Unauthorized
    │
    ├── Permission Check
    │   ├── Own Profile? → ✅ Allow
    │   └── Other User's Profile?
    │       ├── Admin/SuperAdmin? → ✅ Allow
    │       └── Regular User? → ❌ 403 Forbidden
    │
    ├── Data Collection (Parallel Queries)
    │   │
    │   ├── 1. User Basic Info
    │   │   └── Query: xx_User (with user_level)
    │   │
    │   ├── 2. Security Group Memberships
    │   │   └── Query: XX_UserGroupMembership
    │   │       ├── Prefetch: security_group
    │   │       ├── Prefetch: assigned_roles → role
    │   │       ├── Prefetch: assigned_segments
    │   │       └── Prefetch: security_group.group_segments
    │   │
    │   ├── 3. Direct Segment Access (Phase 4)
    │   │   └── Query: XX_UserSegmentAccess
    │   │       ├── Select: segment_type
    │   │       ├── Select: segment
    │   │       └── Select: granted_by
    │   │
    │   ├── 4. Direct Abilities (Phase 4)
    │   │   └── Query: XX_UserSegmentAbility
    │   │       └── Select: granted_by
    │   │
    │   └── 5. Summary Statistics
    │       ├── Count: Memberships
    │       ├── Count: Direct Access
    │       ├── Count: Direct Abilities
    │       └── Aggregate: Unique Abilities
    │
    └── Response Assembly
        └── JSON Response (see structure below)
```

---

## Response Structure - Detailed Breakdown

```
{
  "user_info": {                          ← From xx_User
    "id": 5,
    "username": "john.doe",
    "role": "user",                       ← Django auth role
    "role_display": "User",
    "user_level": {                       ← From xx_UserLevel (FK)
      "id": 2,
      "name": "Manager",
      "level_order": 2
    },
    "is_active": true,
    "is_staff": false,
    "is_superuser": false,
    "can_transfer_budget": true
  },
  
  "security_groups": [                    ← From XX_UserGroupMembership
    {
      "membership_id": 12,
      "group": {                          ← From XX_SecurityGroup
        "id": 3,
        "name": "Finance Team",
        "description": "...",
        "is_active": true
      },
      "assigned_roles": [                 ← From XX_SecurityGroupRole
        {
          "id": 8,
          "role_id": 2,
          "role_name": "Manager",         ← From xx_UserLevel
          "level_order": 2,
          "default_abilities": [          ← JSON field
            "TRANSFER", "APPROVE"
          ]
        }
      ],
      "effective_abilities": [            ← Computed
        "TRANSFER", "APPROVE", "VIEW"     ← custom_abilities OR role defaults
      ],
      "has_custom_abilities": false,      ← Boolean flag
      
      "accessible_segments": [            ← From XX_SecurityGroupSegment
        {
          "segment_type_id": 1,
          "segment_type_name": "Entity",  ← From XX_SegmentType
          "segments": [                   ← From XX_Segment
            {
              "code": "E001",
              "alias": "Main Office",
              "is_active": true
            }
          ]
        }
      ],
      
      "has_specific_segment_assignments": false,
      "joined_at": "2025-01-15T10:30:00Z",
      "assigned_by": "admin",
      "notes": "..."
    }
  ],
  
  "direct_segment_access": [              ← From XX_UserSegmentAccess
    {
      "id": 45,
      "segment_type": {...},              ← From XX_SegmentType
      "segment": {...},                   ← From XX_Segment
      "access_level": "EDIT",
      "granted_at": "2025-02-01T14:20:00Z",
      "granted_by": "superadmin",
      "notes": "..."
    }
  ],
  
  "direct_abilities": [                   ← From XX_UserSegmentAbility
    {
      "id": 78,
      "ability_type": "APPROVE",
      "segment_combination": {            ← JSON field
        "1": "E001",
        "2": "A100"
      },
      "segment_display": "Entity: E001 | Account: A100",
      "granted_at": "2025-02-05T09:15:00Z",
      "granted_by": "admin",
      "notes": "..."
    }
  ],
  
  "summary": {                            ← Computed
    "total_group_memberships": 1,         ← Count
    "total_direct_segment_access": 1,     ← Count
    "total_direct_abilities": 1,          ← Count
    "unique_abilities_from_groups": [     ← Aggregated Set
      "TRANSFER", "APPROVE", "VIEW"
    ],
    "has_any_permissions": true           ← Boolean
  }
}
```

---

## Data Source Mapping

| Response Field | Source Model | Query Type |
|----------------|--------------|------------|
| `user_info.*` | `xx_User` + `xx_UserLevel` | select_related |
| `security_groups` | `XX_UserGroupMembership` | prefetch_related |
| `assigned_roles` | `XX_SecurityGroupRole` → `xx_UserLevel` | prefetch_related |
| `accessible_segments` | `XX_SecurityGroupSegment` → `XX_Segment` | prefetch_related |
| `direct_segment_access` | `XX_UserSegmentAccess` | select_related |
| `direct_abilities` | `XX_UserSegmentAbility` | filter + select |
| `summary.*` | Computed from above | aggregation |

---

## Query Optimization Strategy

### 1. Prefetch Related (Avoid N+1 Queries)
```python
memberships = XX_UserGroupMembership.objects.filter(
    user=user, is_active=True
).prefetch_related(
    'assigned_roles__role',              # 1 query for all roles
    'assigned_segments__segment_type',   # 1 query for segment types
    'assigned_segments__segment',        # 1 query for segments
)
# Total: 4 queries instead of N * 3 queries
```

### 2. Select Related (JOIN Tables)
```python
access_grants = XX_UserSegmentAccess.objects.filter(
    user=user
).select_related(
    'segment_type',    # JOIN XX_SegmentType
    'segment',         # JOIN XX_Segment
    'granted_by'       # JOIN xx_User
)
# Single query with JOINs
```

### 3. Custom Prefetch
```python
Prefetch(
    'security_group__group_segments',
    queryset=XX_SecurityGroupSegment.objects.filter(
        is_active=True
    ).select_related('segment_type', 'segment')
)
# Filtered prefetch with related data
```

---

## Permission Flow Diagram

```
┌──────────────────────────────────────────────┐
│         User Makes Request                   │
│  GET /api/auth/profile/?user_id=X            │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Is Authenticated? │
        └────┬───────┬─────┘
             │       │
         YES │       │ NO
             │       └──────► 401 Unauthorized
             ▼
    ┌──────────────────┐
    │ user_id provided? │
    └────┬──────┬──────┘
         │      │
     YES │      │ NO
         │      └──────────► Use request.user (own profile)
         ▼                           │
┌─────────────────────┐              │
│ Is Admin/SuperAdmin? │◄─────────────┘
└───┬──────────┬──────┘
    │          │
YES │          │ NO
    │          └───────► 403 Forbidden
    ▼
┌──────────────────┐
│ Get target_user  │
└────────┬─────────┘
         │
         ▼
┌──────────────────────┐
│ Build Profile Data   │
│ - Basic Info         │
│ - Groups             │
│ - Permissions        │
│ - Summary            │
└────────┬─────────────┘
         │
         ▼
    200 OK + JSON
```

---

## Use Case Flow Examples

### Use Case 1: User Dashboard
```
User Opens Dashboard
    │
    ├─► Frontend calls GET /api/auth/profile/simple/
    │   (No user_id, gets own profile)
    │
    ├─► Backend validates token
    │
    ├─► Backend queries user + groups (lightweight)
    │
    ├─► Returns: username, role, groups with abilities
    │
    └─► Frontend displays:
        - "Welcome, John Doe"
        - "Your Role: Manager"
        - "Groups: Finance Team"
        - "Can Transfer: Yes" (checks abilities)
```

### Use Case 2: Admin Views User Details
```
Admin Opens User Management
    │
    ├─► Frontend calls GET /api/auth/profile/?user_id=5
    │   (Specifies user_id)
    │
    ├─► Backend validates token + checks admin role
    │
    ├─► Backend queries ALL data for user 5:
    │   - Basic info
    │   - Groups with full details
    │   - Segments
    │   - Abilities
    │   - Summary
    │
    ├─► Returns complete profile
    │
    └─► Frontend displays:
        - User details panel
        - Group memberships table
        - Permissions matrix
        - Segment access list
        - Action buttons (edit, deactivate)
```

### Use Case 3: Permission Check for UI Element
```
Component Renders Transfer Button
    │
    ├─► Frontend calls GET /api/auth/profile/simple/
    │   (Cached from previous call)
    │
    ├─► Check abilities in response:
    │   const canTransfer = profile.groups.some(g => 
    │       g.abilities.includes('TRANSFER')
    │   );
    │
    └─► If canTransfer:
        ├─► Show "Transfer Budget" button
        └─► Else: Hide button or show disabled
```

---

## Database Tables Involved

```
┌─────────────────────────────────────────────────────┐
│                   Core Tables                       │
├─────────────────────────────────────────────────────┤
│ xx_User                    ← User account           │
│ xx_UserLevel               ← Roles (Manager, etc.)  │
│                                                      │
│          Phase 5: Security Groups                   │
│ XX_SecurityGroup           ← Group container        │
│ XX_SecurityGroupRole       ← Available roles        │
│ XX_SecurityGroupSegment    ← Group segments         │
│ XX_UserGroupMembership     ← User ↔ Group link      │
│                                                      │
│          Phase 4: Direct Access                     │
│ XX_UserSegmentAccess       ← Direct segment access  │
│ XX_UserSegmentAbility      ← Direct abilities       │
│                                                      │
│          Segment System                             │
│ XX_SegmentType             ← Entity, Account, etc.  │
│ XX_Segment                 ← Actual segment values  │
└─────────────────────────────────────────────────────┘
```

---

## Key Performance Metrics

### Expected Query Counts
- **Simple Profile:** 2-3 queries (user + memberships)
- **Comprehensive Profile:** 6-8 queries (all data with prefetch)

### Response Times (Typical)
- **Simple Profile:** 50-100ms
- **Comprehensive Profile:** 150-300ms
- **With Caching:** 10-50ms

### Optimization Strategies
1. ✅ Use `select_related` for FK relationships
2. ✅ Use `prefetch_related` for M2M and reverse FK
3. ✅ Custom Prefetch with filters for active records
4. ✅ Simple endpoint for fast queries
5. 🔄 (Future) Redis caching for frequently accessed profiles

---

## Error Handling Flow

```
Request → Validation → Execution → Response

Validation Errors:
├─► 401: No token / Invalid token
├─► 403: Regular user trying to view other profile
└─► 404: Invalid user_id

Execution Errors:
├─► 500: Database error (logged)
└─► 503: Service unavailable

Success:
└─► 200: Profile data
```

---

## Integration Points

```
User Profile API
    │
    ├─► Phase 4: Dynamic Segments
    │   ├─► XX_UserSegmentAccess
    │   └─► XX_UserSegmentAbility
    │
    ├─► Phase 5: Security Groups
    │   ├─► XX_SecurityGroup
    │   ├─► XX_SecurityGroupRole
    │   ├─► XX_SecurityGroupSegment
    │   └─► XX_UserGroupMembership
    │
    ├─► User Management
    │   ├─► xx_User
    │   └─► xx_UserLevel
    │
    └─► Segment System
        ├─► XX_SegmentType
        └─► XX_Segment
```

---

**This architecture enables:**
- 🚀 Fast queries with minimal database hits
- 🔒 Secure permission-based access
- 📊 Comprehensive user information
- 🎯 Flexible data granularity (simple vs comprehensive)
- 🔄 Easy integration with existing systems
