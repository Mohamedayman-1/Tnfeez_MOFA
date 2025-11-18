"""
Celery tasks for budget management
Background tasks that run asynchronously
"""
from celery import shared_task
from django.utils import timezone
import logging

from oracle_fbdi_integration.utilities.budget_integration import create_and_upload_budget
from transaction.models import xx_TransactionTransfer
from oracle_fbdi_integration.utilities.journal_integration import create_and_upload_journal
# Import notification functions from centralized location - DISABLED
# from __NOTIFICATIONS_SETUP__.code.task_notifications import (
#     send_notification,
#     send_upload_started,
#     send_progress_notification,
#     send_upload_completed,
#     send_upload_failed,
#     set_notification_user
# )

logger = logging.getLogger("budget_transfer_tasks")


@shared_task(bind=True, max_retries=3)
def upload_journal_to_oracle(self, transaction_id, entry_type="submit"):
    """
    Background task to upload journal to Oracle
    This runs asynchronously and doesn't block the HTTP request
    Sends real-time WebSocket notifications to user
    
    Args:
        transaction_id: The budget transfer transaction ID
        entry_type: "submit" or "reject"
    """
    from budget_management.models import xx_BudgetTransfer
    
    logger.info(f"=" * 80)
    logger.info(f"CELERY TASK STARTED: upload_journal_to_oracle")
    logger.info(f"Transaction ID: {transaction_id}")
    logger.info(f"Entry Type: {entry_type}")
    logger.info(f"=" * 80)
    
    try:
        logger.info(f"Starting Oracle upload for transaction {transaction_id}")
        
        # Get the budget transfer
        budget_transfer = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)
        logger.info(f"Budget transfer found: {budget_transfer}")
        
        
        
        # Get all transfers
        transfers = xx_TransactionTransfer.objects.filter(transaction=transaction_id)
        
        if not transfers.exists():
            logger.warning(f"No transfers found for transaction {transaction_id}")
            # if user_id:
            #     send_upload_failed(user_id, transaction_id, 'No transfers found')
            return {
                "success": False,
                "error": "No transfers found"
            }
        
       
        
        # Run the complete workflow (UCM → Interface Loader → Journal Import → AutoPost)
        upload_result, result_path = create_and_upload_journal(
            transfers=transfers,
            transaction_id=transaction_id,
            entry_type=entry_type
        )
        
        if upload_result.get("success"):
            # Update the budget transfer
            
            logger.info(f"Oracle upload completed successfully for transaction {transaction_id}")
            
            # Send completion notification - DISABLED
            # if user_id:
            #     send_upload_completed(user_id, transaction_id, result_path)
            
            return {
                "success": True,
                "message": "Upload completed successfully",
                "result_path": str(result_path)
            }
        else:
            logger.error(f"Oracle upload failed for transaction {transaction_id}: {upload_result.get('error')}")
            
            # Revert status to pending
            xx_BudgetTransfer.objects.filter(pk=transaction_id).update(status="pending")
            
            # Send failure notification - DISABLED
            # if user_id:
            #     send_upload_failed(user_id, transaction_id, upload_result.get('error'))
            
            return {
                "success": False,
                "error": upload_result.get("error")
            }
            
    except Exception as e:
        logger.error(f"❌ Error in upload_journal_to_oracle task: {str(e)}")
        logger.exception(e)
        
      
        
        # Retry the task
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds






@shared_task(bind=True, max_retries=3)
def upload_budget_to_oracle(self, transaction_id,entry_type="submit"):
    """
    Background task to upload budget to Oracle
    This runs asynchronously and doesn't block the HTTP request
    Sends real-time WebSocket notifications to user
    
    Args:
        transaction_id: The budget transfer transaction ID
    """
    from budget_management.models import xx_BudgetTransfer
    
    logger.info(f"=" * 80)
    logger.info(f"CELERY TASK STARTED: upload_budget_to_oracle")
    logger.info(f"Transaction ID: {transaction_id}")
    logger.info(f"=" * 80)
    
    try:
        logger.info(f"Starting Oracle upload for transaction {transaction_id}")
        
        # Get the budget transfer
        budget_transfer = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)
        logger.info(f"Budget transfer found: {budget_transfer}")
        
        
        
        # Get all transfers
        transfers = xx_TransactionTransfer.objects.filter(transaction=transaction_id)
        
        if not transfers.exists():
            logger.warning(f"No transfers found for transaction {transaction_id}")
            return {
                "success": False,
                "error": "No transfers found"
            }
        
       
        
        # Create and upload budget
        upload_result, result_path = create_and_upload_budget(
            transfers=transfers,
            transaction_id=transaction_id,
            entry_type=entry_type
        )
        
        if upload_result.get("success"):
            # Update the budget transfer
            
            logger.info(f"Oracle upload completed successfully for transaction {transaction_id}")
            
            return {
                "success": True,
                "message": "Upload completed successfully",
                "result_path": str(result_path)
            }
        else:
            logger.error(f"Oracle upload failed for transaction {transaction_id}: {upload_result.get('error')}")
            
            # Revert status to pending
            xx_BudgetTransfer.objects.filter(pk=transaction_id).update(status="pending")
            
            return {
                "success": False,
                "error": upload_result.get("error")
            }
            
    except Exception as e:
        logger.error(f"❌ Error in upload_budget_to_oracle task: {str(e)}")
        logger.exception(e)
        
      
        
        # Retry the task
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds
