# Redis & Celery Setup Guide for Windows

Complete guide to set up Redis and Celery for asynchronous Oracle FBDI workflow processing.

---

## 📋 Prerequisites

- Windows 10/11
- Python 3.8+
- PowerShell (Administrator access required for installation)
- Django project already set up

---

## 🔧 Step 1: Install Chocolatey (Package Manager)

### 1.1 Open PowerShell as Administrator
Right-click on PowerShell → **Run as administrator**

### 1.2 Install Chocolatey
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

### 1.3 Verify Installation
```powershell
choco --version
# Should show version like: 2.5.1
```

### 1.4 Close and Reopen PowerShell
Close the Administrator PowerShell and open a new one to refresh environment variables.

---

## 🗄️ Step 2: Install Redis (Memurai)

### 2.1 Install Redis/Memurai
```powershell
choco install redis-64 -y
```

This installs **Memurai**, a Redis-compatible server for Windows.

### 2.2 Refresh Environment Variables
```powershell
refreshenv
```

Or close and reopen PowerShell.

### 2.3 Verify Redis Service
```powershell
Get-Service -Name "Memurai"
```

Expected output:
```
Status   Name     DisplayName
------   ----     -----------
Running  Memurai  Memurai
```

### 2.4 Test Redis Connection
```powershell
Test-NetConnection -ComputerName localhost -Port 6379 -InformationLevel Quiet
```

Should return: `True`

### 2.5 Verify Port is Listening
```powershell
netstat -an | Select-String "6379"
```

Should show:
```
TCP    127.0.0.1:6379         0.0.0.0:0              LISTENING
```

---

## 🐍 Step 3: Install Python Packages

### 3.1 Navigate to Project Directory
```powershell
cd C:\Users\m7mad\Documents\GitHub\Tnfeez_MOFA
```

### 3.2 Install Celery and Redis Python Client
```powershell
pip install celery redis
```

### 3.3 Verify Installation
```powershell
pip show celery
pip show redis
```

### 3.4 Test Redis from Python
```powershell
python -c "import redis; r = redis.Redis(host='127.0.0.1', port=6379, db=0); print('Redis Connection OK:', r.ping())"
```

Expected output: `Redis Connection OK: True`

---

## 📁 Step 4: Verify Project Files

Make sure these files exist with correct content:

### 4.1 Check `budget_transfer/__init__.py`
```python
# This will make sure the Celery app is always imported when Django starts
from config.celery import app as celery_app

__all__ = ('celery_app',)
```

### 4.2 Check `config/celery.py`
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')

app = Celery('tnfeez_mofa')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

### 4.3 Check `config/__init__.py`
```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### 4.4 Check `budget_transfer/settings.py` has Celery settings:
```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
CELERY_BROKER_POOL_LIMIT = 10
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 3600,
    'max_connections': 50,
}
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
```

---

## 🚀 Step 5: Start Services (CORRECT ORDER)

### **CRITICAL:** Always start in this order!

### 5.1 ✅ Verify Redis is Running
```powershell
Get-Service -Name "Memurai" | Select-Object Status, Name
```

If stopped, start it:
```powershell
Start-Service -Name "Memurai"
```

---

### 5.2 🔥 Start Celery Worker FIRST

**Open Terminal 1** (labeled "celery"):
```powershell
cd C:\Users\m7mad\Documents\GitHub\Tnfeez_MOFA
celery -A config worker --loglevel=info --pool=solo
```

**Wait for this output:**
```
[INFO/MainProcess] Connected to redis://127.0.0.1:6379/0
[INFO/MainProcess] celery@Mohamed ready.
```

**Important:** Keep this terminal running!

---

### 5.3 🌐 Start Django Server SECOND

**Open Terminal 2** (labeled "Django" or "Python Debug Console"):
```powershell
cd C:\Users\m7mad\Documents\GitHub\Tnfeez_MOFA
python manage.py runserver
```

**Wait for:**
```
Starting development server at http://127.0.0.1:8000/
```

**Important:** Keep this terminal running!

---

## ✅ Step 6: Verify Everything Works

### 6.1 Check All Services
In a new PowerShell terminal:

```powershell
# 1. Check Redis
Get-Service -Name "Memurai"

# 2. Test Redis connection
python -c "import redis; r = redis.Redis(host='127.0.0.1', port=6379, db=0); print('Redis:', r.ping())"

# 3. Check if Celery worker is running (look at celery terminal)
# Should show: "celery@Mohamed ready."

# 4. Check Django server (look at Django terminal)
# Should show: "Starting development server at http://127.0.0.1:8000/"
```

### 6.2 Test Workflow
1. Go to your application UI
2. Submit a budget transfer
3. **Watch the celery terminal** - you should see:
   ```
   [INFO/MainProcess] Task budget_management.tasks.upload_journal_to_oracle[...] received
   [INFO/MainProcess] Starting Oracle upload for transaction XXX
   ```
4. **Django terminal** should show task queued immediately (no 5-minute wait)

---

## 🐛 Troubleshooting

### Problem: "No connection could be made" error

**Solution:**
```powershell
# 1. Check if Redis is running
Get-Service -Name "Memurai"

# 2. If stopped, start it
Start-Service -Name "Memurai"

# 3. Restart Django and Celery in correct order (Celery first, then Django)
```

---

### Problem: Tasks not executing

**Check:**
1. Is Celery worker running? (Check celery terminal)
2. Is Redis running? `Get-Service -Name "Memurai"`
3. Did you start Celery **before** Django?
4. Check `budget_transfer/__init__.py` imports celery_app

**Restart in correct order:**
```powershell
# Terminal 1: Start Celery
celery -A config worker --loglevel=info --pool=solo

# Terminal 2: Start Django (after Celery is ready)
python manage.py runserver
```

---

### Problem: "redis-server not found"

**Don't use `redis-server`!** Memurai runs as a Windows service automatically.

Just check if it's running:
```powershell
Get-Service -Name "Memurai"
```

---

### Problem: Connection timeout or refused

**Check port:**
```powershell
netstat -an | Select-String "6379"
```

Should show `LISTENING` on `127.0.0.1:6379`

**Restart Memurai:**
```powershell
Restart-Service -Name "Memurai"
```

---

### Problem: Celery can't find tasks

**Check:**
1. `budget_transfer/__init__.py` imports celery_app
2. Task is decorated with `@shared_task`
3. Restart Celery worker after code changes

---

## 📊 Monitoring

### View Active Celery Workers
```powershell
celery -A config inspect active
```

### View Registered Tasks
```powershell
celery -A config inspect registered
```

### Purge All Tasks from Queue
```powershell
celery -A config purge
```

### Monitor Redis
```powershell
# Check connections
netstat -an | Select-String "6379"

# Check service
Get-Service -Name "Memurai"
```

---

## 🔄 Daily Workflow

### Starting Work
1. **Check Redis:** `Get-Service -Name "Memurai"` (should be Running)
2. **Start Celery:** `celery -A config worker --loglevel=info --pool=solo`
3. **Start Django:** `python manage.py runserver`

### Stopping Work
1. Stop Django: `Ctrl+C` in Django terminal
2. Stop Celery: `Ctrl+C` in Celery terminal
3. Redis keeps running as a service (no need to stop)

### After Code Changes
1. **Stop** both Celery and Django (`Ctrl+C`)
2. **Restart Celery first**
3. **Then restart Django**

---

## 📦 Required Packages (requirements.txt)

Add these to your `requirements.txt`:
```
celery==5.5.3
redis==7.0.1
```

Install all:
```powershell
pip install -r requirements.txt
```

---

## 🎯 How It Works

### Workflow Flow:
1. User submits budget transfer in UI
2. Django signal fires when status = "submitted"
3. Signal queues Celery task: `upload_journal_to_oracle.delay()`
4. Django returns HTTP 200 immediately (no blocking!)
5. Celery worker picks up task from Redis queue
6. Worker runs Oracle FBDI workflow (5+ minutes)
7. Worker creates audit records for each step
8. Worker updates budget_transfer.journal_uploaded when complete

### Without Celery (OLD):
- User clicks submit
- Signal runs Oracle workflow synchronously
- HTTP request waits 5+ minutes
- User sees loading spinner forever
- Request might timeout

### With Celery (NEW):
- User clicks submit
- Signal queues task in Redis
- HTTP returns in < 1 second
- User sees success message
- Celery processes in background
- Audit table tracks progress

---

## 🔐 Production Considerations

### For Production Deployment:

1. **Use a process manager for Celery:**
   - Windows: NSSM (Non-Sucking Service Manager)
   - Linux: Supervisor or systemd

2. **Monitor Celery workers:**
   ```powershell
   pip install flower
   celery -A config flower
   # Access monitoring at http://localhost:5555
   ```

3. **Configure Redis persistence:**
   - Memurai saves to disk automatically
   - Check: `C:\Program Files\Memurai\memurai.conf`

4. **Set up logging:**
   - Celery logs to console by default
   - Configure file logging in production

5. **Scale workers:**
   ```powershell
   # Multiple workers for better performance
   celery -A config worker --loglevel=info --concurrency=4
   ```

---

## 📞 Support

If you encounter issues:

1. Check Redis is running: `Get-Service -Name "Memurai"`
2. Test Python can connect: `python -c "import redis; print(redis.Redis().ping())"`
3. Check Celery terminal for errors
4. Check Django terminal for errors
5. Verify startup order: Redis → Celery → Django

---

## ✨ Success Indicators

You know it's working when:

✅ Memurai service shows "Running"
✅ Celery terminal shows "celery@Mohamed ready"
✅ Django starts without connection errors
✅ Submit action returns immediately (< 1 second)
✅ Celery terminal shows task received and processing
✅ Audit records appear in database with step-by-step progress
✅ No "WinError 10061" connection refused errors

---

**Last Updated:** November 18, 2025
**Project:** Tnfeez_MOFA - Oracle FBDI Integration
**Authors:** Development Team
