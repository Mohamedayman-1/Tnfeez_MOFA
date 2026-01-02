"""
URL configuration for audit logging API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .audit_views import AuditLogViewSet, LoginHistoryViewSet

router = DefaultRouter()
router.register(r'logs', AuditLogViewSet, basename='audit-log')
router.register(r'login-history', LoginHistoryViewSet, basename='login-history')

urlpatterns = [
    path('', include(router.urls)),
]
