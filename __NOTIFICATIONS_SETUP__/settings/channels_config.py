"""
Django Channels Configuration
Add this to your Django settings.py file
"""

# ============================================================================
# Django Channels & WebSocket Configuration
# ============================================================================

# INSTALLED_APPS - Add these apps
# IMPORTANT: 'daphne' MUST be first in INSTALLED_APPS for ASGI support
INSTALLED_APPS = [
    'daphne',  # ⚠️ Must be FIRST for WebSocket/ASGI support
    'django.contrib.admin',
    'django.contrib.auth',
    # ... other apps ...
    'channels',  # Django Channels for WebSocket
    'rest_framework',
    # ... your apps ...
]

# ASGI Application (for WebSocket support)
# This replaces WSGI for async operations
ASGI_APPLICATION = 'budget_transfer.asgi.application'

# Channel Layers Configuration (using Redis)
# Redis acts as the message broker for WebSocket communication
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            # Redis server host and port
            "hosts": [('127.0.0.1', 6379)],
            
            # Optional: Advanced configuration
            # "capacity": 1500,        # Message buffer capacity
            # "expiry": 10,            # Message expiry in seconds
            # "group_expiry": 86400,   # Group membership expiry (24 hours)
            # "symmetric_encryption_keys": [SECRET_KEY],  # Encryption
        },
    },
}

# ============================================================================
# Celery Configuration (Required for Background Tasks)
# ============================================================================

# Celery broker URL (using Redis)
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'

# Celery result backend (using Redis)
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'

# Broker connection settings
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

# Redis connection pool settings
CELERY_BROKER_POOL_LIMIT = 10
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 3600,
    'max_connections': 50,
}

# Celery task serializer
CELERY_TASK_SERIALIZER = 'json'

# Celery result serializer
CELERY_RESULT_SERIALIZER = 'json'

# Celery accept content types
CELERY_ACCEPT_CONTENT = ['json']

# Celery timezone (match Django timezone)
CELERY_TIMEZONE = 'UTC'

# Celery task time limit (30 minutes for Oracle uploads)
CELERY_TASK_TIME_LIMIT = 30 * 60

# Celery task soft time limit (25 minutes warning)
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60

# ============================================================================
# CORS Configuration (if using separate frontend)
# ============================================================================

# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",     # React/Vue/Angular dev server
#     "http://127.0.0.1:3000",
#     "https://yourdomain.com",    # Production frontend
# ]

# CORS_ALLOW_CREDENTIALS = True  # Required for WebSocket authentication

# ============================================================================
# Security Settings for Production
# ============================================================================

# For WebSocket connections over SSL (production)
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True

# ============================================================================
# Notes
# ============================================================================

# 1. Redis must be running before starting Django/Celery
#    Windows: Get-Service -Name "Memurai"
#    Linux: sudo systemctl status redis-server

# 2. Start services in order:
#    a. Redis (Memurai service)
#    b. Celery worker: celery -A config worker --loglevel=info --pool=solo
#    c. Django server: python manage.py runserver

# 3. For production, use Daphne ASGI server:
#    daphne -b 0.0.0.0 -p 8000 budget_transfer.asgi:application

# 4. Monitor Redis connections:
#    redis-cli client list
#    redis-cli info clients
