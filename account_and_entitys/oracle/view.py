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

        oracle_maanger.download_segment_values_and_load_to_database(1)
        
    

        return Response("done")



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

        control_budget_name = request.query_params.get("control_budget_name","MOFA_CASH")
        period_name = request.query_params.get("period_name","1-25")
       
        oracle_maanger=OracleBalanceReportManager()

        XX_Segment_Funds.objects.all().delete()
        oracle_maanger.download_segments_funds(control_budget_name=control_budget_name, period_name=period_name)
        
    

        return Response("done")