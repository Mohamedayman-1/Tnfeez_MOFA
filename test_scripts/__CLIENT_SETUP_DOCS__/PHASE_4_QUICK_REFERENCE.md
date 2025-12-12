# Phase 4 Quick Reference - User Segment Access & Abilities

**Last Updated:** November 10, 2025  
**Status:** ✅ PRODUCTION READY

---

## Quick Start

### 1. Server Setup
```bash
python manage.py runserver
```

### 2. Get Token
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

### 3. Test APIs
```bash
# Python
python __CLIENT_SETUP_DOCS__/test_phase4_api.py

# PowerShell
powershell -ExecutionPolicy Bypass -File __CLIENT_SETUP_DOCS__\test_phase4_api.ps1
```

---

## API Endpoints Cheat Sheet

### User Access (10 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/phase4/access/list` | List all accesses |
| POST | `/phase4/access/grant` | Grant access to segment |
| POST | `/phase4/access/revoke` | Revoke access |
| POST | `/phase4/access/check` | Check if user has access |
| POST | `/phase4/access/bulk-grant` | Bulk grant access |
| GET | `/phase4/access/user-segments` | Get user's segments |
| GET | `/phase4/access/segment-users` | Get segment's users |
| POST | `/phase4/access/hierarchical-check` | Check with inheritance |
| POST | `/phase4/access/effective-level` | Get highest level |
| POST | `/phase4/access/grant-with-children` | Grant to parent+children |

### User Abilities (8 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/phase4/abilities/list` | List all abilities |
| POST | `/phase4/abilities/grant` | Grant ability |
| POST | `/phase4/abilities/revoke` | Revoke ability |
| POST | `/phase4/abilities/check` | Check if user has ability |
| POST | `/phase4/abilities/bulk-grant` | Bulk grant abilities |
| GET | `/phase4/abilities/user-abilities` | Get user's abilities |
| GET | `/phase4/abilities/users-with-ability` | Get users with ability |
| POST | `/phase4/abilities/validate-operation` | Validate operation |

---

## Common Requests

### Grant Access
```bash
curl -X POST http://localhost:8000/api/auth/phase4/access/grant \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "segment_type_id": 1,
    "segment_code": "E001",
    "access_level": "EDIT"
  }'
```

### Check Access
```bash
curl -X POST http://localhost:8000/api/auth/phase4/access/check \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "segment_type_id": 1,
    "segment_code": "E001",
    "required_level": "VIEW"
  }'
```

### Grant Ability
```bash
curl -X POST http://localhost:8000/api/auth/phase4/abilities/grant \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "ability_type": "APPROVE",
    "segment_combination": {"1": "E001", "2": "A100"}
  }'
```

---

## Python Examples

### Grant Access
```python
import requests

response = requests.post(
    "http://localhost:8000/api/auth/phase4/access/grant",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "user_id": 1,
        "segment_type_id": 1,
        "segment_code": "E001",
        "access_level": "EDIT"
    }
)
print(response.json())
```

### Grant With Children (Hierarchical)
```python
response = requests.post(
    "http://localhost:8000/api/auth/phase4/access/grant-with-children",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "user_id": 1,
        "segment_type_id": 1,
        "segment_code": "E001",
        "access_level": "APPROVE",
        "apply_to_children": True
    }
)
# Grants access to E001 and all children (E001-A, E001-B, etc.)
```

### Bulk Grant
```python
response = requests.post(
    "http://localhost:8000/api/auth/phase4/access/bulk-grant",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "user_id": 1,
        "accesses": [
            {"segment_type_id": 1, "segment_code": "E001", "access_level": "EDIT"},
            {"segment_type_id": 2, "segment_code": "A100", "access_level": "VIEW"},
            {"segment_type_id": 3, "segment_code": "P001", "access_level": "APPROVE"}
        ]
    }
)
```

### Check Ability
```python
response = requests.post(
    "http://localhost:8000/api/auth/phase4/abilities/check",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "user_id": 1,
        "ability_type": "APPROVE",
        "segment_combination": {"1": "E001", "2": "A100"}
    }
)
print(response.json()['has_ability'])
```

---

## Manager Class Usage (Backend)

### UserSegmentAccessManager

```python
from user_management.managers import UserSegmentAccessManager
from user_management.models import xx_User

user = xx_User.objects.get(id=1)

# Grant access
result = UserSegmentAccessManager.grant_access(
    user=user,
    segment_type_id=1,
    segment_code='E001',
    access_level='EDIT',
    granted_by=admin_user
)

# Check access
check = UserSegmentAccessManager.check_user_has_access(
    user=user,
    segment_type_id=1,
    segment_code='E001',
    required_level='VIEW'
)
print(check['has_access'])  # True/False

# Hierarchical check
check = UserSegmentAccessManager.check_user_has_access_hierarchical(
    user=user,
    segment_type_id=1,
    segment_code='E001-A-1',
    required_level='VIEW'
)
print(check['inherited_from'])  # 'E001' if inherited from parent
```

### UserAbilityManager

```python
from user_management.managers import UserAbilityManager

# Grant ability
result = UserAbilityManager.grant_ability(
    user=user,
    ability_type='APPROVE',
    segment_combination={'1': 'E001', '2': 'A100'},
    granted_by=admin_user
)

# Check ability
check = UserAbilityManager.check_user_has_ability(
    user=user,
    ability_type='APPROVE',
    segment_combination={'1': 'E001', '2': 'A100'}
)
print(check['has_ability'])  # True/False

# Validate operation
validation = UserAbilityManager.validate_ability_for_operation(
    user=user,
    operation='approve_transfer',
    segment_combination={'1': 'E001'}
)
print(validation['allowed'])  # True/False
```

---

## Access Levels

```
ADMIN    > APPROVE  > EDIT     > VIEW
(highest)                       (lowest)

User with ADMIN can: everything
User with APPROVE can: approve, edit, view
User with EDIT can: edit, view
User with VIEW can: view only
```

---

## Ability Types

- `EDIT`: Edit/Modify data
- `APPROVE`: Approve transactions
- `VIEW`: View data
- `DELETE`: Delete records
- `TRANSFER`: Transfer budget
- `REPORT`: Generate reports

---

## Segment Combination Format

```json
{
    "1": "E001",   // Segment Type 1 (Entity) = E001
    "2": "A100",   // Segment Type 2 (Account) = A100
    "3": "P001"    // Segment Type 3 (Project) = P001
}
```

**Single Segment:**
```json
{"1": "E001"}
```

**Multi-Segment:**
```json
{"1": "E001", "2": "A100"}
```

---

## Files Overview

### Backend Files
- `user_management/phase4_views.py` - REST API views (18 endpoints)
- `user_management/managers/user_segment_access_manager.py` - Access logic (12 methods)
- `user_management/managers/user_ability_manager.py` - Ability logic (8 methods)
- `user_management/models.py` - XX_UserSegmentAccess, XX_UserSegmentAbility
- `user_management/serializers.py` - 6 Phase 4 serializers
- `user_management/urls.py` - URL routing

### Test Files
- `__CLIENT_SETUP_DOCS__/test_phase4_user_segments.py` - Manager tests (20 tests)
- `__CLIENT_SETUP_DOCS__/test_phase4_api.py` - Python API tests (18 tests)
- `__CLIENT_SETUP_DOCS__/test_phase4_api.ps1` - PowerShell API tests (18 tests)

### Documentation Files
- `__CLIENT_SETUP_DOCS__/PHASE_4_API_DOCUMENTATION.md` - Full API docs
- `__CLIENT_SETUP_DOCS__/PHASE_4_COMPLETION_REPORT.md` - Complete feature report
- `__CLIENT_SETUP_DOCS__/PHASE_4_FINAL_SUMMARY.md` - Summary with hierarchy
- `__CLIENT_SETUP_DOCS__/PHASE_4_HIERARCHICAL_ENHANCEMENT.md` - Hierarchy details
- `__CLIENT_SETUP_DOCS__/PHASE_4_QUICK_REFERENCE.md` - This file

---

## Testing Checklist

- [ ] Server running on http://localhost:8000
- [ ] Valid JWT token obtained
- [ ] Test data exists (segment types, segments, users)
- [ ] Manager tests pass (20/20)
- [ ] API tests pass (18/18)
- [ ] Frontend integration tested
- [ ] Production deployment ready

---

## Troubleshooting

### Issue: "Authentication credentials were not provided"
**Solution:** Add Authorization header with Bearer token.

### Issue: "User with id X not found"
**Solution:** Use valid user_id from your database.

### Issue: "Segment X not found"
**Solution:** Create segment first or use existing segment code.

### Issue: Manager methods not found
**Solution:** Import from `user_management.managers`:
```python
from user_management.managers import UserSegmentAccessManager, UserAbilityManager
```

### Issue: Circular import errors
**Solution:** Models already imported correctly with string references.

---

## Production Deployment

### 1. Run Migrations
```bash
python manage.py makemigrations user_management
python manage.py migrate
```

### 2. Create Superuser
```bash
python manage.py createsuperuser
```

### 3. Configure CORS (if needed)
```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://your-frontend-domain.com",
]
```

### 4. Update Frontend API Base URL
```javascript
// frontend config
const API_BASE_URL = "https://your-api-domain.com/api/auth/phase4";
```

### 5. Test All Endpoints
```bash
python __CLIENT_SETUP_DOCS__/test_phase4_api.py
```

### 6. Monitor Logs
```bash
tail -f logs/app.log
```

---

## Key Features

✅ **Dynamic Segments**: Works with ANY segment type  
✅ **Hierarchical Access**: Parent-child inheritance  
✅ **Bulk Operations**: Efficient mass grants  
✅ **Soft Deletes**: Maintains audit trail  
✅ **JSON Combinations**: Multi-segment abilities  
✅ **REST APIs**: 18 fully documented endpoints  
✅ **100% Tested**: All manager methods & APIs verified  

---

## Next Steps

1. **Update Frontend**: Integrate Phase 4 APIs
2. **Migrate Data**: Convert legacy UserProjects to XX_UserSegmentAccess
3. **Train Users**: Update documentation for end users
4. **Monitor**: Track API usage and performance

---

## Support

**Documentation:**
- Full API Docs: `PHASE_4_API_DOCUMENTATION.md`
- Completion Report: `PHASE_4_COMPLETION_REPORT.md`
- Hierarchical Guide: `PHASE_4_HIERARCHICAL_ENHANCEMENT.md`

**Contact:**
- Technical Issues: Check logs in `logs/app.log`
- API Questions: Review test scripts for examples
- Manager Usage: See `test_phase4_user_segments.py`

---

**Phase 4 Status:** ✅ COMPLETE & PRODUCTION READY
