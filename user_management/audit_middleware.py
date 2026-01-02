"""
Middleware for automatic audit logging of user actions.
"""
import time
import json
import traceback
from django.utils.deprecation import MiddlewareMixin
from django.contrib.contenttypes.models import ContentType
from .audit_models import XX_AuditLog
from . import audit_signals  # Import to make request available to signals


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to automatically log user actions across the system.
    
    Captures:
    - All API requests
    - User who made the request
    - Request method and endpoint
    - IP address and user agent
    - Response status
    - Duration of request
    """
    
    # Endpoints to exclude from logging (to avoid spam)
    EXCLUDED_PATHS = [
        '/admin/jsi18n/',
        '/static/',
        '/media/',
        '/favicon.ico',
        # Add more paths you want to exclude
    ]
    
    # HTTP methods to log
    LOGGED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    # Also log GET for these specific paths (sensitive data access)
    SENSITIVE_GET_PATHS = [
        '/api/transfers/',
        '/api/transactions/',
        '/api/budget/',
        '/api/users/',
        '/api/approvals/',
    ]
    
    def should_log_request(self, request):
        """Determine if this request should be logged"""
        
        # Skip excluded paths
        for excluded_path in self.EXCLUDED_PATHS:
            if request.path.startswith(excluded_path):
                return False
        
        # Log all write operations
        if request.method in self.LOGGED_METHODS:
            return True
        
        # Log GET requests to sensitive endpoints
        if request.method == 'GET':
            for sensitive_path in self.SENSITIVE_GET_PATHS:
                if request.path.startswith(sensitive_path):
                    return True
        
        return False
    
    def get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_action_type(self, request):
        """Determine action type from HTTP method"""
        method_map = {
            'POST': 'CREATE',
            'PUT': 'UPDATE',
            'PATCH': 'UPDATE',
            'DELETE': 'DELETE',
            'GET': 'READ',
        }
        return method_map.get(request.method, 'OTHER')
    
    def get_module_from_path(self, path):
        """Extract module/app name from path"""
        parts = path.strip('/').split('/')
        if len(parts) > 1 and parts[0] == 'api':
            return parts[1] if len(parts) > 1 else 'unknown'
        return parts[0] if parts else 'unknown'
    
    def process_request(self, request):
        """Mark the start time of request and store in thread-local for signals"""
        request._audit_start_time = time.time()
        # Store request in thread-local storage for signals
        audit_signals.set_current_request(request)
        return None
    
    def process_response(self, request, response):
        """Log the request after response is generated"""
        
        # Check if we should log this request
        if not self.should_log_request(request):
            return response
        
        # Calculate duration
        duration_ms = None
        if hasattr(request, '_audit_start_time'):
            duration_ms = int((time.time() - request._audit_start_time) * 1000)
        
        # Get user info
        user = None
        username = 'Anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            username = request.user.username
        
        # Determine action description
        action_description = f"{request.method} {request.path}"
        
        # Determine status
        status = 'SUCCESS' if 200 <= response.status_code < 400 else 'FAILED'
        
        # Determine severity
        severity = 'INFO'
        if 400 <= response.status_code < 500:
            severity = 'WARNING'
        elif response.status_code >= 500:
            severity = 'ERROR'
        
        # Try to create audit log (fail silently to avoid breaking requests)
        try:
            XX_AuditLog.objects.create(
                user=user,
                username=username,
                action_type=self.get_action_type(request),
                action_description=action_description,
                severity=severity,
                endpoint=request.path,
                request_method=request.method,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                status=status,
                timestamp=None,  # Will use auto_now_add
                duration_ms=duration_ms,
                module=self.get_module_from_path(request.path),
                metadata=json.dumps({
                    'status_code': response.status_code,
                    'query_params': dict(request.GET),
                })
            )
        except Exception as e:
            # Log error but don't break the request
            print(f"Failed to create audit log: {e}")
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions that occur during request processing"""
        
        # Get user info
        user = None
        username = 'Anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            username = request.user.username
        
        # Calculate duration
        duration_ms = None
        if hasattr(request, '_audit_start_time'):
            duration_ms = int((time.time() - request._audit_start_time) * 1000)
        
        try:
            XX_AuditLog.objects.create(
                user=user,
                username=username,
                action_type=self.get_action_type(request),
                action_description=f"Exception in {request.method} {request.path}",
                severity='ERROR',
                endpoint=request.path,
                request_method=request.method,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                status='FAILED',
                error_message=f"{type(exception).__name__}: {str(exception)}",
                duration_ms=duration_ms,
                module=self.get_module_from_path(request.path),
                metadata=json.dumps({
                    'exception_type': type(exception).__name__,
                    'traceback': traceback.format_exc(),
                })
            )
        except Exception as e:
            print(f"Failed to log exception: {e}")
        
        return None  # Allow normal exception handling
