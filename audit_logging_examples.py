"""
Example script demonstrating audit logging usage.

This script shows how to use the audit logging system programmatically
in your views and business logic.
"""

from user_management.audit_utils import AuditLogger
from budget_management.models import xx_BudgetTransfer


# Example 1: Log a transaction approval
def approve_transaction(transaction_id, user, request):
    """Approve a budget transaction and log the action."""
    try:
        transaction = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)
        
        # Store old state for comparison
        old_status = transaction.status
        
        # Perform the approval
        transaction.status = 'approved'
        transaction.save()
        
        # Log the approval action
        AuditLogger.log_approval(
            user=user,
            transaction=transaction,
            action='approve',
            comments='Transaction approved after budget verification',
            request=request
        )
        
        return {'success': True, 'message': 'Transaction approved'}
        
    except xx_BudgetTransfer.DoesNotExist:
        # Log the failed attempt
        AuditLogger.log_action(
            user=user,
            action_type='APPROVE',
            action_description=f'Failed to approve transaction {transaction_id} - not found',
            severity='WARNING',
            status='FAILED',
            error_message='Transaction not found',
            request=request
        )
        return {'success': False, 'error': 'Transaction not found'}


# Example 2: Log model creation with full details
def create_budget_transfer(data, user, request):
    """Create a new budget transfer and log it."""
    
    transfer = xx_BudgetTransfer.objects.create(
        amount=data['amount'],
        requested_by=user.username,
        user_id=user.id,
        status='pending',
        # ... other fields
    )
    
    # Log the creation with details
    AuditLogger.log_model_change(
        user=user,
        instance=transfer,
        action_type='CREATE',
        request=request
    )
    
    return transfer


# Example 3: Log model update with before/after comparison
def update_budget_transfer(transfer_id, data, user, request):
    """Update a budget transfer and log changes."""
    
    transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)
    
    # Store original state
    old_transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)
    
    # Update fields
    transfer.amount = data.get('amount', transfer.amount)
    transfer.notes = data.get('notes', transfer.notes)
    transfer.save()
    
    # Log the update with comparison
    AuditLogger.log_model_change(
        user=user,
        instance=transfer,
        action_type='UPDATE',
        old_instance=old_transfer,
        request=request
    )
    
    return transfer


# Example 4: Log data export
def export_transactions(filters, user, request):
    """Export transactions to Excel and log the export."""
    
    transactions = xx_BudgetTransfer.objects.filter(**filters)
    record_count = transactions.count()
    
    # Perform export
    # ... export logic here ...
    
    # Log the export
    AuditLogger.log_export(
        user=user,
        export_type='budget_transactions',
        record_count=record_count,
        request=request
    )
    
    return {'count': record_count, 'file': 'transactions.xlsx'}


# Example 5: Log data import
def import_budget_data(file_path, user, request):
    """Import budget data from file and log the import."""
    
    success = False
    record_count = 0
    error_message = None
    
    try:
        # Parse and import file
        # ... import logic here ...
        record_count = 50  # example
        success = True
        
    except Exception as e:
        error_message = str(e)
    
    # Log the import
    AuditLogger.log_import(
        user=user,
        import_type='budget_allocations',
        record_count=record_count,
        success=success,
        error_message=error_message,
        request=request
    )
    
    return {'success': success, 'records': record_count}


# Example 6: Log custom action with metadata
def process_workflow_step(workflow_id, step, user, request):
    """Process a workflow step and log it."""
    
    # Process workflow
    # ... workflow logic ...
    
    # Log with custom metadata
    AuditLogger.log_action(
        user=user,
        action_type='WORKFLOW',
        action_description=f'Completed workflow step: {step}',
        severity='INFO',
        status='SUCCESS',
        metadata={
            'workflow_id': workflow_id,
            'step': step,
            'next_step': step + 1,
            'completion_time': '2026-01-02T10:30:00Z'
        },
        request=request
    )


# Example 7: Log permission changes
def grant_user_permission(user_id, permission, granter, request):
    """Grant a permission to a user and log it."""
    
    from user_management.models import xx_User
    
    target_user = xx_User.objects.get(id=user_id)
    
    # Grant permission
    # ... permission logic ...
    
    # Log permission change
    AuditLogger.log_action(
        user=granter,
        action_type='PERMISSION_CHANGE',
        action_description=f'Granted {permission} permission to {target_user.username}',
        affected_object=target_user,
        severity='WARNING',  # Permission changes are important
        metadata={
            'permission': permission,
            'target_user': target_user.username,
            'granted_by': granter.username
        },
        request=request
    )


# Example 8: Log with error handling
def risky_operation(data, user, request):
    """Perform a risky operation with comprehensive logging."""
    
    try:
        # Attempt operation
        result = perform_operation(data)
        
        # Log success
        AuditLogger.log_action(
            user=user,
            action_type='OTHER',
            action_description='Risky operation completed successfully',
            severity='INFO',
            status='SUCCESS',
            metadata={'result': result},
            request=request
        )
        
        return result
        
    except Exception as e:
        # Log failure
        AuditLogger.log_action(
            user=user,
            action_type='OTHER',
            action_description='Risky operation failed',
            severity='ERROR',
            status='FAILED',
            error_message=str(e),
            metadata={'input_data': data},
            request=request
        )
        
        raise


# Example 9: Log batch operations
def bulk_update_status(transaction_ids, new_status, user, request):
    """Update multiple transactions and log as a single action."""
    
    transactions = xx_BudgetTransfer.objects.filter(
        transaction_id__in=transaction_ids
    )
    
    updated_count = transactions.update(status=new_status)
    
    # Log the bulk operation
    AuditLogger.log_action(
        user=user,
        action_type='UPDATE',
        action_description=f'Bulk updated {updated_count} transactions to status: {new_status}',
        severity='INFO',
        status='SUCCESS',
        metadata={
            'transaction_ids': transaction_ids,
            'new_status': new_status,
            'count': updated_count
        },
        request=request
    )
    
    return updated_count


# Example 10: Query audit logs
def get_user_activity_report(user_id, days=30):
    """Get a user's activity report from audit logs."""
    
    from user_management.audit_models import XX_AuditLog
    from django.utils import timezone
    from datetime import timedelta
    
    start_date = timezone.now() - timedelta(days=days)
    
    logs = XX_AuditLog.objects.filter(
        user_id=user_id,
        timestamp__gte=start_date
    ).order_by('-timestamp')
    
    # Aggregate statistics
    stats = {
        'total_actions': logs.count(),
        'by_type': {},
        'by_severity': {},
        'errors': logs.filter(status='FAILED').count()
    }
    
    # Count by action type
    for action_type in logs.values_list('action_type', flat=True).distinct():
        stats['by_type'][action_type] = logs.filter(action_type=action_type).count()
    
    return stats


# Helper function (example)
def perform_operation(data):
    """Dummy operation for example."""
    return {'processed': True, 'data': data}


if __name__ == '__main__':
    print("""
    Audit Logging Examples
    ======================
    
    This file contains examples of how to use the audit logging system.
    
    See AUDIT_LOGGING_GUIDE.md for complete documentation.
    
    Key functions:
    - AuditLogger.log_action() - General purpose logging
    - AuditLogger.log_model_change() - Log model CREATE/UPDATE/DELETE
    - AuditLogger.log_approval() - Log approvals/rejections
    - AuditLogger.log_export() - Log data exports
    - AuditLogger.log_import() - Log data imports
    - AuditLogger.log_login() - Log login attempts (automatic)
    - AuditLogger.log_logout() - Log logout (automatic)
    """)
