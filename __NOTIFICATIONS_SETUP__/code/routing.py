"""
WebSocket URL routing for budget_management app
Defines WebSocket URL patterns for real-time notifications
"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),
]
