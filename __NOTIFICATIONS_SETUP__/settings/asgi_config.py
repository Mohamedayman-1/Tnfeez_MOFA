"""
ASGI Configuration for WebSocket Support
File: budget_transfer/asgi.py

This file configures the ASGI application to handle both HTTP and WebSocket connections.
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')

# Initialize Django ASGI application early to ensure settings are loaded
# This must be done before importing any other Django modules
django_asgi_app = get_asgi_application()

# Import WebSocket URL patterns AFTER Django initialization to avoid circular imports
# Update this import path to match your actual app structure
# Example: from notifications.routing import websocket_urlpatterns
# Or create a routing.py file in your main project directory
try:
    from __NOTIFICATIONS_SETUP__ import routing
except ImportError:
    # Fallback to empty urlpatterns if routing module doesn't exist yet
    websocket_urlpatterns = []
# ASGI application configuration
# Routes different protocol types to appropriate handlers
application = ProtocolTypeRouter({
    # HTTP requests handled by Django's standard ASGI application
    'http': django_asgi_app,
    
    # WebSocket connections handled by Channels
    # AuthMiddlewareStack adds user authentication to WebSocket connections
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

# ============================================================================
# Alternative Configurations
# ============================================================================

# For custom authentication (e.g., JWT tokens):
"""
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

@database_sync_to_async
def get_user_from_token(token):
    # Implement your JWT token validation here
    pass

class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Extract token from query string or headers
        token = scope.get('query_string', b'').decode()
        # Validate token and set user
        scope['user'] = await get_user_from_token(token) or AnonymousUser()
        return await self.app(scope, receive, send)

# Use custom middleware:
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': TokenAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
"""

# ============================================================================
# Notes
# ============================================================================

# 1. This file is referenced in settings.py:
#    ASGI_APPLICATION = 'budget_transfer.asgi.application'

# 2. Start server with ASGI support:
#    python manage.py runserver  # Django 3.0+ supports WebSockets
#    OR
#    daphne -b 0.0.0.0 -p 8000 budget_transfer.asgi:application

# 3. For production with Uvicorn:
#    uvicorn budget_transfer.asgi:application --host 0.0.0.0 --port 8000

# 4. WebSocket URL will be:
#    ws://127.0.0.1:8000/ws/notifications/  (development)
#    wss://yourdomain.com/ws/notifications/  (production with SSL)
