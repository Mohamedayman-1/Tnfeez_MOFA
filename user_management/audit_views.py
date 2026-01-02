"""
API views for audit logging.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .audit_models import XX_AuditLog, XX_AuditLoginHistory
from .audit_serializers import (
    AuditLogSerializer,
    AuditLogDetailSerializer,
    LoginHistorySerializer,
    AuditStatsSerializer,
)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs.
    
    Provides:
    - List all audit logs with filtering
    - Retrieve specific audit log
    - Statistics endpoint
    - Export functionality
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = AuditLogSerializer
    
    def get_queryset(self):
        """
        Get audit logs with optional filtering.
        
        Filter parameters:
        - user_id: Filter by user ID
        - username: Filter by username
        - action_type: Filter by action type
        - module: Filter by module/app
        - severity: Filter by severity
        - status: Filter by status
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
        - search: Search in action_description
        """
        queryset = XX_AuditLog.objects.all()
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        username = self.request.query_params.get('username')
        if username:
            queryset = queryset.filter(username__icontains=username)
        
        # Filter by action type
        action_type = self.request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        # Filter by module
        module = self.request.query_params.get('module')
        if module:
            queryset = queryset.filter(module=module)
        
        # Filter by severity
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        # Search in description
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(action_description__icontains=search)
        
        # Only show user's own logs if not admin/superadmin
        user = self.request.user
        if hasattr(user, 'role') and user.role not in ['admin', 'superadmin']:
            queryset = queryset.filter(user=user)
        
        return queryset.select_related('user', 'content_type')
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            return AuditLogDetailSerializer
        return AuditLogSerializer
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get audit statistics.
        
        Query params:
        - days: Number of days to include (default: 30)
        """
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        queryset = XX_AuditLog.objects.filter(timestamp__gte=start_date)
        
        # Only show user's own stats if not admin
        user = request.user
        if hasattr(user, 'role') and user.role not in ['admin', 'superadmin']:
            queryset = queryset.filter(user=user)
        
        # Total actions
        total_actions = queryset.count()
        
        # Actions by type
        actions_by_type = dict(
            queryset.values('action_type')
            .annotate(count=Count('audit_id'))
            .values_list('action_type', 'count')
        )
        
        # Actions by user (only for admins)
        actions_by_user = {}
        if hasattr(user, 'role') and user.role in ['admin', 'superadmin']:
            actions_by_user = dict(
                queryset.values('username')
                .annotate(count=Count('audit_id'))
                .order_by('-count')[:10]
                .values_list('username', 'count')
            )
        
        # Actions by module
        actions_by_module = dict(
            queryset.values('module')
            .annotate(count=Count('audit_id'))
            .values_list('module', 'count')
        )
        
        # Recent errors
        recent_errors = queryset.filter(
            Q(severity__in=['ERROR', 'CRITICAL']) | Q(status='FAILED')
        ).order_by('-timestamp')[:10].values(
            'audit_id',
            'username',
            'action_description',
            'error_message',
            'timestamp',
        )
        
        stats = {
            'total_actions': total_actions,
            'actions_by_type': actions_by_type,
            'actions_by_user': actions_by_user,
            'actions_by_module': actions_by_module,
            'recent_errors': list(recent_errors),
            'time_range': {
                'start': start_date.isoformat(),
                'end': timezone.now().isoformat(),
                'days': days,
            }
        }
        
        serializer = AuditStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_activity(self, request):
        """Get current user's recent activity"""
        queryset = XX_AuditLog.objects.filter(
            user=request.user
        ).order_by('-timestamp')[:50]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent_errors(self, request):
        """Get recent errors (admin only)"""
        user = request.user
        if not hasattr(user, 'role') or user.role not in ['admin', 'superadmin']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = XX_AuditLog.objects.filter(
            Q(severity__in=['ERROR', 'CRITICAL']) | Q(status='FAILED')
        ).order_by('-timestamp')[:100]
        
        serializer = AuditLogDetailSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def action_types(self, request):
        """Get list of all action types"""
        action_types = XX_AuditLog.objects.values_list(
            'action_type', flat=True
        ).distinct()
        
        return Response({
            'action_types': list(action_types)
        })
    
    @action(detail=False, methods=['get'])
    def modules(self, request):
        """Get list of all modules"""
        modules = XX_AuditLog.objects.values_list(
            'module', flat=True
        ).distinct()
        
        return Response({
            'modules': list(modules)
        })


class LoginHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing login history.
    
    Provides:
    - List all login attempts with filtering
    - Retrieve specific login record
    - User's own login history
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = LoginHistorySerializer
    
    def get_queryset(self):
        """Get login history with filtering"""
        queryset = XX_AuditLoginHistory.objects.all()
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        username = self.request.query_params.get('username')
        if username:
            queryset = queryset.filter(username__icontains=username)
        
        # Filter by login type
        login_type = self.request.query_params.get('login_type')
        if login_type:
            queryset = queryset.filter(login_type=login_type)
        
        # Filter by success
        success = self.request.query_params.get('success')
        if success is not None:
            queryset = queryset.filter(success=success.lower() == 'true')
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        # Only show user's own history if not admin
        user = self.request.user
        if hasattr(user, 'role') and user.role not in ['admin', 'superadmin']:
            queryset = queryset.filter(user=user)
        
        return queryset.select_related('user')
    
    @action(detail=False, methods=['get'])
    def my_history(self, request):
        """Get current user's login history"""
        queryset = XX_AuditLoginHistory.objects.filter(
            user=request.user
        ).order_by('-timestamp')[:50]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def failed_attempts(self, request):
        """Get recent failed login attempts (admin only)"""
        user = request.user
        if not hasattr(user, 'role') or user.role not in ['admin', 'superadmin']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        queryset = XX_AuditLoginHistory.objects.filter(
            success=False,
            timestamp__gte=start_date
        ).order_by('-timestamp')[:100]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
