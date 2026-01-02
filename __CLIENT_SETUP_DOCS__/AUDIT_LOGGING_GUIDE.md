# Audit Logging System - Complete Guide

## Overview

The Tnfeez MOFA Budget Transfer System now includes a comprehensive audit logging system that tracks all user actions across the system. This provides complete visibility into who did what, when, and from where.

## Features

### 1. **Automatic Request Logging**

- All API requests are automatically logged via middleware
- Captures user, endpoint, method, IP address, and duration
- Tracks both successful and failed requests
- Records errors and exceptions

### 2. **Authentication Tracking**

- Dedicated login/logout history
- Failed login attempt tracking
- IP address and user agent logging
- Session tracking

### 3. **Model Change Tracking**

- Before/after value comparison
- Field-level change detection
- Support for any Django model
- Automatic timestamping

### 4. **Comprehensive Metadata**

- Request details (endpoint, method, IP, user agent)
- Response status codes
- Error messages and stack traces
- Custom metadata support

---

## Components

### Models

#### XX_AuditLog

Main audit log model that tracks all system actions.

**Key Fields:**

- `user` - User who performed the action (FK)
- `username` - Username (preserved even if user deleted)
- `action_type` - Type of action (CREATE, UPDATE, DELETE, LOGIN, etc.)
- `action_description` - Human-readable description
- `severity` - INFO, WARNING, ERROR, CRITICAL
- `endpoint` - API endpoint called
- `ip_address` - User's IP address
- `affected_object` - Generic FK to any model
- `old_values` / `new_values` - JSON of changed data
- `timestamp` - When action occurred
- `duration_ms` - Request duration

**Action Types:**

- CREATE - Creating new records
- READ - Reading/viewing data
- UPDATE - Modifying existing records
- DELETE - Deleting records
- LOGIN - User login
- LOGOUT - User logout
- APPROVE - Approval actions
- REJECT - Rejection actions
- SUBMIT - Workflow submissions
- EXPORT - Data exports
- IMPORT - Data imports
- UPLOAD - File uploads
- DOWNLOAD - File downloads
- PERMISSION_CHANGE - Permission modifications
- WORKFLOW - Workflow actions
- OTHER - Other actions

#### XX_AuditLoginHistory

Dedicated model for login/logout tracking.

**Key Fields:**

- `user` - User (FK)
- `username` - Username
- `login_type` - LOGIN, LOGOUT, FAILED_LOGIN, TOKEN_REFRESH
- `ip_address` - IP address
- `success` - Boolean
- `failure_reason` - Why login failed
- `timestamp` - When it occurred

---

## API Endpoints

All audit endpoints are under `/api/auth/audit/`

### Audit Logs

#### List Audit Logs

```http
GET /api/auth/audit/logs/
```

**Query Parameters:**

- `user_id` - Filter by user ID
- `username` - Filter by username (contains)
- `action_type` - Filter by action type
- `module` - Filter by module/app
- `severity` - Filter by severity (INFO, WARNING, ERROR, CRITICAL)
- `status` - Filter by status (SUCCESS, FAILED)
- `start_date` - Start date (YYYY-MM-DD)
- `end_date` - End date (YYYY-MM-DD)
- `search` - Search in action description
- `page` - Page number
- `page_size` - Results per page

**Response:**

```json
{
  "count": 100,
  "next": "http://example.com/api/auth/audit/logs/?page=2",
  "previous": null,
  "results": [
    {
      "audit_id": 1,
      "user": 5,
      "username": "admin",
      "user_display": {
        "id": 5,
        "username": "admin",
        "role": "admin"
      },
      "action_type": "CREATE",
      "action_description": "POST /api/transfers/create/",
      "severity": "INFO",
      "endpoint": "/api/transfers/create/",
      "request_method": "POST",
      "ip_address": "192.168.1.100",
      "object_repr": "Transfer 123",
      "status": "SUCCESS",
      "error_message": null,
      "timestamp": "2026-01-02T10:30:00Z",
      "duration_ms": 250,
      "module": "transfers",
      "changes": {
        "amount": {
          "old": null,
          "new": "5000.00"
        }
      },
      "metadata_dict": {
        "status_code": 201
      }
    }
  ]
}
```

#### Get Single Audit Log

```http
GET /api/auth/audit/logs/{audit_id}/
```

Returns detailed information including full old_values and new_values.

#### My Activity

```http
GET /api/auth/audit/logs/my_activity/
```

Returns current user's recent 50 actions.

#### Statistics

```http
GET /api/auth/audit/logs/statistics/?days=30
```

**Response:**

```json
{
  "total_actions": 1523,
  "actions_by_type": {
    "CREATE": 450,
    "UPDATE": 320,
    "DELETE": 50,
    "READ": 600,
    "LOGIN": 103
  },
  "actions_by_user": {
    "admin": 800,
    "user1": 500,
    "user2": 223
  },
  "actions_by_module": {
    "transfers": 600,
    "transactions": 400,
    "budget": 300
  },
  "recent_errors": [...],
  "time_range": {
    "start": "2025-12-03T00:00:00Z",
    "end": "2026-01-02T00:00:00Z",
    "days": 30
  }
}
```

#### Recent Errors (Admin Only)

```http
GET /api/auth/audit/logs/recent_errors/
```

Returns last 100 errors/critical events.

#### Action Types

```http
GET /api/auth/audit/logs/action_types/
```

Returns list of all action types in the system.

#### Modules

```http
GET /api/auth/audit/logs/modules/
```

Returns list of all modules/apps.

### Login History

#### List Login History

```http
GET /api/auth/audit/login-history/
```

**Query Parameters:**

- `user_id` - Filter by user
- `username` - Filter by username
- `login_type` - Filter by type (LOGIN, LOGOUT, FAILED_LOGIN)
- `success` - Filter by success (true/false)
- `start_date` - Start date
- `end_date` - End date

**Response:**

```json
{
  "results": [
    {
      "login_id": 1,
      "user": 5,
      "username": "admin",
      "user_display": {
        "id": 5,
        "username": "admin"
      },
      "login_type": "LOGIN",
      "ip_address": "192.168.1.100",
      "timestamp": "2026-01-02T08:30:00Z",
      "success": true,
      "failure_reason": null,
      "country": "Jordan",
      "city": "Amman"
    }
  ]
}
```

#### My Login History

```http
GET /api/auth/audit/login-history/my_history/
```

Returns current user's login history.

#### Failed Login Attempts (Admin Only)

```http
GET /api/auth/audit/login-history/failed_attempts/?days=7
```

Returns recent failed login attempts.

---

## Programmatic Usage

### Using AuditLogger Utility

```python
from user_management.audit_utils import AuditLogger

# 1. Log a general action
AuditLogger.log_action(
    user=request.user,
    action_type='APPROVE',
    action_description=f'Approved transaction {transaction.code}',
    affected_object=transaction,
    metadata={'comments': 'Looks good'},
    request=request
)

# 2. Log model changes
# For CREATE
AuditLogger.log_model_change(
    user=request.user,
    instance=new_transfer,
    action_type='CREATE',
    request=request
)

# For UPDATE (with before/after comparison)
AuditLogger.log_model_change(
    user=request.user,
    instance=updated_transfer,
    action_type='UPDATE',
    old_instance=original_transfer,  # Pass the old state
    request=request
)

# For DELETE
AuditLogger.log_model_change(
    user=request.user,
    instance=transfer_to_delete,
    action_type='DELETE',
    request=request
)

# 3. Log approvals
AuditLogger.log_approval(
    user=request.user,
    transaction=transaction,
    action='approve',  # or 'reject'
    comments='Budget verified',
    request=request
)

# 4. Log exports
AuditLogger.log_export(
    user=request.user,
    export_type='transactions',
    record_count=150,
    request=request
)

# 5. Log imports
AuditLogger.log_import(
    user=request.user,
    import_type='budget_data',
    record_count=50,
    success=True,
    request=request
)

# 6. Log with custom old/new values
AuditLogger.log_action(
    user=request.user,
    action_type='UPDATE',
    action_description='Updated budget limits',
    affected_object=budget,
    old_values={'limit': '10000', 'status': 'active'},
    new_values={'limit': '15000', 'status': 'active'},
    severity='INFO',
    status='SUCCESS',
    request=request
)
```

---

## Middleware Configuration

The `AuditLoggingMiddleware` automatically logs requests. It's already configured in `settings.py`:

```python
MIDDLEWARE = [
    # ... other middleware
    "user_management.audit_middleware.AuditLoggingMiddleware",
]
```

### Customizing Middleware Behavior

Edit `user_management/audit_middleware.py`:

```python
# Paths to exclude from logging
EXCLUDED_PATHS = [
    '/admin/jsi18n/',
    '/static/',
    '/media/',
    '/favicon.ico',
]

# HTTP methods to always log
LOGGED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']

# Sensitive GET paths to log
SENSITIVE_GET_PATHS = [
    '/api/transfers/',
    '/api/transactions/',
    '/api/budget/',
]
```

---

## Django Admin Interface

Access audit logs in Django admin at:

- `/admin/user_management/xx_auditlog/`
- `/admin/user_management/xx_auditloginhistory/`

**Features:**

- Read-only (cannot manually create audit logs)
- Advanced filtering by action type, severity, status, module, date
- Search by username, description, endpoint, IP
- Date hierarchy navigation
- Detailed view with collapsible sections
- Only superadmins can delete audit logs

---

## Security & Permissions

### View Permissions

- **Regular users**: Can only see their own audit logs
- **Admin/SuperAdmin**: Can see all audit logs

### API Access

- All audit endpoints require authentication
- Statistics and error views require admin role
- Failed login attempts view requires admin role

### Data Retention

- Audit logs are never automatically deleted
- Only superadmins can manually delete via admin
- Consider implementing a data retention policy for compliance

---

## Examples

### 1. View My Recent Activity

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/auth/audit/logs/my_activity/
```

### 2. Find All Failed Actions

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/auth/audit/logs/?status=FAILED"
```

### 3. Get All CREATE Actions in Last Week

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/auth/audit/logs/?action_type=CREATE&start_date=2025-12-26"
```

### 4. View Login History

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/auth/audit/login-history/my_history/
```

### 5. Get Statistics for Last 7 Days (Admin)

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/auth/audit/logs/statistics/?days=7"
```

### 6. Search for Specific Actions

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/auth/audit/logs/?search=transfer%20123"
```

---

## Best Practices

### 1. When to Use Programmatic Logging

- Important business logic operations (approvals, rejections)
- Bulk operations (imports, exports)
- Permission changes
- Critical data modifications
- Operations outside normal request/response cycle (Celery tasks)

### 2. What Gets Logged Automatically

- All POST, PUT, PATCH, DELETE requests
- GET requests to sensitive endpoints
- Login/logout via middleware enhancement
- Exceptions and errors

### 3. Sensitive Data

- Avoid logging passwords or tokens in old_values/new_values
- Be cautious with PII (Personal Identifiable Information)
- Use metadata for additional context, not sensitive data

### 4. Performance Considerations

- Audit logging is async-safe (doesn't block requests)
- Failed audit logs don't break requests (fail silently)
- Consider archiving old logs periodically
- Index important fields for fast queries

---

## Troubleshooting

### Audit Logs Not Appearing

1. Check middleware is enabled in settings.py
2. Verify user is authenticated
3. Check if path is in EXCLUDED_PATHS
4. Check database for errors: `python manage.py migrate`

### Permission Denied Errors

- Regular users can only see their own logs
- Admin views require admin/superadmin role
- Check `request.user.role`

### Performance Issues

- Add database indexes (already configured)
- Archive old logs (implement retention policy)
- Limit date ranges in queries
- Use pagination

---

## Database Tables

### XX_AUDIT_LOG_XX

Main audit log table.

**Indexes:**

- `user_id, timestamp DESC`
- `action_type, timestamp DESC`
- `module, timestamp DESC`
- `content_type_id, object_id`
- `timestamp` (date hierarchy)

### XX_AUDIT_LOGIN_HISTORY_XX

Login history table.

**Indexes:**

- `user_id, timestamp DESC`
- `username, timestamp DESC`
- `timestamp` (date hierarchy)

---

## Future Enhancements

Potential additions:

1. Real-time audit log streaming via WebSockets
2. Advanced analytics dashboard
3. Automated anomaly detection
4. Audit log export to external systems (SIEM)
5. Geo-location tracking for logins
6. Compliance reporting (GDPR, SOX, etc.)
7. Data retention policies with auto-archiving
8. Audit log integrity verification (checksums)

---

## Compliance & Regulatory

This audit system helps with:

- **SOX Compliance**: Financial transaction tracking
- **GDPR**: Data access and modification logs
- **ISO 27001**: Security event logging
- **Internal Audits**: Complete activity trail
- **Forensics**: Investigation capabilities

---

## Contact & Support

For questions or issues with the audit logging system:

- Check Django logs for errors
- Review middleware configuration
- Verify database migrations applied
- Contact system administrator

**Last Updated**: January 2, 2026
**Version**: 1.0
