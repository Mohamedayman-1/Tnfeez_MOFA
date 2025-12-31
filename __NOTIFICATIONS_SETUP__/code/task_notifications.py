"""
Task Notification Helper Functions
Utility functions to send WebSocket notifications from Celery tasks

Usage in Celery tasks:
    from .task_notifications import send_notification, send_progress_notification
    
    @shared_task
    def my_task(user_id):
        send_notification(user_id, 'task_started', {'message': 'Task started'})
        # ... do work ...
        send_progress_notification(user_id, 'Processing', 50, 100)
        # ... more work ...
        send_notification(user_id, 'task_completed', {'message': 'Done!'})
"""

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime
import logging

logger = logging.getLogger("task_notifications")

# Global variable to store user_id for notifications (used by Upload_essjob_api.py)
_current_user_id = None


def set_notification_user(user_id):
    """
    Set the user ID for WebSocket notifications (for workflow functions)
    Used by Upload_essjob_api.py to track which user to notify
    
    Args:
        user_id: The ID of the user to send notifications to
    """
    global _current_user_id
    _current_user_id = user_id


def get_notification_user():
    """
    Get the current notification user ID
    
    Returns:
        int or None: The current user ID for notifications
    """
    global _current_user_id
    return _current_user_id


def send_notification(user_id, event_type, data):
    """
    Send a WebSocket notification to a specific user
    
    Args:
        user_id: The user ID to send notification to
        event_type: Type of event (e.g., 'notification_message', 'oracle_upload_started')
        data: Dictionary of data to send
        
    Example:
        send_notification(123, 'notification_message', {
            'message': 'Your upload is complete',
            'data': {'transaction_id': 602}
        })
    """
    if not user_id:
        logger.warning("send_notification called without user_id")
        return False
    
    try:
        channel_layer = get_channel_layer()
        
        # Add timestamp if not provided
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        
        async_to_sync(channel_layer.group_send)(
            f'notifications_{user_id}',
            {
                'type': event_type,
                **data
            }
        )
        logger.debug(f"Sent {event_type} notification to user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification: {str(e)}")
        return False


def send_progress_notification(user_id, step_name, current_step, total_steps, 
                               transaction_id=None, message=None, status='processing'):
    """
    Send a progress update notification
    
    Args:
        user_id: User ID to notify
        step_name: Name of current step
        current_step: Current step number (1-based)
        total_steps: Total number of steps
        transaction_id: Optional transaction ID
        message: Optional custom message
        status: Status of step ('processing', 'completed', 'failed')
        
    Example:
        send_progress_notification(
            user_id=123,
            step_name='Upload to UCM',
            current_step=2,
            total_steps=5,
            transaction_id=602,
            message='Uploading file to Oracle'
        )
    """
    data = {
        'step': step_name,
        'step_number': current_step,
        'total_steps': total_steps,
        'message': message or f'{step_name} in progress',
        'status': status,
    }
    
    if transaction_id:
        data['transaction_id'] = transaction_id
    
    return send_notification(user_id, 'oracle_upload_progress', data)


def send_upload_started(user_id, transaction_id, message=None, ara_message=None):
    """
    Send upload started notification
    
    Args:
        user_id: User ID to notify
        transaction_id: Transaction ID
        message: Optional custom message
    """
    eng_message = message or f'Oracle upload started for transaction {transaction_id}'
    ara_message = ara_message or eng_message
    return send_notification(user_id, 'oracle_upload_started', {
        'transaction_id': transaction_id,
        'message': eng_message,
        'eng_message': eng_message,
        'ara_message': ara_message,
    })


def send_upload_completed(user_id, transaction_id, result_path=None, message=None, ara_message=None):
    """
    Send upload completed notification
    
    Args:
        user_id: User ID to notify
        transaction_id: Transaction ID
        result_path: Optional path to result file
        message: Optional custom message
    """
    eng_message = message or f'Oracle upload completed for transaction {transaction_id}'
    ara_message = ara_message or eng_message
    data = {
        'transaction_id': transaction_id,
        'message': eng_message,
        'eng_message': eng_message,
        'ara_message': ara_message,
        'success': True
    }
    
    if result_path:
        data['result_path'] = str(result_path)
    
    return send_notification(user_id, 'oracle_upload_completed', data)


def send_upload_failed(user_id, transaction_id, error, message=None, ara_message=None):
    """
    Send upload failed notification
    
    Args:
        user_id: User ID to notify
        transaction_id: Transaction ID
        error: Error message or exception
        message: Optional custom message
    """
    eng_message = message or f'Oracle upload failed for transaction {transaction_id}'
    ara_message = ara_message or eng_message
    return send_notification(user_id, 'oracle_upload_failed', {
        'transaction_id': transaction_id,
        'message': eng_message,
        'eng_message': eng_message,
        'ara_message': ara_message,
        'error': str(error)
    })


def send_generic_message(
    user_id,
    message,
    data=None,
    eng_message=None,
    ara_message=None,
    notification=None,
    notification_id=None,
):
    """
    Send a generic notification message
    
    Args:
        user_id: User ID to notify
        message: Message text
        data: Optional additional data
    """
    if notification is None and notification_id:
        try:
            from user_management.models import xx_notification
            notification = xx_notification.objects.filter(id=notification_id).first()
        except Exception:
            notification = None

    if notification is not None:
        payload = {
            "id": notification.id,
            "Transaction_id": notification.Transaction_id,
            "Type_of_action": notification.Type_of_action,
            "type_of_Trasnction": notification.type_of_Trasnction,
            "eng_message": notification.eng_message,
            "ara_message": notification.ara_message,
            "message": notification.eng_message,
            "is_read": notification.is_read,
            "is_shown": notification.is_shown,
            "is_system_read": notification.is_system_read,
            "created_at": (
                notification.created_at.isoformat()
                if getattr(notification, "created_at", None)
                else None
            ),
        }
    else:
        if eng_message is None:
            eng_message = message
        if ara_message is None:
            ara_message = eng_message
        payload = {
            "eng_message": eng_message,
            "ara_message": ara_message,
            "message": eng_message,
        }

    payload["data"] = data or {}
    return send_notification(user_id, "notification_message", payload)


def send_workflow_notification(transaction_id, step, step_number, total_steps, message, status='processing'):
    """
    Send WebSocket notification about workflow progress
    Uses global _current_user_id set by set_notification_user()
    
    Args:
        transaction_id: Transaction ID
        step: Name of current step
        step_number: Current step number (1-based)
        total_steps: Total number of steps
        message: Status message
        status: Status of step ('processing', 'completed', 'failed')
        
    Example:
        set_notification_user(user_id)
        send_workflow_notification(
            transaction_id=602,
            step='Upload to UCM',
            step_number=1,
            total_steps=5,
            message='Uploading file to Oracle UCM',
            status='processing'
        )
    """
    global _current_user_id
    if not _current_user_id:
        logger.warning("send_workflow_notification called without user_id being set")
        return False
    
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'notifications_{_current_user_id}',
            {
                'type': 'oracle_upload_progress',
                'transaction_id': transaction_id,
                'step': step,
                'step_number': step_number,
                'total_steps': total_steps,
                'message': message,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }
        )
        logger.debug(f"Sent workflow notification: {step} ({step_number}/{total_steps})")
        return True
    except Exception as e:
        logger.error(f"Failed to send workflow notification: {str(e)}")
        return False


# ============================================================================
# Example Usage in Celery Task
# ============================================================================

"""
from celery import shared_task
from .task_notifications import (
    send_upload_started,
    send_progress_notification,
    send_upload_completed,
    send_upload_failed
)

@shared_task(bind=True)
def process_oracle_upload(self, transaction_id, user_id):
    try:
        # Send started notification
        send_upload_started(user_id, transaction_id)
        
        # Step 1: Prepare data
        send_progress_notification(
            user_id, 
            'Preparing Data', 
            1, 5,
            transaction_id
        )
        prepare_data()
        
        # Step 2: Upload to UCM
        send_progress_notification(
            user_id,
            'Upload to UCM',
            2, 5,
            transaction_id,
            'Uploading file to Oracle UCM'
        )
        upload_to_ucm()
        
        # Step 3: Interface Loader
        send_progress_notification(
            user_id,
            'Interface Loader',
            3, 5,
            transaction_id
        )
        run_interface_loader()
        
        # Step 4: Journal Import
        send_progress_notification(
            user_id,
            'Journal Import',
            4, 5,
            transaction_id
        )
        import_journal()
        
        # Step 5: AutoPost
        send_progress_notification(
            user_id,
            'AutoPost',
            5, 5,
            transaction_id
        )
        auto_post()
        
        # Send completion
        send_upload_completed(
            user_id,
            transaction_id,
            result_path='/path/to/result'
        )
        
        return {'success': True}
        
    except Exception as e:
        # Send failure notification
        send_upload_failed(user_id, transaction_id, str(e))
        raise
"""
