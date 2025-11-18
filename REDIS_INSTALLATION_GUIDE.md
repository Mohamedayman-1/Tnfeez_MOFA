# Redis Installation Guide

Complete step-by-step guide to install Redis on Windows and Linux.

---

## 🪟 Windows Installation

### Method 1: Using Chocolatey (Recommended)

#### Step 1: Install Chocolatey Package Manager

**1.1 Open PowerShell as Administrator**
- Press `Windows Key`
- Type "PowerShell"
- Right-click on "Windows PowerShell"
- Select **"Run as administrator"**

**1.2 Install Chocolatey**

Copy and paste this command:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

Wait for installation to complete (may take 1-2 minutes).

**1.3 Verify Chocolatey Installation**

```powershell
choco --version
```

Expected output: `2.5.1` (or higher)

**1.4 Close and Reopen PowerShell**

Close the Administrator PowerShell and open a new one to refresh environment variables.

---

#### Step 2: Install Redis (Memurai)

**2.1 Install Redis Package**

In Administrator PowerShell:

```powershell
choco install redis-64 -y
```

This installs:
- `memurai-developer.install` - Redis-compatible server for Windows
- `redis-64` - Redis package

Installation takes 2-5 minutes.

**2.2 Refresh Environment**

```powershell
refreshenv
```

Or close and reopen PowerShell.

---

#### Step 3: Verify Redis Installation

**3.1 Check Redis Service**

```powershell
Get-Service -Name "Memurai"
```

Expected output:
```
Status   Name     DisplayName
------   ----     -----------
Running  Memurai  Memurai
```

**3.2 Check Port**

```powershell
netstat -an | Select-String "6379"
```

Expected output (should show LISTENING):
```
TCP    127.0.0.1:6379         0.0.0.0:0              LISTENING
```

**3.3 Test Connection**

```powershell
Test-NetConnection -ComputerName localhost -Port 6379 -InformationLevel Quiet
```

Expected output: `True`

---

#### Step 4: Test Redis from Python

**4.1 Install Python Redis Client**

```powershell
pip install redis
```

**4.2 Test Connection**

```powershell
python -c "import redis; r = redis.Redis(host='127.0.0.1', port=6379, db=0); print('Redis Status:', r.ping())"
```

Expected output: `Redis Status: True`

---

### Managing Redis Service on Windows

**Start Redis:**
```powershell
Start-Service -Name "Memurai"
```

**Stop Redis:**
```powershell
Stop-Service -Name "Memurai"
```

**Restart Redis:**
```powershell
Restart-Service -Name "Memurai"
```

**Check Status:**
```powershell
Get-Service -Name "Memurai"
```

**Auto-start on Boot:**
Redis (Memurai) is configured to start automatically when Windows starts. No additional configuration needed.

---

### Uninstall Redis on Windows

```powershell
choco uninstall redis-64 -y
```

---

## 🐧 Linux Installation (Ubuntu/Debian)

### Step 1: Update Package Index

```bash
sudo apt update
```

---

### Step 2: Install Redis Server

```bash
sudo apt install redis-server -y
```

Installation takes 1-2 minutes.

---

### Step 3: Configure Redis

**3.1 Edit Redis Configuration**

```bash
sudo nano /etc/redis/redis.conf
```

**3.2 Set Supervised Mode (Recommended)**

Find the line:
```
supervised no
```

Change to:
```
supervised systemd
```

**3.3 Save and Exit**
- Press `Ctrl + X`
- Press `Y` to confirm
- Press `Enter` to save

---

### Step 4: Start Redis Service

**4.1 Start Redis**

```bash
sudo systemctl start redis-server
```

**4.2 Enable Auto-start on Boot**

```bash
sudo systemctl enable redis-server
```

**4.3 Check Status**

```bash
sudo systemctl status redis-server
```

Expected output:
```
● redis-server.service - Advanced key-value store
     Loaded: loaded (/lib/systemd/system/redis-server.service; enabled)
     Active: active (running)
```

Press `q` to exit.

---

### Step 5: Verify Redis Installation

**5.1 Test Redis CLI**

```bash
redis-cli ping
```

Expected output: `PONG`

**5.2 Check Port**

```bash
sudo netstat -tulpn | grep 6379
```

Expected output:
```
tcp        0      0 127.0.0.1:6379          0.0.0.0:*               LISTEN      1234/redis-server
```

**5.3 Test Connection**

```bash
redis-cli
```

Then type:
```
127.0.0.1:6379> SET test "Hello Redis"
127.0.0.1:6379> GET test
127.0.0.1:6379> exit
```

Expected:
```
OK
"Hello Redis"
```

---

### Step 6: Test Redis from Python

**6.1 Install Python Redis Client**

```bash
pip install redis
```

**6.2 Test Connection**

```bash
python3 -c "import redis; r = redis.Redis(host='127.0.0.1', port=6379, db=0); print('Redis Status:', r.ping())"
```

Expected output: `Redis Status: True`

---

### Managing Redis Service on Linux

**Start Redis:**
```bash
sudo systemctl start redis-server
```

**Stop Redis:**
```bash
sudo systemctl stop redis-server
```

**Restart Redis:**
```bash
sudo systemctl restart redis-server
```

**Check Status:**
```bash
sudo systemctl status redis-server
```

**Enable Auto-start:**
```bash
sudo systemctl enable redis-server
```

**Disable Auto-start:**
```bash
sudo systemctl disable redis-server
```

---

### Uninstall Redis on Linux

```bash
sudo systemctl stop redis-server
sudo systemctl disable redis-server
sudo apt remove redis-server -y
sudo apt autoremove -y
```

---

## 🐧 Linux Installation (CentOS/RHEL/Fedora)

### Using DNF/YUM

**Update:**
```bash
sudo dnf update -y
# or
sudo yum update -y
```

**Install Redis:**
```bash
sudo dnf install redis -y
# or
sudo yum install redis -y
```

**Start and Enable:**
```bash
sudo systemctl start redis
sudo systemctl enable redis
```

**Check Status:**
```bash
sudo systemctl status redis
```

**Test:**
```bash
redis-cli ping
```

---

## 🍎 macOS Installation

### Using Homebrew

**Install Homebrew (if not installed):**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Install Redis:**
```bash
brew install redis
```

**Start Redis:**
```bash
brew services start redis
```

**Check Status:**
```bash
brew services list | grep redis
```

**Test:**
```bash
redis-cli ping
```

---

## 📊 Verify Installation Success

### All Platforms

After installation, verify with these tests:

**1. Service Running:**
- Windows: `Get-Service -Name "Memurai"`
- Linux/macOS: `sudo systemctl status redis-server`

**2. Port Listening:**
- Windows: `netstat -an | Select-String "6379"`
- Linux/macOS: `sudo netstat -tulpn | grep 6379`

**3. Connection Test:**
```bash
redis-cli ping
# Should return: PONG
```

**4. Python Test:**
```bash
python -c "import redis; r = redis.Redis(); print('OK' if r.ping() else 'FAILED')"
# Should return: OK
```

---

## 🔧 Common Redis Configurations

### Redis Configuration File Locations

| Platform | Configuration File |
|----------|-------------------|
| Windows (Memurai) | `C:\Program Files\Memurai\memurai.conf` |
| Ubuntu/Debian | `/etc/redis/redis.conf` |
| CentOS/RHEL | `/etc/redis.conf` |
| macOS | `/usr/local/etc/redis.conf` |

### Important Settings

**Bind Address (Security):**
```
bind 127.0.0.1
```
Only allow local connections (recommended for development).

**Port:**
```
port 6379
```
Default Redis port.

**Password (Recommended for Production):**
```
requirepass yourStrongPasswordHere
```

**Max Memory:**
```
maxmemory 256mb
maxmemory-policy allkeys-lru
```

---

## 🐛 Troubleshooting

### Windows

**Problem: Service won't start**
```powershell
# Restart service
Restart-Service -Name "Memurai"

# Check event logs
Get-EventLog -LogName Application -Source Memurai -Newest 10
```

**Problem: Port already in use**
```powershell
# Find process using port 6379
netstat -ano | findstr :6379

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

---

### Linux

**Problem: Service won't start**
```bash
# Check logs
sudo journalctl -u redis-server -n 50

# Check configuration
sudo redis-server /etc/redis/redis.conf --test-memory 100
```

**Problem: Connection refused**
```bash
# Check if running
sudo systemctl status redis-server

# Check bind address
sudo grep "^bind" /etc/redis/redis.conf

# Should be: bind 127.0.0.1
```

**Problem: Permission denied**
```bash
# Fix ownership
sudo chown redis:redis /var/lib/redis
sudo chmod 770 /var/lib/redis

# Restart
sudo systemctl restart redis-server
```

---

## 📦 Next Steps

After installing Redis:

1. ✅ Install Python packages: `pip install celery redis`
2. ✅ Configure Django settings (see `REDIS_CELERY_SETUP.md`)
3. ✅ Start Celery worker
4. ✅ Start Django server
5. ✅ Test the workflow

---

## 📚 Additional Resources

- **Redis Official:** https://redis.io/
- **Memurai (Windows):** https://www.memurai.com/
- **Chocolatey:** https://chocolatey.org/
- **Redis Python Client:** https://redis-py.readthedocs.io/

---

**Last Updated:** November 18, 2025
**Project:** Tnfeez_MOFA
