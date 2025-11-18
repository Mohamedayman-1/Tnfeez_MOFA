# 🔔 Real-time WebSocket Notifications - Centralized Setup

**⭐ All notification code is centralized in this folder. All project files import from here.**

This folder contains all configuration, code, and documentation for the real-time notification system.

---

## 📁 Folder Structure

```
__NOTIFICATIONS_SETUP__/
├── __init__.py                         # Package initialization
├── README.md                           # This file - Overview
├── ARCHITECTURE.md                     # ⭐ Centralized architecture guide
├── INSTALLATION_CHECKLIST.md          # Complete setup checklist
├── SETUP_COMPLETE.md                  # Quick reference guide
├── WEBSOCKET_NOTIFICATIONS_GUIDE.md   # Complete API documentation
├── websocket_test.html                # Test page
├── code/                              # ⭐ Core implementation (DO NOT COPY - IMPORT DIRECTLY)
│   ├── __init__.py                    # Package exports
│   ├── consumers.py                   # WebSocket consumer
│   ├── routing.py                     # URL routing
│   └── task_notifications.py         # Helper functions for notifications
├── settings/                          # Configuration references
│   ├── channels_config.py            # Django settings reference
│   └── asgi_config.py                # ASGI configuration reference
└── examples/                          # Frontend integration examples
    ├── javascript_integration.js     # Vanilla JavaScript
    └── react_integration.jsx         # React hooks and components
```

---

## 🎯 Key Concept: Centralized Imports

**All project files import notification code from `__NOTIFICATIONS_SETUP__/code/`**

### Examples:

**ASGI Configuration:**
```python
# budget_transfer/asgi.py
from __NOTIFICATIONS_SETUP__.code.routing import websocket_urlpatterns
```

**Celery Tasks:**
```python
# budget_management/tasks.py
from __NOTIFICATIONS_SETUP__.code.task_notifications import (
    send_upload_started,
    send_progress_notification,
    send_upload_completed
)
```

**Oracle Workflow:**
```python
# oracle_fbdi_integration/utilities/Upload_essjob_api.py
from __NOTIFICATIONS_SETUP__.code.task_notifications import (
    set_notification_user,
    send_workflow_notification
)
```

---

## 🚀 Quick Start

1. **Read:** `ARCHITECTURE.md` for centralized architecture overview
2. **Read:** `SETUP_COMPLETE.md` for quick reference
3. **Install:** Required packages (see below)
4. **Configure:** Django settings (see `settings/channels_config.py`)
5. **Update:** ASGI application (see `settings/asgi_config.py`)
6. **Test:** Open `websocket_test.html` in browser

---

## 📦 Required Packages

```bash
pip install channels==4.0.0
pip install channels-redis==4.1.0
pip install daphne==4.0.0
pip install celery==5.5.3
pip install redis==7.0.1
```

---

## 🎯 What This System Does

- ✅ Real-time WebSocket notifications to users
- ✅ Progress updates during Oracle FBDI workflows
- ✅ Non-blocking async task processing
- ✅ Step-by-step workflow tracking
- ✅ Error notifications and retry logic

---

## 📄 Documentation Files

| File | Description |
|------|-------------|
| `ARCHITECTURE.md` | ⭐ Centralized architecture and import guide |
| `INSTALLATION_CHECKLIST.md` | Complete step-by-step setup checklist |
| `SETUP_COMPLETE.md` | Quick reference and getting started |
| `WEBSOCKET_NOTIFICATIONS_GUIDE.md` | Complete API reference and troubleshooting |
| `websocket_test.html` | Test page to verify WebSocket connection |

---

## 💻 Project Integration

### ✅ Updated Files (Import from `__NOTIFICATIONS_SETUP__`):

1. **`budget_transfer/asgi.py`**
   ```python
   from __NOTIFICATIONS_SETUP__.code.routing import websocket_urlpatterns
   ```

2. **`budget_management/tasks.py`**
   ```python
   from __NOTIFICATIONS_SETUP__.code.task_notifications import (
       send_upload_started, send_upload_completed, ...
   )
   ```

3. **`oracle_fbdi_integration/utilities/Upload_essjob_api.py`**
   ```python
   from __NOTIFICATIONS_SETUP__.code.task_notifications import (
       set_notification_user, send_workflow_notification
   )
   ```

### ❌ Deleted Files (Duplicates Removed):

- `budget_management/consumers.py` → Now in `__NOTIFICATIONS_SETUP__/code/consumers.py`
- `budget_management/routing.py` → Now in `__NOTIFICATIONS_SETUP__/code/routing.py`
- `budget_transfer/consumers.py` → Removed (duplicate)
- `budget_transfer/routing.py` → Removed (duplicate)

### 📦 Core Notification Files:

All notification code now lives in `__NOTIFICATIONS_SETUP__/code/`:
- `consumers.py` - WebSocket consumer
- `routing.py` - URL routing
- `task_notifications.py` - Helper functions

---

## 🔧 Setup Steps

### 1. Install Packages
```powershell
pip install channels==4.0.0 channels-redis==4.1.0 daphne==4.0.0
```

### 2. Verify Django Settings

Check `budget_transfer/settings.py` has:

```python
INSTALLED_APPS = [
    'daphne',  # Must be first
    # ... other apps
    'channels',
]

ASGI_APPLICATION = 'budget_transfer.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

### 3. Start Services (In Order)

```powershell
# 1. Redis (Memurai) - should already be running
Get-Service -Name "Memurai"

# 2. Celery Worker
celery -A config worker --loglevel=info --pool=solo

# 3. Django Server
python manage.py runserver
```

### 4. Test WebSocket

Open `websocket_test.html` in browser and click "Connect"

---

## 🧪 Testing

### Quick Test:

1. Open `websocket_test.html`
2. Click "Connect WebSocket"
3. Submit a budget transfer
4. Watch real-time notifications!

### Expected Notifications:

- 🚀 Upload Started
- 📊 Progress (5 steps)
- ✅ Upload Completed
- ❌ Upload Failed (if error)

---

## 🎨 Frontend Integration

See `examples/` folder for:

- **JavaScript** - Vanilla JS integration
- **React** - React component with hooks
- **Vue** - Vue component with composition API

---

## 🐛 Troubleshooting

### Common Issues:

1. **WebSocket won't connect**
   - Check Django is running
   - Verify Redis is running
   - Check user is authenticated

2. **No notifications received**
   - Check Celery worker is running
   - Verify Redis connection
   - Check Django logs

3. **Import errors**
   - Reinstall packages
   - Check Python environment

See `WEBSOCKET_NOTIFICATIONS_GUIDE.md` for detailed troubleshooting.

---

## 📊 Notification Flow

```
User Action (Submit Transfer)
    ↓
Django Signal
    ↓
Celery Task Queued (Redis)
    ↓
Immediate HTTP Response ✅
    ↓
Celery Worker Picks Task
    ↓
Send WebSocket: "Upload Started" 🚀
    ↓
Oracle Workflow (5 steps)
    ↓
Send Progress Notifications 📊
    ↓
Send Completion/Failure ✅/❌
```

---

## 🔐 Security Notes

### For Production:

1. Use WSS (secure WebSocket) with SSL
2. Implement proper authentication (JWT)
3. Rate limit connections
4. Monitor active connections
5. Set connection timeouts

---

## 📈 Performance Tips

1. Use multiple Celery workers
2. Scale WebSocket servers
3. Configure Redis persistence
4. Monitor memory usage
5. Implement reconnection logic

---

## 🆘 Support

For help:

1. Check `WEBSOCKET_NOTIFICATIONS_GUIDE.md`
2. Review code examples in `examples/`
3. Test with `websocket_test.html`
4. Check Django/Celery logs

---

## 📝 File Manifest

### Documentation:
- ✅ README.md (this file)
- ✅ SETUP_COMPLETE.md
- ✅ WEBSOCKET_NOTIFICATIONS_GUIDE.md

### Test Files:
- ✅ websocket_test.html

### Settings (Reference):
- ✅ Channels config in main settings.py
- ✅ ASGI config in budget_transfer/asgi.py

### Code (Already in Project):
- ✅ budget_management/consumers.py
- ✅ budget_management/routing.py
- ✅ budget_management/tasks.py
- ✅ oracle_fbdi_integration/utilities/Upload_essjob_api.py

---

## 🎯 Future Enhancements

Potential improvements:

- [ ] Notification history/logging
- [ ] User notification preferences
- [ ] Email/SMS fallback notifications
- [ ] Mobile app push notifications
- [ ] Notification filtering/categories
- [ ] Read/unread status tracking
- [ ] Notification center UI component

---

## 📞 Maintenance

### Regular Tasks:

1. **Monitor Redis memory usage**
2. **Check WebSocket connection counts**
3. **Review notification logs**
4. **Update packages regularly**
5. **Test after Django/Celery updates**

### When to Update:

- Django Channels releases new version
- Redis client updates
- Security patches available
- New notification features needed

---

**Last Updated:** November 18, 2025  
**Project:** Tnfeez_MOFA  
**Module:** Real-time WebSocket Notifications  
**Version:** 1.0.0
