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
    XX_DynamicBalanceReport,
    XX_gfs_Mamping
)
from account_and_entitys.oracle import OracleBalanceReportManager


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
        
        # Get only required segment types ordered by display_order
        segment_types = XX_SegmentType.objects.filter(
            is_active=True,
            is_required=True
        ).order_by('display_order')

        gfs_mappings = {}
        all_mappings = XX_gfs_Mamping.objects.filter(
            is_active=True
        ).values('From_value', 'Target_value')
        for mapping in all_mappings:
            from_value = mapping['From_value']
            if from_value and from_value not in gfs_mappings:
                gfs_mappings[from_value] = mapping['Target_value']
        
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
                    
                    # Get budget control information using OracleBalanceReportManager
                    budget_info = self._get_budget_control_info(
                        transfer,
                        segment_codes_dict
                    )

                    segment_11_code = segment_codes_dict.get("11")
                    gfs_code = gfs_mappings.get(segment_11_code, 0) if segment_11_code else 0
                    
                    transfer_data = {
                        "transfer_id": transfer.transfer_id,
                        "segments": segments_dict,
                        "from_center": float(transfer.from_center) if transfer.from_center else 0.0,
                        "to_center": float(transfer.to_center) if transfer.to_center else 0.0,
                        "reason": transfer.reason or "",
                        "gfs_code": gfs_code
                        # "budget_control": budget_info
                    }
                    transfer_details.append(transfer_data)
                


                # get gfs code from dynamic balance report
               


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
                    "notes": transaction.notes or "",
                    "transfers": transfer_details,
                    "status": "success",
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
    
    def _get_budget_control_info(self, transfer, segment_codes_dict):
        """
        Get budget control information using OracleBalanceReportManager (same as transfer list view).
        
        Args:
            transfer: xx_TransactionTransfer object
            segment_codes_dict: Dict of {segment_type_id: segment_code}
            
        Returns:
            Dict with budget control information for all control budgets
        """
        try:
            # Initialize Oracle balance manager
            balance_manager = OracleBalanceReportManager()
            
            # Determine transfer direction
            from_center_val = float(transfer.from_center) if transfer.from_center not in [None, ""] else 0.0
            to_center_val = float(transfer.to_center) if transfer.to_center not in [None, ""] else 0.0
            is_source_transfer = from_center_val > 0  # True = taking funds (FROM), False = receiving funds (TO)
            
            # Build segment filters from XX_TransactionSegment records
            transaction_segments = transfer.transaction_segments.select_related(
                'segment_type', 'from_segment_value', 'to_segment_value'
            )
            
            segment_filters = {}
            for trans_seg in transaction_segments:
                segment_type_id = trans_seg.segment_type_id
                
                # Select the correct segment value based on transfer direction
                if is_source_transfer:
                    segment_code = trans_seg.from_segment_value.code if trans_seg.from_segment_value else None
                else:
                    segment_code = trans_seg.to_segment_value.code if trans_seg.to_segment_value else None
                
                if segment_code:
                    segment_filters[segment_type_id] = segment_code
            
            # Get balance data from XX_Segment_Funds using OracleBalanceReportManager
            result = balance_manager.get_segments_fund(segment_filters=segment_filters)
            data = result.get("data", [])
            
            if data and len(data) > 0:
                # Return first control budget record (primary)
                record = data[0]
                
                # Build segment info for response
                segment_info = {}
                for seg_id, seg_code in segment_filters.items():
                    segment_info[f"segment{seg_id}"] = seg_code
                
                return {
                    "control_budget_name": record.get("Control_budget_name", ""),
                    "period_name": record.get("As_of_period", ""),
                    "budget": float(record.get("Budget", 0.0)),
                    "encumbrance": float(record.get("Encumbrance", 0.0)),
                    "funds_available": float(record.get("Funds_available", 0.0)),
                    "actual": float(record.get("Actual", 0.0)),
                    "other": float(record.get("Other", 0.0)),
                    "total_budget": float(record.get("Total_budget", 0.0)),
                    "initial_budget": float(record.get("Initial_budget", 0.0)),
                    "budget_adjustments": float(record.get("Budget_adjustments", 0.0)),
                    "commitments": float(record.get("Commitments", 0.0)),
                    "expenditures": float(record.get("Expenditures", 0.0)),
                    "obligations": float(record.get("Obligation", 0.0)),
                    "all_control_budgets": data,  # Include all control budget records
                    **segment_info
                }
            else:
                # Return empty structure if no balance data found
                return self._empty_budget_control(transfer.transaction.control_budget if hasattr(transfer.transaction, 'control_budget') else "")
                
        except Exception as e:
            # Return empty structure on error with error message
            return {
                "control_budget_name": "",
                "period_name": "",
                "budget": 0.0,
                "encumbrance": 0.0,
                "funds_available": 0.0,
                "actual": 0.0,
                "other": 0.0,
                "total_budget": 0.0,
                "error": str(e)
            }
    
    def _empty_budget_control(self, control_budget_name):
        """Return empty budget control structure."""
        return {
            "control_budget_name": control_budget_name or "",
            "period_name": "",
            "budget": 0.0,
            "encumbrance": 0.0,
            "funds_available": 0.0,
            "actual": 0.0,
            "other": 0.0,
            "total_budget": 0.0
        }
