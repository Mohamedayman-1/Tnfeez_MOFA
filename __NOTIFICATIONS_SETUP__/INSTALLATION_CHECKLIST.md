# Installation & Setup Checklist

Complete checklist for implementing WebSocket notifications in your project.

---

## ✅ Phase 1: Prerequisites

- [ ] Python 3.8+ installed
- [ ] Django project running
- [ ] Redis installed and running (Memurai on Windows)
- [ ] Celery installed and configured
- [ ] Budget transfer workflow working

---

## ✅ Phase 2: Package Installation

### Install Required Packages:

```powershell
pip install channels==4.0.0
pip install channels-redis==4.1.0
pip install daphne==4.0.0
```

### Verify Installation:

```powershell
pip show channels
pip show channels-redis
pip show daphne
```

### Update requirements.txt:

```
channels==4.0.0
channels-redis==4.1.0
daphne==4.0.0
celery==5.5.3
redis==7.0.1
```

---

## ✅ Phase 3: Django Configuration

### 1. Update `settings.py`:

- [ ] Add `'daphne'` as **FIRST** item in `INSTALLED_APPS`
- [ ] Add `'channels'` to `INSTALLED_APPS`
- [ ] Add `ASGI_APPLICATION = 'budget_transfer.asgi.application'`
- [ ] Add `CHANNEL_LAYERS` configuration (see `settings/channels_config.py`)

### 2. Update `asgi.py`:

- [ ] Copy content from `settings/asgi_config.py`
- [ ] Verify imports are correct
- [ ] Check routing configuration

### 3. Update `__init__.py` (budget_transfer):

- [ ] Import Celery app: `from config.celery import app as celery_app`
- [ ] Add `__all__ = ('celery_app',)`

---

## ✅ Phase 4: Code Implementation

### 1. Create WebSocket Consumer:

File: `budget_management/consumers.py`

- [ ] Copy from `code/consumers.py`
- [ ] Verify all imports work
- [ ] Check logger configuration

### 2. Create WebSocket Routing:

File: `budget_management/routing.py`

- [ ] Copy from `code/routing.py`
- [ ] Verify consumer import path

### 3. Update Celery Task:

File: `budget_management/tasks.py`

- [ ] Add WebSocket notification imports
- [ ] Add `send_notification` helper function
- [ ] Update `upload_journal_to_oracle` task
- [ ] Add progress notifications

### 4. Update Oracle Workflow:

File: `oracle_fbdi_integration/utilities/Upload_essjob_api.py`

- [ ] Add notification imports
- [ ] Add `set_notification_user` function
- [ ] Add `send_workflow_notification` function
- [ ] Add notifications to each workflow step

---

## ✅ Phase 5: Testing

### 1. Start Services (in order):

```powershell
# 1. Check Redis
Get-Service -Name "Memurai"

# 2. Start Celery
celery -A config worker --loglevel=info --pool=solo

# 3. Start Django
python manage.py runserver
```

### 2. Test WebSocket Connection:

- [ ] Open `websocket_test.html`
- [ ] Click "Connect WebSocket"
- [ ] Verify connection success message

### 3. Test Notifications:

- [ ] Submit a budget transfer
- [ ] Verify "Upload Started" notification
- [ ] Verify progress notifications (5 steps)
- [ ] Verify "Upload Completed" notification
- [ ] Check for any errors in terminals

### 4. Verify in Browser Console:

```javascript
// Should see WebSocket messages
const ws = new WebSocket('ws://127.0.0.1:8000/ws/notifications/');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

---

## ✅ Phase 6: Integration

### Frontend Integration:

- [ ] Choose integration approach (Vanilla JS / React / Vue)
- [ ] Copy example from `examples/` folder
- [ ] Implement notification UI components
- [ ] Test with real workflow

### UI Components to Implement:

- [ ] Connection status indicator
- [ ] Progress bar
- [ ] Notification list/feed
- [ ] Toast/popup notifications
- [ ] Sound/vibration (optional)

---

## ✅ Phase 7: Production Preparation

### Security:

- [ ] Use WSS (secure WebSocket) with SSL
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up proper authentication
- [ ] Implement rate limiting
- [ ] Add CORS configuration

### Performance:

- [ ] Configure Redis persistence
- [ ] Set up multiple Celery workers
- [ ] Monitor WebSocket connections
- [ ] Implement connection pooling

### Monitoring:

- [ ] Install Flower for Celery monitoring
- [ ] Set up logging for WebSocket connections
- [ ] Monitor Redis memory usage
- [ ] Track notification delivery rates

---

## ✅ Troubleshooting Checklist

### WebSocket Won't Connect:

- [ ] Check Django is running
- [ ] Verify Redis is running
- [ ] Check user is authenticated
- [ ] Review browser console for errors
- [ ] Check Django logs

### No Notifications Received:

- [ ] Verify Celery worker is running
- [ ] Check Celery logs for task execution
- [ ] Verify user_id is set correctly
- [ ] Check budget_transfer has created_by field
- [ ] Review channel layer configuration

### Import Errors:

- [ ] Reinstall packages
- [ ] Check Python environment
- [ ] Verify file paths are correct
- [ ] Review import statements

### Performance Issues:

- [ ] Check Redis memory usage
- [ ] Monitor active WebSocket connections
- [ ] Review Celery worker concurrency
- [ ] Check for memory leaks

---

## 📋 Final Verification

### All Systems Running:

```powershell
# Redis
Get-Service -Name "Memurai"  # Should show "Running"

# Test Redis
python -c "import redis; print(redis.Redis().ping())"  # Should print "True"

# Celery
# Check celery terminal - should show "celery@YourPC ready"

# Django
# Check django terminal - should show "Starting development server"
```

### WebSocket Test:

```javascript
// Browser console
const ws = new WebSocket('ws://127.0.0.1:8000/ws/notifications/');
ws.onopen = () => console.log('✅ Connected');
ws.onmessage = (e) => console.log('📩', JSON.parse(e.data));
// Should see connection_established message
```

### End-to-End Test:

1. [ ] Submit budget transfer
2. [ ] Receive immediate HTTP response
3. [ ] See "Upload Started" notification
4. [ ] See progress notifications (1/5, 2/5, 3/5, 4/5, 5/5)
5. [ ] See "Upload Completed" notification
6. [ ] Verify audit records in database

---

## 🎉 Success Criteria

Your setup is complete when:

✅ Redis service is running  
✅ Celery worker is ready  
✅ Django starts without errors  
✅ WebSocket connects successfully  
✅ Submit returns in < 1 second  
✅ Real-time notifications appear  
✅ Progress bar updates during upload  
✅ No connection errors in logs  
✅ Audit records created correctly  

---

## 📚 Reference Files

| File | Purpose |
|------|---------|
| `README.md` | Overview and navigation |
| `SETUP_COMPLETE.md` | Quick start guide |
| `WEBSOCKET_NOTIFICATIONS_GUIDE.md` | Complete documentation |
| `websocket_test.html` | WebSocket test page |
| `settings/channels_config.py` | Django settings reference |
| `settings/asgi_config.py` | ASGI configuration reference |
| `code/consumers.py` | WebSocket consumer code |
| `code/routing.py` | URL routing code |
| `code/task_notifications.py` | Helper functions |
| `examples/javascript_integration.js` | Vanilla JS example |
| `examples/react_integration.jsx` | React example |

---

## 🆘 Need Help?

1. **Review Documentation:**
   - Start with `SETUP_COMPLETE.md`
   - Check `WEBSOCKET_NOTIFICATIONS_GUIDE.md` for details

2. **Test Components:**
   - Use `websocket_test.html`
   - Check browser console
   - Review Django/Celery logs

3. **Common Solutions:**
   - Restart all services in order
   - Clear browser cache
   - Check firewall settings
   - Verify Python packages installed

---

**Last Updated:** November 18, 2025  
**Project:** Tnfeez_MOFA  
**Module:** WebSocket Notifications
