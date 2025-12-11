from budget_management.models import xx_BudgetTransfer
from transaction.models import xx_TransactionTransfer
from account_and_entitys.models import XX_Segment_Funds, XX_TransactionSegment, XX_Segment, XX_gfs_Mamping
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from django.db import transaction
from django.db.models import Sum, Q, F, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from user_management.managers.security_group_manager import SecurityGroupManager
from user_management.managers import UserSegmentAccessManager


class SegmentTransferAggregationView(APIView):
    """
    Aggregate all transfers by a specific segment type.
    For each unique segment value used in from_segment_value or to_segment_value,
    calculate:
    - Total from_center amount (how much was taken from this segment)
    - Total to_center amount (how much was transferred to this segment)
    - Financial data aggregated from XX_Segment_Funds table
    """

    def get(self, request, format=None):
        """
        GET /api/segment_transfer_aggregation/?segment_type_id=11&control_budget_name=MOFA&page=1&page_size=20
        
        Query params:
        - segment_type_id: Required. The segment type ID to aggregate by (e.g., 11 = Segment11).
        - control_budget_name: Required. The control budget name to filter XX_Segment_Funds.
        - transaction_status: Optional. Filter by transaction status (approved, pending, all)
        - segment_code: Optional. Filter by specific segment code (exact match or comma-separated list)
        - segment_filter: Optional. Filter segments by activity type:
            * 'with_transfers' - Only segments that have transfers
            * 'with_funds' - Only segments that have funds data in XX_Segment_Funds
            * 'with_both' - Only segments that have both transfers and funds
            * 'with_either' - Segments that have transfers OR funds (or both)
            * 'all' or omitted - Return all segments (default)
        - page: Optional. Page number (default: 1)
        - page_size: Optional. Number of items per page (default: 20, max: 100)
        """
        segment_type_id = request.query_params.get("segment_type_id")
        control_budget_name = request.query_params.get("control_budget_name")
        transaction_status = request.query_params.get("transaction_status", "all")
        segment_code_filter = request.query_params.get("segment_code", None)
        segment_filter = request.query_params.get("segment_filter", "all").lower()
        
        # Parse segment_code filter (can be single value or comma-separated list)
        segment_codes_to_filter = None
        if segment_code_filter:
            segment_codes_to_filter = [code.strip() for code in segment_code_filter.split(',') if code.strip()]
        
        # Pagination parameters
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))
            page_size = min(page_size, 100)  # Max 100 items per page
            page = max(page, 1)  # Ensure page is at least 1
        except ValueError:
            page = 1
            page_size = 10
        
        if not segment_type_id:
            return Response(
                {"error": "segment_type_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not control_budget_name:
            return Response(
                {"error": "control_budget_name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            segment_type_id = int(segment_type_id)
        except ValueError:
            return Response(
                {"error": "segment_type_id must be an integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Determine which Segment column to use (Segment1, Segment2, ..., Segment30)
        segment_column = f"Segment{segment_type_id}"
        
        # ====== ACCESS CONTROL: Check user's segment access ======
        user = request.user
        access_source = None
        user_allowed_segment_codes = None
        
        # SuperAdmin bypass
        if user.role == 1:  # SuperAdmin
            access_source = 'superadmin'
        else:
            # Phase 5: Security Groups (preferred)
            security_group_segments = SecurityGroupManager.get_user_accessible_segments(user)
            
            if security_group_segments and segment_type_id in security_group_segments:
                user_allowed_segment_codes = security_group_segments[segment_type_id]
                access_source = 'security_groups'
            else:
                # Phase 4: Direct Access (fallback)
                access_result = UserSegmentAccessManager.get_user_allowed_segments(
                    user=user,
                    segment_type_id=segment_type_id
                )
                
                if access_result and access_result.get('allowed_segment_codes'):
                    user_allowed_segment_codes = access_result['allowed_segment_codes']
                    access_source = 'direct_access'
                else:
                    access_source = 'no_access'
                    user_allowed_segment_codes = []
        
        # If user has no access (and not SuperAdmin), return empty dataset
        if access_source == 'no_access':
            return Response({
                "segment_type_id": segment_type_id,
                "segment_column": segment_column,
                "control_budget_name": control_budget_name,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False,
                },
                "summary": {
                    "total_segments": 0,
                    "grand_initial_budget": 0.0,
                    "grand_total_decrease_fund": 0.0,
                    "grand_total_from": 0.0,
                    "grand_total_to": 0.0,
                    "grand_total_additional_fund": 0.0,
                    "grand_total_budget": 0.0,
                    "grand_encumbrance": 0.0,
                    "grand_Futures_column": 0.0,
                    "grand_actual": 0.0,
                    "grand_total_actual": 0.0,
                    "grand_funds_available": 0.0,
                    "grand_exchange_rate": 0.0,
                },
                "segments": [],
                "access_control": {
                    "access_source": access_source,
                    "user_has_access": False,
                }
            }, status=status.HTTP_200_OK)
        
        # Get all transaction segments for the specified segment type
        transaction_segments = XX_TransactionSegment.objects.filter(
            segment_type_id=segment_type_id
        ).select_related(
            "transaction_transfer",
            "from_segment_value",
            "to_segment_value",
            "segment_type"
        )
        
        # Optional: Filter by transaction status
        if transaction_status == "approved":
            from approvals.models import ApprovalWorkflowInstance
            transaction_segments = transaction_segments.filter(
                transaction_transfer__transaction__workflow_instance__status=ApprovalWorkflowInstance.STATUS_APPROVED
            )
        elif transaction_status == "pending":
            from approvals.models import ApprovalWorkflowInstance
            transaction_segments = transaction_segments.filter(
                transaction_transfer__transaction__workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
            )
        
        # Step 1: Get aggregated financial data from XX_Segment_Funds grouped by the segment column
        funds_aggregation = XX_Segment_Funds.objects.filter(
            CONTROL_BUDGET_NAME=control_budget_name
        ).values(segment_column).annotate(
            total_budget_sum=Coalesce(Sum('TOTAL_BUDGET'), Value(Decimal('0'))),
            budget_adjustments_sum=Coalesce(Sum('BUDGET_ADJUSTMENTS'), Value(Decimal('0'))),
            funds_available_sum=Coalesce(Sum('FUNDS_AVAILABLE_PTD'), Value(Decimal('0'))),
            actual_sum=Coalesce(Sum('ACTUAL_PTD'), Value(Decimal('0'))),
            encumbrance_sum=Coalesce(Sum('ENCUMBRANCE_PTD'), Value(Decimal('0'))),
            commitment_sum=Coalesce(Sum('COMMITMENT_PTD'), Value(Decimal('0'))),
            obligation_sum=Coalesce(Sum('OBLIGATION_PTD'), Value(Decimal('0'))),
            other_sum=Coalesce(Sum('OTHER_PTD'), Value(Decimal('0'))),
            budget_ptd_sum=Coalesce(Sum('BUDGET_PTD'), Value(Decimal('0'))),
            initial_budget_sum=Coalesce(Sum('INITIAL_BUDGET'), Value(Decimal('0'))),
        )
        
        # Convert to dict keyed by segment code
        funds_by_segment = {}
        for item in funds_aggregation:
            segment_code = item[segment_column]
            if segment_code:
                funds_by_segment[segment_code] = {
                    "funds_available": float(item["funds_available_sum"] or 0),
                    "actual": float(item["actual_sum"] or 0),
                    "encumbrance": float(item["encumbrance_sum"] or 0),
                    "total_budget": float(item["total_budget_sum"] or 0),
                    "initial_budget": float(item["initial_budget_sum"] or 0),
                }
        
        # Step 1.5: Get all segment aliases from XX_Segment for this segment type
        segment_aliases = {}
        all_segments = XX_Segment.objects.filter(
            segment_type_id=segment_type_id
        ).values('code', 'alias')
        for seg in all_segments:
            segment_aliases[seg['code']] = seg['alias']
        
        # Step 1.6: Get all GFS mapping codes for this segment type
        # Mapping is based on To_Value matching the segment code
        segment_mappings = {}
        segment_mapping_aliases = {}
        all_mappings = XX_gfs_Mamping.objects.filter(
            is_active=True
        ).values('To_Value', 'Target_value', 'Target_alias')
        for mapping in all_mappings:
            to_value = mapping['To_Value']
            segment_mappings[to_value] = mapping['Target_value']
            segment_mapping_aliases[to_value] = mapping['Target_alias']
        
        # Step 2: Aggregate transfer data by segment code
        aggregation = {}
        segments_with_transfers = set()  # Track which segments have transfers
        
        def get_default_aggregation(code, alias):
            """Return default aggregation structure for a segment"""
            # Get funds data from XX_Segment_Funds if available
            funds_data = funds_by_segment.get(code, {
                "funds_available": 0.0,
                "actual": 0.0,
                "encumbrance": 0.0,
                "total_budget": 0.0,
                "initial_budget": 0.0,
            })
            
            return {
                "mapping_code": segment_mappings.get(code),
                "mapping_code_alias": segment_mapping_aliases.get(code),
                "segment_code": code,
                "segment_alias": alias,
                "initial_budget": funds_data["initial_budget"],
                "total_decrease_fund": Decimal('0'),
                "total_from": Decimal('0'),
                "total_to": Decimal('0'),
                "total_additional_fund": Decimal('0'),
                "total_budget": funds_data["total_budget"],
                "encumbrance": funds_data["encumbrance"],
                "Futures_column": 0.0,
                "actual": funds_data["actual"],
                "total_actual": funds_data["encumbrance"] + funds_data["actual"] + 0.0,  # encumbrance + actual + Futures_column
                "funds_available": funds_data["funds_available"],
                "exchange_rate": 0.0,
            }
        
        for ts in transaction_segments:
            transfer = ts.transaction_transfer
            from_center = transfer.from_center or Decimal('0')
            to_center = transfer.to_center or Decimal('0')
            
            # Get transaction type code (AFR = Additional Fund, DFR = Decrease Fund)
            transaction_code = getattr(transfer.transaction, 'code', '') or ''
            is_afr = transaction_code[:3].upper() == 'AFR'  # Additional Fund Request
            is_dfr = transaction_code[:3].upper() == 'DFR'  # Decrease Fund Request
            
            # Process FROM segment (source of funds)
            if ts.from_segment_value:
                from_code = ts.from_segment_value.code
                from_alias = ts.from_segment_value.alias
                
                if from_code not in aggregation:
                    aggregation[from_code] = get_default_aggregation(from_code, from_alias)
                
                segments_with_transfers.add(from_code)  # Mark as having transfers
                
                if from_center > 0:
                    aggregation[from_code]["total_from"] += from_center
                    
                    # Track AFR and DFR separately for source
                    if is_afr:
                        aggregation[from_code]["total_additional_fund"] += from_center
                    elif is_dfr:
                        aggregation[from_code]["total_decrease_fund"] += from_center
            
            # Process TO segment (destination of funds)
            if ts.to_segment_value:
                to_code = ts.to_segment_value.code
                to_alias = ts.to_segment_value.alias
                
                if to_code not in aggregation:
                    aggregation[to_code] = get_default_aggregation(to_code, to_alias)
                
                segments_with_transfers.add(to_code)  # Mark as having transfers
                
                if to_center > 0:
                    aggregation[to_code]["total_to"] += to_center
                    
                    # Track AFR and DFR separately for destination
                    if is_afr:
                        aggregation[to_code]["total_additional_fund"] += to_center
                    elif is_dfr:
                        aggregation[to_code]["total_decrease_fund"] += to_center
        
        # Calculate exchange rate and total_actual for each segment and convert to float
        for code, data in aggregation.items():
            data["total_decrease_fund"] = float(data["total_decrease_fund"])
            data["total_from"] = float(data["total_from"])
            data["total_to"] = float(data["total_to"])
            data["total_additional_fund"] = float(data["total_additional_fund"])
            
            # Calculate total_actual = encumbrance + actual + Futures_column
            data["total_actual"] = data["encumbrance"] + data["actual"] + data["Futures_column"]
            
            # Calculate Exchange Rate = (total_actual / total_budget) * 100 as percentage
            total_budget = data.get("total_budget", 0)
            total_actual = data.get("total_actual", 0)
            if total_budget and total_budget != 0:
                data["exchange_rate"] = round((total_actual / total_budget) * 100, 2)
            else:
                data["exchange_rate"] = 0.0
        
        # Step 3: Add segments from XX_Segment_Funds that are not in any transfers
        for segment_code, funds_data in funds_by_segment.items():
            if segment_code not in aggregation:
                # Calculate total_actual first
                total_actual = funds_data["encumbrance"] + funds_data["actual"] + 0.0
                
                # Calculate Exchange Rate for this segment
                total_budget = funds_data.get("total_budget", 0)
                if total_budget and total_budget != 0:
                    exchange_rate = round((total_actual / total_budget) * 100, 2)
                else:
                    exchange_rate = 0.0
                
                aggregation[segment_code] = {
                    "mapping_code": segment_mappings.get(segment_code),
                    "mapping_code_alias": segment_mapping_aliases.get(segment_code),
                    "segment_code": segment_code,
                    "segment_alias": segment_aliases.get(segment_code),
                    "initial_budget": funds_data["initial_budget"],
                    "total_decrease_fund": 0.0,
                    "total_from": 0.0,
                    "total_to": 0.0,
                    "total_additional_fund": 0.0,
                    "total_budget": funds_data["total_budget"],
                    "encumbrance": funds_data["encumbrance"],
                    "Futures_column": 0.0,
                    "actual": funds_data["actual"],
                    "total_actual": funds_data["encumbrance"] + funds_data["actual"] + 0.0,  # encumbrance + actual + Futures_column
                    "funds_available": funds_data["funds_available"],
                    "exchange_rate": exchange_rate,
                }
        
        # Step 4: Add ALL segments from XX_Segment that are not yet in aggregation
        for segment_code, segment_alias in segment_aliases.items():
            if segment_code not in aggregation:
                aggregation[segment_code] = {
                    "mapping_code": segment_mappings.get(segment_code),
                    "mapping_code_alias": segment_mapping_aliases.get(segment_code),
                    "segment_code": segment_code,
                    "segment_alias": segment_alias,
                    "initial_budget": 0.0,
                    "total_decrease_fund": 0.0,
                    "total_from": 0.0,
                    "total_to": 0.0,
                    "total_additional_fund": 0.0,
                    "total_budget": 0.0,
                    "encumbrance": 0.0,
                    "Futures_column": 0.0,
                    "actual": 0.0,
                    "total_actual": 0.0,
                    "funds_available": 0.0,
                    "exchange_rate": 0.0,
                }
        
        # Convert to list and sort by segment code
        aggregation_list = list(aggregation.values())
        aggregation_list.sort(key=lambda x: x["segment_code"])
        
        # ====== Apply access control filter to aggregation results ======
        if access_source != 'superadmin' and user_allowed_segment_codes is not None:
            # Filter aggregation to only include segments user has access to
            aggregation_list = [
                item for item in aggregation_list 
                if item["segment_code"] in user_allowed_segment_codes
            ]
        
        # Apply segment_filter based on transfer/funds activity
        if segment_filter == "with_transfers":
            aggregation_list = [item for item in aggregation_list if item["segment_code"] in segments_with_transfers]
        elif segment_filter == "with_funds":
            aggregation_list = [item for item in aggregation_list if item["segment_code"] in funds_by_segment]
        elif segment_filter == "with_both":
            aggregation_list = [item for item in aggregation_list if item["segment_code"] in segments_with_transfers and item["segment_code"] in funds_by_segment]
        elif segment_filter == "with_either":
            aggregation_list = [item for item in aggregation_list if item["segment_code"] in segments_with_transfers or item["segment_code"] in funds_by_segment]
        # 'all' or any other value: no filtering, return all segments
        
        # Apply segment_code filter if provided
        if segment_codes_to_filter:
            aggregation_list = [item for item in aggregation_list if item["segment_code"] in segment_codes_to_filter]
        
        # Calculate grand totals (after filtering, before pagination)
        grand_initial_budget = sum(item["initial_budget"] for item in aggregation_list)
        grand_total_decrease_fund = sum(item["total_decrease_fund"] for item in aggregation_list)
        grand_total_from = sum(item["total_from"] for item in aggregation_list)
        grand_total_to = sum(item["total_to"] for item in aggregation_list)
        grand_total_additional_fund = sum(item["total_additional_fund"] for item in aggregation_list)
        grand_total_budget = sum(item["total_budget"] for item in aggregation_list)
        grand_encumbrance = sum(item["encumbrance"] for item in aggregation_list)
        grand_Futures_column = 0.0  # Always 0
        grand_actual = sum(item["actual"] for item in aggregation_list)
        grand_total_actual = sum(item["total_actual"] for item in aggregation_list)
        grand_funds_available = sum(item["funds_available"] for item in aggregation_list)
        
        # Calculate grand exchange rate
        if grand_total_budget != 0:
            grand_exchange_rate = round((grand_total_actual / grand_total_budget) * 100, 2)
        else:
            grand_exchange_rate = 0.0
        
        # Pagination
        total_count = len(aggregation_list)
        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_segments = aggregation_list[start_index:end_index]
        
        response_payload = {
            "segment_type_id": segment_type_id,
            "segment_column": segment_column,
            "control_budget_name": control_budget_name,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
            "summary": {
                "total_segments": total_count,
                "grand_initial_budget": grand_initial_budget,
                "grand_total_decrease_fund": grand_total_decrease_fund,
                "grand_total_from": grand_total_from,
                "grand_total_to": grand_total_to,
                "grand_total_additional_fund": grand_total_additional_fund,
                "grand_total_budget": grand_total_budget,
                "grand_encumbrance": grand_encumbrance,
                "grand_Futures_column": grand_Futures_column,
                "grand_actual": grand_actual,
                "grand_total_actual": grand_total_actual,
                "grand_funds_available": grand_funds_available,
                "grand_exchange_rate": grand_exchange_rate,
            },
            "segments": paginated_segments,
            "access_control": {
                "access_source": access_source,
                "user_has_access": True,
                "filtered_by_access": access_source not in ['superadmin', None],
            }
        }
        
        return Response(response_payload, status=status.HTTP_200_OK)
