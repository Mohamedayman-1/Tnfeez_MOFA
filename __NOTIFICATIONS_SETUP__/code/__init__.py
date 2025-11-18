"""
Notification Code Package

Contains:
- consumers.py: WebSocket consumer for handling real-time notifications
- routing.py: WebSocket URL routing
- task_notifications.py: Helper functions for sending notifications from Celery tasks
"""

from .consumers import NotificationConsumer
from .routing import websocket_urlpatterns
from . import task_notifications

__all__ = ['NotificationConsumer', 'websocket_urlpatterns', 'task_notifications']
