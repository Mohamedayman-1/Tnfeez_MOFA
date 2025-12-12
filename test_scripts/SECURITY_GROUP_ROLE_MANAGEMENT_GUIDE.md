"""
TEST GUIDE: Security Group Role Management - Activate & Delete

Two new endpoints have been added to manage inactive roles in security groups:

================================================================================
1. REACTIVATE AN INACTIVE ROLE
================================================================================

Endpoint: PATCH /api/auth/security-groups/<group_id>/roles/<role_id>/activate/

Purpose: Reactivate an inactive role (is_active=False) back to active (is_active=True)

Example Request:
----------------
PATCH http://localhost:8000/api/auth/security-groups/1/roles/5/activate/

Headers:
Authorization: Bearer <your_access_token>

Response (Success):
------------------
{
    "success": true,
    "message": "Role 'Finance Manger' has been reactivated in group 'Finance Team'",
    "role": {
        "id": 5,
        "role_id": 42,
        "role_name": "Finance Manger",
        "is_active": true,
        "group_name": "Finance Team"
    }
}

Response (Already Active):
--------------------------
Status: 400 Bad Request
{
    "error": "Role is already active",
    "role_name": "Finance Manger"
}

Response (Not Found):
--------------------
Status: 404 Not Found
{
    "error": "Role not found in this security group"
}

================================================================================
2. PERMANENTLY DELETE A ROLE
================================================================================

Endpoint: DELETE /api/auth/security-groups/<group_id>/roles/<role_id>/delete-permanent/

Purpose: Permanently delete a role from the security group (cannot be undone)

⚠️  WARNING: This will permanently delete the XX_SecurityGroupRole record.
   If any active members are assigned this role, the deletion will be blocked.

Example Request:
----------------
DELETE http://localhost:8000/api/auth/security-groups/1/roles/5/delete-permanent/

Headers:
Authorization: Bearer <your_access_token>

Response (Success):
------------------
{
    "success": true,
    "message": "Role 'Finance Manger' has been permanently deleted from group 'Finance Team'",
    "deleted_role": {
        "role_name": "Finance Manger",
        "group_name": "Finance Team"
    }
}

Response (Members Assigned):
----------------------------
Status: 400 Bad Request
{
    "error": "Cannot delete role",
    "message": "2 active member(s) are assigned this role. Please remove the role from members first.",
    "active_members_count": 2
}

Response (Not Found):
--------------------
Status: 404 Not Found
{
    "error": "Role not found in this security group"
}

================================================================================
EXISTING ENDPOINT (For Reference)
================================================================================

3. SOFT DELETE (Deactivate) A ROLE
-----------------------------------
Endpoint: DELETE /api/auth/security-groups/<group_id>/roles/<role_id>/

Purpose: Deactivate a role (sets is_active=False, can be reactivated later)

This is the default delete behavior - it doesn't permanently remove the role,
just makes it inactive. You can reactivate it using endpoint #1 above.

================================================================================
YOUR SPECIFIC CASE: Finance Manger Role
================================================================================

Current Situation:
- Group: Finance Team (ID: 1)
- Role: Finance Manger (XX_SecurityGroupRole ID: 5)
- Status: INACTIVE (is_active=False)

Solution Options:
-----------------

Option A: Reactivate the existing role (RECOMMENDED)
   PATCH http://localhost:8000/api/auth/security-groups/1/roles/5/activate/

Option B: Delete permanently and add fresh
   Step 1: DELETE http://localhost:8000/api/auth/security-groups/1/roles/5/delete-permanent/
   Step 2: POST http://localhost:8000/api/auth/security-groups/1/roles/
           Body: {"role_ids": [42]}

================================================================================
CURL EXAMPLES
================================================================================

# Reactivate role
curl -X PATCH http://localhost:8000/api/auth/security-groups/1/roles/5/activate/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Delete permanently
curl -X DELETE http://localhost:8000/api/auth/security-groups/1/roles/5/delete-permanent/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Soft delete (deactivate)
curl -X DELETE http://localhost:8000/api/auth/security-groups/1/roles/5/ \
  -H "Authorization: Bearer YOUR_TOKEN"

================================================================================
POSTMAN COLLECTION
================================================================================

1. Activate Role
   - Method: PATCH
   - URL: {{base_url}}/api/auth/security-groups/1/roles/5/activate/
   - Headers: Authorization: Bearer {{access_token}}

2. Delete Permanently
   - Method: DELETE
   - URL: {{base_url}}/api/auth/security-groups/1/roles/5/delete-permanent/
   - Headers: Authorization: Bearer {{access_token}}

================================================================================
"""

print(__doc__)
