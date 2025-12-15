# 🚀 User Profile API - Quick Reference

## Endpoints

### Get My Profile (Comprehensive)
```http
GET /api/auth/profile/
Authorization: Bearer {token}
```
**Returns:** Complete profile with groups, roles, abilities, segments, and summary

### Get My Profile (Simple)
```http
GET /api/auth/profile/simple/
Authorization: Bearer {token}
```
**Returns:** Lightweight profile with just username, role, level, and group list

### Get User Profile by ID (Admin Only)
```http
GET /api/auth/profile/?user_id=5
Authorization: Bearer {admin_token}
```
**Returns:** Another user's profile (admin/superadmin only)

---

## Response Structure (Comprehensive)

```json
{
  "user_info": {
    "id": 5,
    "username": "john.doe",
    "role": "user",
    "user_level": {...}
  },
  "security_groups": [
    {
      "group": {...},
      "assigned_roles": [...],
      "effective_abilities": ["TRANSFER", "APPROVE"],
      "accessible_segments": [...]
    }
  ],
  "direct_segment_access": [...],
  "direct_abilities": [...],
  "summary": {
    "total_group_memberships": 1,
    "unique_abilities_from_groups": ["TRANSFER", "APPROVE"],
    "has_any_permissions": true
  }
}
```

---

## Quick Use Cases

### 1️⃣ Check User Permissions
```javascript
const profile = await fetch('/api/auth/profile/simple/').then(r => r.json());
const canTransfer = profile.groups.some(g => g.abilities.includes('TRANSFER'));
```

### 2️⃣ Display User Groups
```javascript
const profile = await fetch('/api/auth/profile/').then(r => r.json());
console.log('User Groups:', profile.security_groups.map(m => m.group.name));
```

### 3️⃣ Check Group Assignment
```javascript
const profile = await fetch('/api/auth/profile/simple/').then(r => r.json());
if (!profile.is_assigned_to_groups) {
  alert('You are not assigned to any groups');
}
```

### 4️⃣ Get User Abilities
```javascript
const profile = await fetch('/api/auth/profile/').then(r => r.json());
console.log('Abilities:', profile.summary.unique_abilities_from_groups);
```

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200  | ✅ Success |
| 401  | ❌ Not authenticated |
| 403  | ❌ Not authorized (can't view other profiles) |
| 404  | ❌ User not found |

---

## Testing

### curl
```bash
# Login first
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'

# Get profile
curl -X GET http://localhost:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Python
```python
import requests

# Login
response = requests.post('http://localhost:8000/api/auth/login/',
    json={'username': 'testuser', 'password': 'testpass123'})
token = response.json()['access']

# Get profile
profile = requests.get('http://localhost:8000/api/auth/profile/',
    headers={'Authorization': f'Bearer {token}'}).json()

print(f"Groups: {len(profile['security_groups'])}")
print(f"Abilities: {profile['summary']['unique_abilities_from_groups']}")
```

### JavaScript/Fetch
```javascript
// Login
const loginRes = await fetch('/api/auth/login/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({username: 'testuser', password: 'testpass123'})
});
const {access} = await loginRes.json();

// Get profile
const profileRes = await fetch('/api/auth/profile/', {
  headers: {'Authorization': `Bearer ${access}`}
});
const profile = await profileRes.json();
console.log(profile);
```

---

## Key Fields Explained

| Field | Description |
|-------|-------------|
| `user_info` | Basic user data (username, role, level) |
| `security_groups` | Groups user belongs to |
| `assigned_roles` | Roles within each group |
| `effective_abilities` | Actual abilities (custom or role-based) |
| `accessible_segments` | Segments user can access |
| `direct_segment_access` | Phase 4 - Direct segment permissions |
| `direct_abilities` | Phase 4 - Abilities on segment combinations |
| `summary` | Quick stats and unique abilities |

---

## When to Use Which Endpoint

| Scenario | Use |
|----------|-----|
| UI header/menu | **Simple** - Fast, lightweight |
| User dashboard | **Comprehensive** - Full details |
| Admin panel | **Comprehensive** - Need full info |
| Permission check | **Simple** - Just need abilities |
| Access report | **Comprehensive** - Need everything |

---

## Common Patterns

### Check if User Can Perform Action
```javascript
const profile = await getProfile();
const abilities = profile.summary.unique_abilities_from_groups;
if (abilities.includes('APPROVE')) {
  // Show approve button
}
```

### Display User Groups in UI
```jsx
function UserGroups({profile}) {
  return (
    <div>
      <h2>My Groups</h2>
      {profile.security_groups.map(m => (
        <div key={m.membership_id}>
          <h3>{m.group.name}</h3>
          <p>Roles: {m.assigned_roles.map(r => r.role_name).join(', ')}</p>
        </div>
      ))}
    </div>
  );
}
```

### Filter Options Based on Segments
```javascript
const profile = await getProfile();
const allowedEntities = new Set();

profile.security_groups.forEach(membership => {
  membership.accessible_segments.forEach(segmentType => {
    if (segmentType.segment_type_name === 'Entity') {
      segmentType.segments.forEach(seg => {
        allowedEntities.add(seg.code);
      });
    }
  });
});

// Only show entities user has access to
const entityOptions = allEntities.filter(e => allowedEntities.has(e.code));
```

---

## Documentation Files

📄 **Full API Docs:** `__CLIENT_SETUP_DOCS__/USER_PROFILE_API.md`
📄 **Implementation Summary:** `__CLIENT_SETUP_DOCS__/USER_PROFILE_IMPLEMENTATION_SUMMARY.md`
📦 **Postman Collection:** `User_Profile_API.postman_collection.json`
🧪 **Test Script:** `test_scripts/test_user_profile_api.py`

---

## Quick Start

1. **Login** to get access token
2. **Call** `/api/auth/profile/` or `/api/auth/profile/simple/`
3. **Use** the returned data to:
   - Display user info
   - Check permissions
   - Filter UI elements
   - Generate reports

---

**Need Help?** Check the full documentation or run the test script!
