import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from user_management.managers.security_group_manager import SecurityGroupManager
from user_management.managers import UserSegmentAccessManager

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
from budget_management.views import TransferPagination


class segments_fundspaginations(PageNumberPagination):
    """Pagination class for budget transfers"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100




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

        # ====== ACCESS CONTROL: Get user's accessible segments ======
        user = request.user
        user_accessible_segments = {}  # {segment_type_id: [segment_codes]}
        
        # SuperAdmin bypass
        if user.role != 1:  # Not SuperAdmin
            # Phase 5: Security Groups (preferred)
            security_group_segments = SecurityGroupManager.get_user_accessible_segments(user)
            
            if security_group_segments:
                user_accessible_segments = security_group_segments
            else:
                # Phase 4: Direct Access (fallback)
                # Build accessible segments for all types
                for i in range(1, 31):
                    access_result = UserSegmentAccessManager.get_user_allowed_segments(
                        user=user,
                        segment_type_id=i
                    )
                    if access_result and access_result.get('allowed_segment_codes'):
                        user_accessible_segments[i] = access_result['allowed_segment_codes']

        for i in range(1, 31):
            segment_param = request.query_params.get(f"Segment{i}", None)
            if segment_param:
                # Check if user has access to this segment type and value
                if user.role != 1:  # Not SuperAdmin
                    if i in user_accessible_segments:
                        # User has access to this segment type - check if they can see this specific code
                        if segment_param not in user_accessible_segments[i]:
                            # User doesn't have access to this specific segment code
                            return Response(
                                {
                                    "error": f"Access denied to Segment{i}={segment_param}",
                                    "message": "You don't have permission to view this segment",
                                    "accessible_segments": user_accessible_segments.get(i, [])
                                },
                                status=status.HTTP_403_FORBIDDEN
                            )
                    # If segment type not in user_accessible_segments, it means no access at all
                    # Allow query to proceed (will return empty result if they have no access)
                
                filters[f'Segment{i}'] = segment_param
        
        # Get total count first for debugging
        total_records = XX_Segment_Funds.objects.count()
        
        # Get filtered segment funds (or all if no filters)
        segment_funds = XX_Segment_Funds.objects.filter(**filters)
        
        # ====== Filter results by user's accessible segments ======
        if user.role != 1 and user_accessible_segments:  # Not SuperAdmin
            # Build Q filter for accessible segments
            from django.db.models import Q
            accessible_filter = Q()
            
            for segment_type_id, segment_codes in user_accessible_segments.items():
                segment_field = f"Segment{segment_type_id}"
                # Add OR condition: this segment field is in the allowed codes
                accessible_filter |= Q(**{f"{segment_field}__in": segment_codes})
            
            if accessible_filter:
                segment_funds = segment_funds.filter(accessible_filter)
        
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
                "Total_budget": float(fund.TOTAL_BUDGET) if fund.TOTAL_BUDGET else 0,
                "Initial_budget": float(fund.INITIAL_BUDGET) if fund.INITIAL_BUDGET else 0,
                "Budget_adjustments": float(fund.BUDGET_ADJUSTMENTS) if fund.BUDGET_ADJUSTMENTS else 0,
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
                "data": results,
                "access_control": {
                    "user_is_superadmin": user.role == 1,
                    "access_filtered": user.role != 1 and bool(user_accessible_segments),
                    "accessible_segment_types": list(user_accessible_segments.keys()) if user.role != 1 else "all"
                }
            },
            status=status.HTTP_200_OK
        )
    




class get_segments_fund(APIView):
    """API to get segment funds with budget, encumbrance, and financial values"""

    permission_classes = [IsAuthenticated]
    pagination_class = segments_fundspaginations

    def get(self, request):
        filters = {}
        
        # ====== ACCESS CONTROL: Get user's accessible segments ======
        user = request.user
        user_accessible_segments = {}  # {segment_type_id: [segment_codes]}
        
        # SuperAdmin bypass
        if user.role != 1:  # Not SuperAdmin
            # Phase 5: Security Groups (preferred)
            security_group_segments = SecurityGroupManager.get_user_accessible_segments(user)
            
            if security_group_segments:
                user_accessible_segments = security_group_segments
            else:
                # Phase 4: Direct Access (fallback)
                # Build accessible segments for all types
                for i in range(1, 31):
                    access_result = UserSegmentAccessManager.get_user_allowed_segments(
                        user=user,
                        segment_type_id=i
                    )
                    if access_result and access_result.get('allowed_segment_codes'):
                        user_accessible_segments[i] = access_result['allowed_segment_codes']

        control_budget_name = request.query_params.get("control_budget_name")
        period_name = request.query_params.get("period_name")
        Budget = request.query_params.get("Budget")
        Encumbrance = request.query_params.get("Encumbrance")
        Funds_available = request.query_params.get("Funds_available")
        Commitment = request.query_params.get("Commitment")
        Obligation = request.query_params.get("Obligation")
        Actual = request.query_params.get("Actual")
        Other = request.query_params.get("Other")
        total_budget = request.query_params.get("total_budget")
        initial_budget = request.query_params.get("initial_budget")
        budget_adjustments = request.query_params.get("budget_adjustments")

        # numeric fields – still exact match (you can later add range logic if needed)
        if Budget is not None:
            filters['BUDGET_PTD'] = Budget
        if Encumbrance is not None:
            filters['ENCUMBRANCE_PTD'] = Encumbrance
        if Funds_available is not None:
            filters['FUNDS_AVAILABLE_PTD'] = Funds_available
        if Commitment is not None:
            filters['COMMITMENT_PTD'] = Commitment
        if Obligation is not None:
            filters['OBLIGATION_PTD'] = Obligation
        if Actual is not None:
            filters['ACTUAL_PTD'] = Actual
        if Other is not None:
            filters['OTHER_PTD'] = Other
        if total_budget is not None:
            filters['TOTAL_BUDGET'] = total_budget
        if initial_budget is not None:
            filters['INITIAL_BUDGET'] = initial_budget
        if budget_adjustments is not None:
            filters['BUDGET_ADJUSTMENTS'] = budget_adjustments

        # string fields – partial match
        if control_budget_name:
            filters['CONTROL_BUDGET_NAME__icontains'] = control_budget_name
        if period_name:
            filters['PERIOD_NAME__icontains'] = period_name

        # Segments 1..30 – partial match
        for i in range(1, 31):
            segment_param = request.query_params.get(f"segment{i}")
            if segment_param:
                filters[f'Segment{i}__istartswith'] = segment_param

        segment_funds = XX_Segment_Funds.objects.filter(**filters)
        
        # ====== Filter results by user's accessible segments ======
        if user.role != 1 and user_accessible_segments:  # Not SuperAdmin
            # Build Q filter for accessible segments
            from django.db.models import Q
            accessible_filter = Q()
            
            for segment_type_id, segment_codes in user_accessible_segments.items():
                segment_field = f"Segment{segment_type_id}"
                # Add OR condition: this segment field is in the allowed codes
                accessible_filter |= Q(**{f"{segment_field}__in": segment_codes})
            
            if accessible_filter:
                segment_funds = segment_funds.filter(accessible_filter)
        
        total_records = segment_funds.count()

        paginator = self.pagination_class()
        page_qs = paginator.paginate_queryset(segment_funds, request, view=self)

        results = []
        for fund in page_qs:
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
                "total_budget": float(fund.TOTAL_BUDGET) if fund.TOTAL_BUDGET else 0,
                "initial_budget": float(fund.INITIAL_BUDGET) if fund.INITIAL_BUDGET else 0,
                "budget_adjustments": float(fund.BUDGET_ADJUSTMENTS) if fund.BUDGET_ADJUSTMENTS else 0,
                "Created_at": fund.created_at,
            }

            # return only non-null segment columns Segment1..Segment30
            for i in range(1, 31):
                segment_value = getattr(fund, f"Segment{i}", None)
                if segment_value is not None:
                    result_data[f"segment{i}"] = segment_value

            # if you still want to echo back fields from filters
            for key in filters.keys():
                # key may be "FIELD__icontains" – strip lookup part
                field_name = key.split("__", 1)[0]
                field_value = getattr(fund, field_name, None)
                if field_value is not None:
                    result_data[field_name.lower()] = field_value

            results.append(result_data)

        return Response(
            {
                "message": f"Retrieved {paginator.page.paginator.count} segment funds",
                "count": paginator.page.paginator.count,
                "total_records_in_db": total_records,
                "filters_applied": filters,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "page": paginator.page.number,
                "page_size": paginator.get_page_size(request),
                "data": results,
                "access_control": {
                    "user_is_superadmin": user.role == 1,
                    "access_filtered": user.role != 1 and bool(user_accessible_segments),
                    "accessible_segment_types": list(user_accessible_segments.keys()) if user.role != 1 else "all"
                }
            },
            status=status.HTTP_200_OK,
        )