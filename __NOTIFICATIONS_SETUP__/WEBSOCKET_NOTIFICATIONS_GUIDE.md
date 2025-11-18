# WebSocket Real-time Notifications Guide

Complete guide for implementing and using real-time WebSocket notifications for Oracle FBDI workflow updates.

---

## 📋 Overview

The system now supports **real-time push notifications** to users while Oracle workflows run in the background. Users receive instant updates about:

- Upload started
- Each workflow step progress (UCM → Interface Loader → Journal Import → AutoPost)
- Upload completion
- Any errors or failures

---

## 🎯 Architecture

```
User Browser ←→ WebSocket ←→ Django Channels ←→ Redis ←→ Celery Worker
                                    ↑
                                    |
                         Channel Layer (Pub/Sub)
```

### Components:
1. **Django Channels** - Handles WebSocket connections
2. **Redis** - Message broker + Channel layer for real-time messaging
3. **Celery** - Background task processing
4. **WebSocket Consumer** - Manages user connections and notifications
5. **ASGI** - Async server interface (replaces WSGI for WebSockets)

---

## ✅ What Was Installed

### Python Packages:
```
channels==4.0.0          # Django Channels for WebSocket support
channels-redis==4.1.0     # Redis channel layer
daphne==4.0.0            # ASGI server
```

### Files Created:
- ✅ `budget_management/consumers.py` - WebSocket consumer
- ✅ `budget_management/routing.py` - WebSocket URL routing
- ✅ `websocket_test.html` - Test page for WebSocket connection

### Files Modified:
- ✅ `budget_transfer/settings.py` - Added ASGI_APPLICATION, daphne to INSTALLED_APPS
- ✅ `budget_transfer/asgi.py` - Updated with WebSocket routing
- ✅ `budget_management/tasks.py` - Added WebSocket notifications
- ✅ `oracle_fbdi_integration/utilities/Upload_essjob_api.py` - Added progress notifications
- ✅ `requirements.txt` - Added new packages

---

## 🚀 How to Start Services

### **Order Matters! Always start in this sequence:**

### 1. Start Redis (Memurai)
```powershell
# Check if running
Get-Service -Name "Memurai"

# If stopped, start it
Start-Service -Name "Memurai"
```

### 2. Start Celery Worker
```powershell
cd C:\Users\m7mad\Documents\GitHub\Tnfeez_MOFA
celery -A config worker --loglevel=info --pool=solo
```

Wait for: `celery@Mohamed ready.`

### 3. Start Django with ASGI (Daphne)
```powershell
cd C:\Users\m7mad\Documents\GitHub\Tnfeez_MOFA
daphne -b 0.0.0.0 -p 8000 budget_transfer.asgi:application
```

**OR use Django's runserver (also supports WebSockets with Channels):**
```powershell
python manage.py runserver
```

---

## 🧪 Testing WebSocket Connection

### Option 1: Use Test HTML Page

1. **Open** `websocket_test.html` in your browser
2. **Click** "Connect WebSocket" button
3. **Submit** a budget transfer in your application
4. **Watch** real-time notifications appear!

### Option 2: Browser Console Test

Open browser console (F12) and run:

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://127.0.0.1:8000/ws/notifications/');

ws.onopen = () => {
    console.log('✅ Connected!');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('📩 Notification:', data);
};

ws.onerror = (error) => {
    console.error('❌ Error:', error);
};
```

### Option 3: Python Test

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://127.0.0.1:8000/ws/notifications/"
    async with websockets.connect(uri) as websocket:
        print("Connected!")
        
        # Listen for messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(test_websocket())
```

---

## 📡 WebSocket API Reference

### Connection URL:
```
ws://127.0.0.1:8000/ws/notifications/
```

### Authentication:
- Requires authenticated user (Django session or JWT)
- Anonymous users are rejected

---

### Message Types Sent by Server:

#### 1. Connection Established
```json
{
    "type": "connection_established",
    "message": "WebSocket connected successfully",
    "user_id": 123
}
```

#### 2. Upload Started
```json
{
    "type": "oracle_upload_started",
    "transaction_id": 602,
    "message": "Oracle upload started for transaction 602",
    "timestamp": "2025-11-18T12:30:45.123456"
}
```

#### 3. Progress Update
```json
{
    "type": "oracle_upload_progress",
    "transaction_id": 602,
    "step": "Interface Loader",
    "step_number": 3,
    "total_steps": 5,
    "message": "Running Interface Loader to process data",
    "status": "processing",
    "timestamp": "2025-11-18T12:31:15.123456"
}
```

#### 4. Upload Completed
```json
{
    "type": "oracle_upload_completed",
    "transaction_id": 602,
    "message": "Oracle upload completed successfully",
    "success": true,
    "result_path": "/path/to/result",
    "timestamp": "2025-11-18T12:35:20.123456"
}
```

#### 5. Upload Failed
```json
{
    "type": "oracle_upload_failed",
    "transaction_id": 602,
    "message": "Oracle upload failed",
    "error": "Interface loader timeout",
    "timestamp": "2025-11-18T12:33:45.123456"
}
```

---

### Messages Sent by Client (Optional):

#### Ping (Keep-alive)
```json
{
    "type": "ping",
    "timestamp": "2025-11-18T12:30:00.000000"
}
```

**Server Response:**
```json
{
    "type": "pong",
    "timestamp": "2025-11-18T12:30:00.000000"
}
```

---

## 🔗 Frontend Integration

### JavaScript Example (React/Vue/Angular):

```javascript
class NotificationService {
    constructor() {
        this.socket = null;
        this.callbacks = {};
    }

    connect() {
        this.socket = new WebSocket('ws://127.0.0.1:8000/ws/notifications/');

        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.trigger('connected');
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.socket.onclose = () => {
            console.log('WebSocket closed');
            this.trigger('disconnected');
            // Auto-reconnect after 5 seconds
            setTimeout(() => this.connect(), 5000);
        };
    }

    handleMessage(data) {
        switch(data.type) {
            case 'oracle_upload_started':
                this.trigger('uploadStarted', data);
                break;
            case 'oracle_upload_progress':
                this.trigger('uploadProgress', data);
                break;
            case 'oracle_upload_completed':
                this.trigger('uploadCompleted', data);
                break;
            case 'oracle_upload_failed':
                this.trigger('uploadFailed', data);
                break;
        }
    }

    on(event, callback) {
        if (!this.callbacks[event]) {
            this.callbacks[event] = [];
        }
        this.callbacks[event].push(callback);
    }

    trigger(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(callback => callback(data));
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Usage:
const notifications = new NotificationService();

notifications.on('uploadStarted', (data) => {
    showToast('Upload started', 'info');
});

notifications.on('uploadProgress', (data) => {
    updateProgressBar(data.step_number, data.total_steps);
    showToast(`${data.step}: ${data.message}`, 'info');
});

notifications.on('uploadCompleted', (data) => {
    showToast('Upload completed successfully!', 'success');
    refreshTransactionList();
});

notifications.on('uploadFailed', (data) => {
    showToast(`Upload failed: ${data.error}`, 'error');
});

notifications.connect();
```

---

## 📊 Workflow Steps with Notifications

| Step | Step Number | Notification Event |
|------|-------------|-------------------|
| Preparing Data | 1 | `oracle_upload_progress` |
| Upload to UCM | 2 | `oracle_upload_progress` |
| Interface Loader | 3 | `oracle_upload_progress` |
| Journal Import | 4 | `oracle_upload_progress` |
| AutoPost | 5 | `oracle_upload_progress` |
| Completion | - | `oracle_upload_completed` |

---

## 🛠️ Troubleshooting

### WebSocket Connection Refused

**Problem:** `WebSocket connection to 'ws://...' failed`

**Solutions:**
1. Make sure Django is running with ASGI support:
   ```powershell
   daphne -b 0.0.0.0 -p 8000 budget_transfer.asgi:application
   ```
   OR
   ```powershell
   python manage.py runserver  # Django 3.0+ supports WebSockets
   ```

2. Check if Channels is installed:
   ```powershell
   pip show channels
   ```

3. Verify Redis is running:
   ```powershell
   Get-Service -Name "Memurai"
   ```

---

### No Notifications Received

**Problem:** WebSocket connects but no messages arrive

**Check:**
1. Is Celery worker running?
   ```powershell
   celery -A config worker --loglevel=info --pool=solo
   ```

2. Check Celery logs for errors

3. Verify user is authenticated (WebSocket rejects anonymous users)

4. Check Django logs for WebSocket errors

---

### "User has no attribute 'id'"

**Problem:** `budget_transfer.created_by.id` fails

**Solution:** Make sure `xx_BudgetTransfer` model has a `created_by` field:
```python
class xx_BudgetTransfer(models.Model):
    created_by = models.ForeignKey(xx_User, on_delete=models.CASCADE)
    # ... other fields
```

---

### CORS Issues

**Problem:** WebSocket blocked by CORS

**Solution:** Update `settings.py`:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Your frontend URL
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True
```

---

## 🔐 Security Considerations

### Production Checklist:

1. **Use WSS (Secure WebSocket):**
   ```javascript
   const ws = new WebSocket('wss://yourdomain.com/ws/notifications/');
   ```

2. **Configure ALLOWED_HOSTS:**
   ```python
   ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
   ```

3. **Use proper authentication:**
   - JWT tokens in WebSocket headers
   - Session-based auth with secure cookies

4. **Rate limiting:**
   - Limit WebSocket connections per user
   - Implement reconnection backoff

5. **Monitor connections:**
   - Track active WebSocket connections
   - Auto-disconnect idle connections

---

## 📈 Performance Tips

### For Production:

1. **Use multiple Celery workers:**
   ```bash
   celery -A config worker --concurrency=4
   ```

2. **Scale WebSocket connections:**
   - Use multiple Daphne instances behind load balancer
   - Configure Redis for high availability

3. **Optimize Redis:**
   ```python
   CHANNEL_LAYERS = {
       'default': {
           'BACKEND': 'channels_redis.core.RedisChannelLayer',
           'CONFIG': {
               "hosts": [('127.0.0.1', 6379)],
               "capacity": 1500,  # Default message buffer
               "expiry": 10,      # Message expiry in seconds
           },
       },
   }
   ```

4. **Monitor memory usage:**
   - WebSocket connections consume memory
   - Set max connections per server

---

## 📱 Mobile App Integration

For mobile apps (React Native, Flutter):

```javascript
// React Native
import { w3cwebsocket as W3CWebSocket } from "websocket";

const client = new W3CWebSocket('ws://yourserver.com/ws/notifications/');

client.onopen = () => {
    console.log('WebSocket Client Connected');
};

client.onmessage = (message) => {
    const data = JSON.parse(message.data);
    // Handle notification
};
```

---

## 🎓 Next Steps

1. **Customize Notifications:**
   - Add more event types in `consumers.py`
   - Create custom notification handlers

2. **Add User Preferences:**
   - Let users enable/disable notification types
   - Store preferences in database

3. **Implement Notification History:**
   - Save notifications to database
   - Create API to fetch past notifications

4. **Add Sound/Vibration:**
   - Play sounds for important events
   - Vibrate on mobile devices

5. **Browser Notifications:**
   - Request notification permission
   - Show OS-level notifications

---

## 📚 Resources

- **Django Channels Docs:** https://channels.readthedocs.io/
- **WebSocket API:** https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- **Redis Pub/Sub:** https://redis.io/docs/interact/pubsub/
- **Daphne Server:** https://github.com/django/daphne

---

**Last Updated:** November 18, 2025  
**Project:** Tnfeez_MOFA - Oracle FBDI Integration  
**Feature:** Real-time WebSocket Notifications
