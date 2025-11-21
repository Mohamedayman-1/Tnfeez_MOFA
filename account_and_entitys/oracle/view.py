import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from budget_management.models import (
    get_entities_with_children,
    get_level_zero_children,
    get_zero_level_accounts,
    get_zero_level_projects,
)
from account_and_entitys.models import (
    XX_Account,
    XX_Entity,
    XX_Project,
    XX_PivotFund,
    XX_TransactionAudit,
    XX_ACCOUNT_ENTITY_LIMIT,
    XX_BalanceReport,
    Account_Mapping,
    Budget_data,
    XX_ACCOUNT_mapping,
    XX_Entity_mapping,
    EnvelopeManager,
    XX_Segment,
    XX_SegmentType,
    XX_Segment_Funds
)
from account_and_entitys.serializers import (
    AccountSerializer,
    EntitySerializer,
    PivotFundSerializer,
    ProjectSerializer,
    TransactionAuditSerializer,
    AccountEntityLimitSerializer,
    BalanceReportSerializer,
    SegmentValueListSerializer,
)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from django.db import transaction

from django.db.models import CharField
from django.db.models.functions import Cast
from django.db.models import Q
from account_and_entitys.oracle.oracle_balance_report_manager import OracleBalanceReportManager





class Download_segment_values_from_oracle(APIView):
    """Download segment values from Oracle and update local XX_Segment table dynamically
    
    Query Parameters:
    - segment_type: REQUIRED - Segment type ID or name (e.g., 1, 2, 3, "Account", "Project")
    
    Features:
    - Works with any segment type (not limited to 3)
    - Fetches segments from Oracle via stored procedure
    - Upserts segments into local XX_Segment table
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
       
        oracle_maanger=OracleBalanceReportManager()

        XX_Segment.objects.all().delete()

        result=oracle_maanger.download_segment_values_and_load_to_database(1)
        
        if not result['success']:
            return Response(
                {
                    "message": result['message'],
                    "error": "Failed to download segment values"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(
            {
                "message": result['message'],
                "created_count": result['created_count'],
                "skipped_count": result['skipped_count'],
                "total_records": result['total_records'],
                # "data": result['data']
            },
            status=status.HTTP_200_OK
        )



class Download_segment_Funds(APIView):
    """Download segment values from Oracle and update local XX_Segment table dynamically
    
    Query Parameters:
    - segment_type: REQUIRED - Segment type ID or name (e.g., 1, 2, 3, "Account", "Project")
    
    Features:
    - Works with any segment type (not limited to 3)
    - Fetches segments from Oracle via stored procedure
    - Upserts segments into local XX_Segment table
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):

        period_name = request.query_params.get("period_name","1-25")
       
        oracle_maanger=OracleBalanceReportManager()

        XX_Segment_Funds.objects.all().delete()

        control_budget_names = ["MOFA_CASH", "MOFA_COST_2"]
        results = []
        total_success = 0
        total_failed = 0
        
        for control_budget_name in control_budget_names:
            result = oracle_maanger.download_segments_funds(control_budget_name=control_budget_name, period_name=period_name)
            
            if result['success']:
                total_success += 1
            else:
                total_failed += 1
            
            results.append({
                "control_budget": control_budget_name,
                "success": result['success'],
                "message": result['message']
            })
        
        # If all failed, return error
        if total_failed == len(control_budget_names):
            return Response(
                {
                    "message": "Failed to download all segment funds",
                    "results": results
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Return summary of all operations
        return Response(
            {
                "message": f"Successfully processed {total_success}/{len(control_budget_names)} control budgets",
                "total_success": total_success,
                "total_failed": total_failed,
                "results": results
            },
            status=status.HTTP_200_OK
        )
    

class get_segment_fund(APIView):
    """API to get segment funds with budget, encumbrance, and financial values"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Build filter dynamically for all 30 segments
        filters = {}
        for i in range(1, 31):
            segment_param = request.query_params.get(f"Segment{i}", None)
            if segment_param:
                filters[f'Segment{i}'] = segment_param
        
        # Get total count first for debugging
        total_records = XX_Segment_Funds.objects.count()
        
        # Get filtered segment funds (or all if no filters)
        segment_funds = XX_Segment_Funds.objects.filter(**filters)
        
        # Build response data
        results = []
        for fund in segment_funds:
            # Create result dict with all 30 segments
            result_data = {
                "id": fund.id,
                "Control_budget_name": fund.CONTROL_BUDGET_NAME,
                "Period_name": fund.PERIOD_NAME,
                "Budget": float(fund.BUDGET_PTD) if fund.BUDGET_PTD else 0,
                "Encumbrance": float(fund.ENCUMBRANCE_PTD) if fund.ENCUMBRANCE_PTD else 0,
                "Funds_available": float(fund.FUNDS_AVAILABLE_PTD) if fund.FUNDS_AVAILABLE_PTD else 0,
                "Commitment": float(fund.COMMITMENT_PTD) if fund.COMMITMENT_PTD else 0,
                "Obligation": float(fund.OBLIGATION_PTD) if fund.OBLIGATION_PTD else 0,
                "Actual": float(fund.ACTUAL_PTD) if fund.ACTUAL_PTD else 0,
                "Other": float(fund.OTHER_PTD) if fund.OTHER_PTD else 0,
                "Created_at": fund.created_at
            }
            
            # Add only segments that were filtered
            for key in filters.keys():
                # key is like 'Segment5', 'Segment9', etc.
                segment_value = getattr(fund, key, None)
                if segment_value is not None:
                    result_data[key.lower()] = segment_value
            
            results.append(result_data)
        return Response(
            {
                "message": f"Retrieved {len(results)} segment funds",
                "count": len(results),
                "total_records_in_db": total_records,
                "filters_applied": filters,
                "data": results
            },
            status=status.HTTP_200_OK
        )