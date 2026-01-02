# Audit Logging System - Quick Reference

## ✅ What's Been Implemented

### Core Components

1. **Models** (`user_management/audit_models.py`)

   - `XX_AuditLog` - Main audit log for all actions
   - `XX_AuditLoginHistory` - Dedicated login/logout tracking

2. **Middleware** (`user_management/audit_middleware.py`)

   - Automatic request logging
   - Exception tracking
   - Duration measurement

3. **Utilities** (`user_management/audit_utils.py`)

   - `AuditLogger` class for programmatic logging
   - Helper methods for common scenarios

4. **API Views** (`user_management/audit_views.py`)

   - `AuditLogViewSet` - CRUD for audit logs
   - `LoginHistoryViewSet` - Login history access

5. **Serializers** (`user_management/audit_serializers.py`)

   - JSON serialization for API responses

6. **Admin Interface** (`user_management/admin.py`)

   - Django admin integration
   - Read-only audit log browsing

7. **URLs** (`user_management/urls_audit.py`)

   - RESTful API routing

8. **Documentation**
   - Complete guide in `__CLIENT_SETUP_DOCS__/AUDIT_LOGGING_GUIDE.md`
   - Examples in `audit_logging_examples.py`

---

## 🚀 Quick Start

### 1. Database Migration

Already completed:

```bash
python manage.py makemigrations user_management
python manage.py migrate user_management
```

### 2. Middleware Configuration

Already added to `settings.py`:

```python
MIDDLEWARE = [
    # ... other middleware
    "user_management.audit_middleware.AuditLoggingMiddleware",
]
```

### 3. Start Using

The system is now active! All requests are automatically logged.

---

## 📊 API Endpoints

Base URL: `/api/auth/audit/`

### Audit Logs

- `GET /api/auth/audit/logs/` - List all logs (with filters)
- `GET /api/auth/audit/logs/{id}/` - Get specific log
- `GET /api/auth/audit/logs/my_activity/` - Current user's activity
- `GET /api/auth/audit/logs/statistics/?days=30` - Statistics (admin)
- `GET /api/auth/audit/logs/recent_errors/` - Recent errors (admin)
- `GET /api/auth/audit/logs/action_types/` - List action types
- `GET /api/auth/audit/logs/modules/` - List modules

### Login History

- `GET /api/auth/audit/login-history/` - List login attempts
- `GET /api/auth/audit/login-history/{id}/` - Get specific login
- `GET /api/auth/audit/login-history/my_history/` - Current user's logins
- `GET /api/auth/audit/login-history/failed_attempts/?days=7` - Failed logins (admin)

---

## 💻 Programmatic Usage

### Import

```python
from user_management.audit_utils import AuditLogger
```

### Examples

**Log any action:**

```python
AuditLogger.log_action(
    user=request.user,
    action_type='APPROVE',
    action_description='Approved transaction 123',
    affected_object=transaction,
    request=request
)
```

**Log model changes:**

```python
# Create
AuditLogger.log_model_change(user, new_object, 'CREATE', request=request)

# Update (with comparison)
AuditLogger.log_model_change(user, updated_object, 'UPDATE',
                             old_instance=original_object, request=request)

# Delete
AuditLogger.log_model_change(user, object_to_delete, 'DELETE', request=request)
```

**Log approvals:**

```python
AuditLogger.log_approval(
    user=request.user,
    transaction=transaction,
    action='approve',  # or 'reject'
    comments='Budget verified',
    request=request
)
```

**Log exports:**

```python
AuditLogger.log_export(
    user=request.user,
    export_type='transactions',
    record_count=150,
    request=request
)
```

---

## 🔍 What Gets Logged Automatically?

### Via Middleware

- ✅ All POST, PUT, PATCH, DELETE requests
- ✅ GET requests to sensitive endpoints (configurable)
- ✅ User, IP address, user agent
- ✅ Request duration
- ✅ Status codes
- ✅ Exceptions and errors

### Via Enhanced Views

- ✅ Login attempts (success and failures)
- ✅ Logout events

### Requires Manual Logging

- Business logic operations (approvals, rejections)
- Bulk operations
- Celery background tasks
- Custom workflows

---

## 🎯 Action Types

- **CREATE** - Creating records
- **READ** - Reading/viewing data
- **UPDATE** - Modifying records
- **DELETE** - Deleting records
- **LOGIN** - User login
- **LOGOUT** - User logout
- **APPROVE** - Approval actions
- **REJECT** - Rejection actions
- **SUBMIT** - Workflow submissions
- **EXPORT** - Data exports
- **IMPORT** - Data imports
- **UPLOAD** - File uploads
- **DOWNLOAD** - File downloads
- **PERMISSION_CHANGE** - Permission modifications
- **WORKFLOW** - Workflow actions
- **OTHER** - Other actions

---

## 🔐 Security & Permissions

### View Access

- **Regular Users**: Can only see their own audit logs
- **Admin/SuperAdmin**: Can see all audit logs

### Admin Access

- Statistics endpoint requires admin role
- Recent errors endpoint requires admin role
- Failed login attempts requires admin role
- Only superadmins can delete audit logs

---

## 📈 Filtering Examples

### By user:

```
GET /api/auth/audit/logs/?user_id=5
```

### By action type:

```
GET /api/auth/audit/logs/?action_type=CREATE
```

### By date range:

```
GET /api/auth/audit/logs/?start_date=2026-01-01&end_date=2026-01-02
```

### Search in description:

```
GET /api/auth/audit/logs/?search=transaction%20123
```

### Multiple filters:

```
GET /api/auth/audit/logs/?action_type=UPDATE&status=FAILED&severity=ERROR
```

---

## 🎨 Django Admin

Access at:

- `/admin/user_management/xx_auditlog/`
- `/admin/user_management/xx_auditloginhistory/`

Features:

- Read-only interface
- Advanced filtering
- Date hierarchy
- Search functionality
- Collapsible detailed view

---

## 📋 Database Tables

- `XX_AUDIT_LOG_XX` - Main audit log
- `XX_AUDIT_LOGIN_HISTORY_XX` - Login history

Both have appropriate indexes for performance.

---

## 🔧 Configuration

### Exclude paths from logging

Edit `user_management/audit_middleware.py`:

```python
EXCLUDED_PATHS = [
    '/admin/jsi18n/',
    '/static/',
    '/your-path/',
]
```

### Change logged HTTP methods

```python
LOGGED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
```

### Add sensitive GET paths

```python
SENSITIVE_GET_PATHS = [
    '/api/transfers/',
    '/api/your-endpoint/',
]
```

---

## ⚠️ Important Notes

1. **Automatic Logging**: Most actions are logged automatically via middleware
2. **Manual Logging**: Use `AuditLogger` for business logic and important actions
3. **Performance**: Audit logging doesn't block requests (fail silently)
4. **Storage**: Logs are never auto-deleted (implement retention policy if needed)
5. **Sensitive Data**: Don't log passwords or tokens
6. **Errors**: Failed audit logs won't break the application

---

## 📚 Documentation

- **Complete Guide**: `__CLIENT_SETUP_DOCS__/AUDIT_LOGGING_GUIDE.md`
- **Code Examples**: `audit_logging_examples.py`
- **API Documentation**: See complete guide for full API reference

---

## ✨ Features Summary

✅ **Automatic request logging** via middleware  
✅ **Login/logout tracking** with dedicated history  
✅ **Model change tracking** with before/after comparison  
✅ **API endpoints** for querying audit logs  
✅ **Django admin interface** for browsing  
✅ **Statistics and analytics** for admins  
✅ **Error tracking** with stack traces  
✅ **IP address and user agent** logging  
✅ **Flexible programmatic API** for custom logging  
✅ **Permission-based access** control  
✅ **Comprehensive documentation** and examples

---

**Status**: ✅ Fully Implemented and Ready to Use  
**Version**: 1.0  
**Date**: January 2, 2026
