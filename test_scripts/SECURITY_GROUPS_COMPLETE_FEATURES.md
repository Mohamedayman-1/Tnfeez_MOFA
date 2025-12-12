# Security Groups & Roles - Complete Delete & Activate Features

## ✅ Implementation Summary

### Backend Endpoints Added

#### 1. **Security Group Permanent Delete**
```
DELETE /api/auth/security-groups/<group_id>/delete-permanent/
```
- Permanently deletes a security group
- Validates no active members
- Validates no associated budget transfers
- Returns success message with deleted group info

#### 2. **Role Activate (Reactivate Inactive Role)**
```
PATCH /api/auth/security-groups/<group_id>/roles/<role_id>/activate/
```
- Reactivates an inactive role (is_active=False → True)
- Validates role exists and is not already active
- Returns success with role details

#### 3. **Role Permanent Delete**
```
DELETE /api/auth/security-groups/<group_id>/roles/<role_id>/delete-permanent/
```
- Permanently deletes a role from security group
- Validates no active members are using this role
- Cannot be undone

---

## 📁 Files Modified

### Backend Files

1. **`user_management/views_security_groups.py`**
   - Added `SecurityGroupDeletePermanentView` class
   - Added `SecurityGroupRoleActivateView` class
   - Added `SecurityGroupRoleDeletePermanentView` class
   - Updated existing delete methods with better descriptions

2. **`user_management/urls.py`**
   - Added route: `security-groups/<int:group_id>/delete-permanent/`
   - Added route: `security-groups/<int:group_id>/roles/<int:role_id>/activate/`
   - Added route: `security-groups/<int:group_id>/roles/<int:role_id>/delete-permanent/`
   - Added imports for new view classes

### Frontend Files

3. **`Tanfeex_Mofa/src/api/securityGroups.api.ts`**
   - Added `activateGroupRole` mutation
   - Added `deleteGroupRolePermanent` mutation
   - Added `deleteSecurityGroupPermanent` mutation
   - Exported hooks:
     - `useActivateGroupRoleMutation`
     - `useDeleteGroupRolePermanentMutation`
     - `useDeleteSecurityGroupPermanentMutation`

4. **`Tanfeex_Mofa/src/pages/dashboard/components/GroupRolesTab.tsx`**
   - Added imports: `CheckCircle`, `XCircle` icons
   - Added handlers:
     - `handleDeactivateRole()` - soft delete (sets is_active=False)
     - `handleActivateRole()` - reactivates inactive role
     - `handleDeletePermanent()` - permanent delete with confirmation
   - Updated UI:
     - Shows green CheckCircle button for inactive roles
     - Shows orange XCircle button for active roles (deactivate)
     - Shows red Trash2 button for permanent delete

5. **`Tanfeex_Mofa/src/pages/dashboard/SecurityGroups.tsx`**
   - Added `useDeleteSecurityGroupPermanentMutation` hook
   - Added `handleDeleteGroupPermanent()` handler
   - Updated `handleDeleteGroup()` to be deactivate instead of delete
   - Passed `onDeletePermanent` prop to `GroupDetailsPanel`

6. **`Tanfeex_Mofa/src/pages/dashboard/components/GroupDetailsPanel.tsx`**
   - Added `XCircle` icon import
   - Updated interface to include `onDeletePermanent` callback
   - Updated header buttons:
     - Orange XCircle button for deactivate
     - Red Trash2 button for permanent delete
   - Added tooltips for all action buttons

---

## 🎨 UI/UX Features

### Role Management Buttons

| State | Icon | Color | Action |
|-------|------|-------|--------|
| **Active Role** | XCircle | Orange | Deactivate (soft delete) |
| **Inactive Role** | CheckCircle | Green | Reactivate |
| **Any Role** | Trash2 | Red | Delete Permanently |

### Security Group Buttons

| Icon | Color | Action |
|------|-------|--------|
| Edit | White/Transparent | Edit group (TODO) |
| XCircle | Orange | Deactivate group |
| Trash2 | Red | Delete Permanently |

---

## 🔒 Safety Features

### Role Permanent Delete
- ✅ Checks if active members are using the role
- ✅ Blocks deletion if role is assigned to active members
- ✅ Shows member count in error message
- ✅ Confirmation dialog before delete

### Security Group Permanent Delete
- ✅ Checks if group has active members
- ✅ Checks if budget transfers are associated
- ✅ Blocks deletion if either condition is true
- ✅ Shows counts in error message
- ✅ Confirmation dialog with group name

---

## 📝 Translation Keys Needed

Add to `en.json` and `ar.json`:

```json
{
  "securityGroups": {
    "activateRole": "Activate Role",
    "deactivateRole": "Deactivate Role",
    "deletePermanent": "Delete Permanently",
    "roleActivated": "Role activated successfully",
    "roleDeactivated": "Role deactivated successfully",
    "roleDeletedPermanent": "Role permanently deleted",
    "confirmDeactivate": "Are you sure you want to deactivate this role?",
    "confirmDeletePermanent": "Are you sure you want to PERMANENTLY delete {{name}}? This cannot be undone.",
    "groupDeactivated": "Security group deactivated",
    "groupDeletedPermanent": "Security group permanently deleted",
    "confirmDeactivateGroup": "Are you sure you want to deactivate this group?",
    "confirmDeleteGroupPermanent": "Are you sure you want to PERMANENTLY delete {{name}}? This cannot be undone.",
    "deactivate": "Deactivate",
    "edit": "Edit"
  }
}
```

---

## 🧪 Testing Guide

### Test Role Activation
1. Navigate to Security Groups → Select a group → Roles tab
2. Find an inactive role (gray badge)
3. Click green CheckCircle button
4. Role should show as active (green badge)
5. Button changes to orange XCircle (deactivate)

### Test Role Deactivation
1. Find an active role
2. Click orange XCircle button
3. Confirm in dialog
4. Role becomes inactive
5. Button changes to green CheckCircle

### Test Role Permanent Delete
1. Find any role (active or inactive)
2. Click red Trash2 button
3. Confirm in dialog
4. If role has active members → Error message
5. If role has no members → Role deleted permanently

### Test Security Group Permanent Delete
1. Select a security group
2. Click red Trash2 button in header
3. Confirm in dialog
4. If group has active members → Error with count
5. If group has budget transfers → Error with count
6. If group is empty → Deleted permanently

---

## 🔗 API Examples

### Activate Role
```bash
curl -X PATCH http://localhost:8000/api/auth/security-groups/1/roles/5/activate/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Delete Role Permanently
```bash
curl -X DELETE http://localhost:8000/api/auth/security-groups/1/roles/5/delete-permanent/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Delete Security Group Permanently
```bash
curl -X DELETE http://localhost:8000/api/auth/security-groups/1/delete-permanent/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ✨ Next Steps

1. Add translation keys to locale files
2. Test all endpoints with Postman or frontend
3. Add audit logging for permanent deletes
4. Implement group edit functionality (marked as TODO)
5. Consider adding "restore" feature for soft-deleted items

---

**Status**: ✅ Complete - Ready for Testing
**Date**: December 11, 2025
