from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from decimal import Decimal

from .models import xx_TransactionTransfer
from budget_management.models import xx_BudgetTransfer
from account_and_entitys.models import (
    XX_SegmentType, 
    XX_TransactionSegment,
    XX_DynamicBalanceReport
)


class TransactionComprehensiveReportView(APIView):
    """
    Comprehensive transaction report with all details including:
    - Transaction metadata (code, type, dates, requested by)
    - Dynamic segments (with names and codes)
    - Budget control information per segment combination
    - Financial details (budget, encumbrance, actual, etc.)
    
    Supports single or multiple transaction IDs.
    
    Example usage:
    GET /api/transactions/report/?transaction_id=123
    GET /api/transactions/report/?transaction_id=123,456,789
    POST /api/transactions/report/ with {"transaction_ids": [123, 456, 789]}
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Handle GET requests with query parameters."""
        transaction_id_param = request.query_params.get('transaction_id', None)
        
        if not transaction_id_param:
            return Response(
                {
                    "error": "transaction_id parameter is required",
                    "message": "Use ?transaction_id=123 or ?transaction_id=123,456,789"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse comma-separated IDs
        try:
            transaction_ids = [int(tid.strip()) for tid in transaction_id_param.split(',')]
        except ValueError:
            return Response(
                {
                    "error": "Invalid transaction_id format",
                    "message": "Use comma-separated integers like: ?transaction_id=123,456,789"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return self._generate_report(transaction_ids)
    
    def post(self, request):
        """Handle POST requests with body containing transaction_ids array."""
        transaction_ids = request.data.get('transaction_ids', None)
        
        if not transaction_ids:
            return Response(
                {
                    "error": "transaction_ids array is required in request body",
                    "message": "Send POST body: {\"transaction_ids\": [123, 456, 789]}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(transaction_ids, list):
            return Response(
                {
                    "error": "transaction_ids must be an array",
                    "message": "Use format: {\"transaction_ids\": [123, 456, 789]}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            transaction_ids = [int(tid) for tid in transaction_ids]
        except (ValueError, TypeError):
            return Response(
                {
                    "error": "All transaction_ids must be valid integers",
                    "message": "Ensure all IDs are numbers: [123, 456, 789]"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return self._generate_report(transaction_ids)
    
    def _generate_report(self, transaction_ids):
        """Generate comprehensive report for given transaction IDs."""
        results = []
        
        # Get all segment types ordered by display_order
        segment_types = XX_SegmentType.objects.filter(is_active=True).order_by('display_order')
        
        for transaction_id in transaction_ids:
            try:
                # Get transaction
                transaction = xx_BudgetTransfer.objects.filter(
                    transaction_id=transaction_id
                ).first()
                
                if not transaction:
                    results.append({
                        "transaction_id": transaction_id,
                        "error": "Transaction not found",
                        "status": "not_found"
                    })
                    continue
                
                # Get all transfers for this transaction
                transfers = xx_TransactionTransfer.objects.filter(
                    transaction_id=transaction_id
                ).select_related('transaction').order_by('transfer_id')
                
                # Calculate summary totals
                total_from = transfers.aggregate(Sum('from_center'))['from_center__sum'] or Decimal('0')
                total_to = transfers.aggregate(Sum('to_center'))['to_center__sum'] or Decimal('0')
                
                # Build transfer details with segments and budget info
                transfer_details = []
                for transfer in transfers:
                    # Get transaction segments
                    transaction_segments = XX_TransactionSegment.objects.filter(
                        transaction_transfer=transfer
                    ).select_related('segment_type', 'from_segment_value', 'to_segment_value')
                    
                    # Build segments dictionary with dynamic keys
                    segments_dict = {}
                    segment_codes_dict = {}  # For balance report lookup
                    
                    for ts in transaction_segments:
                        segment_key = f"segment_{ts.segment_type.segment_id}"
                        
                        # Determine which segment value to use for balance lookup
                        # Use from_segment if it exists, otherwise to_segment
                        lookup_segment = ts.from_segment_value if ts.from_segment_value else ts.to_segment_value
                        
                        segments_dict[segment_key] = {
                            "segment_name": ts.segment_type.segment_name,
                            "segment_id": ts.segment_type.segment_id,
                            "from_code": ts.from_segment_value.code if ts.from_segment_value else "",
                            "from_name": ts.from_segment_value.alias if ts.from_segment_value else "",
                            "to_code": ts.to_segment_value.code if ts.to_segment_value else "",
                            "to_name": ts.to_segment_value.alias if ts.to_segment_value else ""
                        }
                        
                        if lookup_segment:
                            segment_codes_dict[str(ts.segment_type.segment_id)] = lookup_segment.code
                    
                    # Ensure all segment types are present (even if empty)
                    for seg_type in segment_types:
                        segment_key = f"segment_{seg_type.segment_id}"
                        if segment_key not in segments_dict:
                            segments_dict[segment_key] = {
                                "segment_name": seg_type.segment_name,
                                "segment_id": seg_type.segment_id,
                                "from_code": "",
                                "from_name": "",
                                "to_code": "",
                                "to_name": ""
                            }
                    
                    # Get budget control information from balance report
                    budget_info = self._get_budget_control_info(
                        segment_codes_dict,
                        transaction.control_budget
                    )
                    
                    transfer_data = {
                        "transfer_id": transfer.transfer_id,
                        "segments": segments_dict,
                        "from_center": float(transfer.from_center) if transfer.from_center else 0.0,
                        "to_center": float(transfer.to_center) if transfer.to_center else 0.0,
                        "reason": transfer.reason or "",
                        "budget_control": budget_info
                    }
                    transfer_details.append(transfer_data)
                
                # Build comprehensive transaction report
                transaction_report = {
                    "transaction_id": transaction_id,
                    "code": transaction.code,
                    "budget_type": transaction.type or "",
                    "requested_by": transaction.requested_by,
                    "request_date": transaction.request_date.isoformat() if transaction.request_date else None,
                    "transaction_date": transaction.transaction_date,
                    "transfer_type": transaction.transfer_type or "",
                    "type": transaction.type or "",
                    "control_budget": transaction.control_budget or "",
                    "status": transaction.status,
                    "status_level": transaction.status_level,
                    "notes": transaction.notes or "",
                    "linked_transfer_id": transaction.linked_transfer_id,
                    "summary": {
                        "total_transfers": transfers.count(),
                        "total_from_center": float(total_from),
                        "total_to_center": float(total_to),
                        "balanced": float(total_from) == float(total_to),
                        "balance_difference": float(total_from) - float(total_to)
                    },
                    "transfers": transfer_details,
                    "status": "success"
                }
                
                results.append(transaction_report)
                
            except Exception as e:
                results.append({
                    "transaction_id": transaction_id,
                    "error": str(e),
                    "status": "error"
                })
        
        # Return response
        if len(transaction_ids) == 1:
            return Response(results[0] if results else {}, status=status.HTTP_200_OK)
        else:
            success_count = sum(1 for r in results if r.get('status') == 'success')
            error_count = len(results) - success_count
            
            return Response(
                {
                    "count": len(results),
                    "success_count": success_count,
                    "error_count": error_count,
                    "transactions": results
                },
                status=status.HTTP_200_OK
            )
    
    def _get_budget_control_info(self, segment_codes_dict, control_budget_name):
        """
        Get budget control information from XX_DynamicBalanceReport.
        
        Args:
            segment_codes_dict: Dict of {segment_type_id: segment_code}
            control_budget_name: Control budget name from transaction
            
        Returns:
            Dict with budget control information
        """
        try:
            # Query balance report matching segment combination and control budget
            balance_report = XX_DynamicBalanceReport.objects.filter(
                control_budget_name=control_budget_name
            ).first()
            
            # Try to find exact match based on segments
            if balance_report is None and segment_codes_dict:
                # Try querying with segment values
                for report in XX_DynamicBalanceReport.objects.filter(
                    control_budget_name=control_budget_name
                ).all():
                    # Check if segment_values match
                    if report.segment_values == segment_codes_dict:
                        balance_report = report
                        break
            
            if balance_report:
                # Build segment info for response
                segment_info = {}
                for seg_id, seg_code in balance_report.segment_values.items():
                    segment_info[f"segment{seg_id}"] = seg_code
                
                return {
                    "control_budget_name": balance_report.control_budget_name or "",
                    "period_name": balance_report.as_of_period or "",
                    "budget": float(balance_report.budget_ytd) if balance_report.budget_ytd else 0.0,
                    "encumbrance": float(balance_report.encumbrance_ytd) if balance_report.encumbrance_ytd else 0.0,
                    "funds_available": float(balance_report.funds_available_asof) if balance_report.funds_available_asof else 0.0,
                    "actual": float(balance_report.actual_ytd) if balance_report.actual_ytd else 0.0,
                    "other": float(balance_report.other_ytd) if balance_report.other_ytd else 0.0,
                    "created_at": balance_report.created_at.isoformat() if balance_report.created_at else None,
                    **segment_info
                }
            else:
                # Return empty structure if no balance report found
                return {
                    "control_budget_name": control_budget_name or "",
                    "period_name": "",
                    "budget": 0.0,
                    "encumbrance": 0.0,
                    "funds_available": 0.0,
                    "actual": 0.0,
                    "other": 0.0,
                    "created_at": None
                }
                
        except Exception as e:
            # Return empty structure on error
            return {
                "control_budget_name": control_budget_name or "",
                "period_name": "",
                "budget": 0.0,
                "encumbrance": 0.0,
                "funds_available": 0.0,
                "actual": 0.0,
                "other": 0.0,
                "created_at": None,
                "error": str(e)
            }
