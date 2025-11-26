from budget_management.models import xx_BudgetTransfer
from transaction.models import xx_TransactionTransfer
from account_and_entitys.models import XX_Segment_Funds, XX_TransactionSegment, XX_Segment
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
        - page: Optional. Page number (default: 1)
        - page_size: Optional. Number of items per page (default: 20, max: 100)
        """
        segment_type_id = request.query_params.get("segment_type_id")
        control_budget_name = request.query_params.get("control_budget_name")
        transaction_status = request.query_params.get("transaction_status", "all")
        
        # Pagination parameters
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            page_size = min(page_size, 100)  # Max 100 items per page
            page = max(page, 1)  # Ensure page is at least 1
        except ValueError:
            page = 1
            page_size = 20
        
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
                    "total_budget_sum": float(item["total_budget_sum"] or 0),
                    "budget_adjustments_sum": float(item["budget_adjustments_sum"] or 0),
                    "funds_available_sum": float(item["funds_available_sum"] or 0),
                    "actual_sum": float(item["actual_sum"] or 0),
                    "encumbrance_sum": float(item["encumbrance_sum"] or 0),
                    "commitment_sum": float(item["commitment_sum"] or 0),
                    "obligation_sum": float(item["obligation_sum"] or 0),
                    "other_sum": float(item["other_sum"] or 0),
                    "budget_ptd_sum": float(item["budget_ptd_sum"] or 0),
                    "initial_budget_sum": float(item["initial_budget_sum"] or 0),
                }
        
        # Step 1.5: Get all segment aliases from XX_Segment for this segment type
        segment_aliases = {}
        all_segments = XX_Segment.objects.filter(
            segment_type_id=segment_type_id
        ).values('code', 'alias')
        for seg in all_segments:
            segment_aliases[seg['code']] = seg['alias']
        
        # Step 2: Aggregate transfer data by segment code
        aggregation = {}
        
        def get_default_aggregation(code, alias):
            """Return default aggregation structure for a segment"""
            base = {
                "segment_code": code,
                "segment_alias": alias,
                "total_from_center": Decimal('0'),
                "total_to_center": Decimal('0'),
                "transfers_as_source": 0,
                "transfers_as_destination": 0,
                "net_change": Decimal('0'),
                "transfer_ids_as_source": [],
                "transfer_ids_as_destination": [],
            }
            # Add funds data from XX_Segment_Funds if available
            funds_data = funds_by_segment.get(code, {
                "total_budget_sum": 0.0,
                "budget_adjustments_sum": 0.0,
                "funds_available_sum": 0.0,
                "actual_sum": 0.0,
                "encumbrance_sum": 0.0,
                "commitment_sum": 0.0,
                "obligation_sum": 0.0,
                "other_sum": 0.0,
                "budget_ptd_sum": 0.0,
                "initial_budget_sum": 0.0,
            })
            base.update(funds_data)
            return base
        
        for ts in transaction_segments:
            transfer = ts.transaction_transfer
            from_center = transfer.from_center or Decimal('0')
            to_center = transfer.to_center or Decimal('0')
            
            # Process FROM segment (source of funds)
            if ts.from_segment_value:
                from_code = ts.from_segment_value.code
                from_alias = ts.from_segment_value.alias
                
                if from_code not in aggregation:
                    aggregation[from_code] = get_default_aggregation(from_code, from_alias)
                
                if from_center > 0:
                    aggregation[from_code]["total_from_center"] += from_center
                    aggregation[from_code]["transfers_as_source"] += 1
                    aggregation[from_code]["transfer_ids_as_source"].append(transfer.transfer_id)
            
            # Process TO segment (destination of funds)
            if ts.to_segment_value:
                to_code = ts.to_segment_value.code
                to_alias = ts.to_segment_value.alias
                
                if to_code not in aggregation:
                    aggregation[to_code] = get_default_aggregation(to_code, to_alias)
                
                if to_center > 0:
                    aggregation[to_code]["total_to_center"] += to_center
                    aggregation[to_code]["transfers_as_destination"] += 1
                    aggregation[to_code]["transfer_ids_as_destination"].append(transfer.transfer_id)
        
        # Calculate net change for each segment and convert to float
        for code, data in aggregation.items():
            # Net change = funds received (to_center) - funds given (from_center)
            data["net_change"] = float(data["total_to_center"] - data["total_from_center"])
            data["total_from_center"] = float(data["total_from_center"])
            data["total_to_center"] = float(data["total_to_center"])
        
        # Step 3: Add segments from XX_Segment_Funds that are not in any transfers
        for segment_code, funds_data in funds_by_segment.items():
            if segment_code not in aggregation:
                # This segment exists in funds but has no transfers
                # Look up the alias from XX_Segment
                aggregation[segment_code] = {
                    "segment_code": segment_code,
                    "segment_alias": segment_aliases.get(segment_code),  # Get alias from XX_Segment lookup
                    "total_from_center": 0.0,
                    "total_to_center": 0.0,
                    "transfers_as_source": 0,
                    "transfers_as_destination": 0,
                    "net_change": 0.0,
                    "transfer_ids_as_source": [],
                    "transfer_ids_as_destination": [],
                    "has_transfers": False,
                    **funds_data
                }
            else:
                aggregation[segment_code]["has_transfers"] = True
        
        # Mark segments that have transfers
        for code, data in aggregation.items():
            if "has_transfers" not in data:
                data["has_transfers"] = data["transfers_as_source"] > 0 or data["transfers_as_destination"] > 0
        
        # Convert to list and sort by segment code
        aggregation_list = list(aggregation.values())
        aggregation_list.sort(key=lambda x: x["segment_code"])
        
        # Calculate grand totals (before pagination)
        grand_total_from = sum(item["total_from_center"] for item in aggregation_list)
        grand_total_to = sum(item["total_to_center"] for item in aggregation_list)
        
        # Count segments with and without transfers
        segments_with_transfers = sum(1 for item in aggregation_list if item["has_transfers"])
        segments_without_transfers = len(aggregation_list) - segments_with_transfers
        
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
                "segments_with_transfers": segments_with_transfers,
                "segments_without_transfers": segments_without_transfers,
                "total_segments_in_funds": len(funds_by_segment),
                "grand_total_from_center": grand_total_from,
                "grand_total_to_center": grand_total_to,
                "grand_total_net": grand_total_to - grand_total_from,
                "grand_total_budget": sum(item["total_budget_sum"] for item in aggregation_list),
                "grand_funds_available": sum(item["funds_available_sum"] for item in aggregation_list),
            },
            "segments": paginated_segments,
        }
        
        return Response(response_payload, status=status.HTTP_200_OK)
