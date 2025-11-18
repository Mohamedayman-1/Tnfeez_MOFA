# Celery Setup Guide for Tnfeez_MOFA

## Step 1: Install Required Packages

```powershell
pip install celery redis
```

## Step 2: Install Redis

### On Windows:
```powershell
# Using Chocolatey
choco install redis-64

# Or download from: https://github.com/microsoftarchive/redis/releases
# Download Redis-x64-3.0.504.msi and install
```

### On Linux/Mac:
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# Mac
brew install redis
```

## Step 3: Start Redis Server

```powershell
# Windows (if installed via Chocolatey or MSI)
redis-server

# Or if using WSL
wsl redis-server
```

You should see output like:
```
                _._                                                  
           _.-``__ ''-._                                             
      _.-``    `.  `_.  ''-._           Redis 3.0.504 (00000000/0) 64 bit
  .-`` .-```.  ```\/    _.,_ ''-._                                   
 (    '      ,       .-`  | `,    )     Running in standalone mode
 |`-._`-...-` __...-.``-._|'` _.-'|     Port: 6379
 |    `-._   `._    /     _.-'    |     PID: 1234
  `-._    `-._  `-./  _.-'    _.-'                                   
 |`-._`-._    `-.__.-'    _.-'_.-'|                                  
 |    `-._`-._        _.-'_.-'    |           http://redis.io        
  `-._    `-._`-.__.-'_.-'    _.-'                                   
 |`-._`-._    `-.__.-'    _.-'_.-'|                                  
 |    `-._`-._        _.-'_.-'    |                                  
  `-._    `-._`-.__.-'_.-'    _.-'                                   
      `-._    `-.__.-'    _.-'                                       
          `-._        _.-'                                           
              `-.__.-'                                               

[1234] 18 Nov 01:23:45.678 # Server started, Redis version 3.0.504
[1234] 18 Nov 01:23:45.678 * The server is now ready to accept connections on port 6379
```

## Step 4: Start Celery Worker

Open a new terminal and run:

```powershell
# Navigate to project directory
cd c:\Users\m7mad\Documents\GitHub\Tnfeez_MOFA

# Start Celery worker
celery -A config worker --loglevel=info --pool=solo
```

**Note:** On Windows, use `--pool=solo` instead of the default pool.

You should see output like:
```
 -------------- celery@YOURPC v5.x.x (...)
---- **** ----- 
--- * ***  * -- Windows-10-10.0.19041-SP0 2025-11-18 01:23:45
-- * - **** --- 
- ** ---------- [config]
- ** ---------- .> app:         tnfeez_mofa:0x...
- ** ---------- .> transport:   redis://localhost:6379/0
- ** ---------- .> results:     redis://localhost:6379/0
- *** --- * --- .> concurrency: 8 (solo)
-- ******* ---- .> task events: OFF (enable -E to monitor tasks in this worker)
--- ***** ----- 
 -------------- [queues]
                .> celery           exchange=celery(direct) key=celery

[tasks]
  . budget_management.tasks.upload_journal_to_oracle
  . config.celery.debug_task

[2025-11-18 01:23:45,123: INFO/MainProcess] Connected to redis://localhost:6379/0
[2025-11-18 01:23:45,456: INFO/MainProcess] celery@YOURPC ready.
```

## Step 5: Test the Setup

Open Django shell:
```powershell
python manage.py shell
```

Test Celery:
```python
from budget_management.tasks import upload_journal_to_oracle

# Queue a test task (replace 123 with real transaction_id)
result = upload_journal_to_oracle.delay(transaction_id=123)

# Check task ID
print(f"Task ID: {result.task_id}")

# Check if task is ready (completed)
print(f"Task ready: {result.ready()}")

# Get result (this will wait until task completes)
# print(f"Result: {result.get()}")
```

## Step 6: Run Your Application

Now when you submit a budget transfer, it will:
1. ✅ Return response immediately to user
2. ✅ Queue the Oracle upload task in Celery
3. ✅ Process the task in background
4. ✅ Update the database when complete

## Monitoring Tasks

### Check task status in code:
```python
from celery.result import AsyncResult

task_id = "your-task-id-here"
result = AsyncResult(task_id)

print(f"Status: {result.status}")  # PENDING, STARTED, SUCCESS, FAILURE
print(f"Info: {result.info}")
```

### Check Redis for tasks:
```powershell
redis-cli

# List all keys
KEYS *

# Get task info
GET celery-task-meta-<task-id>
```

## Production Deployment

For production, you'll need:

1. **Supervisor or systemd** to manage Celery workers
2. **Multiple workers** for better performance
3. **Celery Beat** for scheduled tasks (if needed)
4. **Flower** for monitoring (optional):
   ```powershell
   pip install flower
   celery -A config flower
   # Visit http://localhost:5555
   ```

## Troubleshooting

### "Task not registered" error:
```powershell
# Make sure Celery can find tasks
celery -A config inspect registered
```

### Redis connection error:
```powershell
# Test Redis connection
redis-cli ping
# Should return: PONG
```

### Worker not picking up tasks:
```powershell
# Restart worker with verbose logging
celery -A config worker --loglevel=debug --pool=solo
```

## Summary

You now have:
- ✅ Celery configured in `config/celery.py`
- ✅ Settings configured in `budget_transfer/settings.py`
- ✅ Background task in `budget_management/tasks.py`
- ✅ Signal updated to queue tasks instead of blocking

Your Oracle uploads now run in the background! 🚀
