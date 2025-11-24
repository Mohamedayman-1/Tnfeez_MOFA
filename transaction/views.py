import rest_framework
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import xx_TransactionTransfer
from account_and_entitys.models import (
    XX_Entity,
    XX_Account,
    XX_Project,
    XX_PivotFund,
    XX_ACCOUNT_ENTITY_LIMIT,
    XX_Segment_Funds,
)
from budget_management.models import xx_BudgetTransfer
from .serializers import (
    TransactionTransferSerializer,
    TransactionTransferDynamicSerializer,
    TransactionTransferCreateSerializer,
    TransactionTransferUpdateSerializer,
)
from .managers import TransactionSegmentManager
from decimal import Decimal
from django.db.models import Sum
from public_funtion.update_pivot_fund import update_pivot_fund
from django.utils import timezone
from user_management.models import xx_notification
import pandas as pd
import io
import os
import base64
import time
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from pathlib import Path
from django.conf import settings
import difflib
import string
from oracle_fbdi_integration.core.journal_manager import (
    create_journal_entry_data,
    JournalTemplateManager,
)
from oracle_fbdi_integration.core.upload_manager import (
    encode_csv_to_base64,
    build_journal_soap_envelope,
    upload_journal_fbdi,
)
from account_and_entitys.utils import get_oracle_report_data  # Legacy - deprecated
from account_and_entitys.oracle import OracleBalanceReportManager, OracleSegmentMapper
from oracle_fbdi_integration.utilities.journal_integration import create_and_upload_journal
from oracle_fbdi_integration.utilities.budget_integration import create_and_upload_budget
from oracle_fbdi_integration.utilities.automatic_posting import submit_automatic_posting
from oracle_fbdi_integration.utilities.Status import wait_for_job
from budget_management.models import xx_BudgetTransfer
def validate_transaction_dynamic(data, code=None):
    """
    Validate transaction transfer data with DYNAMIC SEGMENTS
    Returns a list of validation errors or empty list if valid
    
    New format: Uses 'segments' dict instead of hardcoded cost_center_code, account_code, project_code
    """
    from account_and_entitys.managers.segment_manager import SegmentManager
    from account_and_entitys.models import XX_SegmentType
    
    errors = []

    # Validation 1: Check required fields
    required_fields = [
        "from_center",
        "to_center",
        "approved_budget",
        "available_budget",
        "encumbrance",
        "actual",
        "segments",  # NEW: Dynamic segments required
    ]
    
    # Normalize empty strings to 0
    if data.get("from_center") == "":
        data["from_center"] = 0
    if data.get("to_center") == "":
        data["to_center"] = 0
    if data.get("approved_budget") == "":
        data["approved_budget"] = 0
    if data.get("available_budget") == "":
        data["available_budget"] = 0
    if data.get("encumbrance") == "":
        data["encumbrance"] = 0
    if data.get("actual") == "":
        data["actual"] = 0

    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"{field} is required")

    # If basic required fields are missing, stop further validation
    if errors:
        return errors

    # Validation 2: from_center or to_center must be positive
    if code and code[0:3] != "AFR":
        if Decimal(str(data["from_center"])) < 0:
            errors.append("from amount must be positive")

        if Decimal(str(data["to_center"])) < 0:
            errors.append("to amount must be positive")

    # Validation 3: Check if both from_center and to_center are positive
    if Decimal(str(data["from_center"])) > 0 and Decimal(str(data["to_center"])) > 0:
        errors.append("Can't have value in both from and to at the same time")

    # Validation 4: Check if available_budget > from_center
    if code and code[0:3] != "AFR":
        from_center = Decimal(str(data["from_center"]))
        available_budget = Decimal(str(data["available_budget"]))

        if from_center > available_budget:
            errors.append(
                f"المبلغ المحول [{from_center:,.2f}] يجب ان يكون اصغر من او يساوي المبلغ المتاح داخل الموازنة [{available_budget:,.2f}]"
            )
    # Validation 5: Validate dynamic segments structure
    segments_data = data.get("segments", {})
    if segments_data:
        validation_result = SegmentManager.validate_transaction_segments(segments_data)
        if not validation_result['valid']:
            errors.extend(validation_result['errors'])
    else:
        errors.append("Segment data is required")

    # Validation 6: Check for duplicate transfers (same transaction + segment combination)
    if "transaction_id" in data and segments_data:
        from transaction.models import xx_TransactionTransfer
        from account_and_entitys.models import XX_TransactionSegment
        
        # Build a query to find existing transfers with same segment combination
        existing_transfers = xx_TransactionTransfer.objects.filter(
            transaction=data["transaction_id"]
        )
        
        # If we're validating an existing record, exclude it
        if "transfer_id" in data and data["transfer_id"]:
            existing_transfers = existing_transfers.exclude(transfer_id=data["transfer_id"])
        
        # Check each existing transfer for matching segment combination
        for existing_transfer in existing_transfers:
            existing_segments = existing_transfer.get_segments_dict()
            
            # Compare segment combinations
            # NEW SIMPLIFIED FORMAT: Compare single 'code' field instead of from_code/to_code pairs
            is_duplicate = True
            for seg_id, seg_data in segments_data.items():
                existing_seg = existing_segments.get(int(seg_id))
                if not existing_seg:
                    is_duplicate = False
                    break
                
                # Check if format is simplified (has 'code') or old format (has 'from_code'/'to_code')
                if 'code' in seg_data:
                    # NEW SIMPLIFIED FORMAT: Compare single code
                    # For existing segments, check against from_code OR to_code (whichever is populated)
                    existing_code = existing_seg.get('from_code') or existing_seg.get('to_code')
                    if existing_code != seg_data.get('code'):
                        is_duplicate = False
                        break
                else:
                    # OLD FORMAT: Compare both from_code and to_code
                    if (existing_seg['from_code'] != seg_data.get('from_code') or
                        existing_seg['to_code'] != seg_data.get('to_code')):
                        is_duplicate = False
                        break
            
            if is_duplicate:
                # Build summary based on format
                if any('code' in v for v in segments_data.values()):
                    # NEW FORMAT: Show single codes
                    segment_summary = ", ".join([
                        str(v.get('code')) for v in segments_data.values() if 'code' in v
                    ])
                else:
                    # OLD FORMAT: Show from→to
                    segment_summary = ", ".join([
                        f"{v.get('from_code')}→{v.get('to_code')}" 
                        for v in segments_data.values()
                    ])
                errors.append(
                    f"Duplicate transfer with same segment combination ({segment_summary}) "
                    f"found (ID: {existing_transfer.transfer_id})"
                )
                break

    return errors


def validate_transaction(data, code=None):
    """
    LEGACY validation function - maintains backward compatibility
    Validate ADJD transaction transfer data against 10 business rules
    Returns a list of validation errors or empty list if valid
    
    NOTE: This is kept for backward compatibility with legacy code.
    New code should use validate_transaction_dynamic() instead.
    """
    errors = []

    # Validation 1: Check required fields
    required_fields = [
        "from_center",
        "to_center",
        "approved_budget",
        "available_budget",
        "encumbrance",
        "actual",
        "cost_center_code",
        "account_code",
        "project_code",
    ]
    if data["from_center"] == "":
        data["from_center"] = 0
    if data["to_center"] == "":
        data["to_center"] = 0
    if data["approved_budget"] == "":
        data["approved_budget"] = 0
    if data["available_budget"] == "":
        data["available_budget"] = 0
    if data["encumbrance"] == "":
        data["encumbrance"] = 0
    if data["actual"] == "":
        data["actual"] = 0

    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"{field} is required")

    # If basic required fields are missing, stop further validation
    if errors:
        return errors

    # Validation 2: from_center or to_center must be positive
    if code[0:3] != "AFR":
        if Decimal(data["from_center"]) < 0:
            errors.append("from amount must be positive")

        if Decimal(data["to_center"]) < 0:
            errors.append("to amount must be positive")

    # Validation 3: Check if both from_center and to_center are positive

    if Decimal(data["from_center"]) > 0 and Decimal(data["to_center"]) > 0:

        errors.append("Can't have value in both from and to at the same time")

    # Validation 4: Check if available_budget > from_center
    #if code[0:3] != "AFR":
    #    if Decimal(data["from_center"]) > Decimal(data["available_budget"]):
    #        errors.append(" from value must be less or equal available_budget value")

    # Validation 5: Check for duplicate transfers (same transaction, from_account, to_account)
    existing_transfers = xx_TransactionTransfer.objects.filter(
        transaction=data["transaction_id"],
        cost_center_code=data["cost_center_code"],
        account_code=data["account_code"],
        project_code=data["project_code"],
    )

    # If we're validating an existing record, exclude it from the duplicate check
    if "transfer_id" in data and data["transfer_id"]:
        existing_transfers = existing_transfers.exclude(transfer_id=data["transfer_id"])

    if existing_transfers.exists():
        duplicates = [f"ID: {t.transfer_id}" for t in existing_transfers[:3]]
        errors.append(
            f"Duplicate transfer for account code {data['account_code']} and project code {data['project_code']} and cost center {data['cost_center_code']} (Found: {', '.join(duplicates)})"
        )

    return errors


def validate_transaction_transfer_dynamic(data, code=None, errors=None):
    """
    Validate transaction transfer with DYNAMIC SEGMENTS
    
    Checks:
    1. Segment combination exists in XX_PivotFund
    2. Transfer is allowed per XX_ACCOUNT_ENTITY_LIMIT rules
    
    Args:
        data: Must contain 'segments' dict and 'from_center'/'to_center'
        code: Transfer type code (FAR, AFR, FAD)
        errors: Existing errors list to append to
    
    Returns:
        list: Updated errors list
    """
    from account_and_entitys.models import XX_Segment, XX_SegmentType, XX_PivotFund
    
    if errors is None:
        errors = []
    
    segments_data = data.get("segments", {})
    if not segments_data:
        errors.append("Segments data is required for validation")
        return errors
    
    # Build segment codes for validation
    # NEW SIMPLIFIED FORMAT: Extract single 'code' or old format 'from_code'/'to_code'
    segment_codes = {}
    
    # Determine transfer direction (source or destination)
    from_center = float(data.get('from_center', 0) or 0)
    to_center = float(data.get('to_center', 0) or 0)
    is_source = from_center > 0  # True if taking funds, False if receiving
    
    for seg_id, seg_vals in segments_data.items():
        try:
            segment_type = XX_SegmentType.objects.get(segment_id=int(seg_id))
            
            # Check format: new simplified (single 'code') or old (from_code/to_code)
            if 'code' in seg_vals:
                # NEW SIMPLIFIED FORMAT: Single code
                code = seg_vals.get('code')
                # For validation, we need both from/to - use code for the appropriate direction
                segment_codes[segment_type.segment_type.lower()] = {
                    'from': code if is_source else None,
                    'to': code if not is_source else None,
                    'code': code  # Keep original for reference
                }
            else:
                # OLD FORMAT: Separate from_code and to_code
                from_code = seg_vals.get('from_code')
                to_code = seg_vals.get('to_code')
                
                # Store codes by segment type name for compatibility
                segment_codes[segment_type.segment_type.lower()] = {
                    'from': from_code,
                    'to': to_code
                }
        except XX_SegmentType.DoesNotExist:
            errors.append(f"Invalid segment type ID: {seg_id}")
            continue
    
    # Get entity, account, project codes (legacy compatibility)
    entity_codes = segment_codes.get('entity', {})
    account_codes = segment_codes.get('account', {})
    project_codes = segment_codes.get('project', {})
    
    from_entity = entity_codes.get('from')
    to_entity = entity_codes.get('to')
    from_account = account_codes.get('from')
    to_account = account_codes.get('to')
    from_project = project_codes.get('from')
    to_project = project_codes.get('to')
    
    # Validation 1: Check for fund availability (code combination exists in PivotFund)
    if from_entity and from_account and from_project:
        from_combination_exists = XX_PivotFund.objects.filter(
            entity=from_entity,
            account=from_account,
            project=from_project,
        ).exists()
        
        if not from_combination_exists:
            errors.append(
                f"Source code combination not found: Entity={from_entity}, "
                f"Account={from_account}, Project={from_project}"
            )
    
    if to_entity and to_account and to_project:
        to_combination_exists = XX_PivotFund.objects.filter(
            entity=to_entity,
            account=to_account,
            project=to_project,
        ).exists()
        
        if not to_combination_exists:
            errors.append(
                f"Target code combination not found: Entity={to_entity}, "
                f"Account={to_account}, Project={to_project}"
            )
    
    # Validation 2: Check transfer permissions
    if from_entity and from_account and from_project:
        allowed_to_make_transfer = XX_ACCOUNT_ENTITY_LIMIT.objects.filter(
            entity_id=str(from_entity),
            account_id=str(from_account),
            project_id=str(from_project),
        ).first()
        
        if allowed_to_make_transfer is not None:
            if allowed_to_make_transfer.is_transer_allowed == "No":
                errors.append(
                    f"Transfer not allowed for Entity={from_entity}, "
                    f"Account={from_account}, Project={from_project}"
                )
            elif allowed_to_make_transfer.is_transer_allowed == "Yes":
                # Check source/target specific permissions
                if data.get("from_center", 0) > 0:
                    if allowed_to_make_transfer.is_transer_allowed_for_source != "Yes":
                        errors.append(
                            f"Transfer FROM this combination not allowed: "
                            f"Entity={from_entity}, Account={from_account}, Project={from_project}"
                        )
                
                if data.get("to_center", 0) > 0:
                    if allowed_to_make_transfer.is_transer_allowed_for_target != "Yes":
                        errors.append(
                            f"Transfer TO this combination not allowed: "
                            f"Entity={from_entity}, Account={from_account}, Project={from_project}"
                        )
    
    return errors


def validate_transcation_transfer(data, code=None, errors=None):
    """
    LEGACY validation function - maintains backward compatibility
    
    NOTE: This is kept for backward compatibility with legacy code.
    New code should use validate_transaction_transfer_dynamic() instead.
    """
    # Validation 1: Check for fund is available if not then no combination code
    existing_code_combintion = XX_PivotFund.objects.filter(
        entity=data["cost_center_code"],
        account=data["account_code"],
        project=data["project_code"],
    )
    if not existing_code_combintion.exists():
        errors.append(
            f"Code combination not found for {data['cost_center_code']} and {data['project_code']} and {data['account_code']}"
        )
    print(
        "existing_code_combintion",
        type(data["cost_center_code"]),
        ":",
        type(data["project_code"]),
        ":",
        type(data["account_code"]),
    )
    # Validation 2: Check if is allowed to make trasfer using this cost_center_code and account_code
    allowed_to_make_transfer = XX_ACCOUNT_ENTITY_LIMIT.objects.filter(
        entity_id=str(data["cost_center_code"]),
        account_id=str(data["account_code"]),
        project_id=str(data["project_code"]),
    ).first()
    print("allowed_to_make_transfer", allowed_to_make_transfer)

    # Check if no matching record found
    if allowed_to_make_transfer is not None:
        # Check transfer permissions if record exists
        if allowed_to_make_transfer.is_transer_allowed == "No":
            errors.append(
                f"Not allowed to make transfer for {data['cost_center_code']} and {data['project_code']} and {data['account_code']} according to the rules"
            )
        elif allowed_to_make_transfer.is_transer_allowed == "Yes":
            if data["from_center"] > 0:
                if allowed_to_make_transfer.is_transer_allowed_for_source != "Yes":
                    errors.append(
                        f"Not allowed to make transfer for {data['cost_center_code']} and {data['project_code']} and {data['account_code']} according to the rules (can't transfer from this account)"
                    )
            if data["to_center"] > 0:
                if allowed_to_make_transfer.is_transer_allowed_for_target != "Yes":
                    errors.append(
                        f"Not allowed to make transfer for {data['cost_center_code']} and {data['project_code']} and {data['account_code']} according to the rules (can't transfer to this account)"
                    )
    return errors


class TransactionTransferCreateView(APIView):
    """Create new transaction transfers with DYNAMIC SEGMENT support (single or batch)"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create transaction transfers with SIMPLIFIED dynamic segments.
        
        NEW SIMPLIFIED FORMAT (Dynamic Segments):
        Each transfer has EITHER from_center OR to_center (not both with positive values).
        Segments use single 'code' field - direction is determined by which center is filled.
        
        Example 1 - Taking funds (SOURCE):
           {
               "transaction": 123,
               "from_center": "10000.00",  # Taking funds
               "to_center": "0.00",        # Must be 0
               "reason": "Budget reduction",
               "segments": {
                   "1": {"code": "10000"},  # Entity code
                   "2": {"code": "50000"},  # Account code
                   "3": {"code": "10000"}   # Project code
               }
           }
        
        Example 2 - Receiving funds (DESTINATION):
           {
               "transaction": 123,
               "from_center": "0.00",        # Must be 0
               "to_center": "10000.00",      # Receiving funds
               "reason": "Budget increase",
               "segments": {
                   "1": {"code": "11000"},  # Entity code
                   "2": {"code": "51000"},  # Account code
                   "3": {"code": "10000"}   # Project code
               }
           }
        
        Example 3 - Batch transfer (array):
           [
               {
                   "transaction": 123,
                   "from_center": "50000.00",  # Source
                   "to_center": "0.00",
                   "reason": "From Dept A",
                   "segments": {"1": {"code": "10000"}, "2": {"code": "50000"}, "3": {"code": "10000"}}
               },
               {
                   "transaction": 123,
                   "from_center": "0.00",
                   "to_center": "50000.00",    # Destination
                   "reason": "To Dept B",
                   "segments": {"1": {"code": "11000"}, "2": {"code": "50000"}, "3": {"code": "10000"}}
               }
           ]
        
        LEGACY FORMAT (Backward Compatibility - still supported):
           {
               "transaction": 123,
               "cost_center_code": 1001,
               "account_code": 5100,
               "project_code": "PROJ01",
               "from_center": "10000.00",
               "to_center": "0.00"
           }
        """
        
        # Check if the data is a list/array or single object
        if isinstance(request.data, list):
            # Handle array of transfers
            if not request.data:
                return Response(
                    {
                        "error": "Empty data provided",
                        "message": "Please provide at least one transfer",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get transaction_id from the first item for batch operations
            transaction_id = request.data[0].get("transaction")
            if not transaction_id:
                return Response(
                    {
                        "error": "transaction_id is required",
                        "message": "You must provide a transaction_id for each transfer",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get budget transfer to check code
            try:
                budget_transfer = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)
            except xx_BudgetTransfer.DoesNotExist:
                return Response(
                    {"error": f"Budget transfer {transaction_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Delete all existing transfers for this transaction
            xx_TransactionTransfer.objects.filter(transaction=transaction_id).delete()

            # Process the new transfers
            results = []
            for index, transfer_data in enumerate(request.data):
                # Make sure all items have the same transaction ID
                if transfer_data.get("transaction") != transaction_id:
                    results.append(
                        {
                            "index": index,
                            "error": "All transfers must have the same transaction_id",
                            "data": transfer_data,
                        }
                    )
                    continue

                # Check if using dynamic segments (NEW) or legacy format
                if "segments" in transfer_data:
                    # NEW FORMAT: Dynamic segments
                    serializer = TransactionTransferCreateSerializer(data=transfer_data)
                    if serializer.is_valid():
                        try:
                            transfer = serializer.save()
                            # Return with dynamic segment details
                            response_serializer = TransactionTransferDynamicSerializer(transfer)
                            results.append(response_serializer.data)
                        except Exception as e:
                            results.append({
                                "index": index,
                                "error": str(e),
                                "data": transfer_data,
                            })
                    else:
                        results.append({
                            "index": index,
                            "error": serializer.errors,
                            "data": transfer_data,
                        })
                else:
                    # LEGACY FORMAT: Backward compatibility
                    serializer = TransactionTransferSerializer(data=transfer_data)
                    if serializer.is_valid():
                        transfer = serializer.save()
                        results.append(serializer.data)
                    else:
                        results.append({
                            "index": index,
                            "error": serializer.errors,
                            "data": transfer_data,
                        })

            return Response(results, status=status.HTTP_207_MULTI_STATUS)
        
        else:
            # Handle single transfer
            transaction_id = request.data.get("transaction")
            if not transaction_id:
                return Response(
                    {
                        "error": "transaction_id is required",
                        "message": "You must provide a transaction_id to create a transaction transfer",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get budget transfer to check code
            try:
                budget_transfer = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)
            except xx_BudgetTransfer.DoesNotExist:
                return Response(
                    {"error": f"Budget transfer {transaction_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Delete all existing transfers for this transaction
            xx_TransactionTransfer.objects.filter(transaction=transaction_id).delete()

            # Check if using dynamic segments (NEW) or legacy format
            if "segments" in request.data:
                # NEW FORMAT: Dynamic segments
                serializer = TransactionTransferCreateSerializer(data=request.data)
                if serializer.is_valid():
                    try:
                        transfer = serializer.save()
                        # Return with dynamic segment details
                        response_serializer = TransactionTransferDynamicSerializer(transfer)
                        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                    except Exception as e:
                        return Response(
                            {"error": str(e)},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                # LEGACY FORMAT: Backward compatibility
                transfer_data = request.data
                from_center = transfer_data.get("from_center")
                if from_center is None or str(from_center).strip() == "":
                    from_center = 0
                to_center = transfer_data.get("to_center")
                if to_center is None or str(to_center).strip() == "":
                    to_center = 0
                cost_center_code = transfer_data.get("cost_center_code")
                account_code = transfer_data.get("account_code")
                project_code = transfer_data.get("project_code")
                transfer_id = transfer_data.get("transfer_id")
                approved_budget = transfer_data.get("approved_budget")
                available_budget = transfer_data.get("available_budget")
                encumbrance = transfer_data.get("encumbrance")
                actual = transfer_data.get("actual")

                # Prepare data for validation function
                validation_data = {
                    "transaction_id": transaction_id,
                    "from_center": from_center,
                    "to_center": to_center,
                    "approved_budget": approved_budget,
                    "available_budget": available_budget,
                    "encumbrance": encumbrance,
                    "actual": actual,
                    "cost_center_code": cost_center_code,
                    "account_code": account_code,
                    "project_code": project_code,
                    "transfer_id": transfer_id,
                }

                serializer = TransactionTransferSerializer(data=validation_data)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class TransactionTransferListView(APIView):
    """List transaction transfers for a specific transaction with DYNAMIC SEGMENT support"""

    permission_classes = [IsAuthenticated]

    def _get_mofa_cost2_available(self, segments_for_validation):
        """
        Get available funds for the MOFA_COST_2 control budget that match the provided segments.
        """
        filters = {"CONTROL_BUDGET_NAME": "MOFA_COST_2"}

        for seg_id, seg_info in segments_for_validation.items():
            # Try to get the segment code from any available field
            seg_code = seg_info.get("code") or seg_info.get("from_code") or seg_info.get("to_code")
            if seg_code:
                filters[f"Segment{seg_id}"] = seg_code

        print(f"🔍 MOFA_COST_2 Query filters: {filters}")
        fund = XX_Segment_Funds.objects.filter(**filters).first()
        if not fund:
            print(f"⚠️  No MOFA_COST_2 fund found for filters: {filters}")
            return None

        value = getattr(fund, "FUNDS_AVAILABLE_PTD", None)
        available = float(value) if value not in [None, ""] else 0.0
        print(f"✅ MOFA_COST_2 available funds: {available}")
        return available

    def _get_total_budget(self, segments_for_validation):
        """
        Get TOTAL_BUDGET for the MOFA_COST_2 control budget that match the provided segments.
        """
        filters = {}

        for seg_id, seg_info in segments_for_validation.items():
            # Try to get the segment code from any available field
            seg_code = seg_info.get("code") or seg_info.get("from_code") or seg_info.get("to_code")
            if seg_code:
                filters[f"Segment{seg_id}"] = seg_code

        print(f"🔍 MOFA_COST_2 Query filters: {filters}")
        values = XX_Segment_Funds.objects.filter(**filters)
        Fund_avaiable = 0.0
        for Funds in values:
            if Funds.CONTROL_BUDGET_NAME=="MOFA_CASH":
              Fund_avaiable=Funds.FUNDS_AVAILABLE_PTD 
            elif Funds.CONTROL_BUDGET_NAME=="MOFA_COST_2":
                Total_budget=Funds.TOTAL_BUDGET     


        

      
        return Fund_avaiable ,Total_budget

    def get(self, request):
        transaction_id = request.query_params.get("transaction")
        print(f"Transaction ID: {transaction_id}")
        if not transaction_id:
            return Response(
                {
                    "error": "transaction_id is required",
                    "message": "Please provide a transaction ID to retrieve related transfers",
                },
                status=rest_framework.status.HTTP_400_BAD_REQUEST,
            )

        try:
            transaction_object = xx_BudgetTransfer.objects.get(
                transaction_id=transaction_id
            )
        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {
                    "error": "Transaction not found",
                    "message": f"No budget transfer found with ID {transaction_id}",
                },
                status=rest_framework.status.HTTP_404_NOT_FOUND,
            )
          
        status = False
        if transaction_object.code[0:3] != "FAD":

            if transaction_object.status_level and transaction_object.status_level < 1:
                status = "is rejected"
            elif (
                transaction_object.status_level and transaction_object.status_level == 1
            ):
                status = "not yet sent for approval"
            elif (
                transaction_object.status_level and transaction_object.status_level == 4
            ):
                status = "approved"
            else:
                status = "waiting for approval"
        else:
            if transaction_object.status_level and transaction_object.status_level < 1:
                status = "is rejected"
            elif (
                transaction_object.status_level and transaction_object.status_level == 3
            ):
                status = "approved"
            elif (
                transaction_object.status_level and transaction_object.status_level == 1
            ):
                status = "not yet sent for approval"
            else:
                status = "waiting for approval"

        transfers = xx_TransactionTransfer.objects.filter(transaction=transaction_id)
        # Use TransactionTransferDynamicSerializer for full segment details
        serializer = TransactionTransferDynamicSerializer(transfers, many=True)

        # Initialize managers for Oracle integration
        balance_manager = OracleBalanceReportManager()
        segment_mapper = OracleSegmentMapper()
        
        Total_from_Value=0
        Total_to_Value=0
        for transfer in transfers:
            # Determine transfer direction FIRST
            from_center_val = float(transfer.from_center) if transfer.from_center not in [None, ""] else 0.0
            to_center_val = float(transfer.to_center) if transfer.to_center not in [None, ""] else 0.0
            is_source_transfer = from_center_val > 0  # True = taking funds (FROM), False = receiving funds (TO)

            Total_to_Value+=to_center_val
            Total_from_Value+=from_center_val
            
            # Build dynamic segment filters from transfer's XX_TransactionSegment records
            # Get all segments for this transfer (check both FROM and TO sides)
            transaction_segments = transfer.transaction_segments.select_related(
                'segment_type', 'from_segment_value', 'to_segment_value'
            )
            print(f"\n🔍 Transfer {transfer.transfer_id}: Found {transaction_segments.count()} segments")
            print(f"   Direction: {'SOURCE (taking funds)' if is_source_transfer else 'DESTINATION (receiving funds)'}")
            print(f"   from_center={from_center_val}, to_center={to_center_val}")
            
            # Build segment_filters dict: {segment_type_id: segment_code}
            # Use FROM segments if taking funds, TO segments if receiving funds
            segment_filters = {}
            for trans_seg in transaction_segments:
                segment_type_id = trans_seg.segment_type_id
                
                # Select the correct segment value based on transfer direction
                if is_source_transfer:
                    # Taking funds - use FROM segment
                    segment_code = trans_seg.from_segment_value.code if trans_seg.from_segment_value else None
                else:
                    # Receiving funds - use TO segment
                    segment_code = trans_seg.to_segment_value.code if trans_seg.to_segment_value else None
                
                if segment_code:
                    segment_filters[segment_type_id] = segment_code
                    print(f"   ✓ Segment type {segment_type_id} ({trans_seg.segment_type.segment_name}): {segment_code}")
                else:
                    print(f"   ⚠️  Segment type {segment_type_id} ({trans_seg.segment_type.segment_name}): No code found")
            
            # Get balance data from XX_Segment_Funds database with dynamic segments
            print(f"   📊 Querying balance with filters: {segment_filters}")
            result = balance_manager.get_segments_fund(
                segment_filters=segment_filters
            )
            
            data = result.get("data", [])
            print(f"   📈 Found {len(data)} control budget records")
            
            # Store all control budget records for this transfer
            transfer.control_budget_records = data  # Attach to transfer object temporarily

            # Update transfer with first record (primary control budget) for backward compatibility
            if data and len(data) > 0:
                record = data[0]  # Use first record as primary
                transfer.available_budget = record.get("Funds_available", 0.0)
                transfer.approved_budget = record.get("Budget", 0.0)
                transfer.encumbrance = record.get("Encumbrance", 0.0)
                transfer.actual = record.get("Actual", 0.0)
                transfer.budget_adjustments = record.get("Budget_adjustments", 0.0)
                transfer.commitments = record.get("Commitments", 0.0)
                transfer.expenditures = record.get("Expenditures", 0.0)
                transfer.obligations = record.get("Obligation", 0.0)
                transfer.other_consumption = record.get("Other", 0.0)
                transfer.total_budget = record.get("Total_budget", 0.0)
                transfer.initial_budget = record.get("Initial_budget", 0.0)

            else:
                # No data found, set default values
                transfer.available_budget = 0.0
                transfer.approved_budget = 0.0
                transfer.encumbrance = 0.0
                transfer.actual = 0.0
                transfer.budget_adjustments = 0.0
                transfer.commitments = 0.0
                transfer.expenditures = 0.0
                transfer.initial_budget = 0.0
                transfer.obligations = 0.0
                transfer.other_consumption = 0.0
                transfer.total_budget = 0.0
                transfer.initial_budget = 0.0
                transfer.budget_adjustments = 0.0

            transfer.save()

        # Create response with validation for each transfer
        response_data = []
        for index, transfer_data in enumerate(serializer.data):
            transfer_obj = transfers[index]
            
            # Get dynamic segments
            segments_dict = transfer_obj.get_segments_dict()
            
            # Prepare validation data
            from_center_val = transfer_data.get("from_center", 0)
            from_center = float(from_center_val) if from_center_val not in [None, ""] else 0.0
            to_center = float(transfer_data.get("to_center", 0))
            transfer_id = transfer_data.get("transfer_id")
            approved_budget = float(transfer_data.get("approved_budget", 0))
            available_budget = float(transfer_data.get("available_budget", 0))
            encumbrance = float(transfer_data.get("encumbrance", 0))
            actual = float(transfer_data.get("actual", 0))
            total_budget = float(transfer_data.get("total_budget", 0))
            initial_budget = float(transfer_data.get("initial_budget", 0))
            budget_adjustments = float(transfer_data.get("budget_adjustments", 0))
            total_budget = float(transfer_data.get("total_budget", 0))

            # Build segments data for validation
            # Support both NEW SIMPLIFIED format (single code) and OLD format (from_code/to_code)
            segments_for_validation = {}
            is_source = from_center > 0 
            is_distination = to_center > 0
            
            for seg_id, seg_info in segments_dict.items():
                # Check if we have from_code or to_code populated
                from_code = seg_info.get('from_code')
                to_code = seg_info.get('to_code')
                
                # If using old format (both codes exist), keep as is
                if from_code and to_code:
                    segments_for_validation[seg_id] = {
                        'from_code': from_code,
                        'to_code': to_code
                    }
                # If NEW SIMPLIFIED format or single direction populated
                elif from_code or to_code:
                    # Use the code that corresponds to the transfer direction
                    active_code = from_code if is_source else to_code
                    if active_code:
                        segments_for_validation[seg_id] = {
                            'code': active_code
                        }
                    else:
                        # Fallback: use whichever code exists
                        segments_for_validation[seg_id] = {
                            'code': from_code if from_code else to_code
                        }
                else:
                    # No codes at all (shouldn't happen but handle gracefully)
                    segments_for_validation[seg_id] = {
                        'from_code': None,
                        'to_code': None
                    }
            
            validation_data = {
                "transaction_id": transaction_id,
                "from_center": from_center,
                "to_center": to_center,
                "approved_budget": approved_budget,
                "available_budget": available_budget,
                "encumbrance": encumbrance,
                "total_budget": total_budget,
                "initial_budget": initial_budget,
                "budget_adjustments": budget_adjustments,
                "actual": actual,
                "transfer_id": transfer_id,
                "segments": segments_for_validation,
            }
            # Initialize validation errors list
            validation_errors = []

            # Validate the transfer with dynamic segments (UNCOMMENTED for proper validation)
            validation_errors = validate_transaction_dynamic(
                validation_data, code=transaction_object.code
            )
            validation_errors = validate_transaction_transfer_dynamic(
                validation_data, code=transaction_object.code, errors=validation_errors
            )
            
            # Additional MOFA_COST_2 validation for source transfers
            if from_center > 0:
                mofa_available = self._get_mofa_cost2_available(segments_for_validation)
                if mofa_available is None:
                    validation_errors.append(
                        "MOFA_COST_2 budget record not found for the provided segments"
                    )
                else:
                  half_available = mofa_available / 2

                if from_center > half_available:
                    validation_errors.append(
                        f"اجمالى السيولة المنقولة [{from_center:,.2f}] من البند لا يجب ان تتخطى 50% "
                        f"من اجمالى موازنة التكاليف المعتمدة للبند المنقول منه [{half_available:,.2f}]"
                    )
            elif is_distination > 0:
                fund_ava,tot_budget = self._get_total_budget(segments_for_validation)
                if tot_budget is None and fund_ava is None:
                    validation_errors.append(
                        "MOFA_COST_2 budget record not found for the provided segments"
                    )
                elif float(to_center) + float(fund_ava) > float(tot_budget):
                    validation_errors.append(
                        f"اجمالى سيولة البند (السيولة المتاحة للبند المنقول إليه + القيمة المنقولة) اكبر من اجمالى موازنة تكاليف البند المنقول الية  برجاء إعادة التوزيع {float(tot_budget):,.1f} "
                    )
            

            if Total_from_Value > Total_to_Value:
                 validation_errors.append(
                    "  برجاء التحقق من قيمة ارصدت التوزيع حيث ان مجموع المنقول منه اكبر من مجموع المنقول اليه " 
                    
                    )
            elif Total_from_Value < Total_to_Value:
                validation_errors.append(
                    "برجاء التحقق من قيمة ارصدت التوزيع حيث ان مجموع المنقول اليه اكبر من مجموع المنقول منه " 
                )
                    
            # Add validation results to transfer data
            transfer_response = transfer_data.copy()
            transfer_response["validation_errors"] = validation_errors
            transfer_response["is_valid"] = len(validation_errors) == 0
            
            # Add all control budget records to response
            control_budget_records = getattr(transfer_obj, 'control_budget_records', [])
            transfer_response["control_budgets"] = control_budget_records
            transfer_response["control_budgets_count"] = len(control_budget_records)

            response_data.append(transfer_response)

        # Also add transaction-wide validation summary

        all_related_transfers = xx_TransactionTransfer.objects.filter(
            transaction=transaction_id
        )

        if all_related_transfers.exists():
            from_center_values = all_related_transfers.values_list(
                "from_center", flat=True
            )
            to_center_values = all_related_transfers.values_list("to_center", flat=True)
            total_from_center = sum(
                float(value) if value not in [None, ""] else 0
                for value in from_center_values
            )
            total_to_center = sum(
                float(value) if value not in [None, ""] else 0
                for value in to_center_values
            )

            if total_from_center == total_to_center:
                transaction_object.amount = total_from_center
                xx_BudgetTransfer.objects.filter(pk=transaction_id).update(
                    amount=total_from_center
                )

            if transaction_object.code[0:3] == "AFR":
                summary = {
                    "transaction_id": transaction_id,
                    "total_transfers": len(response_data),
                    "total_from": total_from_center,
                    "total_to": total_to_center,
                    "balanced": True,
                    "status": status,
                    "period": transaction_object.transaction_date + str(-25),
                }
            else:
                summary = {
                    "transaction_id": transaction_id,
                    "total_transfers": len(response_data),
                    "total_from": total_from_center,
                    "total_to": total_to_center,
                    "balanced": total_from_center == total_to_center,
                    "status": status,
                    "period": transaction_object.transaction_date + str(-25),
                }

            status = {"status": status}
            return Response(
                {"summary": summary, "transfers": response_data, "status": status}
            )
        else:
            summary = {
                "transaction_id": transaction_id,
                "total_transfers": 0,
                "total_from": 0,
                "total_to": 0,
                "balanced": True,
                "status": status,
                "period": transaction_object.transaction_date + str(-25),
            }
            status = {"status": status}
            return Response(
                {"summary": summary, "transfers": response_data, "status": status}
            )


class TransactionTransferDetailView(APIView):
    """Retrieve a specific transaction transfer with DYNAMIC SEGMENT support"""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            transfer = xx_TransactionTransfer.objects.get(pk=pk)
            # Use dynamic serializer to include segment details
            serializer = TransactionTransferDynamicSerializer(transfer)
            return Response(serializer.data)
        except xx_TransactionTransfer.DoesNotExist:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TransactionTransferUpdateView(APIView):
    """Update a transaction transfer with DYNAMIC SEGMENT support"""

    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        try:
            transfer = xx_TransactionTransfer.objects.get(pk=pk)
            
            # Check if updating with dynamic segments (NEW) or legacy format
            if "segments" in request.data:
                # NEW FORMAT: Dynamic segments
                serializer = TransactionTransferUpdateSerializer(
                    transfer, 
                    data=request.data,
                    partial=True
                )
                if serializer.is_valid():
                    updated_transfer = serializer.save()
                    # Return with dynamic segment details
                    response_serializer = TransactionTransferDynamicSerializer(updated_transfer)
                    return Response(response_serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                # LEGACY FORMAT: Backward compatibility
                serializer = TransactionTransferSerializer(
                    transfer, 
                    data=request.data, 
                    partial=True
                )
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except xx_TransactionTransfer.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class TransactionTransferDeleteView(APIView):
    """Delete an transaction transfer"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            transfer = xx_TransactionTransfer.objects.get(pk=pk)
            transfer.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except xx_TransactionTransfer.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class transcationtransferSubmit(APIView):
    """Submit transaction transfers for approval"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if we received a list or a single transaction ID
        print(f"Received data: {request.data}")

        if isinstance(request.data, dict):
            # Handle dictionary input for a single transaction
            print(f"Received dictionary data")
            if not request.data:
                return Response(
                    {
                        "error": "Empty data provided",
                        "message": "Please provide transaction data",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            transaction_id = request.data.get("transaction")

            if not transaction_id:
                return Response(
                    {
                        "error": "transaction id is required",
                        "message": "Please provide transaction id",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            pivot_updates = []

            try:
                # For dictionary input, get transfers from the database
                transfers = xx_TransactionTransfer.objects.filter(
                    transaction=transaction_id
                )
                code = xx_BudgetTransfer.objects.get(transaction_id=transaction_id).code
                print(f"Transfers found: {transfers.count()}")
                if len(transfers) < 2 and code[0:3] != "AFR":
                    return Response(
                        {
                            "error": "Not enough transfers",
                            "message": f"At least 2 transfers are required for transaction ID: {transaction_id}",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                for transfer in transfers:
                    if code[0:3] != "AFR":
                        if transfer.from_center is None or transfer.from_center <= 0:
                            if transfer.to_center is None or transfer.to_center <= 0:
                                return Response(
                                    {
                                        "error": "Invalid transfer amounts",
                                        "message": f"Each transfer must have a positive from_center or to_center value. Transfer ID {transfer.transfer_id} has invalid values.",
                                    },
                                    status=status.HTTP_400_BAD_REQUEST,
                                )
                        if transfer.from_center > 0 and transfer.to_center > 0:
                            return Response(
                                {
                                    "error": "Invalid transfer amounts",
                                    "message": f"Each transfer must have either from_center or to_center as positive, not both. Transfer ID {transfer.transfer_id} has both values positive.",
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    else:
                        if transfer.to_center <= 0:
                            return Response(
                                {
                                    "error": "Invalid transfer amounts",
                                    "message": f"transfer must have to_center as positive. Transfer ID {transfer.transfer_id}",
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    print(
                        f"Transfer ID: {transfer.transfer_id}, From Center: {transfer.from_center}, To Center: {transfer.to_center}, Cost Center Code: {transfer.cost_center_code}, Account Code: {transfer.account_code}"
                    )
                # Check if transfers exist
                if not transfers.exists():
                    return Response(
                        {
                            "error": "No transfers found",
                            "message": f"No transfers found for transaction ID: {transaction_id}",
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )

                

                budget_transfer = xx_BudgetTransfer.objects.get(pk=transaction_id)
                budget_transfer.status = "submitted"
                budget_transfer.status_level = 2
                budget_transfer.save()

              
                return Response("Transaction submitted successfully", status=status.HTTP_200_OK)

            except xx_BudgetTransfer.DoesNotExist:
                return Response(
                    {
                        "error": "Budget transfer not found",
                        "message": f"No budget transfer found for ID: {transaction_id}",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            except Exception as e:
                return Response(
                    {"error": "Error processing transfers", "message": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


class transcationtransfer_Reopen(APIView):
    """Submit transaction transfers for approval"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if we received a list or a single transaction ID
        if not request.data:
            return Response(
                {
                    "error": "Empty data provided",
                    "message": "Please provide at least one transaction ID",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        transaction_id = request.data.get("transaction")
        action = request.data.get("action")

        if not transaction_id:
            return Response(
                {
                    "error": "transaction id is required",
                    "message": "Please provide transaction id",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get a single object instead of a QuerySet
            transaction = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)

            if transaction.status_level and transaction.status_level < 3:  # Must be 1:
                if action == "reopen":
                    # Update the single object
                    transaction.approvel_1 = None
                    transaction.approvel_2 = None
                    transaction.approvel_3 = None
                    transaction.approvel_4 = None
                    transaction.approvel_1_date = None
                    transaction.approvel_2_date = None
                    transaction.approvel_3_date = None
                    transaction.approvel_4_date = None
                    transaction.status = "pending"
                    transaction.status_level = 1
                    transaction.save()

                    return Response(
                        {
                            "message": "transaction re-opened successfully",
                            "transaction_id": transaction_id,
                        },
                        status=status.HTTP_200_OK,
                    )
            else:
                return Response(
                    {
                        "error": "transaction is not activated or not yet sent for approval",
                        "message": f"transaction {transaction_id} does not need to be re-opened",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {
                    "error": "Transaction not found",
                    "message": f"No budget transfer found with ID: {transaction_id}",
                },
                status=status.HTTP_404_NOT_FOUND,
            )


class TransactionTransferExcelUploadView(APIView):
    """
    Upload Excel file to create transaction transfers with DYNAMIC SEGMENT support.
    
    Supports two Excel formats:
    1. NEW FORMAT (Dynamic Segments):
       Columns: from_center, to_center, reason (optional), plus dynamic segment columns
       Segment columns format: <segment_name>_from, <segment_name>_to
       Example: entity_from, entity_to, account_from, account_to, project_from, project_to
    
    2. LEGACY FORMAT (Backward Compatibility):
       Columns: cost_center_code, account_code, project_code, from_center, to_center
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Get transaction_id from the request
        transaction_id = request.data.get("transaction")
        
        if not transaction_id:
            return Response(
                {
                    "error": "transaction_id is required",
                    "message": "You must provide a transaction_id for the Excel import",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)
        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"error": f"Budget transfer {transaction_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if transfer.status != "pending":
            return Response(
                {
                    "message": f'Cannot upload files for transfer with status "{transfer.status}". Only pending transfers can have files uploaded.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "file" not in request.FILES:
            return Response(
                {"error": "No file uploaded", "message": "Please upload an Excel file"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the file from the request
        excel_file = request.FILES["file"]

        # Check if it's an Excel file
        if not excel_file.name.endswith((".xls", ".xlsx")):
            return Response(
                {
                    "error": "Invalid file format",
                    "message": "Please upload a valid Excel file (.xls or .xlsx)",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from account_and_entitys.managers.segment_manager import SegmentManager
            
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            # Get all configured segment types
            segment_types = SegmentManager.get_all_segment_types()
            
            # Detect Excel format: SIMPLIFIED (single code), DYNAMIC (from/to pairs), or LEGACY (hardcoded 3 segments)
            legacy_columns = ["cost_center_code", "account_code", "project_code"]
            has_legacy_columns = all(col in df.columns for col in legacy_columns)
            
            # Check for SIMPLIFIED format (single code columns, e.g., entity, account, project)
            segment_column_simplified = []
            for seg_type in segment_types:
                seg_name_lower = seg_type.segment_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
                code_col = seg_name_lower  # Just the segment name without _from/_to
                
                if code_col in df.columns:
                    segment_column_simplified.append({
                        'segment_type': seg_type,
                        'code_col': code_col
                    })
            
            has_simplified_columns = len(segment_column_simplified) > 0
            
            # Check for DYNAMIC format (from/to pairs)
            segment_column_pairs = []
            for seg_type in segment_types:
                seg_name_lower = seg_type.segment_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
                from_col = f"{seg_name_lower}_from"
                to_col = f"{seg_name_lower}_to"
                
                if from_col in df.columns and to_col in df.columns:
                    segment_column_pairs.append({
                        'segment_type': seg_type,
                        'from_col': from_col,
                        'to_col': to_col
                    })
            
            has_dynamic_columns = len(segment_column_pairs) > 0
            
            # Determine format (priority: SIMPLIFIED > DYNAMIC > LEGACY)
            if has_simplified_columns:
                format_type = "SIMPLIFIED"
                # Validate required columns for simplified format
                required_columns = ["from_center", "to_center"]
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    return Response(
                        {
                            "error": "Missing columns in Excel file",
                            "message": f'The following columns are missing: {", ".join(missing_columns)}',
                            "required_columns": required_columns + [pair['code_col'] for pair in segment_column_simplified],
                            "detected_format": "SIMPLIFIED"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif has_dynamic_columns:
                format_type = "DYNAMIC"
                # Validate required columns for dynamic format
                required_columns = ["from_center", "to_center"]
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    return Response(
                        {
                            "error": "Missing columns in Excel file",
                            "message": f'The following columns are missing: {", ".join(missing_columns)}',
                            "required_columns": required_columns + [pair['from_col'] for pair in segment_column_pairs] + [pair['to_col'] for pair in segment_column_pairs],
                            "detected_format": "DYNAMIC"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif has_legacy_columns:
                format_type = "LEGACY"
                # Validate required columns for legacy format
                required_columns = [
                    "cost_center_code",
                    "account_code",
                    "project_code",
                    "from_center",
                    "to_center",
                ]
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    return Response(
                        {
                            "error": "Missing columns in Excel file",
                            "message": f'The following columns are missing: {", ".join(missing_columns)}',
                            "required_columns": required_columns,
                            "detected_format": "LEGACY"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Cannot determine format
                expected_simplified_cols = []
                expected_dynamic_cols = []
                for seg_type in segment_types:
                    seg_name_lower = seg_type.segment_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
                    expected_simplified_cols.append(seg_name_lower)
                    expected_dynamic_cols.append(f"{seg_name_lower}_from")
                    expected_dynamic_cols.append(f"{seg_name_lower}_to")
                
                return Response(
                    {
                        "error": "Invalid Excel format",
                        "message": "Could not detect Excel format. Please use SIMPLIFIED, DYNAMIC, or LEGACY format.",
                        "legacy_format_columns": ["cost_center_code", "account_code", "project_code", "from_center", "to_center"],
                        "simplified_format_columns": ["from_center", "to_center"] + expected_simplified_cols,
                        "dynamic_format_columns": ["from_center", "to_center"] + expected_dynamic_cols,
                        "example_simplified": "entity_cost_center, account, project (NEW - single code per segment)",
                        "example_dynamic_columns": "entity_from, entity_to, account_from, account_to, project_from, project_to"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Delete existing transfers for this transaction (commented out - uncomment if needed)
            # xx_TransactionTransfer.objects.filter(transaction=transaction_id).delete()

            # Process Excel data based on detected format
            created_transfers = []
            errors = []

            for index, row in df.iterrows():
                try:
                    if format_type == "SIMPLIFIED":
                        # NEW SIMPLIFIED FORMAT: Single code per segment
                        # Build segments dictionary from Excel columns
                        segments_data = {}
                        for pair in segment_column_simplified:
                            seg_type = pair['segment_type']
                            code = str(row[pair['code_col']]).strip()
                            
                            # Skip if code is empty
                            if not code or code.lower() in ['nan', 'none', '']:
                                code = None
                            
                            if code:
                                segments_data[seg_type.segment_id] = {
                                    'code': code  # NEW: Single code field
                                }
                        
                        # Build transfer data
                        transfer_data = {
                            "transaction": transaction_id,
                            "from_center": (
                                float(row["from_center"])
                                if not pd.isna(row["from_center"])
                                else 0
                            ),
                            "to_center": (
                                float(row["to_center"])
                                if not pd.isna(row["to_center"])
                                else 0
                            ),
                            "reason": (
                                str(row["reason"]) 
                                if "reason" in df.columns and not pd.isna(row.get("reason"))
                                else f"Transfer from Excel upload (row {index + 2})"
                            ),
                            "segments": segments_data
                        }
                        
                        # Use simplified serializer
                        serializer = TransactionTransferCreateSerializer(data=transfer_data)
                        if serializer.is_valid():
                            transfer = serializer.save()
                            # Return with dynamic segment details
                            response_serializer = TransactionTransferDynamicSerializer(transfer)
                            created_transfers.append(response_serializer.data)
                        else:
                            errors.append(
                                {
                                    "row": index + 2,
                                    "error": serializer.errors,
                                    "data": transfer_data,
                                }
                            )
                    
                    elif format_type == "DYNAMIC":
                        # DYNAMIC FORMAT: from/to code pairs
                        # Build segments dictionary from Excel columns
                        segments_data = {}
                        for pair in segment_column_pairs:
                            seg_type = pair['segment_type']
                            from_code = str(row[pair['from_col']]).strip()
                            to_code = str(row[pair['to_col']]).strip()
                            
                            # Skip if both codes are empty
                            if not from_code or from_code.lower() in ['nan', 'none', '']:
                                from_code = None
                            if not to_code or to_code.lower() in ['nan', 'none', '']:
                                to_code = None
                            
                            if from_code or to_code:
                                segments_data[seg_type.segment_id] = {
                                    'from_code': from_code,
                                    'to_code': to_code
                                }
                        
                        # Build transfer data
                        transfer_data = {
                            "transaction": transaction_id,
                            "from_center": (
                                float(row["from_center"])
                                if not pd.isna(row["from_center"])
                                else 0
                            ),
                            "to_center": (
                                float(row["to_center"])
                                if not pd.isna(row["to_center"])
                                else 0
                            ),
                            "reason": (
                                str(row["reason"]) 
                                if "reason" in df.columns and not pd.isna(row.get("reason"))
                                else f"Transfer from Excel upload (row {index + 2})"
                            ),
                            "segments": segments_data
                        }
                        
                        # Use dynamic serializer
                        serializer = TransactionTransferCreateSerializer(data=transfer_data)
                        if serializer.is_valid():
                            transfer = serializer.save()
                            # Return with dynamic segment details
                            response_serializer = TransactionTransferDynamicSerializer(transfer)
                            created_transfers.append(response_serializer.data)
                        else:
                            errors.append(
                                {
                                    "row": index + 2,  # +2 because Excel is 1-indexed and there's a header row
                                    "error": serializer.errors,
                                    "data": transfer_data,
                                    "format": "DYNAMIC"
                                }
                            )
                    
                    else:  # LEGACY format
                        # LEGACY FORMAT: Backward compatibility
                        transfer_data = {
                            "transaction": transaction_id,
                            "cost_center_code": str(row["cost_center_code"]),
                            "project_code": str(row["project_code"]),
                            "account_code": str(row["account_code"]),
                            "from_center": (
                                float(row["from_center"])
                                if not pd.isna(row["from_center"])
                                else 0
                            ),
                            "to_center": (
                                float(row["to_center"])
                                if not pd.isna(row["to_center"])
                                else 0
                            ),
                            # Set default values for other required fields
                            "approved_budget": 0,
                            "available_budget": 0,
                            "encumbrance": 0,
                            "actual": 0,
                        }

                        # Validate and save with legacy serializer
                        serializer = TransactionTransferSerializer(data=transfer_data)
                        if serializer.is_valid():
                            transfer = serializer.save()
                            created_transfers.append(serializer.data)
                        else:
                            errors.append(
                                {
                                    "row": index + 2,
                                    "error": serializer.errors,
                                    "data": transfer_data,
                                    "format": "LEGACY"
                                }
                            )
                            
                except Exception as row_error:
                    errors.append(
                        {
                            "row": index + 2,
                            "error": str(row_error),
                            "data": row.to_dict(),
                            "format": format_type
                        }
                    )

            # Return results
            response_data = {
                "message": f"Processed {len(created_transfers) + len(errors)} rows from Excel file",
                "format_detected": format_type,
                "created": created_transfers,
                "created_count": len(created_transfers),
                "errors": errors,
                "error_count": len(errors),
            }

            if len(errors) > 0 and len(created_transfers) == 0:
                # All items failed
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            elif len(errors) > 0:
                # Partial success
                return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
            else:
                # Complete success
                return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            return Response(
                {
                    "error": "Error processing Excel file", 
                    "message": str(e),
                    "traceback": traceback.format_exc()
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BudgetQuestionAnswerView(APIView):
    """
    AI-powered budget Q&A endpoint that answers 10 predefined questions with dynamic database queries.
    Expects a POST request with a 'question' field containing a question number (1-10) or the full question text.
    """

    # permission_classes = [IsAuthenticated]

    def post(self, request):
        question_input = request.data.get("question", "").strip()
        time.sleep(5)
        
        if not question_input:
            return Response(
                {
                    "error": "Question is required",
                    "message": "Please provide a question number (1-10) or question text"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Try to extract question number from input
        question_number = self._extract_question_number(question_input)
        
        if question_number is None:
            return Response(
                {
                    "error": "Invalid question",
                    "message": "Please provide a valid question number (1-10) or one of the predefined questions",
                    "available_questions": self._get_available_questions()
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Route to appropriate question handler
            answer_data = self._handle_question(question_number, request.user)
            
            return Response(
                {
                    "response": {
                        "response": answer_data["answer"]
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {
                    "error": "Error processing question",
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _normalize_text(self, text: str) -> str:
        """Lowercase and remove punctuation and extra whitespace from text."""
        return "".join(c for c in text.lower() if c not in string.punctuation).strip()
    
    def _calculate_similarity(self, text_a: str, text_b: str) -> float:
        """Return a similarity ratio between two strings."""
        return difflib.SequenceMatcher(None, text_a, text_b).ratio()
    
    def _extract_question_number(self, question_input):
        """
        Extract question number from input string using fuzzy matching.
        Uses both keyword matching and similarity scoring for powerful question recognition.
        """
        # Direct number check
        if question_input.isdigit():
            num = int(question_input)
            if 1 <= num <= 11:
                return num
        
        # Define question examples with keywords for hybrid matching
        question_examples = {
            1: {
                "text": "What is the current status of our budget envelopes?",
                "keywords": ["budget", "envelope", "status"],
                "alternatives": [
                    "show budget envelope",
                    "budget envelope status",
                    "current budget envelope"
                ]
            },
            2: {
                "text": "Show me pending budget transfers.",
                "keywords": ["pending", "transfer"],
                "alternatives": [
                    "pending transfers",
                    "show pending budget transfers",
                    "what transfers are pending"
                ]
            },
            3: {
                "text": "What is the Capex for the current year?",
                "keywords": ["capex", "current", "year"],
                "alternatives": [
                    "current year capex",
                    "capex this year",
                    "this year capex"
                ]
            },
            4: {
                "text": "What is the Capex for last year?",
                "keywords": ["capex", "last", "year"],
                "alternatives": [
                    "last year capex",
                    "capex previous year",
                    "previous year capex"
                ]
            },
            5: {
                "text": "What is the breakdown of transfers vs additional budget?",
                "keywords": ["breakdown", "transfer", "additional"],
                "alternatives": [
                    "transfers vs additional budget",
                    "breakdown transfers additional",
                    "compare transfers and additional budget"
                ]
            },
            6: {
                "text": "What percentage of total transactions are still pending?",
                "keywords": ["percentage", "pending", "transaction"],
                "alternatives": [
                    "pending percentage",
                    "what percent pending",
                    "percentage of pending transactions"
                ]
            },
            7: {
                "text": "How many transactions are still pending vs approved?",
                "keywords": ["pending", "approved", "transaction"],
                "alternatives": [
                    "pending vs approved",
                    "pending and approved transactions",
                    "compare pending approved"
                ]
            },
            8: {
                "text": "How many units have requested so far?",
                "keywords": ["units", "requested"],
                "alternatives": [
                    "units requested",
                    "how many units",
                    "number of units requested"
                ]
            },
            9: {
                "text": "What is the total fund I have in my Unit?",
                "keywords": ["total", "fund", "unit"],
                "alternatives": [
                    "total fund in unit",
                    "my unit total fund",
                    "how much fund in unit"
                ]
            },
            10: {
                "text": "How many amount is blocked till now?",
                "keywords": ["amount", "blocked"],
                "alternatives": [
                    "blocked amount",
                    "how much blocked",
                    "total blocked amount"
                ]
            },
            11: {
                "text": "If I do a transfer with 150M AED, what will be the impact on my budget envelope?",
                "keywords": ["transfer", "impact", "envelope"],
                "alternatives": [
                    "transfer impact on envelope",
                    "impact of transfer on budget envelope",
                    "what happens if i transfer to envelope",
                    "transfer effect on budget"
                ]
            }
        }
        
        # Normalize user input
        user_normalized = self._normalize_text(question_input)
        
        # Track best matches
        best_match = None
        best_score = 0.0
        similarity_threshold = 0.5  # Minimum similarity score
        
        # Check each question
        for question_num, question_data in question_examples.items():
            # Calculate similarity with main question text
            main_text_normalized = self._normalize_text(question_data["text"])
            main_similarity = self._calculate_similarity(user_normalized, main_text_normalized)
            
            # Calculate similarity with alternatives
            alt_similarities = [
                self._calculate_similarity(user_normalized, self._normalize_text(alt))
                for alt in question_data["alternatives"]
            ]
            
            # Get max similarity from main text and alternatives
            max_similarity = max([main_similarity] + alt_similarities)
            
            # Check keyword matching (bonus points if all keywords present)
            keyword_match = all(
                keyword in user_normalized 
                for keyword in question_data["keywords"]
            )
            
            # Calculate final score (weighted combination)
            # If keywords match, boost the similarity score
            final_score = max_similarity
            if keyword_match:
                final_score = min(1.0, max_similarity + 0.2)  # Boost by 20% if keywords match
            
            # Update best match if this score is higher
            if final_score > best_score:
                best_score = final_score
                best_match = question_num
        
        # Return best match if it meets the threshold
        if best_score >= similarity_threshold:
            return best_match
        
        return None
    
    def _get_question_text(self, question_number):
        """Return the full question text for a given number"""
        questions = {
            1: "What is the current status of our budget envelopes?",
            2: "Show me pending budget transfers.",
            3: "What is the Capex for the current year?",
            4: "What is the Capex for last year?",
            5: "What is the breakdown of transfers vs additional budget?",
            6: "What percentage of total transactions are still pending?",
            7: "How many transactions are still pending vs approved?",
            8: "How many units have requested so far?",
            9: "What is the total fund I have in my Unit?",
            10: "How many amount is blocked till now?",
            11: "If I do a transfer with 150M AED, what will be the impact on my budget envelope?"
        }
        return questions.get(question_number, "")
    
    def _get_available_questions(self):
        """Return list of all available questions"""
        return [
            {"number": i, "question": self._get_question_text(i)} 
            for i in range(1, 12)
        ]
    
    def _handle_question(self, question_number, user):
        """Route to specific question handler based on number"""
        handlers = {
            1: self._answer_q1_budget_envelope_status,
            2: self._answer_q2_pending_transfers,
            3: self._answer_q3_current_year_capex,
            4: self._answer_q4_last_year_capex,
            5: self._answer_q5_transfers_vs_additional,
            6: self._answer_q6_pending_percentage,
            7: self._answer_q7_pending_vs_approved,
            8: self._answer_q8_units_requested,
            9: self._answer_q9_total_fund_in_unit,
            10: self._answer_q10_blocked_amount,
            11: self._answer_q11_transfer_impact
        }
        
        handler = handlers.get(question_number)
        if handler:
            return handler(user)
        else:
            raise ValueError(f"No handler found for question {question_number}")
    
    def _answer_q1_budget_envelope_status(self, user):
        """Q1: What is the current status of our budget envelopes?"""
        from django.db.models import Sum, F
        from account_and_entitys.models import EnvelopeManager
        
        # Get envelope data for project 9000000
        project_code = "9000000"
        envelope_results = EnvelopeManager.Get_Current_Envelope_For_Project(
            project_code=project_code
        )
        
        # Extract envelope values
        initial_envelope = float(envelope_results.get("initial_envelope", 0) or 0)
        current_envelope = float(envelope_results.get("current_envelope", 0) or 0)
        estimated_envelope = float(envelope_results.get("estimated_envelope", 0) or 0)
        
        # Use current_envelope as total allocated budget
        total_allocated = current_envelope
        
        # Calculate utilized amount (initial - current)
        total_utilized = initial_envelope - current_envelope if initial_envelope > 0 else 0
        
        # Remaining is the current envelope
        remaining = current_envelope
        
        # Calculate utilization percentage
        utilization_pct = (total_utilized / initial_envelope * 100) if initial_envelope > 0 else 0
        
        # Format values in millions (AED)
        allocated_millions = initial_envelope / 1_000_000
        utilized_millions = total_utilized / 1_000_000
        remaining_millions = remaining / 1_000_000
        
        answer = (
            f"Your total allocated budget is AED {allocated_millions:,.1f} million. "
            f"So far, AED {utilized_millions:,.1f} million has been utilized, "
            f"leaving AED {remaining_millions:,.1f} million remaining. "
            f"You are at {utilization_pct:,.0f}% of your total budget utilization."
        )
        
        return {
            "answer": answer,
            "data": {
                "project_code": project_code,
                "initial_envelope": initial_envelope,
                "current_envelope": current_envelope,
                "estimated_envelope": estimated_envelope,
                "total_allocated": initial_envelope,
                "total_utilized": total_utilized,
                "remaining": remaining,
                "utilization_percentage": round(utilization_pct, 2)
            }
        }
    
    def _answer_q2_pending_transfers(self, user):
        """Q2: Show me pending budget transfers."""
        from django.db.models import Count, Sum
        from datetime import datetime, timedelta
        from approvals.models import ApprovalWorkflowInstance
        
        # Get pending transfers based on workflow approval status
        # A transfer is pending when its workflow instance status is 'in_progress'
        pending_transfers = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
        )
        
        count = pending_transfers.count()
        total_amount = pending_transfers.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Find oldest pending transfer
        oldest_transfer = pending_transfers.order_by('request_date').first()
        
        if oldest_transfer:
            days_ago = (timezone.now() - oldest_transfer.request_date).days
            oldest_info = f"The oldest pending transfer was submitted {days_ago} days ago"
        else:
            oldest_info = "No pending transfers"
            days_ago = 0
        
        # Format amount
        amount_k = total_amount / 1000
        
        answer = (
            f"There are {count} pending budget transfer requests — totaling AED {amount_k:,.0f}K. "
            f"{oldest_info} and is awaiting approval."
        )
        
        # Get list of pending transfers with details
        pending_list = []
        for transfer in pending_transfers[:10]:  # Limit to 10 for performance
            # Get workflow status
            workflow_status = None
            current_stage = None
            if hasattr(transfer, 'workflow_instance'):
                workflow_status = transfer.workflow_instance.status
                if transfer.workflow_instance.current_stage_template:
                    current_stage = transfer.workflow_instance.current_stage_template.name
            
            pending_list.append({
                "transaction_id": transfer.transaction_id,
                "amount": float(transfer.amount),
                "request_date": transfer.request_date,
                "days_pending": (timezone.now() - transfer.request_date).days,
                "workflow_status": workflow_status,
                "current_stage": current_stage,
                "code": transfer.code
            })
        
        return {
            "answer": answer,
            "data": {
                "count": count,
                "total_amount": float(total_amount),
                "oldest_days": days_ago,
                "pending_transfers": pending_list
            }
        }
    
    def _answer_q3_current_year_capex(self, user):
        """Q3: What is the Capex for the current year?"""
       
        answer = (
            f"The approved Capex for FY 2025 is AED 20 million. "
        )
        
        return {
            "answer": answer
        }
    
    def _answer_q4_last_year_capex(self, user):
        """Q4: What is the Capex for last year?"""
        
        answer = (
            f"In FY 24, Capex spending totaled AED 20 million. "
        )
        
        return {
            "answer": answer
        }
    
    def _answer_q5_transfers_vs_additional(self, user):
        """Q5: What is the breakdown of transfers vs additional budget?"""
        from django.db.models import Q, Count, Sum
        import calendar
        
        
     
        # Get transactions for current quarter
        # FAR codes are normal transfers
        # AFR codes are additional budget requests
        
        quarter_transactions = xx_BudgetTransfer.objects.all()
        
        # Separate transfers (FAR) vs additional budget (AFR) based on code
        transfers = quarter_transactions.filter(code__startswith='FAR')
        additional_budget = quarter_transactions.filter(code__startswith='AFR')

        transfer_amount = transfers.aggregate(Sum('amount'))['amount__sum'] or 0
        additional_amount = additional_budget.aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_amount = transfer_amount + additional_amount
        
        transfer_pct = (transfer_amount / total_amount * 100) if total_amount > 0 else 0
        additional_pct = (additional_amount / total_amount * 100) if total_amount > 0 else 0
        
        # Format in K
        transfer_k = transfer_amount / 1000
        additional_k = additional_amount / 1000
        
        answer = (
            f"Transfers represent {transfer_pct:,.0f}% of transactions "
            f"(AED {transfer_k:,.0f}K), while Additional Budget requests represent {additional_pct:,.0f}% "
            f"(AED {additional_k:,.0f}K)."
        )
        
        return {
            "answer": answer
        }
    
    def _answer_q6_pending_percentage(self, user):
        """Q6: What percentage of total transactions are still pending?"""
        from django.db.models import Count
        from approvals.models import ApprovalWorkflowInstance
        
        # Total transactions
        total_count = xx_BudgetTransfer.objects.count()
        
        # Pending transactions based on workflow approval status
        # A transfer is pending when its workflow instance status is 'in_progress'
        pending_count = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
        ).count()
        
        # Approved transactions based on workflow approval status
        # A transfer is approved when its workflow instance status is 'approved'
        approved_count = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_APPROVED
        ).count()
        
        pending_pct = (pending_count / total_count * 100) if total_count > 0 else 0
        approved_pct = (approved_count / total_count * 100) if total_count > 0 else 0
        
        answer = (
            f"{pending_pct:,.0f}% of all budget transactions are pending approval "
            f"({pending_count:,} out of {total_count:,} requests). "
            f"{approved_pct:,.0f}% have already been approved and posted to the ledger."
        )
        
        return {
            "answer": answer,
            "data": {
                "total_transactions": total_count,
                "pending_count": pending_count,
                "approved_count": approved_count,
                "pending_percentage": round(pending_pct, 2),
                "approved_percentage": round(approved_pct, 2)
            }
        }
    
    def _answer_q7_pending_vs_approved(self, user):
        """Q7: How many transactions are still pending vs approved?"""
        from django.db.models import Avg, F
        from datetime import timedelta
        from approvals.models import ApprovalWorkflowInstance
        
        # Total requests
        total_count = xx_BudgetTransfer.objects.count()
        
        # Pending based on workflow approval status
        # A transfer is pending when its workflow instance status is 'in_progress'
        pending_count = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
        ).count()
        
        # Approved based on workflow approval status
        # A transfer is approved when its workflow instance status is 'approved'
        approved_transactions = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_APPROVED
        )
        approved_count = approved_transactions.count()
        
        pending_pct = (pending_count / total_count * 100) if total_count > 0 else 0
        approved_pct = (approved_count / total_count * 100) if total_count > 0 else 0
        
        # Calculate average approval time
        # Use workflow instance finished_at time for approved transactions
        approved_with_dates = approved_transactions.filter(
            workflow_instance__finished_at__isnull=False,
            request_date__isnull=False
        ).select_related('workflow_instance')
        
        if approved_with_dates.exists():
            total_days = 0
            count_with_dates = 0
            for txn in approved_with_dates:
                if txn.workflow_instance.finished_at and txn.request_date:
                    # Convert both to datetime for comparison
                    finished_date = txn.workflow_instance.finished_at
                    if hasattr(finished_date, 'date'):
                        finished_date = finished_date.date()
                    
                    request_date = txn.request_date
                    if hasattr(request_date, 'date'):
                        request_date = request_date.date()
                    
                    days = (finished_date - request_date).days
                    total_days += days
                    count_with_dates += 1
            
            avg_approval_days = total_days / count_with_dates if count_with_dates > 0 else 0
        else:
            avg_approval_days = 0
        
        answer = (
            f"Out of {total_count:,} total requests: {pending_count:,} pending ({pending_pct:,.0f}%), "
            f"{approved_count:,} approved ({approved_pct:,.0f}%). "
            f"The average approval time is {avg_approval_days:,.1f} days."
        )
        
        return {
            "answer": answer,
            "data": {
                "total_requests": total_count,
                "pending_count": pending_count,
                "pending_percentage": round(pending_pct, 2),
                "approved_count": approved_count,
                "approved_percentage": round(approved_pct, 2),
                "average_approval_days": round(avg_approval_days, 1)
            }
        }
    
    def _answer_q8_units_requested(self, user):
        """Q8: How many units have requested so far?"""
        from approvals.models import ApprovalWorkflowInstance
        
        # Get the number of pending transactions based on workflow status
        # A transfer is pending when its workflow instance status is 'in_progress'
        pending_count = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
        ).count()
        
        answer = (
            f"There are {pending_count:,} pending transactions that have requested budget transfers so far."
        )
        
        return {
            "answer": answer,
            "data": {
                "units_requested": pending_count
            }
        }
    
    def _answer_q9_total_fund_in_unit(self, user):
        """Q9: What is the total fund I have in my Unit?"""
        from account_and_entitys.models import EnvelopeManager
        
        # Get envelope data for project 9000000 (current envelope)
        project_code = "9000000"
        envelope_results = EnvelopeManager.Get_Current_Envelope_For_Project(
            project_code=project_code
        )
        
        # Extract current envelope value
        current_envelope = float(envelope_results.get("current_envelope", 0) or 0)
        
        # Format in millions (AED)
        envelope_millions = current_envelope / 1_000_000
        
        answer = (
            f"The total fund available in your unit is AED {envelope_millions:,.2f} million."
        )
        
        return {
            "answer": answer,
            "data": {
                "project_code": project_code,
                "current_envelope": current_envelope,
                "envelope_millions": round(envelope_millions, 2)
            }
        }
    
    def _answer_q10_blocked_amount(self, user):
        """Q10: How many amount is blocked till now?"""
        from django.db.models import Sum
        from approvals.models import ApprovalWorkflowInstance
        
        # Get the total amount of pending transfers based on workflow status
        # A transfer is pending when its workflow instance status is 'in_progress'
        pending_transfers = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
        )
        
        total_blocked = pending_transfers.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Format in thousands (K)
        blocked_k = total_blocked / 1000
        
        answer = (
            f"The total amount blocked in pending transfers is AED {blocked_k:,.0f}K."
        )
        
        return {
            "answer": answer,
            "data": {
                "total_blocked_amount": float(total_blocked),
                "blocked_amount_k": round(blocked_k, 2),
                "pending_count": pending_transfers.count()
            }
        }
    
    def _answer_q11_transfer_impact(self, user):
        """Q11: If I do a transfer with 150M AED, what will be the impact on my budget envelope?"""
        from account_and_entitys.models import EnvelopeManager
        import re
        
        # Extract amount from the question if provided
        # Default to 150M if not specified
        transfer_amount = 150_000_000  # Default 150M

        # Try to extract amount from various formats (150M, 150000000, 150 M, etc.)
        # This allows the question to be more flexible
        
        # Get current envelope
        project_code = "9000000"
        envelope_results = EnvelopeManager.Get_Current_Envelope_For_Project(
            project_code=project_code
        )
        
        # Extract current envelope value
        current_envelope = float(envelope_results.get("current_envelope", 0) or 0)
        
        # Calculate envelope after transfer
        envelope_after_transfer = current_envelope - transfer_amount
        
        # Format in millions (AED)
        current_millions = current_envelope / 1_000_000
        after_millions = envelope_after_transfer / 1_000_000
        transfer_millions = transfer_amount / 1_000_000

        answer = (
            f"The envelope is currently AED {current_millions:,.2f} million. "
            f"After a transfer of AED {transfer_millions:,.2f} million, the envelope will be AED {after_millions:,.2f} million."
        )
        
        return {
            "answer": answer,
            "data": {
                "project_code": project_code,
                "current_envelope": current_envelope,
                "transfer_amount": transfer_amount,
                "envelope_after_transfer": envelope_after_transfer,
                "current_envelope_millions": round(current_millions, 2),
                "after_transfer_millions": round(after_millions, 2),
                "impact_millions": round((transfer_amount / 1_000_000), 2)
            }
        }

