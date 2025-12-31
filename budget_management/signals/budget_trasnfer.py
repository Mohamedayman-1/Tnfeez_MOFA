"""
Django signals for xx_BudgetTransfer model
Automatically execute functions when budget transfer changes occur
"""

from django.db.models.signals import post_save, pre_save, post_delete, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from approvals.managers import ApprovalManager, ARCHIVED_STAGE_ORDER_INDEX_START
from __NOTIFICATIONS_SETUP__.code.task_notifications import send_generic_message
from ..models import xx_BudgetTransfer
from user_management.models import xx_notification, XX_UserGroupMembership
import logging
from budget_transfer.global_function.dashbaord import dashboard_smart, dashboard_normal
from transaction.models import xx_TransactionTransfer
from budget_management.tasks import upload_journal_to_oracle

# Configure logging for budget transfer signals
logger = logging.getLogger("budget_transfer_signals")

# ============================================================================
# xx_BudgetTransfer Signals
# ============================================================================


@receiver(post_save, sender=xx_BudgetTransfer)
def budget_transfer_post_save(sender, instance, created, **kwargs):
    """
    Function executed AFTER saving xx_BudgetTransfer
    Use this for notifications, related updates, or post-processing
    """
    try:
        # Run dashboard function for ALL saves (create AND update)
        if instance.status == "approved":
            print("approved enterd")
            dashboard_smart()
        # elif instance.status == "pending":
        print("pending enterd")
        dashboard_normal()

        if created:
            logger.info(
                f"New BudgetTransfer created: {instance.transaction_id} - Dashboard updated"
            )
        else:
            logger.info(
                f"BudgetTransfer updated: {instance.transaction_id} - Dashboard updated"
            )

    except Exception as e:
        logger.error(f"Error in budget_transfer_post_save: {str(e)}")


@receiver(post_delete, sender=xx_BudgetTransfer)
def budget_transfer_post_delete(sender, instance, **kwargs):
    """
    Function executed AFTER deleting xx_BudgetTransfer
    Use this for cleanup, notifications, or post-deletion processing
    """
    try:
        dashboard_smart()
        dashboard_normal()
        logger.info(
            f"Dashboard updated after deleting BudgetTransfer {instance.transaction_id}"
        )

    except Exception as e:
        logger.error(f"Error in budget_transfer_post_delete: {str(e)}")



@receiver(post_save, sender=xx_BudgetTransfer)
def Run_oracle_upload_journal_workflow(sender, instance, created, **kwargs):
    """
    Upload journal to Oracle when budget transfer is submitted
    Uses Celery for asynchronous processing (doesn't block the request)
    """
    try:
        # Only run for existing records (not newly created) when status changes to submitted
        if not created and instance.status == "submitted":
            print(
                "[DEBUG] Queueing Oracle upload journal workflow for transfer",
                instance.transaction_id,
            )
            
            # Check if code requires Oracle upload
            if instance.code and instance.code[0:3] == "FAR" or instance.code[0:3] == "HFR":
                # Queue the task in Celery (runs in background)
                upload_journal_to_oracle.delay(
                    transaction_id=instance.transaction_id,
                    entry_type="submit"
                )
                logger.info(
                    f"Oracle upload task queued for BudgetTransfer {instance.transaction_id}"
                )
            else:
                logger.info(
                    f"BudgetTransfer {instance.transaction_id} has DFR or AFR code, skipping Oracle journal upload"
                )
                
    except Exception as e:
        logger.error(
            f"Error queueing Oracle upload workflow for BudgetTransfer {instance.transaction_id}: {str(e)}"
        )




@receiver(post_save, sender=xx_BudgetTransfer)
def create_workflow_instance(sender, instance, created, **kwargs):
    print(
        "[DEBUG] post_save fired for transfer", instance.transaction_id, "created:", created
    )
    if created:
        ApprovalManager.create_instance(
            transfer_type=instance.type.upper(), budget_transfer=instance
        )
    else:
        if instance.status == "submitted":
            # ====== SECURITY GROUP VALIDATION ======
            # Require security group for workflow submission to ensure proper role-based filtering
            if not instance.security_group_id:
                print(f"[ERROR] Transfer {instance.code} cannot be submitted without a security group")
                instance.status = "pending"  # Keep as pending, don't start workflow
                instance.save(update_fields=["status"])
                # Note: This will silently fail. Consider raising ValidationError in the view instead.
                return

            recipient_ids = set()
            try:
                workflows = instance.workflow_instances.select_related("template").all()
                for workflow in workflows:
                    stages = workflow.template.stages.filter(
                        order_index__lt=ARCHIVED_STAGE_ORDER_INDEX_START
                    )
                    for stage in stages:
                        if stage.required_role:
                            role_group = stage.required_role.security_group
                            member_ids = (
                                XX_UserGroupMembership.objects.filter(
                                    security_group=role_group,
                                    is_active=True,
                                    assigned_roles=stage.required_role,
                                ).values_list("user_id", flat=True)
                            )
                        else:
                            member_ids = (
                                XX_UserGroupMembership.objects.filter(
                                    security_group=instance.security_group,
                                    is_active=True,
                                ).values_list("user_id", flat=True)
                            )
                        recipient_ids.update(member_ids)
            except Exception as e:
                logger.error(
                    f"Error collecting approval recipients for transfer {instance.transaction_id}: {str(e)}"
                )

            if getattr(instance, "user_id", None):
                recipient_ids.add(instance.user_id)

            if recipient_ids:
                eng_message = f"Transaction {instance.code} submitted for approval"
                ara_message = f"تم إرسال المعاملة {instance.code} للاعتماد"
                for user_id in recipient_ids:
                    action_type = "List" if user_id == instance.user_id else "Approval"
                    notification = xx_notification.objects.create(
                        user_id=user_id,
                        Transaction_id=instance.transaction_id,
                        type_of_Trasnction=instance.type,
                        Type_of_action=action_type,
                        eng_message=eng_message,
                        ara_message=ara_message,
                    )
                    send_generic_message(
                        user_id,
                        message=eng_message,
                        eng_message=eng_message,
                        ara_message=ara_message,
                        notification=notification,
                        data={
                            "transaction_id": instance.transaction_id,
                            "status": "submitted",
                            "code": instance.code,
                        },
                    )

            instance.status = "pending"
            instance.save(update_fields=["status"])
            ApprovalManager.start_workflow(
                transfer_type=instance.type.lower(), budget_transfer=instance
            )



