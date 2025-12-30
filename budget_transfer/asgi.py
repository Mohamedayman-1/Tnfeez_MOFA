"""
ASGI config for budget_transfer project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "budget_transfer.settings")

django_asgi_app = get_asgi_application()

try:
    from __NOTIFICATIONS_SETUP__.code.routing import websocket_urlpatterns
    from __NOTIFICATIONS_SETUP__.code.jwt_auth_middleware import (
        JWTAuthMiddlewareStack,
    )
except Exception:
    websocket_urlpatterns = []

    def JWTAuthMiddlewareStack(inner):
        return inner

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
