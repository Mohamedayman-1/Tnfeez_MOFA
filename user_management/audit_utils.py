"""
Utility functions for creating audit logs programmatically.
"""
import json
from django.contrib.contenttypes.models import ContentType
from .audit_models import XX_AuditLog, XX_AuditLoginHistory


class AuditLogger:
    """
    Utility class for creating audit logs programmatically.
    Use this in views, signals, or business logic to explicitly log actions.
    """
    
    @staticmethod
    def log_action(
        user,
        action_type,
        action_description,
        affected_object=None,
        old_values=None,
        new_values=None,
        severity='INFO',
        status='SUCCESS',
        error_message=None,
        metadata=None,
        request=None
    ):
        """
        Create an audit log entry.
        
        Args:
            user: Django user object
            action_type: Type of action (CREATE, UPDATE, DELETE, etc.)
            action_description: Human-readable description
            affected_object: Django model instance that was affected
            old_values: Dict of values before change
            new_values: Dict of values after change
            severity: INFO, WARNING, ERROR, CRITICAL
            status: SUCCESS, FAILED, PARTIAL
            error_message: Error message if action failed
            metadata: Additional metadata dict
            request: HTTP request object (optional)
        
        Returns:
            XX_AuditLog instance
        """
        
        # Prepare data
        username = user.username if user and hasattr(user, 'username') else 'System'
        
        # Get content type and object details
        content_type = None
        object_id = None
        object_repr = None
        module = None
        
        if affected_object:
            content_type = ContentType.objects.get_for_model(affected_object)
            object_id = affected_object.pk
            object_repr = str(affected_object)[:500]
            module = affected_object._meta.app_label
        
        # Request details
        endpoint = None
        request_method = None
        ip_address = None
        user_agent = None
        
        if request:
            endpoint = request.path
            request_method = request.method
            # Get IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        # Serialize values
        old_values_json = json.dumps(old_values) if old_values else None
        new_values_json = json.dumps(new_values) if new_values else None
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Create audit log
        audit_log = XX_AuditLog.objects.create(
            user=user,
            username=username,
            action_type=action_type,
            action_description=action_description,
            severity=severity,
            endpoint=endpoint,
            request_method=request_method,
            ip_address=ip_address,
            user_agent=user_agent,
            content_type=content_type,
            object_id=object_id,
            object_repr=object_repr,
            old_values=old_values_json,
            new_values=new_values_json,
            metadata=metadata_json,
            status=status,
            error_message=error_message,
            module=module,
        )
        
        return audit_log
    
    @staticmethod
    def log_login(user, success=True, failure_reason=None, request=None):
        """Log a login attempt"""
        username = user.username if user and hasattr(user, 'username') else 'Unknown'
        
        # Get IP and user agent
        ip_address = None
        user_agent = None
        
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create login history
        login_type = 'LOGIN' if success else 'FAILED_LOGIN'
        
        XX_AuditLoginHistory.objects.create(
            user=user if success else None,
            username=username,
            login_type=login_type,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
        )
        
        # Also create general audit log
        AuditLogger.log_action(
            user=user if success else None,
            action_type='LOGIN' if success else 'OTHER',
            action_description=f"{'Successful' if success else 'Failed'} login attempt for {username}",
            severity='INFO' if success else 'WARNING',
            status='SUCCESS' if success else 'FAILED',
            error_message=failure_reason,
            metadata={'login_type': login_type},
            request=request,
        )
    
    @staticmethod
    def log_logout(user, request=None):
        """Log a logout"""
        username = user.username if user and hasattr(user, 'username') else 'Unknown'
        
        # Get IP and user agent
        ip_address = None
        user_agent = None
        
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create login history
        XX_AuditLoginHistory.objects.create(
            user=user,
            username=username,
            login_type='LOGOUT',
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        
        # Also create general audit log
        AuditLogger.log_action(
            user=user,
            action_type='LOGOUT',
            action_description=f"User {username} logged out",
            severity='INFO',
            status='SUCCESS',
            request=request,
        )
    
    @staticmethod
    def log_model_change(user, instance, action_type, old_instance=None, request=None):
        """
        Convenience method for logging model changes.
        
        Args:
            user: User performing the action
            instance: Model instance after change
            action_type: CREATE, UPDATE, or DELETE
            old_instance: Model instance before change (for UPDATE)
            request: HTTP request object
        """
        
        # Get model fields
        old_values = {}
        new_values = {}
        
        if action_type == 'DELETE':
            # For delete, capture current state as old values
            for field in instance._meta.fields:
                try:
                    old_values[field.name] = str(getattr(instance, field.name))
                except:
                    pass
        
        elif action_type == 'UPDATE' and old_instance:
            # For update, capture changes
            for field in instance._meta.fields:
                try:
                    old_val = getattr(old_instance, field.name)
                    new_val = getattr(instance, field.name)
                    if old_val != new_val:
                        old_values[field.name] = str(old_val)
                        new_values[field.name] = str(new_val)
                except:
                    pass
        
        elif action_type == 'CREATE':
            # For create, capture new state
            for field in instance._meta.fields:
                try:
                    new_values[field.name] = str(getattr(instance, field.name))
                except:
                    pass
        
        # Create description
        model_name = instance._meta.verbose_name or instance.__class__.__name__
        action_description = f"{action_type} {model_name}: {str(instance)[:100]}"
        
        return AuditLogger.log_action(
            user=user,
            action_type=action_type,
            action_description=action_description,
            affected_object=instance if action_type != 'DELETE' else None,
            old_values=old_values if old_values else None,
            new_values=new_values if new_values else None,
            request=request,
        )
    
    @staticmethod
    def log_approval(user, transaction, action, comments=None, request=None):
        """Log approval workflow actions"""
        action_type = 'APPROVE' if action == 'approve' else 'REJECT'
        
        metadata = {
            'transaction_id': transaction.transaction_id,
            'transaction_code': getattr(transaction, 'code', None),
            'action': action,
            'comments': comments,
        }
        
        action_description = f"{action.title()} transaction {transaction.code or transaction.transaction_id}"
        if comments:
            action_description += f" - {comments}"
        
        return AuditLogger.log_action(
            user=user,
            action_type=action_type,
            action_description=action_description,
            affected_object=transaction,
            metadata=metadata,
            request=request,
        )
    
    @staticmethod
    def log_export(user, export_type, record_count, request=None):
        """Log data export actions"""
        return AuditLogger.log_action(
            user=user,
            action_type='EXPORT',
            action_description=f"Exported {record_count} {export_type} records",
            metadata={
                'export_type': export_type,
                'record_count': record_count,
            },
            request=request,
        )
    
    @staticmethod
    def log_import(user, import_type, record_count, success=True, error_message=None, request=None):
        """Log data import actions"""
        return AuditLogger.log_action(
            user=user,
            action_type='IMPORT',
            action_description=f"Imported {record_count} {import_type} records",
            status='SUCCESS' if success else 'FAILED',
            error_message=error_message,
            severity='INFO' if success else 'ERROR',
            metadata={
                'import_type': import_type,
                'record_count': record_count,
            },
            request=request,
        )
