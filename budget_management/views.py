from datetime import time
from decimal import Decimal
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q, Sum
from django.db.models.functions import Cast, Coalesce
from django.db.models import CharField
from approvals.managers import ApprovalManager
from approvals.models import ApprovalAction, ApprovalWorkflowInstance
from budget_management.tasks import upload_budget_to_oracle, upload_journal_to_oracle
from oracle_fbdi_integration.utilities.automatic_posting import submit_automatic_posting
from oracle_fbdi_integration.utilities.Status import wait_for_job
from oracle_fbdi_integration.utilities.journal_integration import create_and_upload_journal
from oracle_fbdi_integration.utilities.budget_integration import create_and_upload_budget

from user_management.models import xx_User, xx_notification, XX_UserGroupMembership
from .models import (
    filter_budget_transfers_all_in_entities,
    xx_BudgetTransfer,
    xx_BudgetTransferAttachment,
    xx_BudgetTransferRejectReason,
    xx_budget_integration_audit,
    xx_DashboardBudgetTransfer,
)
from account_and_entitys.models import XX_PivotFund, XX_Entity, XX_Account
from transaction.models import xx_TransactionTransfer
from .serializers import BudgetIntegrationAuditSerializer, BudgetTransferSerializer
from user_management.permissions import IsAdmin, CanTransferBudget
from budget_transfer.global_function.dashbaord import (
    get_all_dashboard_data,
    get_approval_rate_change,
    get_saved_dashboard_data,
    refresh_dashboard_data,
)
from public_funtion.update_pivot_fund import update_pivot_fund
import base64
from django.db.models.functions import Cast
from django.db.models import CharField
from collections import defaultdict
from django.db.models import Prefetch
from collections import defaultdict
from decimal import Decimal
import time
import multiprocessing
from itertools import islice
from decimal import Decimal
import multiprocessing
from collections import defaultdict
from decimal import Decimal
import time
from itertools import islice
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import rest_framework
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Count, Case, When, Value, F
from oracle_fbdi_integration.utilities.journal_integration import create_and_upload_journal
from oracle_fbdi_integration.utilities.budget_integration import create_and_upload_budget
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from budget_management.models import xx_BudgetTransfer
from budget_management.serializers import BudgetTransferSerializer

# Initialize logger
logger = logging.getLogger(__name__)


class TransferPagination(PageNumberPagination):
    """Pagination class for budget transfers"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CreateBudgetTransferView(APIView):
    """Create budget transfers"""

    permission_classes = [IsAuthenticated]

    def post(self, request):

        if not request.data.get("transaction_date") or not request.data.get("notes"):
            return Response(
                {
                    "message": "Transaction date and notes are required fields.",
                    "errors": {
                        "transaction_date": (
                            "This field is required."
                            if not request.data.get("transaction_date")
                            else None
                        ),
                        "notes": (
                            "This field is required."
                            if not request.data.get("notes")
                            else None
                        ),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        linked_budget_transfer = request.data.get("source_transaction_id")
        budget=None
        transfers=None
        if linked_budget_transfer:
             budget=xx_BudgetTransfer.objects.filter(transaction_id=linked_budget_transfer).first()
             if budget:
                    linked_budget_transfer=budget.transaction_id
                    transfers=xx_TransactionTransfer.objects.filter(transaction_id=budget.transaction_id)
                 
                 


        type = request.data.get("type").upper()
        transfer_control_budget = request.data.get("budget_control", "")
        transfer_type=request.data.get("transfer_type","")

        if type in ["FAR", "AFR", "FAD", "DFR","HFR"]:
            prefix = f"{type}-"
        else:

            prefix = "FAR-"

        last_transfer = (
            xx_BudgetTransfer.objects.filter(code__startswith=prefix)
            .order_by("-code")
            .first()
        )

        if last_transfer and last_transfer.code:
            try:
                last_num = int(last_transfer.code.replace(prefix, ""))
                new_num = last_num + 1
            except (ValueError, AttributeError):

                new_num = 1
        else:

            new_num = 1

        new_code = f"{prefix}{new_num:04d}"

        serializer = BudgetTransferSerializer(data=request.data)

        if serializer.is_valid():
            # ====== AUTO-ASSIGN SECURITY GROUP ======
            # Automatically assign security group based on user's membership
            # If user belongs to multiple groups, use the first active one (or allow user to specify)
            from user_management.models import XX_UserGroupMembership
            
            # Check if user explicitly provided security_group in request
            security_group_id = request.data.get('security_group')
            
            if not security_group_id:
                # Auto-assign from user's first active security group
                user_membership = XX_UserGroupMembership.objects.filter(
                    user=request.user,
                    is_active=True
                ).first()
                
                if user_membership:
                    security_group_id = user_membership.security_group_id
                    print(f"[AUTO-ASSIGN] Setting security_group_id={security_group_id} for user {request.user.username}")
                else:
                    print(f"[WARNING] User {request.user.username} has no active security group membership")

            transfer = serializer.save(
                requested_by=request.user.username,
                user_id=request.user.id,
                status="pending",
                request_date=timezone.now(),
                code=new_code,
                control_budget=transfer_control_budget,
                transfer_type=transfer_type,
                linked_transfer_id=linked_budget_transfer,
                security_group_id=security_group_id
            )
            if linked_budget_transfer:
                from account_and_entitys.models import XX_TransactionSegment
                
                # ========== HFR AUTO-CALCULATION LOGIC ==========
                # If source is HFR, calculate remaining hold and adjust amounts automatically
                hfr_remaining = Decimal('0.00')
                is_hfr_source = budget and budget.code and budget.code[0:3] == "HFR"
                
                if is_hfr_source:
                    # Get HFR original hold amount (total from_center)
                    hfr_transfers = xx_TransactionTransfer.objects.filter(transaction_id=linked_budget_transfer)
                    hfr_original_hold = sum(
                        Decimal(str(t.from_center)) if t.from_center else Decimal('0.00')
                        for t in hfr_transfers
                    )
                    
                    # Find all FAR transfers already linked to this HFR
                    linked_fars = xx_BudgetTransfer.objects.filter(
                        linked_transfer_id=linked_budget_transfer,
                        code__startswith="FAR"
                    )
                    
                    # Calculate total already used
                    total_used = sum(
                        Decimal(str(far.amount)) if far.amount else Decimal('0.00')
                        for far in linked_fars
                    )
                    
                    # Calculate remaining in HFR hold
                    hfr_remaining = hfr_original_hold - total_used
                    
                    print(f"🔍 HFR Auto-Calculation:")
                    print(f"   Original Hold: {hfr_original_hold}")
                    print(f"   Already Used: {total_used}")
                    print(f"   Remaining: {hfr_remaining}")
                
                for transfer_item in transfers:
                    # Determine the actual amounts to use based on HFR remaining
                    from_center_amount = transfer_item.from_center
                    to_center_amount = transfer_item.to_center
                    
                    if is_hfr_source and from_center_amount:
                        # User is taking from HFR hold
                        requested_amount = Decimal(str(from_center_amount))
                        
                        if requested_amount <= hfr_remaining:
                            # Scenario 1: Requested amount fits within HFR hold
                            # Use only from HFR (no change needed)
                            from_center_amount = requested_amount
                            print(f"   ✅ Using {requested_amount} from HFR hold (sufficient)")
                        else:
                            # Scenario 2: Requested amount > HFR remaining
                            # This will be handled by taking remaining from HFR + rest from fund
                            # The "rest from fund" happens automatically via available budget
                            from_center_amount = requested_amount
                            extra_needed = requested_amount - hfr_remaining
                            print(f"   ⚠️  Requested {requested_amount} > Remaining {hfr_remaining}")
                            print(f"   📊 Will use {hfr_remaining} from HFR + {extra_needed} from available fund")
                    
                    # Create new transaction transfer with calculated amounts
                    new_transfer = xx_TransactionTransfer.objects.create(
                        transaction=transfer,
                        from_center=from_center_amount,
                        to_center=to_center_amount,
                        reason=transfer_item.reason,
                        account_code=transfer_item.account_code,
                        account_name=transfer_item.account_name,
                        project_code=transfer_item.project_code,
                        project_name=transfer_item.project_name,
                        cost_center_code=transfer_item.cost_center_code,
                        cost_center_name=transfer_item.cost_center_name,
                    )
                    
                    # Copy transaction segments (from and to)
                    source_segments = XX_TransactionSegment.objects.filter(
                        transaction_transfer=transfer_item
                    ).select_related('segment_type', 'segment_value', 'from_segment_value', 'to_segment_value')
                    
                    for segment in source_segments:
                        XX_TransactionSegment.objects.create(
                            transaction_transfer=new_transfer,
                            segment_type=segment.segment_type,
                            segment_value=segment.segment_value,
                            from_segment_value=segment.from_segment_value,
                            to_segment_value=segment.to_segment_value,
                        )
            Notification_object = xx_notification.objects.create(
                user_id=request.user.id,
                message=f"New budget transfer request created with code {new_code}",
            )
            Notification_object.save()
            return Response(
                {
                    "message": "Budget transfer request created successfully.",
                    "data": BudgetTransferSerializer(transfer).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListBudgetTransferView(APIView):
    """List budget transfers with pagination"""

    permission_classes = [IsAuthenticated]
    pagination_class = TransferPagination

    def get(self, request):
        status_type = request.query_params.get("status_type", None)
        search = request.query_params.get("search")
        day = request.query_params.get("day")
        month = request.query_params.get("month")
        year = request.query_params.get("year")
        sdate = request.query_params.get("start_date")
        edate = request.query_params.get("end_date")
        code = request.query_params.get("code", None)
        print( f"code value: {code} ({type(code)})")

        # ====== SECURITY GROUP FILTERING ======
        user = request.user
        
        # SuperAdmin bypasses all security group checks
        user_memberships = None
        print(user.role)
        if user.role == "superadmin":
            user_approval_groups = None  # None = see all groups
        else:
            # Check if user has approval permissions
            from user_management.models import XX_UserGroupMembership
            
            # Get user's security group memberships with approval access
            # Check custom_abilities or role's default_abilities for 'APPROVE'
            user_memberships = XX_UserGroupMembership.objects.filter(
                user=user,
                is_active=True
            ).prefetch_related('assigned_roles')
            
            user_approval_groups = []
            for membership in user_memberships:
                # Check custom_abilities first
                if membership.custom_abilities and 'TRANSFER' in membership.custom_abilities:
                    user_approval_groups.append(membership.security_group_id)
                    continue
                
                # Check role's default_abilities
                for role in membership.assigned_roles.all():
                    if role.is_active and role.default_abilities and 'TRANSFER' in role.default_abilities:
                        user_approval_groups.append(membership.security_group_id)
                        break
            
            if not user_approval_groups:
                # User has no approval access in any security group
                print(f"DEBUG: User {user.username} (ID: {user.id}) has no TRANSFER permissions")
                print(f"DEBUG: User memberships: {user_memberships.count()}")
                for membership in user_memberships:
                    print(f"  - Group: {membership.security_group.group_name}")
                    print(f"    Custom abilities: {membership.custom_abilities}")
                    for role in membership.assigned_roles.all():
                        print(f"    Role: {role.role.name}, Active: {role.is_active}, Abilities: {role.default_abilities}")

                return Response(
                    {
                        "success": False,
                        "status":rest_framework.status.HTTP_403_FORBIDDEN,
                        "error": "ACCESS_DENIED",
                        "message": "You do not have approval permissions. Please contact your administrator to grant you approval access in a security group.",
                        "details": "Your account is not assigned to any security group with approval permissions.",
                        "results": []
                        
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Filter transactions to only those in user's security groups OR with no security group restriction
            transfers = xx_BudgetTransfer.objects.filter(
                Q(security_group_id__in=user_approval_groups) | Q(security_group__isnull=True)
            )
        
        # Apply user restriction if not admin
        if not IsAdmin().has_permission(request, self):
            transfers = transfers.filter(user_id=request.user.id)
        else:
            transfers=xx_BudgetTransfer.objects.all()
        # Apply status restriction
        if status_type:
            if status_type == "finished":
                transfers = transfers.filter(
                    Q(status="approved") | Q(status="rejected")
                )
            else:
                transfers = transfers.filter(status=status_type)
        # print(type(code))

        if code:
            # Coerce to string first and use upper() to avoid errors if a non-string is provided
            code_upper = code.upper()
            transfers = transfers.filter(type=code_upper)

        if request.user.abilities_legacy.count() > 0:
            transfers = filter_budget_transfers_all_in_entities(
                budget_transfers=transfers, user=request.user, Type="edit"
            )

        # Free-text search across common fields (icontains)
        if search:
            s = str(search).strip()
            query = (
                Q(code__icontains=s)
                | Q(requested_by__icontains=s)
                | Q(status__icontains=s)
                | Q(transaction_date__icontains=s)
                | Q(type__icontains=s)
            )
            if s.isdigit():
                # Support numeric search on transaction_id
                try:
                    query |= Q(transaction_id=int(s))
                except Exception:
                    pass
            transfers = transfers.filter(query)

        try:
            from datetime import datetime as _dt

            def _validate(fmt, value):
                try:
                    _dt.strptime(value, fmt)
                    return True
                except Exception:
                    return False

            if day:
                if not _validate("%Y-%m-%d", day):
                    return Response(
                        {"error": "Invalid day format. Use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                transfers = transfers.filter(request_date__startswith=day)
            elif month:
                mval = str(month)
                prefix = None
                if _validate("%Y-%m", mval):
                    prefix = mval
                else:
                    if year:
                        try:
                            yi = int(year)
                            mi = int(mval)
                            if 1 <= mi <= 12 and 1900 <= yi <= 2100:
                                prefix = f"{yi}-{mi:02d}"
                        except Exception:
                            pass
                if not prefix:
                    return Response(
                        {
                            "error": "Invalid month. Provide YYYY-MM or month with 'year'"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                transfers = transfers.filter(request_date__startswith=prefix)
            elif year:
                try:
                    yi = int(year)
                    if yi < 1900 or yi > 2100:
                        raise ValueError()
                except Exception:
                    return Response(
                        {"error": "Invalid year. Use YYYY in range 1900-2100"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                transfers = transfers.filter(request_date__startswith=f"{int(year)}-")
            elif sdate and edate:
                sd = str(sdate)
                ed = str(edate)
                if not (_validate("%Y-%m-%d", sd) and _validate("%Y-%m-%d", ed)):
                    return Response(
                        {
                            "error": "Invalid date range. Use YYYY-MM-DD for start_date and end_date"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if sd > ed:
                    sd, ed = ed, sd
                transfers = transfers.filter(request_date__gte=sd, request_date__lte=ed)
        except Exception as _date_err:
            return Response(
                {"error": f"Failed to apply date filter: {_date_err}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Use only safe fields for ordering to avoid Oracle NCLOB issues
        transfers = transfers.order_by("-transaction_id")

        # Ensure we return the workflow instance status (if any) in the `status` column.
        # If no workflow instance exists, fall back to the transfer's own status.
        # Phase 6: Get active workflow (lowest execution_order with active status)
        # Annotate under a different name to avoid conflict with the model's `status` field
        from django.db.models import Subquery, OuterRef
        active_workflow_status = ApprovalWorkflowInstance.objects.filter(
            budget_transfer_id=OuterRef('transaction_id'),
            status__in=['pending', 'in_progress']
        ).order_by('execution_order').values('status')[:1]
        
        transfers = transfers.annotate(
            workflow_status=Coalesce(Subquery(active_workflow_status), F("status"))
        )

        # Convert to list to avoid lazy evaluation issues with Oracle
        # Exclude TextField columns that become NCLOB in Oracle
        transfer_list = list(
            transfers.values(
                "transaction_id",
                "transaction_date",
                "amount",
                "workflow_status",
                "requested_by",
                "user_id",
                "request_date",
                "code",
                "status_level",
                "attachment",
                "report",
                "type",
                "notes",
                "transfer_type",
                "control_budget"
            )
        )

        # Convert DB rows to a list and then map `workflow_status` -> `status`
        transfer_list = list(transfer_list)
        for row in transfer_list:
            # Prefer the workflow_status annotation, fall back to existing status if present
            row["status"] = row.pop("workflow_status", row.get("status"))
            
            transaction_id = row.get("transaction_id")
            
            # ========== Get Approval Actions (Reasons/Comments) ==========
            approval_actions = []
            try:
                # Get active workflow instance for this transaction (Phase 6: get lowest execution_order active workflow)
                workflow_instance = ApprovalWorkflowInstance.objects.filter(
                    budget_transfer_id=transaction_id,
                    status__in=['pending', 'in_progress', 'approved', 'rejected']
                ).order_by('execution_order').first()
                
                if workflow_instance:
                    # Get all stage instances for this workflow
                    stage_instances = workflow_instance.stage_instances.all()
                    
                    # Get only reject actions from all stages
                    for stage_instance in stage_instances:
                        actions = stage_instance.actions.filter(action='reject').select_related('user').order_by('created_at')
                        
                        for action in actions:
                            approval_actions.append({
                                "action": action.action,
                                "comment": action.comment,
                                "user": action.user.username if action.user else "System",
                                "user_id": action.user.id if action.user else None,
                                "stage_name": stage_instance.stage.name if stage_instance.stage else None,
                                "stage_order": stage_instance.stage.order if stage_instance.stage else None,
                                "created_at": action.created_at.strftime('%Y-%m-%d %H:%M:%S') if action.created_at else None
                            })
                    
                    print(f"Transaction {transaction_id}: Found {len(approval_actions)} approval actions from {stage_instances.count()} stages")
                else:
                    print(f"Transaction {transaction_id}: No workflow instance found")
                    
                # Fallback: Check legacy reject reasons table
                if not approval_actions:
                    reject_reasons = xx_BudgetTransferRejectReason.objects.filter(
                        Transcation_id=transaction_id  # Note: Field name has typo in model
                    ).order_by('-reject_date')
                    
                    if reject_reasons.exists():
                        print(f"Transaction {transaction_id}: Found {reject_reasons.count()} legacy reject reasons")
                        for reason in reject_reasons:
                            approval_actions.append({
                                "action": "reject",
                                "comment": reason.reason_text,
                                "user": reason.reject_by if hasattr(reason, 'reject_by') else "Unknown",
                                "user_id": None,
                                "stage_name": "Legacy Rejection",
                                "stage_order": None,
                                "created_at": reason.reject_date.strftime('%Y-%m-%d %H:%M:%S') if hasattr(reason, 'reject_date') and reason.reject_date else None
                            })
                        
            except Exception as e:
                print(f"Error fetching approval actions for transaction {transaction_id}: {e}")
                import traceback
                traceback.print_exc()
            
            row["approval_actions"] = approval_actions
            
            # ========== HFR-Specific: Add hold availability flags ==========
            if row.get("type") == "HFR":
                transaction_id = row.get("transaction_id")
                
                # Calculate HFR hold status
                hfr_transfers = xx_TransactionTransfer.objects.filter(transaction_id=transaction_id)
                original_hold = sum(
                    Decimal(str(t.from_center)) if t.from_center else Decimal('0.00')
                    for t in hfr_transfers
                )
                
                # Find all FAR transfers linked to this HFR that are IN PROGRESS or APPROVED
                # Only count FARs that have been submitted (status_level >= 2) or approved
                linked_fars = xx_BudgetTransfer.objects.filter(
                    linked_transfer_id=transaction_id,
                    code__startswith="FAR"
                ).filter(
                    Q(status="approved") | Q(status_level__gte=2)  # In progress (submitted) or approved
                ).exclude(
                    status_level__lt=1  # Exclude rejected (status_level < 1)
                )
                
                # Calculate total used by summing actual transfer amounts (from_center) from linked FARs
                total_used = Decimal('0.00')
                for far in linked_fars:
                    # Get the actual transfers for this FAR and sum their from_center values
                    far_transfers = xx_TransactionTransfer.objects.filter(transaction_id=far.transaction_id)
                    far_total = sum(
                        Decimal(str(t.from_center)) if t.from_center else Decimal('0.00')
                        for t in far_transfers
                    )
                    total_used += far_total
                
                remaining = original_hold - total_used
                
                # Add HFR flags to the row
                row["hfr_original_hold"] = float(original_hold)
                row["hfr_total_used"] = float(total_used)
                row["hfr_remaining"] = float(remaining)
                row["hfr_has_remaining"] = remaining > 0  # True = show buttons, False = hide/disable
                row["hfr_is_fully_used"] = remaining <= 0  # True = all used, False = still available
                row["hfr_linked_far_count"] = linked_fars.count()

        # Manual pagination to avoid Oracle issues
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        paginated_data = transfer_list[start_idx:end_idx]

        return Response(
            {
                "results": paginated_data,
                "count": len(transfer_list),
                "next": (
                    f"?page={page + 1}&page_size={page_size}"
                    if end_idx < len(transfer_list)
                    else None
                ),
                "previous": (
                    f"?page={page - 1}&page_size={page_size}" if page > 1 else None
                ),
            }
        )


class ListBudgetTransfer_approvels_View(APIView):
    """List budget transfers with two lists: pending and history (approved/rejected)"""

    permission_classes = [IsAuthenticated]
    pagination_class = TransferPagination

    def get(self, request):
        code = request.query_params.get("code", None)
        date = request.data.get("date", None)
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)
        status_filter = request.query_params.get("status", None)

        if code is None:
            code = "FAR"
        
        # ====== SECURITY GROUP & APPROVAL PERMISSION CHECK ======
        user = request.user
        
        # SuperAdmin bypasses all security group checks
        user_memberships = None
        if user.role == 1:
            user_approval_groups = None  # None = see all groups
        else:
            # Check if user has approval permissions
            from user_management.models import XX_UserGroupMembership
            
            # Get user's security group memberships with approval access
            # Check custom_abilities or role's default_abilities for 'APPROVE'
            user_memberships = XX_UserGroupMembership.objects.filter(
                user=user,
                is_active=True
            ).prefetch_related('assigned_roles')
            
            user_approval_groups = []
            for membership in user_memberships:
                # Check custom_abilities first
                if membership.custom_abilities and 'APPROVE' in membership.custom_abilities:
                    user_approval_groups.append(membership.security_group_id)
                    continue
                
                # Check role's default_abilities
                for role in membership.assigned_roles.all():
                    if role.is_active and role.default_abilities and 'APPROVE' in role.default_abilities:
                        user_approval_groups.append(membership.security_group_id)
                        break
            
            if not user_approval_groups:
                # User has no approval access in any security group
                print(f"DEBUG: User {user.username} (ID: {user.id}) has no APPROVE permissions")
                print(f"DEBUG: User memberships: {user_memberships.count()}")
                for membership in user_memberships:
                    print(f"  - Group: {membership.security_group.group_name}")
                    print(f"    Custom abilities: {membership.custom_abilities}")
                    for role in membership.assigned_roles.all():
                        print(f"    Role: {role.role.name}, Active: {role.is_active}, Abilities: {role.default_abilities}")
                
                return Response(
                    {
                        "success": False,
                        "error": "ACCESS_DENIED",
                        "status":rest_framework.status.HTTP_403_FORBIDDEN,
                        "message": "You do not have approval permissions. Please contact your administrator to grant you approval access in a security group.",
                        "details": "Your account is not assigned to any security group with approval permissions.",
                        "results": []
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Initialize combined data list
        all_data = []
        
        # If status filter is "pending" or None, include pending transfers
        if status_filter in [None, "pending"]:
            # Get pending transfers for this user (already filtered by ApprovalManager)
            # This returns transfers where user has pending assignments in active stages
            pending_transfers = ApprovalManager.get_user_pending_approvals(request.user)
            
            # Additional filter: only transfers from user's approval security groups (skip for SuperAdmin)
            if user_approval_groups is not None:
                # Further filter: user must be assigned to stages that match their role in security group
                from approvals.models import ApprovalWorkflowStageInstance, ApprovalAssignment
                
                # Get user's roles in each security group
                user_roles_by_group = {}
                if user_memberships:
                    for membership in user_memberships:
                        group_id = membership.security_group_id
                        user_roles_by_group[group_id] = list(
                            membership.assigned_roles.values_list('role_id', flat=True)
                        )
                
                # Build list of transfer IDs where user has pending assignments
                # Note: We don't filter by transfer.security_group_id here because multi-stage
                # workflows may have stages requiring different security groups than the transfer's
                # origin group. The workflow system handles proper assignment validation.
                valid_transfer_ids = []
                print(f"\n=== DEBUG: Assignment filtering for user {user.username} ===")
                
                for transfer in pending_transfers:
                    workflow_instance = getattr(transfer, 'workflow_instance', None)
                    if not workflow_instance:
                        continue
                    
                    print(f"\n--- Transfer {transfer.code} (ID: {transfer.transaction_id}) ---")
                    
                    # Get user's active pending assignments for this transfer
                    user_assignments = ApprovalAssignment.objects.filter(
                        user=request.user,
                        status=ApprovalAssignment.STATUS_PENDING,
                        stage_instance__workflow_instance__id=workflow_instance.id,
                        stage_instance__status=ApprovalWorkflowStageInstance.STATUS_ACTIVE
                    ).select_related('stage_instance__stage_template')
                    
                    print(f"User has {user_assignments.count()} pending assignments for this transfer")
                    
                    # If user has any pending assignments for this transfer, they can see it
                    if user_assignments.exists():
                        print(f"  ✅ User has pending assignment - ALLOWED")
                        valid_transfer_ids.append(transfer.transaction_id)
                
                print(f"\n=== Valid transfer IDs after assignment check: {valid_transfer_ids} ===\n")
                
                # Filter to only valid transfers
                pending_transfers = pending_transfers.filter(transaction_id__in=valid_transfer_ids)
            else:
                # SuperAdmin: apply basic security group filter
                pending_transfers = pending_transfers.filter(
                    Q(security_group_id__isnull=True) | Q(security_group__isnull=False)
                )

            if request.user.abilities_legacy.count() > 0:
                pending_transfers = filter_budget_transfers_all_in_entities(
                    pending_transfers, request.user, "approve"
                )

            if code:
                pending_transfers = pending_transfers.filter(code__icontains=code)

            pending_transfers = pending_transfers.order_by("-request_date")

            # Serialize pending transfers
            pending_serializer = BudgetTransferSerializer(pending_transfers, many=True)
            for item in pending_serializer.data:
                filtered_item = {
                    "transaction_id": item.get("transaction_id"),
                    "amount": item.get("amount"),
                    "status": item.get("status"),
                    "status_level": item.get("status_level"),
                    "requested_by": item.get("requested_by"),
                    "request_date": item.get("request_date"),
                    "code": item.get("code"),
                    "transaction_date": item.get("transaction_date"),
                    "category": "pending"  # Add category identifier
                }
                all_data.append(filtered_item)

        # If status filter is "history" or None, include history transfers
        if status_filter in [None, "history"]:
            # Get history transfers (approved or rejected) that were assigned to this user
            from approvals.models import ApprovalAction, ApprovalWorkflowStageInstance, ApprovalAssignment
            
            # Additional filter: only transfers from user's approval security groups (skip for SuperAdmin)
            if user_approval_groups is not None:
                # Get user's roles in each security group
                user_roles_by_group = {}
                if user_memberships:
                    for membership in user_memberships:
                        group_id = membership.security_group_id
                        user_roles_by_group[group_id] = list(
                            membership.assigned_roles.values_list('role_id', flat=True)
                        )
                
                # Get all assignments for this user where they participated
                user_assignments = ApprovalAssignment.objects.filter(
                    user=request.user
                ).exclude(
                    status=ApprovalAssignment.STATUS_PENDING
                ).select_related(
                    'stage_instance__workflow_instance__budget_transfer',
                    'stage_instance__stage_template'
                )
                
                # Filter assignments where user's role matched the stage requirement
                valid_transfer_ids = []
                for assignment in user_assignments:
                    transfer = assignment.stage_instance.workflow_instance.budget_transfer
                    
                    # Only include finished transfers
                    if transfer.status not in ["approved", "rejected"]:
                        continue
                    
                    transfer_group_id = transfer.security_group_id
                    
                    # Check if transfer belongs to user's security groups
                    if transfer_group_id not in user_approval_groups and transfer_group_id is not None:
                        continue
                    
                    # User was assigned to this transfer - they can see it in history
                    valid_transfer_ids.append(transfer.transaction_id)
                
                # Get unique transfer IDs
                valid_transfer_ids = list(set(valid_transfer_ids))
                
                # Get the budget transfers
                history_transfers = xx_BudgetTransfer.objects.filter(
                    transaction_id__in=valid_transfer_ids
                ).filter(
                    Q(status="approved") | Q(status="rejected")
                )
            else:
                # SuperAdmin: get all history where user was assigned
                user_stage_instances = ApprovalWorkflowStageInstance.objects.filter(
                    assignments__user=request.user
                ).values_list('workflow_instance__budget_transfer__transaction_id', flat=True)

                history_transfers = xx_BudgetTransfer.objects.filter(
                    transaction_id__in=user_stage_instances
                ).filter(
                    Q(status="approved") | Q(status="rejected")
                )

            if request.user.abilities_legacy.count() > 0:
                history_transfers = filter_budget_transfers_all_in_entities(
                    history_transfers, request.user, "approve"
                )

            if code:
                history_transfers = history_transfers.filter(code__icontains=code)

            history_transfers = history_transfers.order_by("-request_date")

            # Serialize history transfers
            history_serializer = BudgetTransferSerializer(history_transfers, many=True)
            for item in history_serializer.data:
                filtered_item = {
                    "transaction_id": item.get("transaction_id"),
                    "amount": item.get("amount"),
                    "status": item.get("status"),
                    "status_level": item.get("status_level"),
                    "requested_by": item.get("requested_by"),
                    "request_date": item.get("request_date"),
                    "code": item.get("code"),
                    "transaction_date": item.get("transaction_date"),
                    "category": "history"  # Add category identifier
                }
                all_data.append(filtered_item)

        return Response({"results": all_data}, status=status.HTTP_200_OK)


class ApproveBudgetTransferView(APIView):
    """Approve or reject budget transfer requests (admin only)"""

    permission_classes = [IsAuthenticated, IsAdmin]

    def put(self, request, transfer_id):
        try:
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)

            if transfer.status != "pending":
                return Response(
                    {"message": f"This transfer has already been {transfer.status}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            action = request.data.get("action")

            if action not in ["approve", "reject"]:
                return Response(
                    {"message": 'Invalid action. Use "approve" or "reject".'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            transfer.status = "approved" if action == "approve" else "rejected"

            current_level = transfer.status_level or 0
            next_level = current_level + 1

            if next_level <= 4:
                setattr(transfer, f"approvel_{next_level}", request.user.username)
                setattr(transfer, f"approvel_{next_level}_date", timezone.now())
                transfer.status_level = next_level

            transfer.save()

            return Response(
                {
                    "message": f"Budget transfer {transfer.status}.",
                    "data": BudgetTransferSerializer(transfer).data,
                }
            )

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"message": "Transfer not found."}, status=status.HTTP_404_NOT_FOUND
            )


class GetBudgetTransferView(APIView):
    """Get a specific budget transfer by ID"""

    permission_classes = [IsAuthenticated]

    def get(self, request, transfer_id):
        try:
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)

            # Check permissions: admin can see all, users can only see their own
            # if request.user.role != 'admin' and transfer.user_id != request.user.id:
            #     return Response(
            #         {'message': 'You do not have permission to view this transfer.'},
            #         status=status.HTTP_403_FORBIDDEN
            #     )
            # serializer = BudgetTransferSerializer(transfer)
            # return Response(serializer.data)
            data = {
                "transaction_id": transfer.transaction_id,
                "amount": transfer.amount,
                "status": transfer.status,
                "requested_by": transfer.requested_by,
                "description": transfer.notes,
            }

            return Response(data)

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"message": "Transfer not found."}, status=status.HTTP_404_NOT_FOUND
            )


class UpdateBudgetTransferView(APIView):
    """Update a budget transfer"""

    permission_classes = [IsAuthenticated]

    def put(self, request, transfer_id):
        try:
            # Fetch by URL parameter
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)

            # Only pending transfers can be updated
            if transfer.status != "pending":
                return Response(
                    {
                        "message": f'Cannot update transfer with status "{transfer.status}". '
                        f"Only pending transfers can be updated."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Permission check
            if (
                not getattr(request.user, "role", None) == "admin"
                and transfer.user_id != request.user.id
            ):
                return Response(
                    {"message": "You do not have permission to update this transfer."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Allow only specific fields to be updated
            allowed_fields = {
                "notes",
                "description_x",
                "amount",
                "transaction_date",
                "security_group",
                "transfer_type",
                "control_budget",
            }
            update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
            if "budget_control" in request.data and "control_budget" not in update_data:
                update_data["control_budget"] = request.data.get("budget_control")

            if not update_data:
                return Response(
                    {"message": "No valid fields to update."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Use serializer for validation + saving
            serializer = BudgetTransferSerializer(
                transfer, data=update_data, partial=True
            )

            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "message": "Budget transfer updated successfully.",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"message": "Transfer not found."}, status=status.HTTP_404_NOT_FOUND
            )


class DeleteBudgetTransferView(APIView):
    """Delete a specific budget transfer by ID"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, transfer_id):
        try:
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)

            if transfer.status != "pending":
                return Response(
                    {
                        "message": f'Cannot delete transfer with status "{transfer.status}". Only pending transfers can be deleted.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if request.user.role != "admin" and transfer.user_id != request.user.id:
                return Response(
                    {"message": "You do not have permission to delete this transfer."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            transfer_code = transfer.code
            transfer.delete()

            return Response(
                {"message": f"Budget transfer {transfer_code} deleted successfully."},
                status=status.HTTP_200_OK,
            )

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"message": "Transfer not found."}, status=status.HTTP_404_NOT_FOUND
            )


class transcationtransferapprovel_reject(APIView):
    """Submit ADJD transaction transfers for approval"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if we received valid data
        if not request.data:
            return Response(
                {
                    "error": "Empty data provided",
                    "message": "Please provide at least one transaction ID",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Convert single item to list for consistent handling
        items_to_process = []

        # Map new format (single object with arrays) to old format (array of individual objects)
        if isinstance(request.data, dict) and all(
            isinstance(v, list) for v in request.data.values()
        ):
            transaction_ids = request.data.get("transaction_id", [])
            decide = (
                request.data.get("decide", [])[0]
                if request.data.get("decide")
                else None
            )
            reason = (
                request.data.get("reason", [])[0]
                if request.data.get("reason")
                else None
            )
            other_user_id = (
                request.data.get("other_user_id", [])[0]
                if request.data.get("other_user_id")
                else None
            )

            # Create an object for each transaction_id
            for tid in transaction_ids:
                item = {
                    "transaction_id": [str(tid)],
                    "decide": [decide] if decide else None,
                }
                if reason:
                    item["reason"] = [reason]
                if other_user_id:
                    item["other_user_id"] = [str(other_user_id)]
                items_to_process.append(item)
        elif isinstance(request.data, list):
            items_to_process = request.data
        else:
            # Handle single transaction case
            items_to_process = [request.data]
        results = []
        OtherUser = None
        reson = None
        # Process each transaction
        for item in items_to_process:
            transaction_id = item.get("transaction_id")[0]
            decide = item.get("decide")[0]
            if item.get("reason") is not None and len(item.get("reason")) > 0:
                reson = item.get("reason")[0]
            if (
                item.get("other_user_id") is not None
                and len(item.get("other_user_id")) > 0
            ):
                OtherUserId = item.get("other_user_id")[0]

            # Validate required fields
            if not transaction_id:
                return Response(
                    {
                        "error": "transaction id is required",
                        "message": "Please provide transaction id",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if decide not in dict(ApprovalAction.ACTION_CHOICES):
                return Response(
                    {
                        "error": "Invalid decision value",
                        "message": "Decision value must be One from "
                        + str(ApprovalAction.ACTION_CHOICES),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if decide == ApprovalAction.ACTION_REJECT and not reson:
                return Response(
                    {
                        "error": "Reason is required for rejection",
                        "message": "Please provide a reason for rejection",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if decide == ApprovalAction.ACTION_DELEGATE:
                if not OtherUserId:
                    return Response(
                        {
                            "error": "Other user is required for delegation",
                            "message": "Please provide a user to delegate the approval to",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                elif not xx_User.objects.filter(id=OtherUserId).exists():
                    return Response(
                        {
                            "error": "Selected user does not exist",
                            "message": "Please select a valid user for delegation",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                else:
                    OtherUser = xx_User.objects.get(id=OtherUserId)
                    if not OtherUser.is_active:
                        return Response(
                            {
                                "error": "Selected user is inactive",
                                "message": "Please select an active user for delegation",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
            try:
                # Get the transfer record - use get() for single record
                trasncation = xx_BudgetTransfer.objects.get(
                    transaction_id=transaction_id
                )
                ApprovalManager.process_action(
                    trasncation,
                    request.user,
                    decide,
                    comment=reson,
                    target_user=OtherUser,
                )
                # Update pivot fund if final approval or rejection
                trasncation = xx_BudgetTransfer.objects.get(
                    transaction_id=transaction_id
                )
                
                isFinal, Status = ApprovalManager.is_workflow_finished(trasncation)
                if isFinal:
                    trasfers = xx_TransactionTransfer.objects.filter(
                        transaction_id=transaction_id
                    )
                    # for transfer in trasfers:
                    try:
                        # Update the pivot fund
                        if trasncation.code[0:3] != "HFR":

                            if Status == "approved":
                                # Queue background task for Oracle upload
                                print(f"Queuing budget upload task for transaction {transaction_id}")
                                upload_budget_to_oracle.delay(
                                    transaction_id=transaction_id,
                                    entry_type="Approve"
                                )
                                results.append({
                                    "transaction_id": transaction_id,
                                    "status": "success",
                                    "message": "Transaction approved successfully"
                                })
                            
                            if Status == "rejected":
                                print(f"Queuing journal upload task for transaction {transaction_id}")
                                upload_journal_to_oracle.delay(
                                    transaction_id=transaction_id,
                                    entry_type="reject"
                                )
                                results.append({
                                    "transaction_id": transaction_id,
                                    "status": "success",
                                    "message": "Transaction rejected successfully"
                                })
                        
                        # ========== HFR REJECTION LOGIC ==========
                        # For HFR: When rejected, return remaining unused amount to Oracle
                        elif trasncation.code[0:3] == "HFR":
                            if Status == "rejected":
                                # Calculate remaining unused amount
                                hfr_transfers = xx_TransactionTransfer.objects.filter(transaction_id=transaction_id)
                                original_hold = sum(
                                    Decimal(str(t.from_center)) if t.from_center else Decimal('0.00')
                                    for t in hfr_transfers
                                )
                                
                                # Find all approved/in-progress FAR transfers linked to this HFR
                                linked_fars = xx_BudgetTransfer.objects.filter(
                                    linked_transfer_id=transaction_id,
                                    code__startswith="FAR"
                                ).filter(
                                    Q(status="approved") | Q(status_level__gte=2)
                                ).exclude(
                                    status_level__lt=1
                                )
                                
                                total_used = Decimal('0.00')
                                for far in linked_fars:
                                    far_transfers = xx_TransactionTransfer.objects.filter(transaction_id=far.transaction_id)
                                    far_total = sum(
                                        Decimal(str(t.from_center)) if t.from_center else Decimal('0.00')
                                        for t in far_transfers
                                    )
                                    total_used += far_total
                                
                                remaining = original_hold - total_used
                                
                                print(f"🔴 HFR REJECTION: Transaction {transaction_id}")
                                print(f"   Original Hold: {original_hold}")
                                print(f"   Already Used: {total_used}")
                                print(f"   Remaining to Return: {remaining}")
                                
                                # Only upload journal if there's remaining amount to return
                                if remaining > 0:
                                    print(f"Queuing journal upload for HFR rejection (returning {remaining})")
                                    upload_journal_to_oracle.delay(
                                        transaction_id=transaction_id,
                                        entry_type="reject"
                                    )
                                    results.append({
                                        "transaction_id": transaction_id,
                                        "status": "success",
                                        "message": f"HFR rejected - returning {float(remaining):,.2f} to fund"
                                    })
                                else:
                                    print(f"No remaining amount to return (fully used)")
                                    results.append({
                                        "transaction_id": transaction_id,
                                        "status": "success",
                                        "message": "HFR rejected - hold was fully used, no amount to return"
                                    })
                            elif Status == "approved":
                                # HFR approved - no Oracle action needed (hold remains active)
                                results.append({
                                    "transaction_id": transaction_id,
                                    "status": "success",
                                    "message": "HFR approved - hold is now active"
                                })
                    
                    except Exception as e:
                        results.append(
                            {
                                "transaction_id": transaction_id,
                                "status": "error",
                                "message": str(e),
                            }
                        )

                        # Add the result for this transaction
                    
                    trasncation.save()
            except xx_BudgetTransfer.DoesNotExist:
                results.append(
                    {
                        "transaction_id": transaction_id,
                        "status": "error",
                        "message": f"Budget transfer not found",
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "transaction_id": transaction_id,
                        "status": "error",
                        "message": str(e),
                    }
                )
        return Response(
            {"message": "Transfers processed", "results": results},
            status=status.HTTP_200_OK,
        )


class BudgetTransferFileUploadView(APIView):
    """Upload files for a budget transfer and store as BLOBs"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Check if the transfer exists
            transaction_id = request.data.get("transaction_id")
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)
            if transfer.status != "pending":
                return Response(
                    {
                        "message": f'Cannot upload files for transfer with status "{transfer.status}". Only pending transfers can have files uploaded.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if any files were provided
            if not request.FILES:
                return Response(
                    {
                        "error": "No files provided",
                        "message": "Please upload at least one file",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Process each uploaded file
            uploaded_files = []
            for file_key, uploaded_file in request.FILES.items():
                # Read the file data
                file_data = uploaded_file.read()

                # Create the attachment record
                attachment = xx_BudgetTransferAttachment.objects.create(
                    budget_transfer=transfer,
                    file_name=uploaded_file.name,
                    file_type=uploaded_file.content_type,
                    file_size=len(file_data),
                    file_data=file_data,
                )

                uploaded_files.append(
                    {
                        "attachment_id": attachment.attachment_id,
                        "file_name": attachment.file_name,
                        "file_type": attachment.file_type,
                        "file_size": attachment.file_size,
                        "upload_date": attachment.upload_date,
                    }
                )

            # Update the attachment flag on the budget transfer
            transfer.attachment = "Yes"
            transfer.save()

            return Response(
                {
                    "message": f"{len(uploaded_files)} files uploaded successfully",
                    "files": uploaded_files,
                },
                status=status.HTTP_201_CREATED,
            )

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {
                    "error": "Budget transfer not found",
                    "message": f"No budget transfer found with ID: {transaction_id}",
                },
                status=status.HTTP_404_NOT_FOUND,
            )


class DeleteBudgetTransferAttachmentView(APIView):
    """Delete a specific file attachment from a budget transfer"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, transfer_id, attachment_id):
        try:
            # First, check if the budget transfer exists
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)
            if transfer.status != "pending":
                return Response(
                    {
                        "message": f'Cannot upload files for transfer with status "{transfer.status}". Only pending transfers can have files uploaded.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if user has permission to modify this transfer
            if not request.user.role == "admin" and transfer.user_id != request.user.id:
                return Response(
                    {
                        "message": "You do not have permission to modify attachments for this transfer."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Check if transfer is in editable state
            if transfer.status != "pending":
                return Response(
                    {
                        "message": f'Cannot modify attachments for transfer with status "{transfer.status}". Only pending transfers can be modified.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Find the specific attachment
            try:
                attachment = xx_BudgetTransferAttachment.objects.get(
                    attachment_id=attachment_id, budget_transfer=transfer
                )

                # Keep attachment details for response
                attachment_details = {
                    "attachment_id": attachment.attachment_id,
                    "file_name": attachment.file_name,
                }

                # Delete the attachment
                attachment.delete()

                # Check if this was the last attachment for this transfer
                remaining_attachments = xx_BudgetTransferAttachment.objects.filter(
                    budget_transfer=transfer
                ).exists()
                if not remaining_attachments:
                    transfer.attachment = "No"
                    transfer.save()

                return Response(
                    {
                        "message": f'File "{attachment_details["file_name"]}" deleted successfully',
                        "attachment_id": attachment_details["attachment_id"],
                    },
                    status=status.HTTP_200_OK,
                )

            except xx_BudgetTransferAttachment.DoesNotExist:
                return Response(
                    {
                        "error": "Attachment not found",
                        "message": f"No attachment found with ID {attachment_id} for this transfer",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {
                    "error": "Budget transfer not found",
                    "message": f"No budget transfer found with ID: {transfer_id}",
                },
                status=status.HTTP_404_NOT_FOUND,
            )


class ListBudgetTransferAttachmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:

            transfer_id = request.query_params.get("transaction_id")
            # Retrieve the main budget transfer record
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)

            # Fetch related attachments
            attachments = xx_BudgetTransferAttachment.objects.filter(
                budget_transfer=transfer
            )

            # Build a simplified response
            data = []
            for attach in attachments:
                encoded_data = base64.b64encode(attach.file_data).decode("utf-8")
                data.append(
                    {
                        "attachment_id": attach.attachment_id,
                        "file_name": attach.file_name,
                        "file_type": attach.file_type,
                        "file_size": attach.file_size,
                        "file_data": encoded_data,  # base64-encoded
                        "upload_date": attach.upload_date,
                    }
                )

            return Response(
                {"transaction_id": transfer_id, "attachments": data},
                status=status.HTTP_200_OK,
            )
        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"error": "Transfer not found"}, status=status.HTTP_404_NOT_FOUND
            )


class list_budget_transfer_reject_reason(APIView):
    """List all budget transfer reject reasons"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            reasons = xx_BudgetTransferRejectReason.objects.filter(
                Transcation_id=request.query_params.get("transaction_id")
            )
            data = []
            for reason in reasons:
                data.append(
                    {
                        "transaction_id": reason.Transcation_id.transaction_id,
                        "reason_text": reason.reason_text,
                        "created_at": reason.reject_date,
                        "rejected by": reason.reject_by,
                    }
                )
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StaticDashboardView(APIView):
    """Optimized dashboard view for encrypted budget transfers"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get dashboard type from query params (default to 'smart')
            dashboard_type = request.query_params.get("type", "smart")

            # Check if user wants to force refresh
            force_refresh = (
                request.query_params.get("refresh", "false").lower() == "true"
            )

            if force_refresh:
                # Only refresh when explicitly requested
                data = refresh_dashboard_data(dashboard_type)
                if data:
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"error": "Failed to refresh dashboard data"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:
                # Always try to get existing cached data first
                if dashboard_type == "all":
                    # Get all dashboard data (both smart and normal)
                    data = get_all_dashboard_data()
                    if data:
                        return Response(data, status=status.HTTP_200_OK)
                    else:
                        # Return empty structure if no data exists yet
                        return Response(
                            {
                                "message": "No dashboard data available yet. Data will be generated in background.",
                                "data": {},
                            },
                            status=status.HTTP_200_OK,
                        )
                else:
                    # Get specific dashboard type (smart or normal)
                    data = get_saved_dashboard_data(dashboard_type)
                    if data:
                        return Response(data, status=status.HTTP_200_OK)
                    else:
                        # Return message if no cached data exists
                        return Response(
                            {
                                "message": f"No {dashboard_type} dashboard data available yet. Data will be generated in background.",
                                "data": {},
                            },
                            status=status.HTTP_200_OK,
                        )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DashboardBudgetTransferView(APIView):
    """Optimized dashboard view for encrypted budget transfers"""

    permission_classes = [IsAuthenticated]

    def get(self, request):

        try:
            # Get dashboard type from query params (default to 'smart')

            return_data = {}
            dashboard_type = request.query_params.get("type", "smart")
            force_refresh = (
                request.query_params.get("refresh", "false").lower() == "true"
            )

            DashBoard_filler_per_Project = request.query_params.get(
                "DashBoard_filler_per_Project", None
            )

            start_time = time.time()
            print("Starting optimized normal dashboard calculation...")

            # PHASE 1: Database-level counting and aggregations
            count_start = time.time()

            # Get all transfers with minimal data loading
            transfers_queryset = xx_BudgetTransfer.objects.only(
                "code", "status", "status_level", "request_date", "transaction_date","security_group", "requested_by"
            )
            
            # PHASE 6: Filter by security group membership
            # Show transfers where user's security group matches transfer's security group
            # This allows:
            # 1. Creators (planners) - see all transfers from their group
            # 2. Approvers (managers) - see all transfers they need to approve in their group
            # 3. SuperAdmin - sees all transfers
            
            # Check if user is SuperAdmin (role=1)
            if request.user.role == 1:
                # SuperAdmin sees all transfers
                print(f"User {request.user.username} is SuperAdmin - showing all transfers")
            else:
                # Get all security groups user belongs to
                user_security_group_ids = XX_UserGroupMembership.objects.filter(
                    user=request.user,
                    is_active=True
                ).values_list('security_group_id', flat=True)
                
                if user_security_group_ids:
                    # Show all transfers from user's security groups
                    transfers_queryset = transfers_queryset.filter(
                        security_group_id__in=user_security_group_ids
                    )
                    print(f"User {request.user.username} sees transfers from {len(user_security_group_ids)} security group(s)")
                else:
                    # User not in any security group - no transfers visible
                    transfers_queryset = transfers_queryset.none()
                    print(f"User {request.user.username} has no security group membership")
            
            print(f"Transfers after filtering: {transfers_queryset.count()}")
           


            if dashboard_type == "normal" or dashboard_type == "all":
                # Use database aggregations for counting
                try:

                    total_count = transfers_queryset.count()

                    # Count by status using database aggregation
                    status_counts = transfers_queryset.aggregate(
                        approved=Count("transaction_id", filter=Q(status="approved")),
                        rejected=Count("transaction_id", filter=Q(status="rejected")),
                        pending=Count("transaction_id", filter=Q(status="pending")),
                    )

                    # Count by status level using database aggregation
                    level_counts = transfers_queryset.aggregate(
                        level1=Count("transaction_id", filter=Q(status_level=1)),
                        level2=Count("transaction_id", filter=Q(status_level=2)),
                        level3=Count("transaction_id", filter=Q(status_level=3)),
                        level4=Count("transaction_id", filter=Q(status_level=4)),
                    )

                    # Count by code prefix using database functions
                    code_counts = transfers_queryset.aggregate(
                        far=Count("transaction_id", filter=Q(code__istartswith="FAR")),
                        afr=Count("transaction_id", filter=Q(code__istartswith="AFR")),
                        fad=Count("transaction_id", filter=Q(code__istartswith="FAD")),
                    )

                    # Get request dates efficiently (only non-null dates)
                    request_dates = list(
                        transfers_queryset.filter(request_date__isnull=False)
                        .values_list("request_date", flat=True)
                        .order_by("-request_date")[
                            :1000
                        ]  # Limit to recent 1000 for performance
                    )

                    # Convert datetime objects to ISO format strings for JSON serialization
                    request_dates_iso = [date.isoformat() for date in request_dates]

                    # NEW: Approval rate analysis (last vs current month)
                    approval_rate_data = get_approval_rate_change(transfers_queryset)

                    print(
                        f"Database counting completed in {time.time() - count_start:.2f}s"
                    )

                    # PHASE 2: Format response data
                    data = {
                        "total_transfers": total_count,
                        "total_transfers_far": code_counts["far"],
                        "total_transfers_afr": code_counts["afr"],
                        "total_transfers_fad": code_counts["fad"],
                        "approved_transfers": status_counts["approved"],
                        "rejected_transfers": status_counts["rejected"],
                        "pending_transfers": status_counts["pending"],
                        "pending_transfers_by_level": {
                            "Level1": level_counts["level1"],
                            "Level2": level_counts["level2"],
                            "Level3": level_counts["level3"],
                            "Level4": level_counts["level4"],
                        },
                        "request_dates": request_dates_iso,
                        "approval_rate_analysis": approval_rate_data,
                        "performance_metrics": {
                            "total_processing_time": round(time.time() - start_time, 2),
                            "counting_time": round(time.time() - count_start, 2),
                            "total_records_processed": total_count,
                            "request_dates_retrieved": len(request_dates_iso),
                        },
                    }

                    print(
                        f"Total optimized processing time: {time.time() - start_time:.2f}s"
                    )
                    print(f"Processed {total_count} transfers")

                    # Save dashboard data
                    save_start = time.time()
                    try:
                        # Ensure a local container exists to store dashboard data
                        return_data["normal"] = data

                        # If only normal dashboard is requested, return now.
                        if dashboard_type == "normal":
                            return Response(return_data, status=status.HTTP_200_OK)
                    except Exception as e:
                        print(f"Error occurred while saving dashboard data: {str(e)}")
                except Exception as e:
                    print(f"Error occurred while saving dashboard data: {str(e)}")
            if dashboard_type == "smart" or dashboard_type == "all":
                try:
                    start_time = time.time()

                    print("Starting optimized smart dashboard calculation...")
                    if DashBoard_filler_per_Project:
                        print(
                            f"Filters applied: cost_center={DashBoard_filler_per_Project}"
                        )
                    # PHASE 1: Database-level aggregations for approved transfers
                    aggregation_start = time.time()

                    # Build base queryset with optimized filtering
                    base_queryset = xx_TransactionTransfer.objects.select_related(
                        "transaction"
                    ).filter(transaction__status="approved")

                    # Apply additional filters if provided
                    if DashBoard_filler_per_Project:
                        base_queryset = base_queryset.filter(
                            cost_center_code=DashBoard_filler_per_Project
                        )

                    # Aggregate by cost center code (single database query)
                    cost_center_totals = list(
                        base_queryset.values("cost_center_code")
                        .annotate(
                            total_from_center=Sum("from_center"),
                            total_to_center=Sum("to_center"),
                        )
                        .order_by("cost_center_code")
                    )

                    # Aggregate by account code (single database query)
                    account_code_totals = list(
                        base_queryset.values("account_code")
                        .annotate(
                            total_from_center=Sum("from_center"),
                            total_to_center=Sum("to_center"),
                        )
                        .order_by("account_code")
                    )

                    # Aggregate by combination of cost center and account code (single database query)
                    all_combinations = list(
                        base_queryset.values("cost_center_code", "account_code")
                        .annotate(
                            total_from_center=Sum("from_center"),
                            total_to_center=Sum("to_center"),
                        )
                        .order_by("cost_center_code", "account_code")
                    )

                    # Get filtered individual records if filters are applied
                    if DashBoard_filler_per_Project:
                        filtered_combinations = list(
                            base_queryset.values(
                                "cost_center_code",
                                "account_code",
                                "from_center",
                                "to_center",
                            )
                        )
                    else:
                        # If no filters, use aggregated data to avoid large result sets
                        filtered_combinations = all_combinations

                    print(
                        f"Database aggregations completed in {time.time() - aggregation_start:.2f}s"
                    )

                    # PHASE 2: Format response data
                    format_start = time.time()

                    # Convert Decimal to float for JSON serialization
                    for item in cost_center_totals:
                        item["total_from_center"] = float(
                            item["total_from_center"] or 0
                        )
                        item["total_to_center"] = float(item["total_to_center"] or 0)

                    for item in account_code_totals:
                        item["total_from_center"] = float(
                            item["total_from_center"] or 0
                        )
                        item["total_to_center"] = float(item["total_to_center"] or 0)

                    for item in all_combinations:
                        item["total_from_center"] = float(
                            item["total_from_center"] or 0
                        )
                        item["total_to_center"] = float(item["total_to_center"] or 0)

                    # Convert filtered combinations
                    for item in filtered_combinations:
                        if "from_center" in item:  # Individual records
                            item["from_center"] = float(item["from_center"] or 0)
                            item["to_center"] = float(item["to_center"] or 0)

                    print(
                        f"Data formatting completed in {time.time() - format_start:.2f}s"
                    )

                    # Prepare final response
                    data = {
                        "filtered_combinations": filtered_combinations,
                        "cost_center_totals": cost_center_totals,
                        "account_code_totals": account_code_totals,
                        "all_combinations": all_combinations,
                        "applied_filters": {
                            "cost_center_code": DashBoard_filler_per_Project,
                        },
                        "performance_metrics": {
                            "total_processing_time": round(time.time() - start_time, 2),
                            "aggregation_time": round(
                                time.time() - aggregation_start, 2
                            ),
                            "cost_center_groups": len(cost_center_totals),
                            "account_code_groups": len(account_code_totals),
                            "total_combinations": len(all_combinations),
                        },
                    }

                    print(
                        f"Total optimized processing time: {time.time() - start_time:.2f}s"
                    )
                    print(
                        f"Found {len(cost_center_totals)} cost centers, {len(account_code_totals)} account codes"
                    )

                    # Save dashboard data
                    save_start = time.time()
                    try:
                        return_data["smart"] = data
                        # If only smart dashboard is requested, return now.
                        if dashboard_type == "smart":
                            return Response(return_data, status=status.HTTP_200_OK)
                    except Exception as save_error:
                        print(f"Error saving dashboard data: {save_error}")
                        return data

                    except Exception as e:
                        import traceback

                        traceback.print_exc()
                        return Response(
                            {"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
                except Exception as e:
                    print(f"Error processing dashboard data: {e}")
                    return Response(
                        {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            # If we reach here, and we have collected one or more sections (e.g., type=all), return them.
            if return_data:
                return Response(return_data, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback

            traceback.print_exc()
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_users_in_same_security_groups(self, user):
        """
        Get all users who are in the same security group(s) as the given user.
        Includes the current user.
        
        Returns:
            QuerySet of xx_User objects
        """
        # Get all security groups the user belongs to
        user_group_ids = XX_UserGroupMembership.objects.filter(
            user=user,
            is_active=True
        ).values_list('security_group_id', flat=True)
        
        if not user_group_ids:
            # User not in any groups, return only the user
            return xx_User.objects.filter(id=user.id)
        
        # Get all users in those same security groups
        users_in_same_groups = xx_User.objects.filter(
            group_memberships__security_group_id__in=user_group_ids,
            group_memberships__is_active=True,
            is_active=True
        ).distinct()
        
        return users_in_same_groups

    def _filter_by_group_entities(self, queryset, entity_ids, dashboard_filler_per_project=None):
        """
        Filter budget transfers by entity IDs from all users in the security group.
        Similar to filter_budget_transfers_all_in_entities but uses provided entity_ids.
        
        Args:
            queryset: QuerySet of xx_BudgetTransfer
            entity_ids: List of entity IDs to filter by
            dashboard_filler_per_project: Optional specific project filter
            
        Returns:
            Filtered QuerySet
        """
        from account_and_entitys.models import get_entities_with_children
        from django.db import connection
        
        if dashboard_filler_per_project is not None:
            if int(dashboard_filler_per_project) in entity_ids:
                entity_ids = [int(dashboard_filler_per_project)]
        
        entities = get_entities_with_children(entity_ids)
        
        # Collect allowed entity codes and convert to integers
        raw_entity_codes = [e.entity for e in entities]
        numeric_entity_codes = []
        for code in raw_entity_codes:
            try:
                numeric_entity_codes.append(int(str(code).strip()))
            except Exception:
                continue
        
        if not numeric_entity_codes:
            return queryset.none()
        
        # Use raw SQL to filter transfers (same logic as filter_budget_transfers_all_in_entities)
        try:
            with connection.cursor() as cursor:
                placeholders = ",".join(["%s"] * len(numeric_entity_codes))
                sql = f"""
                    SELECT bt.transaction_id
                    FROM XX_BUDGET_TRANSFER_XX bt
                    WHERE NOT EXISTS (
                        SELECT 1 
                        FROM XX_TRANSACTION_TRANSFER_XX tt 
                        WHERE tt.transaction_id = bt.transaction_id 
                        AND tt.cost_center_code NOT IN ({placeholders})
                    )
                    AND EXISTS (
                        SELECT 1 
                        FROM XX_TRANSACTION_TRANSFER_XX tt2 
                        WHERE tt2.transaction_id = bt.transaction_id
                    )

                    UNION

                    SELECT bt.transaction_id
                    FROM XX_BUDGET_TRANSFER_XX bt
                    WHERE NOT EXISTS (
                        SELECT 1 
                        FROM XX_TRANSACTION_TRANSFER_XX tt 
                        WHERE tt.transaction_id = bt.transaction_id
                    )
                """
                cursor.execute(sql, numeric_entity_codes)
                allowed_ids = [row[0] for row in cursor.fetchall()]
            
            return queryset.filter(transaction_id__in=allowed_ids)
        except Exception as e:
            print(f"Error filtering by group entities: {e}")
            return queryset


### mobile version #####           
class ListBudgetTransfer_approvels_MobileView(APIView):
    """List budget transfers with pagination"""

    permission_classes = [IsAuthenticated]
    pagination_class = TransferPagination

    def get(self, request):
        code = request.query_params.get("code", None)
        date = request.data.get("date", None)
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)

        if code is None:
            code = "FAR"
        status_level_val = (
            request.user.user_level.level_order
            if request.user.user_level.level_order
            else 0
        )
        transfers = ApprovalManager.get_user_pending_approvals(request.user)

        if request.user.abilities_legacy.count() > 0:
            transfers = filter_budget_transfers_all_in_entities(
                transfers, request.user, "approve"
            )

        if code:
            transfers = transfers.filter(code__icontains=code)

        transfers = transfers.order_by("-request_date")
        # Return all results without pagination
        serializer = BudgetTransferSerializer(transfers, many=True)

        # Create a list of dictionaries with just the fields we want
        filtered_data = []
        for item in serializer.data:
            filtered_item = {
                "transaction_id": item.get("transaction_id"),
                "amount": item.get("amount"),
                "status": item.get("status"),
                "status_level": item.get("status_level"),
                "requested_by": item.get("requested_by"),
                "request_date": item.get("request_date"),
                "code": item.get("code"),
                "transaction_date": item.get("transaction_date"),
            }
            filtered_data.append(filtered_item)

        return Response(filtered_data, status=status.HTTP_200_OK)


class Approval_Status(APIView):
    """Get approval status options"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        transaction_id = request.query_params.get("transaction_id", None)
        if not transaction_id:
            return Response(
                {"detail": "transaction_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transaction_obj = xx_BudgetTransfer.objects.get(
                transaction_id=transaction_id
            )
        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"detail": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Phase 6: Get all workflows for this transfer, ordered by execution_order
        workflows = transaction_obj.workflow_instances.all().order_by('execution_order')
        if not workflows.exists():
            return Response(
                {"detail": "No workflow instances for this transaction"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Process all workflows
        all_workflows_data = []
        
        for workflow in workflows:
            archived_order_start = 9999

            # Map of stage_template_id -> stage_instance (if created)
            stage_instances_qs = workflow.stage_instances.select_related(
                "stage_template", "workflow_instance"
            ).all().order_by("stage_template__order_index", "id")
            instances_by_tpl = {si.stage_template_id: si for si in stage_instances_qs}
            has_archived_instances = stage_instances_qs.filter(
                stage_template__order_index__gte=archived_order_start
            ).exists()

            # Stage templates in order (hide archived stages)
            stage_templates = workflow.template.stages.filter(
                order_index__lt=archived_order_start
            ).order_by("order_index")

            # For rejected workflows, capture the latest reject per order_index to reflect group outcome
            latest_reject_by_order = {}
            if workflow.status == ApprovalWorkflowInstance.STATUS_REJECTED:
                for si in stage_instances_qs:
                    order_idx = si.stage_template.order_index
                    r = (
                        si.actions.filter(action=ApprovalAction.ACTION_REJECT)
                        .order_by("-created_at")
                        .first()
                    )
                    if r and (
                        order_idx not in latest_reject_by_order
                        or r.created_at > latest_reject_by_order[order_idx].created_at
                    ):
                        latest_reject_by_order[order_idx] = r

            results = []
            order_index_map = {}
            display_order = 0

            def get_display_order(order_index):
                nonlocal display_order
                if order_index not in order_index_map:
                    display_order += 1
                    order_index_map[order_index] = display_order
                return order_index_map[order_index]

            if has_archived_instances:
                stage_sources = [(si.stage_template, si) for si in stage_instances_qs]
            else:
                stage_sources = [(stpl, instances_by_tpl.get(stpl.id)) for stpl in stage_templates]

            for stpl, si in stage_sources:

                stage_info = {
                    "order_index": (
                        get_display_order(stpl.order_index)
                        if has_archived_instances
                        else stpl.order_index
                    ),
                    "name": stpl.name,
                    "decision_policy": stpl.decision_policy,
                }

                # Determine status for this stage
                if si is None:
                    # Not yet instantiated -> pending (not started)
                    stage_info["status"] = "pending"
                    results.append(stage_info)
                    continue

                # Map instance status to friendly label
                inst_status = si.status
                if inst_status == "active":
                    stage_info["status"] = "in_progress"
                elif inst_status == "pending":
                    stage_info["status"] = "pending"
                elif inst_status == "skipped":
                    stage_info["status"] = "skipped"
                elif inst_status in ("completed", "cancelled"):
                    # Determine outcome based on actions
                    # If any reject action exists on this stage -> rejected else approved (or skipped above)
                    last_reject = (
                        si.actions.filter(action=ApprovalAction.ACTION_REJECT)
                        .order_by("-created_at")
                        .first()
                    )
                    if last_reject:
                        stage_info["status"] = "rejected"
                        actor = last_reject.user
                        stage_info["acted_by"] = {
                            "id": getattr(actor, "id", None),
                            "username": getattr(
                                actor, "username", "SYSTEM" if actor is None else None
                            ),
                            "action_at": (
                                last_reject.created_at.isoformat()
                                if getattr(last_reject, "created_at", None)
                                else None
                            ),
                        }
                        stage_info["comment"] = last_reject.comment
                    else:
                        # If workflow is rejected and another parallel stage in this order was rejected,
                        # mark this stage as rejected to reflect the group outcome.
                        group_reject = latest_reject_by_order.get(stpl.order_index)
                        if group_reject:
                            stage_info["status"] = "rejected"
                            actor = group_reject.user
                            stage_info["acted_by"] = {
                                "id": getattr(actor, "id", None),
                                "username": getattr(
                                    actor, "username", "SYSTEM" if actor is None else None
                                ),
                                "action_at": (
                                    group_reject.created_at.isoformat()
                                    if getattr(group_reject, "created_at", None)
                                    else None
                                ),
                            }
                            stage_info["comment"] = group_reject.comment
                            results.append(stage_info)
                            continue
                        # Approved if there is at least one approve action (user or system auto-skip approve)
                        last_approve = (
                            si.actions.filter(action=ApprovalAction.ACTION_APPROVE)
                            .order_by("-created_at")
                            .first()
                        )
                        stage_info["status"] = "approved" if last_approve else "completed"
                        if last_approve:
                            actor = last_approve.user
                            stage_info["acted_by"] = {
                                "id": getattr(actor, "id", None),
                                "username": getattr(
                                    actor, "username", "SYSTEM" if actor is None else None
                                ),
                                "action_at": (
                                    last_approve.created_at.isoformat()
                                    if getattr(last_approve, "created_at", None)
                                    else None
                                ),
                            }
                            stage_info["comment"] = last_approve.comment
                else:
                    # Fallback
                    stage_info["status"] = inst_status

                if (
                    workflow.status == ApprovalWorkflowInstance.STATUS_APPROVED
                    and stage_info["status"] == "completed"
                ):
                    stage_info["status"] = "approved"

                results.append(stage_info)

            # Add this workflow's data to the list
            all_workflows_data.append({
                "execution_order": workflow.execution_order,
                "workflow_code": workflow.template.code,
                "workflow_name": workflow.template.name,
                "workflow_status": workflow.status,
                "stages": results,
            })

        return Response(
            {
                "transaction_id": transaction_obj.transaction_id,
                "transfer_status": transaction_obj.status,
                "workflows": all_workflows_data,
            },
            status=status.HTTP_200_OK,
        )


class Oracle_Status(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            transaction_id = request.query_params.get("transaction_id", None)
            
            if not transaction_id:
                return Response(
                    {"error": "transaction_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            audit_records = xx_budget_integration_audit.objects.filter(
                transaction_id=transaction_id
            ).order_by('step_number')
            
            # Group records by Action_Type
            grouped_data = {}
            for record in audit_records:
                action_type = record.Action_Type or "Unknown"
                
                if action_type not in grouped_data:
                    grouped_data[action_type] = {
                        "action_type": action_type,
                        "steps": []
                    }
                
                grouped_data[action_type]["steps"].append({
                    "step_number": record.step_number,
                    "step_name": record.step_name,
                    "status": record.status,
                    "message": record.message,
                    "request_id": record.request_id,
                    "document_id": record.document_id,
                    "group_id": record.group_id,
                    "created_at": record.created_at,
                    "completed_at": record.completed_at
                })
            
            # Convert to list and maintain order
            action_groups = list(grouped_data.values())
            
            return Response(
                {
                    "transaction_id": transaction_id,
                    "total_records": audit_records.count(),
                    "action_groups": action_groups
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TransactionSecurityGroupView(APIView):
    "Manage security group assignment for budget transactions"
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, transaction_id):
        "Get the security group assigned to a transaction"
        try:
            transaction = xx_BudgetTransfer.objects.select_related('security_group').get(
                transaction_id=transaction_id
            )
            
            if transaction.security_group:
                return Response({
                    "transaction_id": transaction_id,
                    "security_group": {
                        "group_id": transaction.security_group.group_id,
                        "group_name": transaction.security_group.group_name,
                        "description": transaction.security_group.description,
                        "is_active": transaction.security_group.is_active
                    },
                    "is_restricted": True
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "transaction_id": transaction_id,
                    "security_group": None,
                    "is_restricted": False,
                    "message": "This transaction is accessible to all users"
                }, status=status.HTTP_200_OK)
                
        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"error": "Transaction not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, transaction_id):
        "Assign or change security group for a transaction"
        try:
            transaction = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)
            
            # Permission check: Only transaction owner or admin can assign security group
            if request.user.role not in [1, 2] and transaction.user_id != request.user.id:
                return Response(
                    {"error": "You don't have permission to modify this transaction's security group"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            security_group_id = request.data.get('security_group_id')
            
            if security_group_id:
                # Validate security group exists
                from user_management.models import XX_SecurityGroup
                try:
                    security_group = XX_SecurityGroup.objects.get(group_id=security_group_id, is_active=True)
                    transaction.security_group = security_group
                    transaction.save()
                    
                    return Response({
                        "message": f"Transaction {transaction_id} assigned to security group '{security_group.group_name}'",
                        "transaction_id": transaction_id,
                        "security_group": {
                            "group_id": security_group.group_id,
                            "group_name": security_group.group_name,
                            "description": security_group.description
                        }
                    }, status=status.HTTP_200_OK)
                    
                except XX_SecurityGroup.DoesNotExist:
                    return Response(
                        {"error": f"Security group with ID {security_group_id} not found or inactive"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                return Response(
                    {"error": "security_group_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"error": "Transaction not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def delete(self, request, transaction_id):
        "Remove security group restriction from a transaction"
        try:
            transaction = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)
            
            # Permission check: Only transaction owner or admin
            if request.user.role not in [1, 2] and transaction.user_id != request.user.id:
                return Response(
                    {"error": "You don't have permission to modify this transaction's security group"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if transaction.security_group:
                group_name = transaction.security_group.group_name
                transaction.security_group = None
                transaction.save()
                
                return Response({
                    "message": f"Security group restriction removed. Transaction {transaction_id} is now accessible to all users",
                    "transaction_id": transaction_id,
                    "previous_group": group_name
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "message": "Transaction already has no security group restriction",
                    "transaction_id": transaction_id
                }, status=status.HTTP_200_OK)
                
        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"error": "Transaction not found"},
                status=status.HTTP_404_NOT_FOUND
            )
