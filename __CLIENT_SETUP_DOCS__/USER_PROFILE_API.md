# User Profile API Documentation

## Overview
The User Profile API provides comprehensive information about users including their security group memberships, roles, permissions, and segment access.

## Endpoints

### 1. Comprehensive User Profile
**Endpoint:** `GET /api/auth/profile/`

Returns complete user profile information including:
- Basic user information (username, role, level, etc.)
- Security group memberships with roles and abilities
- Direct segment access grants (Phase 4)
- Direct abilities on segment combinations (Phase 4)
- Summary statistics

#### Authentication
- **Required:** Yes
- **Permission:** Any authenticated user can view their own profile
- **Admin Access:** Admins and superadmins can view other users' profiles using `?user_id=<id>`

#### Request Examples

**Get current user's profile:**
```http
GET /api/auth/profile/
Authorization: Bearer <access_token>
```

**Get specific user's profile (admin only):**
```http
GET /api/auth/profile/?user_id=5
Authorization: Bearer <access_token>
```

#### Response Structure

```json
{
  "user_info": {
    "id": 5,
    "username": "john.doe",
    "role": "user",
    "role_display": "User",
    "user_level": {
      "id": 2,
      "name": "Manager",
      "level_order": 2
    },
    "is_active": true,
    "is_staff": false,
    "is_superuser": false,
    "can_transfer_budget": true
  },
  "security_groups": [
    {
      "membership_id": 12,
      "group": {
        "id": 3,
        "name": "Finance Team",
        "description": "Finance department users",
        "is_active": true
      },
      "assigned_roles": [
        {
          "id": 8,
          "role_id": 2,
          "role_name": "Manager",
          "level_order": 2,
          "default_abilities": ["TRANSFER", "APPROVE"]
        }
      ],
      "effective_abilities": ["TRANSFER", "APPROVE", "VIEW"],
      "has_custom_abilities": false,
      "accessible_segments": [
        {
          "segment_type_id": 1,
          "segment_type_name": "Entity",
          "segments": [
            {
              "code": "E001",
              "alias": "Main Office",
              "is_active": true
            },
            {
              "code": "E002",
              "alias": "Branch Office",
              "is_active": true
            }
          ]
        },
        {
          "segment_type_id": 2,
          "segment_type_name": "Account",
          "segments": [
            {
              "code": "A100",
              "alias": "Operating Account",
              "is_active": true
            }
          ]
        }
      ],
      "has_specific_segment_assignments": false,
      "joined_at": "2025-01-15T10:30:00Z",
      "assigned_by": "admin",
      "notes": "Added to finance team"
    }
  ],
  "direct_segment_access": [
    {
      "id": 45,
      "segment_type": {
        "id": 1,
        "name": "Entity",
        "is_required": true
      },
      "segment": {
        "code": "E003",
        "alias": "Special Project",
        "is_active": true
      },
      "access_level": "EDIT",
      "granted_at": "2025-02-01T14:20:00Z",
      "granted_by": "superadmin",
      "notes": "Special project access"
    }
  ],
  "direct_abilities": [
    {
      "id": 78,
      "ability_type": "APPROVE",
      "segment_combination": {
        "1": "E001",
        "2": "A100"
      },
      "segment_display": "Entity: E001 | Account: A100",
      "granted_at": "2025-02-05T09:15:00Z",
      "granted_by": "admin",
      "notes": "Approval authority for Entity E001, Account A100"
    }
  ],
  "summary": {
    "total_group_memberships": 1,
    "total_direct_segment_access": 1,
    "total_direct_abilities": 1,
    "unique_abilities_from_groups": ["TRANSFER", "APPROVE", "VIEW"],
    "has_any_permissions": true
  }
}
```

#### Response Fields Explained

**user_info:**
- Basic user information
- Includes role, level, and system permissions

**security_groups:**
- All active group memberships
- Each membership includes:
  - `assigned_roles`: Roles the user has within this group (1-2 roles)
  - `effective_abilities`: Actual abilities (either custom or role-based)
  - `accessible_segments`: Segments the user can see (specific or all group segments)
  - `has_specific_segment_assignments`: Whether user has restricted segment access
  - `has_custom_abilities`: Whether user has custom ability overrides

**direct_segment_access:**
- Phase 4 feature: Direct segment-level access grants
- Independent of security groups
- Allows fine-grained access control per segment

**direct_abilities:**
- Phase 4 feature: Abilities on specific segment combinations
- Example: APPROVE ability on Entity:E001 + Account:A100 combination
- `segment_display`: Human-readable format of segment combination

**summary:**
- Quick statistics about the user's permissions
- Shows total counts and unique abilities
- `has_any_permissions`: Quick check if user has any access

---

### 2. Simple User Profile
**Endpoint:** `GET /api/auth/profile/simple/`

Lightweight version of the profile endpoint with only essential information.

#### Authentication
- **Required:** Yes
- **Permission:** Same as comprehensive profile

#### Request Examples

```http
GET /api/auth/profile/simple/
Authorization: Bearer <access_token>
```

```http
GET /api/auth/profile/simple/?user_id=5
Authorization: Bearer <access_token>
```

#### Response Structure

```json
{
  "user_id": 5,
  "username": "john.doe",
  "role": "user",
  "user_level": "Manager",
  "groups": [
    {
      "group_name": "Finance Team",
      "roles": ["Manager"],
      "abilities": ["TRANSFER", "APPROVE", "VIEW"]
    },
    {
      "group_name": "Audit Committee",
      "roles": ["Observer"],
      "abilities": ["VIEW", "REPORT"]
    }
  ],
  "is_assigned_to_groups": true
}
```

#### When to Use Simple vs Comprehensive

**Use Simple Profile when:**
- You only need to know which groups the user belongs to
- Displaying basic user info in UI headers/menus
- Checking if user has group assignments
- Lightweight queries for performance

**Use Comprehensive Profile when:**
- You need detailed segment access information
- Building admin dashboards
- Displaying full user permissions
- Debugging access control issues
- Generating user access reports

---

## Use Cases

### 1. User Dashboard - "My Profile"
Show the current user their complete profile:
```javascript
fetch('/api/auth/profile/', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
})
.then(res => res.json())
.then(data => {
  console.log('My Groups:', data.security_groups);
  console.log('My Abilities:', data.summary.unique_abilities_from_groups);
  console.log('My Segments:', data.security_groups[0].accessible_segments);
});
```

### 2. Admin View - User Management
Admins viewing user details:
```javascript
// Get user profile for admin review
fetch(`/api/auth/profile/?user_id=${userId}`, {
  headers: {
    'Authorization': `Bearer ${adminToken}`
  }
})
.then(res => res.json())
.then(data => {
  console.log('User Info:', data.user_info);
  console.log('Group Memberships:', data.security_groups.length);
  console.log('Has Permissions:', data.summary.has_any_permissions);
});
```

### 3. Permission Check - UI Rendering
Quick check for UI elements:
```javascript
// Use simple profile for fast permission checks
fetch('/api/auth/profile/simple/', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
})
.then(res => res.json())
.then(data => {
  const canTransfer = data.groups.some(g => 
    g.abilities.includes('TRANSFER')
  );
  
  if (canTransfer) {
    showTransferButton();
  }
});
```

### 4. Access Audit Trail
Generate report of user access:
```javascript
fetch(`/api/auth/profile/?user_id=${userId}`, {
  headers: {
    'Authorization': `Bearer ${adminToken}`
  }
})
.then(res => res.json())
.then(data => {
  // Generate audit report
  const report = {
    user: data.user_info.username,
    groups: data.security_groups.map(g => g.group.name),
    abilities: data.summary.unique_abilities_from_groups,
    direct_access: data.direct_segment_access.length,
    last_checked: new Date()
  };
  
  generatePDF(report);
});
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
When non-admin tries to view another user's profile:
```json
{
  "error": "You don't have permission to view other user profiles"
}
```

### 404 Not Found
When specified user_id doesn't exist:
```json
{
  "detail": "Not found."
}
```

---

## Related Endpoints

- **Security Groups:** `/api/auth/security-groups/`
- **User Segment Access:** `/api/auth/phase4/access/list`
- **User Abilities:** `/api/auth/phase4/abilities/list`
- **User Memberships:** `/api/auth/users/<user_id>/memberships/`

---

## Technical Notes

### Performance Considerations
1. **Comprehensive Profile:** Uses prefetch_related and select_related for optimal queries
2. **Simple Profile:** Minimal database queries for fast response
3. **Caching:** Consider caching profile data for frequently accessed users

### Data Privacy
- Users can only see their own profile by default
- Admin/SuperAdmin roles required to view other users
- Sensitive data (passwords, tokens) never included in response

### Future Enhancements
- Profile picture support
- Last login timestamp
- Activity history
- Notification preferences

---

## Integration with Frontend

### React Example
```jsx
import { useEffect, useState } from 'react';

function UserProfile() {
  const [profile, setProfile] = useState(null);
  
  useEffect(() => {
    fetch('/api/auth/profile/', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    .then(res => res.json())
    .then(data => setProfile(data));
  }, []);
  
  if (!profile) return <div>Loading...</div>;
  
  return (
    <div>
      <h1>{profile.user_info.username}</h1>
      <p>Role: {profile.user_info.role_display}</p>
      
      <h2>My Groups</h2>
      {profile.security_groups.map(membership => (
        <div key={membership.membership_id}>
          <h3>{membership.group.name}</h3>
          <p>Roles: {membership.assigned_roles.map(r => r.role_name).join(', ')}</p>
          <p>Abilities: {membership.effective_abilities.join(', ')}</p>
        </div>
      ))}
      
      <h2>Permissions Summary</h2>
      <p>Total Groups: {profile.summary.total_group_memberships}</p>
      <p>Abilities: {profile.summary.unique_abilities_from_groups.join(', ')}</p>
    </div>
  );
}
```

### Vue.js Example
```vue
<template>
  <div v-if="profile">
    <h1>{{ profile.user_info.username }}</h1>
    <p>Level: {{ profile.user_info.user_level?.name }}</p>
    
    <div v-for="group in profile.security_groups" :key="group.membership_id">
      <h3>{{ group.group.name }}</h3>
      <ul>
        <li v-for="role in group.assigned_roles" :key="role.id">
          {{ role.role_name }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      profile: null
    };
  },
  mounted() {
    this.fetchProfile();
  },
  methods: {
    async fetchProfile() {
      const response = await fetch('/api/auth/profile/', {
        headers: {
          'Authorization': `Bearer ${this.$store.state.token}`
        }
      });
      this.profile = await response.json();
    }
  }
};
</script>
```

---

## Testing

### Manual Testing with curl

**Get own profile:**
```bash
curl -X GET http://localhost:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Get another user's profile (admin):**
```bash
curl -X GET "http://localhost:8000/api/auth/profile/?user_id=5" \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN"
```

**Get simple profile:**
```bash
curl -X GET http://localhost:8000/api/auth/profile/simple/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Expected Test Scenarios

1. ✅ User views own profile - should return 200 with full data
2. ✅ User tries to view another user's profile - should return 403
3. ✅ Admin views another user's profile - should return 200
4. ✅ Unauthenticated request - should return 401
5. ✅ Invalid user_id - should return 404
6. ✅ User with no group memberships - should return empty arrays
7. ✅ User with custom abilities - should show custom_abilities in response

---

## Changelog

### Version 1.0 (December 2025)
- Initial release with comprehensive and simple profile endpoints
- Integration with Phase 4 (Dynamic Segments) and Phase 5 (Security Groups)
- Support for direct segment access and abilities
- Summary statistics for quick permission overview
