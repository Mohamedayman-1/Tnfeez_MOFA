# Security Groups API - Postman Testing Guide

## Base URL
```
http://localhost:8000/api/auth
```

## Authentication
All requests require authentication token in header:
```
Authorization: Bearer YOUR_TOKEN_HERE
```

---

## 1. CREATE SECURITY GROUP

### Endpoint
```
POST /api/auth/security-groups/
```

### Request Body
```json
{
  "group_name": "Finance Team",
  "description": "Finance department users"
}
```

### Response (201)
```json
{
  "message": "Security group 'Finance Team' created successfully",
  "group": {
    "group_id": 1,
    "group_name": "Finance Team",
    "description": "Finance department users",
    "is_active": true,
    "total_members": 0,
    "total_roles": 0,
    "total_segments": 0,
    "created_at": "2025-12-10T10:30:00Z",
    "created_by": "admin"
  }
}
```

---

## 2. LIST ALL SECURITY GROUPS

### Endpoint
```
GET /api/auth/security-groups/
```

### Response (200)
```json
{
  "total_groups": 2,
  "groups": [
    {
      "group_id": 1,
      "group_name": "Finance Team",
      "description": "Finance department users",
      "is_active": true,
      "total_members": 3,
      "total_roles": 2,
      "total_segments": 10,
      "created_at": "2025-12-10T10:30:00Z",
      "created_by": "admin"
    },
    {
      "group_id": 2,
      "group_name": "IT Department",
      "description": "IT staff",
      "is_active": true,
      "total_members": 5,
      "total_roles": 3,
      "total_segments": 8,
      "created_at": "2025-12-10T11:00:00Z",
      "created_by": "admin"
    }
  ]
}
```

---

## 3. GET GROUP DETAILS

### Endpoint
```
GET /api/auth/security-groups/1/
```

### Response (200)
```json
{
  "group_id": 1,
  "group_name": "Finance Team",
  "description": "Finance department users",
  "is_active": true,
  "created_at": "2025-12-10T10:30:00Z",
  "created_by": "admin",
  "roles": [
    {
      "id": 5,
      "role_id": 2,
      "role_name": "Accountant",
      "is_active": true
    },
    {
      "id": 6,
      "role_id": 3,
      "role_name": "Manager",
      "is_active": true
    }
  ],
  "segments": [
    {
      "id": 10,
      "segment_type_id": 1,
      "segment_type_name": "Entity",
      "segment_code": "E001",
      "segment_alias": "Finance Dept",
      "is_active": true
    },
    {
      "id": 11,
      "segment_type_id": 1,
      "segment_type_name": "Entity",
      "segment_code": "E005",
      "segment_alias": "IT Dept",
      "is_active": true
    },
    {
      "id": 12,
      "segment_type_id": 2,
      "segment_type_name": "Account",
      "segment_code": "A100",
      "segment_alias": "Salaries",
      "is_active": true
    }
  ],
  "members": [
    {
      "membership_id": 1,
      "user_id": 10,
      "username": "john.doe",
      "assigned_roles": ["Accountant", "Manager"],
      "is_active": true,
      "joined_at": "2025-12-10T10:35:00Z"
    }
  ]
}
```

---

## 4. ADD ROLES TO GROUP

### Endpoint
```
POST /api/auth/security-groups/1/roles/
```

### Request Body
```json
{
  "role_ids": [2, 3, 5]
}
```

**Note:** `role_ids` are from `xx_UserLevel` table (the roles table).

### Response (200)
```json
{
  "message": "Added 3 roles to security group 'Finance Team'",
  "added_count": 3,
  "roles": [
    {"role_id": 2, "role_name": "Accountant"},
    {"role_id": 3, "role_name": "Manager"},
    {"role_id": 5, "role_name": "Auditor"}
  ]
}
```

---

## 5. ADD SEGMENTS TO GROUP

### Endpoint
```
POST /api/auth/security-groups/1/segments/
```

### Request Body
```json
{
  "segment_assignments": [
    {
      "segment_type_id": 1,
      "segment_codes": ["E001", "E005", "E009", "E011"]
    },
    {
      "segment_type_id": 2,
      "segment_codes": ["A100", "A200", "A300"]
    },
    {
      "segment_type_id": 3,
      "segment_codes": ["P001", "P005"]
    }
  ]
}
```

**Note:** Only **required** segments (where `is_required=true` in `XX_SegmentType`) can be added.

### Response (200)
```json
{
  "message": "Added 9 segments to security group 'Finance Team'",
  "added_count": 9
}
```

---

## 6. ADD MEMBER TO GROUP

### Endpoint
```
POST /api/auth/security-groups/1/members/
```

### Request Body
```json
{
  "user_id": 10,
  "role_ids": [5, 6],
  "notes": "Finance accountant - handles all regions"
}
```

**Note:** 
- `user_id` is from `xx_User` table
- `role_ids` are from `XX_SecurityGroupRole` table (IDs from step 4, NOT from xx_UserLevel)
- Must assign 1-2 roles

### Response (201)
```json
{
  "message": "User 'john.doe' added to security group 'Finance Team'",
  "membership": {
    "membership_id": 5,
    "user_id": 10,
    "username": "john.doe",
    "assigned_roles": ["Accountant", "Manager"],
    "is_active": true,
    "joined_at": "2025-12-10T12:00:00Z"
  }
}
```

**At this point, User #10 sees ALL group segments (E001, E005, E009, E011, A100, A200, A300, P001, P005) ✅**

---

## 7. ASSIGN SPECIFIC SEGMENTS TO MEMBER (RESTRICT ACCESS)

### Endpoint
```
POST /api/auth/security-groups/1/members/5/segments/
```

### Request Body (RECOMMENDED FORMAT)
```json
{
  "segments": {
    "1": ["E005", "E009", "E011"],
    "2": ["A100"],
    "3": ["P005"]
  }
}
```

**Explanation:**
- `"1"` = Segment Type 1 (Entity)
- `"2"` = Segment Type 2 (Account)
- `"3"` = Segment Type 3 (Project)
- User will now see ONLY: E005, E009, E011, A100, P005

### Response (200)
```json
{
  "message": "Assigned 5 specific segments to member 'john.doe'",
  "assigned_count": 5,
  "access_mode": "restricted"
}
```

**Now User #10 sees ONLY: E005, E009, E011, A100, P005 ✅**

---

## 8. VIEW MEMBER'S ACCESSIBLE SEGMENTS

### Endpoint
```
GET /api/auth/security-groups/1/members/5/segments/
```

### Response (200)
```json
{
  "membership_id": 5,
  "user": "john.doe",
  "group": "Finance Team",
  "has_specific_assignments": true,
  "access_mode": "restricted",
  "accessible_segments": [
    {
      "segment_type_id": 1,
      "segment_type_name": "Entity",
      "segment_count": 3,
      "segments": [
        {"code": "E005", "alias": "IT Dept", "description": "Information Technology"},
        {"code": "E009", "alias": "Operations", "description": "Operations Department"},
        {"code": "E011", "alias": "Marketing", "description": "Marketing Department"}
      ]
    },
    {
      "segment_type_id": 2,
      "segment_type_name": "Account",
      "segment_count": 1,
      "segments": [
        {"code": "A100", "alias": "Salaries", "description": "Salary Payments"}
      ]
    },
    {
      "segment_type_id": 3,
      "segment_type_name": "Project",
      "segment_count": 1,
      "segments": [
        {"code": "P005", "alias": "Project Beta", "description": "Beta Project"}
      ]
    }
  ],
  "total_segment_types": 3
}
```

---

## 9. REMOVE MEMBER'S SEGMENT RESTRICTIONS (GIVE FULL ACCESS)

### Endpoint
```
DELETE /api/auth/security-groups/1/members/5/segments/
```

### Response (200)
```json
{
  "message": "Removed 5 specific segment assignments. Member now has full group access.",
  "removed_count": 5,
  "access_mode": "full_group_access"
}
```

**Now User #10 sees ALL group segments again ✅**

---

## 10. GET USER'S ACCESSIBLE SEGMENTS (ALL GROUPS)

### Endpoint
```
GET /api/auth/users/10/accessible-segments/
```

### Response (200)
```json
{
  "user_id": 10,
  "username": "john.doe",
  "roles": ["Accountant", "Manager", "Developer"],
  "accessible_segments": [
    {
      "segment_type_id": 1,
      "segment_type_name": "Entity",
      "segment_count": 5,
      "segments": [
        {"code": "E001", "alias": "Finance Dept", "description": "..."},
        {"code": "E005", "alias": "IT Dept", "description": "..."},
        {"code": "E009", "alias": "Operations", "description": "..."},
        {"code": "E011", "alias": "Marketing", "description": "..."},
        {"code": "E020", "alias": "Sales", "description": "..."}
      ]
    },
    {
      "segment_type_id": 2,
      "segment_type_name": "Account",
      "segment_count": 3,
      "segments": [
        {"code": "A100", "alias": "Salaries", "description": "..."},
        {"code": "A200", "alias": "Travel", "description": "..."},
        {"code": "A300", "alias": "Equipment", "description": "..."}
      ]
    }
  ],
  "total_segment_types": 2
}
```

**This shows aggregated segments from ALL groups the user belongs to.**

---

## 11. UPDATE MEMBER'S ROLES

### Endpoint
```
PUT /api/auth/security-groups/1/members/5/
```

### Request Body
```json
{
  "role_ids": [6],
  "notes": "Changed to Manager only"
}
```

### Response (200)
```json
{
  "message": "Membership updated successfully",
  "assigned_roles": ["Manager"]
}
```

---

## 12. REMOVE MEMBER FROM GROUP

### Endpoint
```
DELETE /api/auth/security-groups/1/members/5/
```

### Response (200)
```json
{
  "message": "User 'john.doe' removed from group 'Finance Team'"
}
```

---

## 13. REMOVE ROLE FROM GROUP

### Endpoint
```
DELETE /api/auth/security-groups/1/roles/5/
```

**Note:** `5` is the `XX_SecurityGroupRole` ID, not the role_id from xx_UserLevel.

### Response (200)
```json
{
  "message": "Role 'Accountant' removed from security group 'Finance Team'"
}
```

---

## 14. REMOVE SEGMENT FROM GROUP

### Endpoint
```
DELETE /api/auth/security-groups/1/segments/10/
```

**Note:** `10` is the `XX_SecurityGroupSegment` ID.

### Response (200)
```json
{
  "message": "Segment 'Entity: E001' removed from security group 'Finance Team'"
}
```

---

## 15. UPDATE GROUP

### Endpoint
```
PUT /api/auth/security-groups/1/
```

### Request Body
```json
{
  "group_name": "Finance Department",
  "description": "Updated description",
  "is_active": true
}
```

### Response (200)
```json
{
  "message": "Security group updated successfully",
  "group": {
    "group_id": 1,
    "group_name": "Finance Department",
    "description": "Updated description",
    "is_active": true
  }
}
```

---

## 16. DELETE GROUP (SOFT DELETE)

### Endpoint
```
DELETE /api/auth/security-groups/1/
```

### Response (200)
```json
{
  "message": "Security group 'Finance Team' deleted successfully"
}
```

---

## COMPLETE WORKFLOW EXAMPLE

### Scenario: Create Finance Team with Restricted Members

```bash
# Step 1: Create Group
POST /api/auth/security-groups/
{
  "group_name": "Finance Team",
  "description": "Finance department"
}
# Response: group_id = 1

# Step 2: Add Roles to Group
POST /api/auth/security-groups/1/roles/
{
  "role_ids": [2, 3]  # Accountant, Manager from xx_UserLevel
}
# Response: Added 2 roles, XX_SecurityGroupRole IDs = [5, 6]

# Step 3: Add Segments to Group (10 segments total)
POST /api/auth/security-groups/1/segments/
{
  "segment_assignments": [
    {
      "segment_type_id": 1,
      "segment_codes": ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    }
  ]
}
# Response: Added 10 segments

# Step 4: Add Manager (Full Access)
POST /api/auth/security-groups/1/members/
{
  "user_id": 5,
  "role_ids": [6],  # Manager role (XX_SecurityGroupRole ID)
  "notes": "Finance Manager - full access"
}
# Response: membership_id = 1
# Manager sees ALL 10 segments ✅

# Step 5: Add Accountant #1 (Restricted to segments 5 and 6)
POST /api/auth/security-groups/1/members/
{
  "user_id": 10,
  "role_ids": [5],  # Accountant role
  "notes": "Handles regions 5 and 6"
}
# Response: membership_id = 2

# Step 6: Restrict Accountant #1 to segments 5 and 6
POST /api/auth/security-groups/1/members/2/segments/
{
  "segments": {
    "1": ["E005", "E006"]
  }
}
# Response: Assigned 2 segments
# Accountant #1 sees ONLY E005, E006 ✅

# Step 7: Add Accountant #2 (Restricted to segments 9, 10)
POST /api/auth/security-groups/1/members/
{
  "user_id": 11,
  "role_ids": [5],
  "notes": "Handles regions 9 and 10"
}
# Response: membership_id = 3

POST /api/auth/security-groups/1/members/3/segments/
{
  "segments": {
    "1": ["E009", "E010"]
  }
}
# Accountant #2 sees ONLY E009, E010 ✅

# Step 8: Verify Access
GET /api/auth/security-groups/1/members/1/segments/
# Manager: Sees all 10 segments (no restrictions)

GET /api/auth/security-groups/1/members/2/segments/
# Accountant #1: Sees E005, E006 only

GET /api/auth/security-groups/1/members/3/segments/
# Accountant #2: Sees E009, E010 only
```

---

## ERROR RESPONSES

### 400 Bad Request - Segment Not in Group
```json
{
  "errors": [
    "Segment Type 1, Code 'E999' not found in group or not active"
  ]
}
```

### 404 Not Found - Group Doesn't Exist
```json
{
  "error": "Security group not found"
}
```

### 400 Bad Request - Invalid Role Count
```json
{
  "error": "User must have 1-2 roles assigned"
}
```

### 400 Bad Request - Role Count Validation
```json
{
  "error": "User can have maximum 2 roles assigned in the security group."
}
```

---

## POSTMAN COLLECTION SETUP

### Environment Variables
```
base_url: http://localhost:8000
token: YOUR_AUTH_TOKEN_HERE
```

### Headers (All Requests)
```
Authorization: Bearer {{token}}
Content-Type: application/json
```

### Tests (Add to GET requests)
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has data", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.be.an('object');
});
```

---

## QUICK TESTING CHECKLIST

- [ ] Create security group
- [ ] Add 2 roles to group
- [ ] Add 10 segments to group
- [ ] Get group details (verify roles and segments)
- [ ] Add member with full access
- [ ] Verify member sees all 10 segments
- [ ] Restrict member to 2 segments
- [ ] Verify member sees only 2 segments
- [ ] Remove restrictions
- [ ] Verify member sees all 10 segments again
- [ ] Get user's accessible segments (all groups)
- [ ] Update member's roles
- [ ] Remove member from group
- [ ] Delete group

---

## SEGMENT TYPE ID REFERENCE

To find your segment type IDs:

```
GET /api/account-entitys/segments/types/

Response:
[
  {"segment_id": 1, "segment_name": "Entity", "is_required": true},
  {"segment_id": 2, "segment_name": "Account", "is_required": true},
  {"segment_id": 3, "segment_name": "Project", "is_required": false}
]
```

Use these `segment_id` values in your requests!

---

**Ready to test in Postman!** 🚀
