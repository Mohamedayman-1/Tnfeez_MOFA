"""
Django signals for automatic audit logging of model changes.

This module automatically tracks changes to important models and logs them
with before/after values in the audit system.
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from threading import local
import json

from .audit_utils import AuditLogger
from .audit_models import XX_AuditLog

# Thread-local storage to keep track of old instances
_thread_locals = local()


def get_current_request():
    """Get the current request from thread local storage."""
    return getattr(_thread_locals, 'request', None)


def set_current_request(request):
    """Store the current request in thread local storage."""
    _thread_locals.request = request


def get_old_instance(instance):
    """Get the old instance from thread local storage."""
    key = f"{instance.__class__.__name__}_{instance.pk}"
    return getattr(_thread_locals, key, None)


def set_old_instance(instance):
    """Store the old instance in thread local storage."""
    key = f"{instance.__class__.__name__}_{instance.pk}"
    setattr(_thread_locals, key, instance)


def clear_old_instance(instance):
    """Clear the old instance from thread local storage."""
    key = f"{instance.__class__.__name__}_{instance.pk}"
    if hasattr(_thread_locals, key):
        delattr(_thread_locals, key)


def should_audit_model(model_class):
    """
    Determine if a model should be audited.
    
    Add model names here that you want to automatically audit.
    """
    audited_models = [
        'xx_BudgetTransfer',
        'xx_TransactionTransfer',
        'xx_User',
        'xx_UserLevel',
        'XX_SecurityGroup',
        'XX_UserSegmentAccess',
        'XX_Segment',
        'XX_SegmentType',
        'ApprovalWorkflowInstance',
        'ApprovalWorkflowStep',
    ]
    
    return model_class.__name__ in audited_models


def get_model_fields_as_dict(instance, exclude_fields=None):
    """
    Get all model fields as a dictionary.
    
    Args:
        instance: Model instance
        exclude_fields: List of field names to exclude
    
    Returns:
        Dictionary of field names and values
    """
    if exclude_fields is None:
        exclude_fields = ['password', 'created_at', 'updated_at']
    
    data = {}
    for field in instance._meta.fields:
        if field.name in exclude_fields:
            continue
        
        try:
            value = getattr(instance, field.name)
            
            # Convert complex types to strings
            if hasattr(value, 'pk'):  # Foreign key
                data[field.name] = f"{value.pk}"
            elif isinstance(value, (list, dict)):
                data[field.name] = json.dumps(value)
            else:
                data[field.name] = str(value) if value is not None else None
        except Exception:
            # Skip fields that can't be serialized
            pass
    
    return data


def get_user_from_request():
    """Get user from current request, or return None."""
    request = get_current_request()
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None


@receiver(pre_save)
def capture_old_instance(sender, instance, **kwargs):
    """
    Capture the old state of an instance before it's saved.
    This runs before save() is called.
    """
    # Skip if it's a new instance or if we shouldn't audit this model
    if not instance.pk or not should_audit_model(sender):
        return
    
    # Skip audit log models to avoid infinite loops
    if sender.__name__ in ['XX_AuditLog', 'XX_AuditLoginHistory']:
        return
    
    try:
        # Get the old instance from the database
        old_instance = sender.objects.get(pk=instance.pk)
        # Store it in thread-local storage
        set_old_instance(old_instance)
    except sender.DoesNotExist:
        pass


@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    """
    Log model creation and updates to the audit system.
    This runs after save() is called.
    """
    # Skip if we shouldn't audit this model
    if not should_audit_model(sender):
        return
    
    # Skip audit log models to avoid infinite loops
    if sender.__name__ in ['XX_AuditLog', 'XX_AuditLoginHistory']:
        return
    
    try:
        user = get_user_from_request()
        request = get_current_request()
        
        # Determine action type
        action_type = 'CREATE' if created else 'UPDATE'
        
        # Get old and new values
        old_values = None
        new_values = get_model_fields_as_dict(instance)
        
        if not created:
            # For updates, get the old instance we captured in pre_save
            old_instance = get_old_instance(instance)
            if old_instance:
                old_values = get_model_fields_as_dict(old_instance)
                # Clear from thread-local storage
                clear_old_instance(instance)
        
        # Create action description
        model_name = sender._meta.verbose_name or sender.__name__
        action_description = f"{action_type} {model_name}: {str(instance)[:100]}"
        
        # Log to audit system
        AuditLogger.log_action(
            user=user,
            action_type=action_type,
            action_description=action_description,
            affected_object=instance,
            old_values=old_values,
            new_values=new_values,
            severity='INFO',
            status='SUCCESS',
            request=request
        )
        
    except Exception as e:
        # Don't break the save operation if audit logging fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log model save: {e}")


@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    """
    Log model deletion to the audit system.
    This runs after delete() is called.
    """
    # Skip if we shouldn't audit this model
    if not should_audit_model(sender):
        return
    
    # Skip audit log models to avoid infinite loops
    if sender.__name__ in ['XX_AuditLog', 'XX_AuditLoginHistory']:
        return
    
    try:
        user = get_user_from_request()
        request = get_current_request()
        
        # Get the values that were deleted
        old_values = get_model_fields_as_dict(instance)
        
        # Create action description
        model_name = sender._meta.verbose_name or sender.__name__
        action_description = f"DELETE {model_name}: {str(instance)[:100]}"
        
        # Log to audit system
        # Note: We can't use affected_object since it's deleted
        AuditLogger.log_action(
            user=user,
            action_type='DELETE',
            action_description=action_description,
            affected_object=None,  # Object is deleted
            old_values=old_values,
            new_values=None,
            severity='WARNING',  # Deletions are more important
            status='SUCCESS',
            metadata={
                'deleted_model': sender.__name__,
                'deleted_pk': instance.pk,
                'deleted_repr': str(instance)[:500]
            },
            request=request
        )
        
    except Exception as e:
        # Don't break the delete operation if audit logging fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log model delete: {e}")


# Signal specifically for transaction status changes
@receiver(post_save, sender='budget_management.xx_BudgetTransfer')
def log_transaction_status_change(sender, instance, created, **kwargs):
    """
    Special handler for transaction status changes.
    Logs with higher severity when status changes to approved/rejected.
    """
    if created:
        return
    
    old_instance = get_old_instance(instance)
    if not old_instance:
        return
    
    # Check if status changed
    if old_instance.status != instance.status:
        user = get_user_from_request()
        request = get_current_request()
        
        # Determine severity based on new status
        severity = 'INFO'
        if instance.status in ['approved', 'rejected']:
            severity = 'WARNING'
        
        action_description = f"Transaction {instance.code or instance.transaction_id} status changed from '{old_instance.status}' to '{instance.status}'"
        
        AuditLogger.log_action(
            user=user,
            action_type='UPDATE',
            action_description=action_description,
            affected_object=instance,
            old_values={'status': old_instance.status},
            new_values={'status': instance.status},
            severity=severity,
            status='SUCCESS',
            metadata={
                'transaction_id': instance.transaction_id,
                'transaction_code': instance.code,
                'status_change': f"{old_instance.status} → {instance.status}"
            },
            request=request
        )
