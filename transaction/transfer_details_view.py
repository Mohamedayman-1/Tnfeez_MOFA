from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from decimal import Decimal

from .models import xx_TransactionTransfer
from budget_management.models import xx_BudgetTransfer
from account_and_entitys.models import XX_SegmentType, XX_TransactionSegment


class TransactionTransferDetailsView(APIView):
    """
    Retrieve detailed transfer information for one or multiple transactions.
    
    Supports:
    - Single transaction: GET /api/transactions/transfer-details/?transaction_id=123
    - Multiple transactions: GET /api/transactions/transfer-details/?transaction_id=123,456,789
    - POST body: POST /api/transactions/transfer-details/ with {"transaction_ids": [123, 456, 789]}
    
    Response structure for single transaction:
    {
        "transaction_id": 123,
        "transaction_code": "FAR-2024-001",
        "transaction_status": "approved",
        "request_date": "2024-01-15",
        "summary": {
            "total_transfers": 5,
            "total_from_center": 100000.00,
            "total_to_center": 100000.00,
            "balanced": true
        },
        "transfers": [
            {
                "transfer_id": 1,
                "segments": {
                    "1": {"segment_name": "Entity", "from_code": "100", "to_code": "101", ...},
                    "2": {"segment_name": "Account", "from_code": "5000", "to_code": "5000", ...}
                },
                "from_center": "50000.00",
                "to_center": "0.00",
                "available_budget": "200000.00",
                ...
            },
            ...
        ]
    }
    
    Response structure for multiple transactions:
    {
        "count": 3,
        "transactions": [
            { ... transaction_1_data ... },
            { ... transaction_2_data ... },
            { ... transaction_3_data ... }
        ]
    }
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
        
        return self._get_transfer_details(transaction_ids)
    
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
        
        return self._get_transfer_details(transaction_ids)
    
    def _get_transfer_details(self, transaction_ids):
        """Core logic to retrieve and structure transfer details."""
        results = []
        
        # Get all segment types ordered by display_order
        segment_types = XX_SegmentType.objects.filter(is_active=True).order_by('display_order')
        
        for transaction_id in transaction_ids:
            try:
                # Check if transaction exists
                transaction = xx_BudgetTransfer.objects.filter(
                    transaction_id=transaction_id
                ).first()
                
                if not transaction:
                    results.append({
                        "transaction_id": transaction_id,
                        "error": "Transaction not found",
                        "status": "not_found",
                        "transfers": []
                    })
                    continue
                
                # Get all transfers for this transaction
                transfers = xx_TransactionTransfer.objects.filter(
                    transaction_id=transaction_id
                ).select_related('transaction').order_by('transfer_id')
                
                # Calculate summary totals
                total_from = transfers.aggregate(Sum('from_center'))['from_center__sum'] or Decimal('0')
                total_to = transfers.aggregate(Sum('to_center'))['to_center__sum'] or Decimal('0')
                
                # Check if transaction is balanced
                is_balanced = float(total_from) == float(total_to)
                
                # Build transfer list with dynamic segments
                transfer_list = []
                for transfer in transfers:
                    # Get all transaction segments for this transfer
                    transaction_segments = XX_TransactionSegment.objects.filter(
                        transaction_transfer=transfer
                    ).select_related('segment_type', 'from_segment_value', 'to_segment_value')
                    
                    # Build segments dictionary
                    segments_dict = {}
                    for ts in transaction_segments:
                        segment_key = f"segment_{ts.segment_type.segment_id}"
                        segments_dict[segment_key] = {
                            "segment_name": ts.segment_type.segment_name,
                            "from_code": ts.from_segment_value.code if ts.from_segment_value else "",
                            "from_name": ts.from_segment_value.alias if ts.from_segment_value else "",
                            "to_code": ts.to_segment_value.code if ts.to_segment_value else "",
                            "to_name": ts.to_segment_value.alias if ts.to_segment_value else ""
                        }
                    
                    # Ensure all segment types are present (even if empty)
                    for seg_type in segment_types:
                        segment_key = f"segment_{seg_type.segment_id}"
                        if segment_key not in segments_dict:
                            segments_dict[segment_key] = {
                                "segment_name": seg_type.segment_name,
                                "from_code": "",
                                "from_name": "",
                                "to_code": "",
                                "to_name": ""
                            }
                    
                    transfer_data = {
                        "transfer_id": transfer.transfer_id,
                        "segments": segments_dict,  # Group all segments under "segments" key
                        "from_center": float(transfer.from_center) if transfer.from_center else 0.0,
                        "to_center": float(transfer.to_center) if transfer.to_center else 0.0,
                        "reason": transfer.reason or "",
                        "available_budget": float(transfer.available_budget) if transfer.available_budget else 0.0,
                        "approved_budget": float(transfer.approved_budget) if transfer.approved_budget else 0.0,
                        "encumbrance": float(transfer.encumbrance) if transfer.encumbrance else 0.0,
                        "actual": float(transfer.actual) if transfer.actual else 0.0
                    }
                    transfer_list.append(transfer_data)
                
                # Structure the response
                transaction_data = {
                    "transaction_id": transaction_id,
                    "transaction_code": transaction.code,
                    "transaction_status": transaction.status,
                    "status_level": transaction.status_level,
                    "request_date": transaction.request_date.isoformat() if transaction.request_date else None,
                    "transaction_date": transaction.transaction_date.isoformat() if transaction.transaction_date else None,
                    "requested_by": transaction.requested_by,
                    "notes": transaction.notes,
                    "summary": {
                        "total_transfers": transfers.count(),
                        "total_from_center": float(total_from),
                        "total_to_center": float(total_to),
                        "balanced": is_balanced,
                        "balance_difference": float(total_from) - float(total_to) if not is_balanced else 0.0
                    },
                    "transfers": transfer_list,
                    "status": "success"
                }
                
                results.append(transaction_data)
                
            except Exception as e:
                results.append({
                    "transaction_id": transaction_id,
                    "error": str(e),
                    "status": "error",
                    "transfers": []
                })
        
        # Return response
        if len(transaction_ids) == 1:
            # Single transaction - return object directly
            return Response(results[0] if results else {}, status=status.HTTP_200_OK)
        else:
            # Multiple transactions - return array
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
