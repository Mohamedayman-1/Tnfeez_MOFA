# approval/managers.py

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from budget_management.models import xx_BudgetTransfer
from user_management.models import xx_User, xx_UserLevel
from .models import (
    ApprovalWorkflowTemplate,
    ApprovalWorkflowStageTemplate,
    ApprovalWorkflowInstance,
    ApprovalWorkflowStageInstance,
    ApprovalAssignment,
    ApprovalAction,
    ApprovalDelegation,
)

User = get_user_model()

ARCHIVED_STAGE_ORDER_INDEX_START = 9999


class ApprovalManager:
    """
    Central manager for dynamic approval workflows.
    Use these methods from your application layer.
    """

    # ----------------------
    # Helpers
    # ----------------------
    @staticmethod
    def _get_system_user():
        """
        Return a user to log system actions. Configure settings.APPROVAL_SYSTEM_USER_ID.
        Fallback to first superuser.
        """
        user_id = getattr(settings, "APPROVAL_SYSTEM_USER_ID", None)
        if user_id:
            try:
                return xx_User.objects.get(pk=user_id)
            except xx_User.DoesNotExist:
                pass

        # fallback: first superuser (if you have a flag). If your user model doesn't have is_superuser,
        # adjust accordingly.
        try:
            return (
                xx_User.objects.filter(is_superuser=True).first()
                or xx_User.objects.first()
            )
        except Exception:
            raise ValueError(
                "No system user available for logging approval system actions. "
                "Set settings.APPROVAL_SYSTEM_USER_ID."
            )

    # ----------------------
    # Create / start / restart / cancel
    # ----------------------
    @staticmethod
    def create_instance(
        budget_transfer: xx_BudgetTransfer, transfer_type: str = None
    ) -> list:
        """
        Create workflow instances based on the transfer's security group assignments.
        
        NEW BEHAVIOR (Phase 6):
        - Gets ALL workflow templates assigned to the transfer's security group
        - Creates one workflow instance per assignment, ordered by execution_order
        - Returns list of created instances (first one will be activated)
        
        Args:
            budget_transfer: The transfer to create workflows for
            transfer_type: Optional override for transfer type
        
        Returns:
            List of ApprovalWorkflowInstance objects (empty if no assignments found)
        """
        from .models import XX_WorkflowTemplateAssignment
        
        if not transfer_type:
            transfer_type = getattr(budget_transfer, "transfer_type", "GEN") or "GEN"
        
        # Check if transfer has security group
        if not budget_transfer.security_group_id:
            print(f"[WARNING] Transfer {budget_transfer.code} has no security group - no workflows created")
            return []
        
        # Get transaction code prefix (e.g., "FAR", "DFR")
        transaction_code_prefix = budget_transfer.code[:3] if budget_transfer.code and len(budget_transfer.code) >= 3 else None
        
        # Get all workflow template assignments for this security group
        # Filter by transaction_code_filter if specified
        from django.db.models import Q
        assignments = XX_WorkflowTemplateAssignment.objects.filter(
            security_group=budget_transfer.security_group,
            is_active=True
        ).filter(
            Q(transaction_code_filter__isnull=True) |  # No filter = applies to all
            Q(transaction_code_filter='') |  # Empty filter = applies to all
            Q(transaction_code_filter=transaction_code_prefix)  # Matches transaction code
        ).select_related('workflow_template').order_by('execution_order')
        
        if not assignments.exists():
            print(f"[WARNING] No workflow templates assigned to security group {budget_transfer.security_group.group_name} for transaction code {transaction_code_prefix}")
            return []
        
        print(f"[INFO] Found {assignments.count()} workflows for {budget_transfer.code} (prefix: {transaction_code_prefix})")
        
        created_instances = []
        # Re-number execution_order sequentially (1, 2, 3...) for this transaction code group
        for index, assignment in enumerate(assignments, start=1):
            template = assignment.workflow_template
            active_stage_templates = template.stages.filter(
                order_index__lt=ARCHIVED_STAGE_ORDER_INDEX_START
            )
            
            # Validate quorum config sanity
            for st in active_stage_templates:
                if (
                    st.decision_policy == ApprovalWorkflowStageTemplate.POLICY_QUORUM
                    and st.quorum_count
                ):
                    if st.quorum_count < 1:
                        raise ValueError(
                            f"Invalid quorum_count {st.quorum_count} on stage {st}"
                        )
            
            # Create workflow instance with sequential execution order (1, 2, 3 for this transaction code)
            instance = ApprovalWorkflowInstance.objects.create(
                budget_transfer=budget_transfer,
                template=template,
                workflow_assignment=assignment,
                execution_order=index,  # Sequential per transaction code: 1, 2, 3...
                status=ApprovalWorkflowInstance.STATUS_PENDING,
            )
            created_instances.append(instance)
            print(f"[INFO] Created workflow instance: {template.code} (Order: {index}, Filter: {assignment.transaction_code_filter or 'ALL'})")
        
        return created_instances

    @classmethod
    def start_workflow(
        cls, budget_transfer: xx_BudgetTransfer, transfer_type: str = None
    ) -> ApprovalWorkflowInstance:
        """
        Start workflow(s) for a transfer.
        
        NEW BEHAVIOR (Phase 6):
        - Creates ALL workflow instances if they don't exist
        - Activates ONLY the first workflow (execution_order=1)
        - Returns the first workflow instance
        """
        # Get or create workflow instances
        active_workflow = budget_transfer.workflow_instance  # Uses property to get active workflow
        
        if not active_workflow:
            # Create all workflow instances
            instances = cls.create_instance(budget_transfer, transfer_type)
            if not instances:
                raise ValueError(f"No workflow templates assigned to security group for transfer {budget_transfer.code}")
            
            # Get the first workflow (lowest execution_order)
            active_workflow = instances[0]
        
        # if pending -> activate first stage(s)
        if active_workflow.status == ApprovalWorkflowInstance.STATUS_PENDING:
            cls._activate_next_stage_internal(budget_transfer, instance=active_workflow)

        return active_workflow

    @classmethod
    def restart_workflow(
        cls, budget_transfer: xx_BudgetTransfer, transfer_type: str = None
    ) -> ApprovalWorkflowInstance:
        """
        Cancel current workflow instance and start a fresh one.
        """
        cls.cancel_workflow(budget_transfer, reason="Restarted by system/user")
        return cls.start_workflow(budget_transfer, transfer_type)

    @classmethod
    def cancel_workflow(
        cls, budget_transfer: xx_BudgetTransfer, reason: str = None
    ) -> ApprovalWorkflowInstance:
        instance = getattr(budget_transfer, "workflow_instance", None)
        if not instance:
            raise ValueError("No workflow instance found to cancel")

        if instance.status in [
            ApprovalWorkflowInstance.STATUS_APPROVED,
            ApprovalWorkflowInstance.STATUS_REJECTED,
            ApprovalWorkflowInstance.STATUS_CANCELLED,
        ]:
            return instance

        with transaction.atomic():
            active_stages = instance.stage_instances.filter(
                status=ApprovalWorkflowStageInstance.STATUS_ACTIVE
            )
            now = timezone.now()
            for stage in active_stages:
                stage.status = ApprovalWorkflowStageInstance.STATUS_CANCELLED
                stage.completed_at = now
                stage.save(update_fields=["status", "completed_at"])

                # deactivate any delegations for the stage
                stage.delegations.filter(active=True).update(
                    active=False, deactivated_at=now
                )

            instance.status = ApprovalWorkflowInstance.STATUS_CANCELLED
            instance.finished_at = now
            instance.current_stage_template = None
            instance.save(
                update_fields=["status", "finished_at", "current_stage_template"]
            )

            # log system comment action on first active stage or instance
            system_user = cls._get_system_user()
            if active_stages.exists():
                ApprovalAction.objects.create(
                    stage_instance=active_stages.first(),
                    user=system_user,
                    assignment=active_stages.first()
                    .assignments.filter(user=system_user)
                    .first(),
                    action=ApprovalAction.ACTION_REJECT,
                    comment=f"Workflow cancelled. Reason: {reason or 'No reason provided'}",
                    triggers_stage_completion=False,
                )

        return instance

    # ----------------------
    # Internal: activation & assignments
    # ----------------------
    @classmethod
    def _create_assignments(cls, stage_instance: ApprovalWorkflowStageInstance):
        """
        Create assignments based on stage template filters.
        
        NEW BEHAVIOR (Phase 6):
        - Gets security group from the transfer's workflow assignment (not from stage template)
        - Filters users by required_role (XX_SecurityGroupRole) within that security group
        - Stage template's security_group field is now ignored
        
        If no users found -> return empty list (caller should auto-skip).
        """
        from user_management.models import XX_UserGroupMembership, XX_SecurityGroupRole
        
        st = stage_instance.stage_template
        workflow_instance = stage_instance.workflow_instance
        budget_transfer = workflow_instance.budget_transfer
        
        # Get security group from the transfer (all workflows use the same group now)
        if not budget_transfer.security_group_id:
            print(f"[WARNING] Transfer {budget_transfer.code} has no security group - no assignments created")
            return []
        
        security_group = budget_transfer.security_group
        
        # Filter by required role if specified
        # required_role is FK to XX_SecurityGroupRole (group-specific role assignment)
        if st.required_role:
            # CRITICAL FIX: Use the role's security_group, NOT the transaction's security_group
            # This allows cross-group workflows (e.g., Finance Team transaction -> Fusion Team approvers)
            role_security_group = st.required_role.security_group
            
            print(f"\n=== DEBUG _create_assignments ===")
            print(f"Stage: {st.name} (ID: {st.id})")
            print(f"Transaction Security Group: {security_group.group_name}")
            print(f"Required Role: {st.required_role}")
            print(f"Role Security Group: {role_security_group.group_name}")
            
            # Get active members who have this specific role in the role's security group
            member_user_ids = XX_UserGroupMembership.objects.filter(
                security_group=role_security_group,  # Use role's security group
                is_active=True,
                assigned_roles=st.required_role  # Direct FK lookup
            ).values_list('user_id', flat=True)
            
            print(f"Users with required role in {role_security_group.group_name}: {list(member_user_ids)}")
            
        else:
            # No required role - use transaction's security group members
            print(f"\n=== DEBUG _create_assignments ===")
            print(f"Stage: {st.name} (ID: {st.id})")
            print(f"Security Group: {security_group.group_name}")
            print(f"Required Role: None - using all active members")
            
            member_user_ids = XX_UserGroupMembership.objects.filter(
                security_group=security_group,
                is_active=True
            ).values_list('user_id', flat=True)
        
        qs = xx_User.objects.filter(
            id__in=member_user_ids,
            is_active=True
        )
        
        print(f"Total users to assign: {qs.count()}")
        
        created = []
        for user in qs.distinct():
            print(f"Creating assignment for user: {user.username} (ID: {user.id})")
            obj, created_flag = ApprovalAssignment.objects.get_or_create(
                stage_instance=stage_instance,
                user=user,
                defaults={
                    "role_snapshot": getattr(user, "role", None),
                    "level_snapshot": getattr(user.user_level, "name", None) if user.user_level else None,
                    "is_mandatory": True,
                },
            )
            if created_flag:
                created.append(obj)
        
        print(f"Created {len(created)} new assignments")
        print("=== END DEBUG ===\n")
        
        if not created:
            role_group = st.required_role.security_group.group_name if st.required_role else security_group.group_name
            print(f"[WARNING] No users found for stage {st.name} with role {st.required_role} in group {role_group}")
        
        return created

    @classmethod
    def _activate_next_stage_internal(
        cls,
        budget_transfer: xx_BudgetTransfer,
        instance: ApprovalWorkflowInstance = None,
    ):
        """
        Core: activate the next set of stage_instances that share the lowest order_index
        greater than the current stage (or the first stage if none active).
        """
        if not instance:
            instance = getattr(budget_transfer, "workflow_instance", None)
            if not instance:
                raise ValueError("No workflow instance to progress")

        # Lock instance and its stage_instances
        with transaction.atomic():
            instance = ApprovalWorkflowInstance.objects.select_for_update().get(
                pk=instance.pk
            )
            active_stage_templates = instance.template.stages.filter(
                order_index__lt=ARCHIVED_STAGE_ORDER_INDEX_START
            )

            # prevent progressing finished workflows
            if instance.status in {
                ApprovalWorkflowInstance.STATUS_APPROVED,
                ApprovalWorkflowInstance.STATUS_REJECTED,
                ApprovalWorkflowInstance.STATUS_CANCELLED,
            }:
                return instance

            # find active stage(s)
            active = instance.stage_instances.filter(
                status=ApprovalWorkflowStageInstance.STATUS_ACTIVE
            )
            if not active.exists():
                # Did workflow ever start?
                completed = instance.stage_instances.filter(
                    status=ApprovalWorkflowStageInstance.STATUS_COMPLETED
                ).order_by("-stage_template__order_index")

                if completed.exists():
                    # continue after last completed
                    last_order = completed.first().stage_template.order_index
                    next_template = (
                        active_stage_templates.filter(order_index__gt=last_order)
                        .order_by("order_index")
                        .first()
                    )
                    if not next_template:
                        # no more stages -> mark workflow approved
                        instance.status = ApprovalWorkflowInstance.STATUS_APPROVED
                        instance.finished_at = timezone.now()
                        instance.current_stage_template = None
                        instance.save(
                            update_fields=[
                                "status",
                                "finished_at",
                                "current_stage_template",
                            ]
                        )
                        
                        # NEW: Check if there's a next workflow to start (Phase 6)
                        next_workflow = ApprovalWorkflowInstance.get_next_workflow(budget_transfer, instance)
                        if next_workflow:
                            print(f"[INFO] Workflow {instance.template.code} completed. Starting next workflow: {next_workflow.template.code}")
                            cls._activate_next_stage_internal(budget_transfer, instance=next_workflow)
                        else:
                            print(f"[INFO] All workflows completed for transfer {budget_transfer.code}")
                            
                            # Update budget transfer status to 'approved'
                            budget_transfer.status = 'approved'
                            budget_transfer.save(update_fields=['status'])
                            print(f"[INFO] Budget transfer {budget_transfer.code} status updated to 'approved'")
                            
                            # Trigger Oracle upload for approved workflows
                            from budget_management.tasks import upload_budget_to_oracle, upload_journal_to_oracle
                            
                            if budget_transfer.code and budget_transfer.code[0:3] != "HFR":
                                print(f"[INFO] Queuing budget upload task for transaction {budget_transfer.transaction_id}")
                                upload_budget_to_oracle.delay(
                                    transaction_id=budget_transfer.transaction_id,
                                    entry_type="Approve"
                                )
                            else:
                                print(f"[INFO] Skipping Oracle upload for HFR transaction {budget_transfer.code}")
                        
                        return instance
                    next_order = next_template.order_index
                else:
                    # truly first activation
                    next_template = active_stage_templates.order_by(
                        "order_index"
                    ).first()
                    if not next_template:
                        raise ValueError("Workflow template has no stages defined")
                    next_order = next_template.order_index
            else:
                # mark existing active as completed if they are "done"
                # (caller should have set them completed already; this path will just pick next order)
                current_order = active.first().stage_template.order_index
                next_q = (
                    active_stage_templates.filter(order_index__gt=current_order)
                    .order_by("order_index")
                    .first()
                )
                if not next_q:
                    # no more stages -> mark workflow approved
                    instance.status = ApprovalWorkflowInstance.STATUS_APPROVED
                    instance.finished_at = timezone.now()
                    instance.current_stage_template = None
                    instance.save(
                        update_fields=[
                            "status",
                            "finished_at",
                            "current_stage_template",
                        ]
                    )
                    
                    # NEW: Check if there's a next workflow to start (Phase 6)
                    next_workflow = ApprovalWorkflowInstance.get_next_workflow(budget_transfer, instance)
                    if next_workflow:
                        print(f"[INFO] Workflow {instance.template.code} completed. Starting next workflow: {next_workflow.template.code}")
                        cls._activate_next_stage_internal(budget_transfer, instance=next_workflow)
                    else:
                        print(f"[INFO] All workflows completed for transfer {budget_transfer.code}")
                        
                        # Update budget transfer status to 'approved'
                        budget_transfer.status = 'approved'
                        budget_transfer.save(update_fields=['status'])
                        print(f"[INFO] Budget transfer {budget_transfer.code} status updated to 'approved'")
                        
                        # Trigger Oracle upload for approved workflows
                        from budget_management.tasks import upload_budget_to_oracle, upload_journal_to_oracle
                        
                        if budget_transfer.code and budget_transfer.code[0:3] != "HFR":
                            print(f"[INFO] Queuing budget upload task for transaction {budget_transfer.transaction_id}")
                            upload_budget_to_oracle.delay(
                                transaction_id=budget_transfer.transaction_id,
                                entry_type="Approve"
                            )
                        else:
                            print(f"[INFO] Skipping Oracle upload for HFR transaction {budget_transfer.code}")
                    
                    return instance
                next_order = next_q.order_index

            # activate all stage templates with order_index == next_order
            next_templates = active_stage_templates.filter(
                order_index=next_order
            ).order_by("order_index")
            created_stage_instances = []
            now = timezone.now()
            for tpl in next_templates:
                si = ApprovalWorkflowStageInstance.objects.create(
                    workflow_instance=instance,
                    stage_template=tpl,
                    status=ApprovalWorkflowStageInstance.STATUS_ACTIVE,
                    activated_at=now,
                )
                created_stage_instances.append(si)
                # create assignments
                assignments = cls._create_assignments(si)
                # If no assignments created -> skip stage automatically
                if not assignments:
                    si.status = ApprovalWorkflowStageInstance.STATUS_SKIPPED
                    si.completed_at = timezone.now()
                    si.save(update_fields=["status", "completed_at"])
                    # also record system action
                    system_user = cls._get_system_user()
                    ApprovalAction.objects.create(
                        stage_instance=si,
                        user=system_user,
                        assignment=None,
                        action=ApprovalAction.ACTION_APPROVE,
                        comment="Stage auto-skipped: no eligible approvers.",
                        triggers_stage_completion=True,
                    )
                    # Deactivate any delegations if present (defensive)
                    si.delegations.filter(active=True).update(
                        active=False, deactivated_at=now
                    )
                    # Call hook
                    cls.on_stage_skipped(si)
                else:
                    # call hook for active stage (notifications)
                    cls.on_stage_activated(si)

            # set workflow instance status
            instance.status = ApprovalWorkflowInstance.STATUS_IN_PROGRESS
            # set current_stage_template to the first of activated templates for convenience
            instance.current_stage_template = (
                created_stage_instances[0].stage_template
                if created_stage_instances
                else None
            )
            instance.save(update_fields=["status", "current_stage_template"])
        return instance

    # ----------------------
    # Stage completion / evaluation
    # ----------------------
    @classmethod
    def check_finished_stage(cls, budget_transfer: xx_BudgetTransfer):
        """
        Evaluate active stage group (the lowest order_index active stages) and determine whether
        the collection is finished and the overall outcome.
        Returns: (is_finished_bool, outcome_str) where outcome_str in {"approved","rejected","pending"}
        """
        instance = getattr(budget_transfer, "workflow_instance", None)
        if not instance:
            raise ValueError("No workflow instance found")

        # lock active stages in transaction when caller wants to progress
        active_stages = instance.stage_instances.filter(
            status=ApprovalWorkflowStageInstance.STATUS_ACTIVE
        )
        if not active_stages.exists():
            return False, "pending"

        # Determine the order_index group to evaluate (lowest order_index among active)
        order_index = (
            active_stages.order_by("stage_template__order_index")
            .first()
            .stage_template.order_index
        )
        group_stages = instance.stage_instances.filter(
            status=ApprovalWorkflowStageInstance.STATUS_ACTIVE,
            stage_template__order_index=order_index,
        )

        any_rejected = False
        all_approved = True

        for stage in group_stages:
            stpl = stage.stage_template
            # short-circuit: if rejects exist and rejection allowed -> reject
            if (
                stpl.allow_reject
                and stage.actions.filter(action=ApprovalAction.ACTION_REJECT).exists()
            ):
                any_rejected = True
                continue

            # approvals count: consider distinct assignment ids
            approved_assignment_ids = (
                stage.actions.filter(action=ApprovalAction.ACTION_APPROVE)
                .values_list("assignment_id", flat=True)
                .distinct()
            )
            approved_count = len([x for x in approved_assignment_ids if x])

            total_assignments = stage.assignments.count()

            if stpl.decision_policy == ApprovalWorkflowStageTemplate.POLICY_ALL:
                # require all assignments to have approved (ignoring delegated mandatory? we treat delegated assignment as assigned person)
                all_ids = set(stage.assignments.values_list("id", flat=True))
                if set(approved_assignment_ids) != all_ids:
                    all_approved = False

            elif stpl.decision_policy == ApprovalWorkflowStageTemplate.POLICY_ANY:
                if approved_count < 1:
                    all_approved = False

            elif stpl.decision_policy == ApprovalWorkflowStageTemplate.POLICY_QUORUM:
                quorum = stpl.quorum_count or max(1, total_assignments // 2 + 1)
                if approved_count < quorum:
                    all_approved = False
                # validate quorum does not exceed total assignments
                if stpl.quorum_count and stpl.quorum_count > max(1, total_assignments):
                    # misconfigured: treat as impossible to approve -> mark not finished
                    all_approved = False

            else:
                if approved_count < 1:
                    all_approved = False

        if any_rejected:
            return True, "rejected"
        if all_approved:
            return True, "approved"
        return False, "pending"

    @classmethod
    def _complete_active_stage_group(
        cls, instance: ApprovalWorkflowInstance, outcome: str, comment: str = None
    ):
        """
        Mark active group (lowest order_index) as completed/skipped according to outcome,
        deactivate delegations, log actions and invoke hooks.
        """
        active_stages = instance.stage_instances.filter(
            status=ApprovalWorkflowStageInstance.STATUS_ACTIVE
        )
        if not active_stages.exists():
            return

        order_index = (
            active_stages.order_by("stage_template__order_index")
            .first()
            .stage_template.order_index
        )
        group_stages = instance.stage_instances.filter(
            status=ApprovalWorkflowStageInstance.STATUS_ACTIVE,
            stage_template__order_index=order_index,
        )
        now = timezone.now()
        system_user = cls._get_system_user()

        if outcome == "approved":
            for st in group_stages:
                st.status = ApprovalWorkflowStageInstance.STATUS_COMPLETED
                st.completed_at = now
                st.save(update_fields=["status", "completed_at"])
                # deactivate delegations for stage
                st.delegations.filter(active=True).update(
                    active=False, deactivated_at=now
                )
                # delete any remaining pending assignments on this completed stage
                st.assignments.filter(status=ApprovalAssignment.STATUS_PENDING).delete()
                # call hook
                cls.on_stage_completed(st)
                # optionally log system action (not necessary if user actions recorded)
        elif outcome == "rejected":
            for st in group_stages:
                st.status = ApprovalWorkflowStageInstance.STATUS_COMPLETED
                st.completed_at = now
                st.save(update_fields=["status", "completed_at"])
                st.delegations.filter(active=True).update(
                    active=False, deactivated_at=now
                )
                # delete any remaining pending assignments on this completed stage
                st.assignments.filter(status=ApprovalAssignment.STATUS_PENDING).delete()
                cls.on_stage_completed(st)
            # mark workflow rejected
            instance.status = ApprovalWorkflowInstance.STATUS_REJECTED
            instance.finished_at = now
            instance.current_stage_template = None
            instance.save(
                update_fields=["status", "finished_at", "current_stage_template"]
            )
            # log system action
            ApprovalAction.objects.create(
                stage_instance=group_stages.first(),
                user=system_user,
                assignment=None,
                action=ApprovalAction.ACTION_REJECT,
                comment=comment or "Workflow rejected",
                triggers_stage_completion=True,
            )

    # ----------------------
    # Manager-facing action processing
    # ----------------------
    @classmethod
    def process_action(
        cls,
        budget_transfer: xx_BudgetTransfer,
        user: xx_User,
        action: str,
        comment: str = None,
        target_user: xx_User = None,
    ):
        """
        Unified entry point for user actions:
         - Approve
         - Reject
         - Delegate (requires target_user)
         - Comment (action == "comment")
        """
        instance = getattr(budget_transfer, "workflow_instance", None)
        if not instance:
            raise ValueError("No workflow instance found for this transfer")

        with transaction.atomic():
            instance = ApprovalWorkflowInstance.objects.select_for_update().get(
                pk=instance.pk
            )

            active_stage = instance.stage_instances.filter(
                status=ApprovalWorkflowStageInstance.STATUS_ACTIVE
            ).first()
            if not active_stage:
                raise ValueError("No active stage to act on")

            assignment = active_stage.assignments.filter(user=user).first()
            if not assignment:
                # user may be acting because of delegation: check active delegations pointing to this user
                # If user has an assignment by delegation it should already exist; else reject.
                raise ValueError(f"User {user} has no assignment in this active stage")

            if action not in {
                ApprovalAction.ACTION_APPROVE,
                ApprovalAction.ACTION_REJECT,
                ApprovalAction.ACTION_DELEGATE,
            }:
                raise ValueError(f"Invalid action: {action}")

            # enforce policies
            if (
                action == ApprovalAction.ACTION_REJECT
                and not active_stage.stage_template.allow_reject
            ):
                raise ValueError("Rejection not allowed in this stage")
            if (
                action == ApprovalAction.ACTION_DELEGATE
                and not active_stage.stage_template.allow_delegate
            ):
                raise ValueError("Delegation not allowed in this stage")

            # prevent duplicate approve/reject by same user for stage
            if action in {ApprovalAction.ACTION_APPROVE, ApprovalAction.ACTION_REJECT}:
                existing = ApprovalAction.objects.filter(
                    stage_instance=active_stage,
                    user=user,
                    action__in=[
                        ApprovalAction.ACTION_APPROVE,
                        ApprovalAction.ACTION_REJECT,
                    ],
                    comment=comment,
                ).first()
                if existing:
                    raise ValueError(
                        f"User {user} already submitted action {existing.action} for this stage"
                    )

            # perform action
            if action == ApprovalAction.ACTION_DELEGATE:
                if not target_user:
                    raise ValueError("Delegation requires target_user parameter")
                # call dedicated delegate routine (ensures validations & atomic)
                cls.delegate(user, target_user, active_stage, comment=comment)
                return instance

            # create log action
            ApprovalAction.objects.create(
                stage_instance=active_stage,
                user=user,
                assignment=assignment,
                action=action,
                comment=comment,
                triggers_stage_completion=False,
            )

            # update assignment status if approve/reject
            if action in (ApprovalAction.ACTION_APPROVE, ApprovalAction.ACTION_REJECT):
                assignment.status = action
                assignment.save(update_fields=["status"])

            # Evaluate whether stage group has finished
            finished, outcome = cls.check_finished_stage(budget_transfer)
            if finished:
                # mark stage(s) complete and progress
                cls._complete_active_stage_group(instance, outcome, comment=comment)
                if outcome == "approved":
                    # progress to next stage(s)
                    cls._activate_next_stage_internal(
                        budget_transfer, instance=instance
                    )
                # If rejected: _complete_active_stage_group already marked workflow rejected
            else:
                # still pending; maybe call hooks
                pass

        return instance

    # ----------------------
    # Delegation
    # ----------------------
    @classmethod
    def delegate(
        cls,
        from_user: xx_User,
        to_user: xx_User,
        stage_instance: ApprovalWorkflowStageInstance,
        comment: str = None,
    ):
        """
        Perform safe delegation:
          - validate stage allows delegation
          - from_user must have pending assignment
          - to_user must not already be involved
          - create ApprovalDelegation + assignment for delegate
          - mark original assignment delegated
        """
        if not stage_instance.stage_template.allow_delegate:
            raise ValueError("Delegation not allowed in this stage")

        with transaction.atomic():
            from_assignment = (
                stage_instance.assignments.filter(user=from_user)
                .select_for_update()
                .first()
            )
            if not from_assignment:
                raise ValueError(f"{from_user} has no assignment in this stage")
            if from_assignment.status != ApprovalAssignment.STATUS_PENDING:
                raise ValueError("Assignment already processed")

            existing_assignment = stage_instance.assignments.filter(
                user=to_user
            ).first()
            existing_delegation = ApprovalDelegation.objects.filter(
                to_user=to_user, stage_instance=stage_instance, active=True
            ).first()
            if existing_assignment or existing_delegation:
                raise ValueError("Target user already involved in this stage")

            # create delegation record
            delegation = ApprovalDelegation.objects.create(
                from_user=from_user,
                to_user=to_user,
                stage_instance=stage_instance,
                active=True,
            )

            # create assignment for delegate
            delegate_assignment = ApprovalAssignment.objects.create(
                stage_instance=stage_instance,
                user=to_user,
                role_snapshot=getattr(to_user, "role", None),
                level_snapshot=getattr(to_user.user_level, "name", None),
                is_mandatory=from_assignment.is_mandatory,
                status=ApprovalAssignment.STATUS_PENDING,
            )

            # update original assignment
            from_assignment.status = ApprovalAssignment.STATUS_DELEGATED
            from_assignment.save(update_fields=["status"])

            # log delegation action
            ApprovalAction.objects.create(
                stage_instance=stage_instance,
                user=from_user,
                assignment=from_assignment,
                action=ApprovalAction.ACTION_DELEGATE,
                comment=comment or f"Delegated to {to_user}",
                triggers_stage_completion=False,
            )

        return delegation

    # ----------------------
    # Utility / queries
    # ----------------------
    @staticmethod
    def get_user_pending_approvals(user: xx_User):
        """
        Return list of BudgetTransfer objects for which this user
        has pending approval assignments in active workflow stages.
        
        NEW BEHAVIOR (Phase 6):
        - Uses workflow_instances (ForeignKey) instead of workflow_instance (OneToOneField)
        - Filters by user's role matching the stage's required_role
        """
        base_qs = xx_BudgetTransfer.objects.filter(
            workflow_instances__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
        ).distinct()
        print(f"Total transfers in queryset: {base_qs.count()}")

        # Pre-user filter: active stages with any pending assignments
        transfers = base_qs.filter(
            workflow_instances__stage_instances__status=ApprovalWorkflowStageInstance.STATUS_ACTIVE,
            workflow_instances__stage_instances__assignments__status=ApprovalAssignment.STATUS_PENDING,
        ).distinct()
        print(f"Transfers with active stages: {transfers.count()}")
        print(f"Transfers with pending assignments: {transfers.count()}")
        try:
            pre_ids = list(transfers.values_list("id", flat=True))
        except Exception:
            pre_ids = []
        # Debug: list stages and assignments (with users) before filtering by user
        try:
            print("Debug: Active stages and assignments for current transfers (before user filter):")
            for tr in transfers:
                wi = getattr(tr, "workflow_instance", None)
                wi_id = getattr(wi, "id", None)
                tr_id = getattr(tr, "id", getattr(tr, "pk", "?"))
                print(f"- Transfer {tr_id}, WorkflowInstance {wi_id}")
                if not wi:
                    continue
                stages_qs = wi.stage_instances.filter(
                    status=ApprovalWorkflowStageInstance.STATUS_ACTIVE
                )
                for stg in stages_qs:
                    stg_id = getattr(stg, "id", getattr(stg, "pk", "?"))
                    tpl_name = getattr(getattr(stg, "stage_template", None), "name", "<no tpl>")
                    print(f"  Stage {stg_id} ({tpl_name}) status={stg.status}")
                    for asg in stg.assignments.all():
                        asg_id = getattr(asg, "id", getattr(asg, "pk", "?"))
                        asg_user = getattr(asg, "user", None)
                        asg_user_id = getattr(asg_user, "id", getattr(asg_user, "pk", None))
                        asg_user_name = None
                        try:
                            asg_user_name = str(asg_user)
                        except Exception:
                            asg_user_name = f"<user {asg_user_id}>"
                        print(
                            f"    Assignment {asg_id}: user={asg_user_name} (id={asg_user_id}) status={asg.status}"
                        )
        except Exception as e:
            print(f"Debug listing error: {e}")
        # IMPORTANT: Anchor user+pending to the SAME active stage instance.
        # Using the assignment's stage_instance relation avoids mixing conditions
        # across different stages in the same workflow.
        # NEW: Uses workflow_instances (ForeignKey) instead of workflow_instance
        transfers = base_qs.filter(
            workflow_instances__stage_instances__assignments__user=user,
            workflow_instances__stage_instances__assignments__status=ApprovalAssignment.STATUS_PENDING,
            workflow_instances__stage_instances__assignments__stage_instance__status=ApprovalWorkflowStageInstance.STATUS_ACTIVE,
        ).distinct()
        print(
            f"Transfers with active pending assignment for user {user}: {transfers.count()}"
        )
        try:
            post_ids = list(transfers.values_list("id", flat=True))
            excluded = sorted(set(pre_ids) - set(post_ids))
            if excluded:
                print(
                    f"Transfers excluded after anchoring to user's active pending assignment: {excluded}"
                )
        except Exception:
            pass

        # Extra debug: list the exact assignment(s) for this user in active stages
        try:
            user_asgs = ApprovalAssignment.objects.filter(
                user=user,
                status=ApprovalAssignment.STATUS_PENDING,
                stage_instance__status=ApprovalWorkflowStageInstance.STATUS_ACTIVE,
                stage_instance__workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS,
                stage_instance__workflow_instance__budget_transfer__in=transfers,
            ).select_related(
                "stage_instance__workflow_instance",
                "stage_instance__stage_template",
            )[:100]  # Limit for debug output
            print(
                f"Debug: Active PENDING assignments for user {user} that drive the final result: {user_asgs.count()}"
            )
            for asg in user_asgs:
                tr_id = getattr(
                    getattr(asg.stage_instance.workflow_instance, "budget_transfer", None),
                    "id",
                    None,
                )
                stg = asg.stage_instance
                tpl_name = getattr(stg.stage_template, "name", "<no tpl>")
                print(
                    f"  -> Transfer {tr_id}, Stage {stg.id} ({tpl_name}), assignment {asg.id}, status={asg.status}"
                )
        except Exception as e:
            print(f"Debug (user assignments) listing error: {e}")

        return transfers

    @staticmethod
    def is_workflow_finished(budget_transfer: xx_BudgetTransfer):
        """
        Check if the entire workflow instance for a transfer is finished.
        Returns: (is_finished_bool, status_str)
        status_str in {"approved", "rejected", "cancelled", "pending", "in_progress"}
        """
        instance = getattr(budget_transfer, "workflow_instance", None)
        if not instance:
            return False, "no_instance"

        if instance.status in {
            ApprovalWorkflowInstance.STATUS_APPROVED,
            ApprovalWorkflowInstance.STATUS_REJECTED,
            ApprovalWorkflowInstance.STATUS_CANCELLED,
        }:
            return True, instance.status.lower()

        return False, instance.status.lower()

    # ----------------------
    # Hooks (override or attach listeners)
    # ----------------------
    @staticmethod
    def on_stage_activated(stage_instance: ApprovalWorkflowStageInstance):
        """
        Hook: called when a stage is activated (assignments created).
        Use this to send notifications / create SLA timers.
        """
        # Example: create SLA timer, send notifications
        pass

    @staticmethod
    def on_stage_completed(stage_instance: ApprovalWorkflowStageInstance):
        """
        Hook: called when a stage is completed.
        """
        pass

    @staticmethod
    def on_stage_skipped(stage_instance: ApprovalWorkflowStageInstance):
        """
        Hook: called when a stage was auto-skipped because no assignees were eligible.
        """
        pass

    @staticmethod
    def on_sla_breached(stage_instance: ApprovalWorkflowStageInstance):
        """
        Hook: SLA breached - escalate/auto-approve as per business rules.
        """
        pass
