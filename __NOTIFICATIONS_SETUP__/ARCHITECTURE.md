# WebSocket Notification System - Centralized Architecture

## 📁 Project Structure

All notification-related code is now centralized in the `__NOTIFICATIONS_SETUP__/` folder:

```
__NOTIFICATIONS_SETUP__/
├── __init__.py                        # Package initialization
├── README.md                          # Main overview and quick start
├── INSTALLATION_CHECKLIST.md         # Step-by-step setup guide
├── SETUP_COMPLETE.md                 # Quick reference
├── WEBSOCKET_NOTIFICATIONS_GUIDE.md  # Complete API documentation
├── websocket_test.html               # Test page
├── code/                             # ⭐ Core implementation files
│   ├── __init__.py                   # Package exports
│   ├── consumers.py                  # WebSocket consumer
│   ├── routing.py                    # URL routing
│   └── task_notifications.py         # Helper functions
├── settings/                         # Configuration references
│   ├── channels_config.py           # Django settings
│   └── asgi_config.py               # ASGI configuration
└── examples/                         # Frontend integrations
    ├── javascript_integration.js    # Vanilla JS
    └── react_integration.jsx        # React hooks
```

---

## 🔄 Import Structure

### All project files now import from `__NOTIFICATIONS_SETUP__`:

#### 1. **ASGI Configuration** (`budget_transfer/asgi.py`)
```python
from __NOTIFICATIONS_SETUP__.code.routing import websocket_urlpatterns
```

#### 2. **Celery Tasks** (`budget_management/tasks.py`)
```python
from __NOTIFICATIONS_SETUP__.code.task_notifications import (
    send_notification,
    send_upload_started,
    send_progress_notification,
    send_upload_completed,
    send_upload_failed,
    set_notification_user
)
```

#### 3. **Oracle Workflow** (`oracle_fbdi_integration/utilities/Upload_essjob_api.py`)
```python
from __NOTIFICATIONS_SETUP__.code.task_notifications import (
    set_notification_user,
    send_workflow_notification
)
```

---

## ✨ Key Benefits

### 1. **Centralized Maintenance**
- All notification code in one location
- Easy to find and update
- No duplicate files

### 2. **Clear Separation**
- Notification logic separated from business logic
- Clean import statements
- Better code organization

### 3. **Easy Testing**
- All notification code in one place
- Simplified testing
- Clear dependencies

### 4. **Documentation**
- All docs and examples together
- Easy onboarding for new developers
- Complete reference material

---

## 🚀 Usage Examples

### Sending Notifications from Celery Tasks

```python
from celery import shared_task
from __NOTIFICATIONS_SETUP__.code.task_notifications import (
    send_upload_started,
    send_progress_notification,
    send_upload_completed,
    send_upload_failed
)

@shared_task
def my_background_task(user_id, transaction_id):
    try:
        # Notify start
        send_upload_started(user_id, transaction_id)
        
        # Send progress updates
        send_progress_notification(
            user_id=user_id,
            step_name='Processing Data',
            current_step=1,
            total_steps=3,
            transaction_id=transaction_id
        )
        
        # Do work...
        process_data()
        
        # Notify completion
        send_upload_completed(user_id, transaction_id)
        
    except Exception as e:
        # Notify failure
        send_upload_failed(user_id, transaction_id, str(e))
        raise
```

### Using Workflow Notifications

```python
from __NOTIFICATIONS_SETUP__.code.task_notifications import (
    set_notification_user,
    send_workflow_notification
)

def run_oracle_workflow(transaction_id, user_id):
    # Set the user to receive notifications
    set_notification_user(user_id)
    
    # Step 1
    send_workflow_notification(
        transaction_id=transaction_id,
        step='Upload to UCM',
        step_number=1,
        total_steps=5,
        message='Uploading file to Oracle UCM',
        status='processing'
    )
    upload_to_ucm()
    
    # Step 2
    send_workflow_notification(
        transaction_id=transaction_id,
        step='Interface Loader',
        step_number=2,
        total_steps=5,
        message='Running Interface Loader',
        status='processing'
    )
    run_interface_loader()
    
    # ... continue with remaining steps
```

---

## 📦 Available Functions

### From `task_notifications.py`:

| Function | Purpose | Parameters |
|----------|---------|------------|
| `send_notification()` | Generic notification | `user_id, event_type, data` |
| `send_progress_notification()` | Progress updates | `user_id, step_name, current_step, total_steps, ...` |
| `send_upload_started()` | Upload started | `user_id, transaction_id, message=None` |
| `send_upload_completed()` | Upload completed | `user_id, transaction_id, result_path=None, message=None` |
| `send_upload_failed()` | Upload failed | `user_id, transaction_id, error, message=None` |
| `send_generic_message()` | Generic message | `user_id, message, data=None` |
| `send_workflow_notification()` | Workflow progress | `transaction_id, step, step_number, total_steps, message, status` |
| `set_notification_user()` | Set notification user | `user_id` |
| `get_notification_user()` | Get current user | None |

---

## 🔧 Configuration

### Django Settings (`budget_transfer/settings.py`)

```python
# 1. Add to INSTALLED_APPS (Daphne must be FIRST!)
INSTALLED_APPS = [
    'daphne',  # Must be first!
    'channels',
    # ... other apps
]

# 2. Configure ASGI
ASGI_APPLICATION = 'budget_transfer.asgi.application'

# 3. Configure Channel Layers
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

### ASGI Application (`budget_transfer/asgi.py`)

```python
from __NOTIFICATIONS_SETUP__.code.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

---

## 🧪 Testing

### 1. **Start Services**
```powershell
# Redis (auto-starts as service)
Get-Service -Name "Memurai"

# Celery
celery -A config worker --loglevel=info --pool=solo

# Django
python manage.py runserver
```

### 2. **Test WebSocket**
Open `__NOTIFICATIONS_SETUP__/websocket_test.html` in browser

### 3. **Test Notifications**
Submit a budget transfer and watch real-time progress

---

## 📝 File Manifest

### Deleted (Duplicates Removed):
- ❌ `budget_management/consumers.py`
- ❌ `budget_management/routing.py`
- ❌ `budget_transfer/consumers.py`
- ❌ `budget_transfer/routing.py`

### Active (Centralized in `__NOTIFICATIONS_SETUP__/`):
- ✅ `__NOTIFICATIONS_SETUP__/code/consumers.py` - WebSocket consumer
- ✅ `__NOTIFICATIONS_SETUP__/code/routing.py` - URL routing
- ✅ `__NOTIFICATIONS_SETUP__/code/task_notifications.py` - Helper functions

### Updated (Import from `__NOTIFICATIONS_SETUP__`):
- ✅ `budget_transfer/asgi.py`
- ✅ `budget_management/tasks.py`
- ✅ `oracle_fbdi_integration/utilities/Upload_essjob_api.py`

---

## 🔍 Troubleshooting

### Import Error: `ModuleNotFoundError: No module named '__NOTIFICATIONS_SETUP__'`

**Solution:** The `__NOTIFICATIONS_SETUP__` folder is at the project root and should be accessible. If you get this error, ensure:
1. The folder exists at project root: `c:\Users\m7mad\Documents\GitHub\Tnfeez_MOFA\__NOTIFICATIONS_SETUP__\`
2. It has an `__init__.py` file
3. Your Python path includes the project root

### WebSocket Connection Failed

**Check:**
1. Redis is running: `Get-Service -Name "Memurai"`
2. Django is running on correct port
3. ASGI application configured correctly
4. User is authenticated

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | This file - Architecture overview |
| `INSTALLATION_CHECKLIST.md` | Complete setup checklist |
| `SETUP_COMPLETE.md` | Quick reference guide |
| `WEBSOCKET_NOTIFICATIONS_GUIDE.md` | Complete API documentation |
| `settings/channels_config.py` | Django settings reference |
| `settings/asgi_config.py` | ASGI config reference |

---

## 🎯 Next Steps

1. ✅ All notification code centralized
2. ✅ Imports updated across project
3. ✅ Duplicate files removed
4. 🔄 Test the complete workflow
5. 📝 Add Vue.js integration example (optional)
6. 🚀 Deploy to production

---

**Last Updated:** November 18, 2025  
**Version:** 2.0 (Centralized Architecture)  
**Project:** Tnfeez_MOFA
