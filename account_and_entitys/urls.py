from django.urls import path
from .views import (
    # Unified Dynamic Segment Views
    SegmentDeleteAllView,
    SegmentListView,
    SegmentTypeDeleteAllView,
    SegmentTypesListView,
    SegmentTypeCreateView,
    SegmentTypeDetailView,
    SegmentTypeUpdateView,
    SegmentTypeDeleteView,
    SegmentCreateView,
    SegmentDetailView,
    SegmentUpdateView,
    SegmentDeleteView,
    SegmentBulkUploadView,
    AccountWiseDashboardView,
    PivotFundListView,
    PivotFundCreateView,
    PivotFundDetailView,
    PivotFundUpdateView,
    PivotFundDeleteView,
    ProjectEnvelopeListView,
    ProjectWiseDashboardView,
    TransactionAuditListView,
    TransactionAuditCreateView,
    TransactionAuditDetailView,
    TransactionAuditUpdateView,
    TransactionAuditDeleteView,
    Upload_ProjectEnvelopeView,
    list_ACCOUNT_ENTITY_LIMIT,
    UpdateAccountEntityLimit,
    DeleteAccountEntityLimit,
    AccountEntityLimitAPI,
    RefreshBalanceReportView,
    BalanceReportListView,
    BalanceReportSegmentsView,
    BalanceReportFinancialDataView,
    Single_BalanceReportView,
    UploadAccountMappingView,
    UploadBudgetDataView,
    UploadMappingExcelView,
    EntityMappingListView,
    ActiveProjectsWithEnvelopeView,
)
from .oracle.view import (

    Download_segment_values_from_oracle,
    Download_segment_Funds,
)

# Import Phase 3 views
from .phase3_views import (
    # Envelope Views
    SegmentEnvelopeListCreateView,
    SegmentEnvelopeDetailView,
    SegmentEnvelopeCheckBalanceView,
    SegmentEnvelopeSummaryView,
    # Mapping Views
    SegmentMappingListCreateView,
    SegmentMappingDetailView,
    SegmentMappingLookupView,
    # Transfer Limit Views
    SegmentTransferLimitListCreateView,
    SegmentTransferLimitDetailView,
    SegmentTransferLimitValidateView,
)

urlpatterns = [
    # ============================================
    # UNIFIED DYNAMIC SEGMENT API
    # ============================================
    # Segment Type Management (CRUD for segment types)
 
    
    # ============================================
    # LEGACY ENDPOINTS (For backward compatibility)
    # ============================================
    # Note: Legacy CREATE endpoints removed - use unified /segments/create/ with segment_type parameter
    # The system is now fully dynamic and doesn't hardcode segment types
    
    # Project URLs (Legacy - Detail/Update/Delete only)
    path(
        "projects/envelope/", ProjectEnvelopeListView.as_view(), name="project-envelope"
    ),

    path(
        "projects/envelope/upload/",
        Upload_ProjectEnvelopeView.as_view(),
        name="upload-project-envelope",
    ),
    path(
        "projects/active-with-envelope/",
        ActiveProjectsWithEnvelopeView.as_view(),
        name="active-projects-with-envelope",
    ),
    
    # PivotFund URLs
    path("pivot-funds/", PivotFundListView.as_view(), name="pivotfund-list"),
    path("pivot-funds/create/", PivotFundCreateView.as_view(), name="pivotfund-create"),
    path("pivot-funds/getdetail/", PivotFundDetailView.as_view(), name="pivotfund-detail"),
    path(
        "pivot-funds/<int:pk>/update/",
        PivotFundUpdateView.as_view(),
        name="pivotfund-update",
    ),
    path(
        "pivot-funds/<int:pk>/delete/",
        PivotFundDeleteView.as_view(),
        name="pivotfund-delete",
    ),
    # ADJD Transaction Audit URLs
    path(
        "transaction-audits/",
        TransactionAuditListView.as_view(),
        name="transaction-audit-list",
    ),
    path(
        "transaction-audits/create/",
        TransactionAuditCreateView.as_view(),
        name="transaction-audit-create",
    ),
    path(
        "transaction-audits/<int:pk>/",
        TransactionAuditDetailView.as_view(),
        name="transaction-audit-detail",
    ),
    path(
        "transaction-audits/<int:pk>/update/",
        TransactionAuditUpdateView.as_view(),
        name="transaction-audit-update",
    ),
    path(
        "transaction-audits/<int:pk>/delete/",
        TransactionAuditDeleteView.as_view(),
        name="transaction-audit-delete",
    ),
    # Fix the URL for list_ACCOUNT_ENTITY_LIMIT view
    path(
        "account-entity-limit/list/",
        list_ACCOUNT_ENTITY_LIMIT.as_view(),
        name="account-entity-limits",
    ),
    path(
        "account-entity-limit/upload/",
        AccountEntityLimitAPI.as_view(),
        name="account-entity-limits",
    ),
    # Update and Delete URLs for Account Entity Limit
    path(
        "account-entity-limit/update/",
        UpdateAccountEntityLimit.as_view(),
        name="update_limit",
    ),
    path(
        "account-entity-limit/delete/",
        DeleteAccountEntityLimit.as_view(),
        name="delete_limit",
    ),
    # Balance Report URLs
    path(
        "balance-report/refresh/",
        RefreshBalanceReportView.as_view(),
        name="refresh-balance-report",
    ),
    path(
        "balance-report/list/",
        BalanceReportListView.as_view(),
        name="list-balance-report",
    ),
    path(
        "balance-report/segments/",
        BalanceReportSegmentsView.as_view(),
        name="balance-report-segments",
    ),
    path(
        "balance-report/financial-data/",
        BalanceReportFinancialDataView.as_view(),
        name="balance-report-financial-data",
    ),
    path(
        "balance-report/single_balance/",
        Single_BalanceReportView.as_view(),
        name="balance-report",
    ),
    path(
        "budget-data/upload/",
        UploadBudgetDataView.as_view(),
        name="upload-budget-data",
    ),
    # Mapping URLs
    path(
        "account-mapping/upload/",
        UploadAccountMappingView.as_view(),
        name="upload-account-mapping",
    ),
    # Mapping URLs
    path(
        "project-wise-dashboard/",
        ProjectWiseDashboardView.as_view(),
        name="project-wise-dashboard",
    ),
    path(
        "mappings/upload-excel/",
        UploadMappingExcelView.as_view(),
        name="upload-mapping-excel",
    ),
    path(
        "account-wise-dashboard/",
        AccountWiseDashboardView.as_view(),
        name="account-wise-dashboard",
    ),
    path(
        "entities/mapping/list/",
        EntityMappingListView.as_view(),
        name="mapping-for-fusion",
    ),
    # path(
    #     "mappings/accounts/",
    #     AccountMappingListView.as_view(),
    #     name="account-mapping-list",
    # ),
    # path(
    #     "mappings/accounts/<int:pk>/",
    #     AccountMappingDetailView.as_view(),
    #     name="account-mapping-detail",
    # ),
    # path(
    #     "mappings/entities/",
    #     EntityMappingListView.as_view(),
    #     name="entity-mapping-list",
    # ),
    # path(
    #     "mappings/entities/<int:pk>/",
    #     EntityMappingDetailView.as_view(),
    #     name="entity-mapping-detail",
    # ),
    
    # ============================================
    # PHASE 3: ENVELOPE, MAPPING, AND TRANSFER LIMIT APIs
    # NEW SIMPLIFIED DYNAMIC SEGMENT FORMAT
    # ============================================
    
    # Segment Envelope APIs (Budget Management)
    path("phase3/envelopes/", SegmentEnvelopeListCreateView.as_view(), name="envelope-list-create"),
    path("phase3/envelopes/<int:envelope_id>/", SegmentEnvelopeDetailView.as_view(), name="envelope-detail"),
    path("phase3/envelopes/check-balance/", SegmentEnvelopeCheckBalanceView.as_view(), name="envelope-check-balance"),
    path("phase3/envelopes/summary/", SegmentEnvelopeSummaryView.as_view(), name="envelope-summary"),
    
    # Segment Mapping APIs (Segment-to-Segment Mapping)
    path("phase3/mappings/", SegmentMappingListCreateView.as_view(), name="mapping-list-create"),
    path("phase3/mappings/<int:mapping_id>/", SegmentMappingDetailView.as_view(), name="mapping-detail"),
    path("phase3/mappings/lookup/", SegmentMappingLookupView.as_view(), name="mapping-lookup"),
    
    # Transfer Limit APIs (Transfer Permission Management)
    path("phase3/transfer-limits/", SegmentTransferLimitListCreateView.as_view(), name="transfer-limit-list-create"),
    path("phase3/transfer-limits/<int:limit_id>/", SegmentTransferLimitDetailView.as_view(), name="transfer-limit-detail"),
    path("phase3/transfer-limits/validate/", SegmentTransferLimitValidateView.as_view(), name="transfer-limit-validate"),

    path(
        "segment-types/delete-all/",
        SegmentTypeDeleteAllView.as_view(),
        name="segment-type-delete-all",
    ),
    path(
        "segments/delete-all/",
        SegmentDeleteAllView.as_view(),
        name="segment-delete-all",
    ),


    path("segment-types/", SegmentTypesListView.as_view(), name="segment-types-list"),
    path("segment-types/create/", SegmentTypeCreateView.as_view(), name="segment-type-create"),
    path("segment-types/<int:pk>/", SegmentTypeDetailView.as_view(), name="segment-type-detail"),
    path("segment-types/<int:pk>/update/", SegmentTypeUpdateView.as_view(), name="segment-type-update"),
    path("segment-types/<int:pk>/delete/", SegmentTypeDeleteView.as_view(), name="segment-type-delete"),

    
    
    # Main unified CRUD endpoints for all segment types
    path("segments/", SegmentListView.as_view(), name="segment-list"),
    path("segments/create/", SegmentCreateView.as_view(), name="segment-create"),
    path("segments/<int:pk>/", SegmentDetailView.as_view(), name="segment-detail"),
    path("segments/<int:pk>/update/", SegmentUpdateView.as_view(), name="segment-update"),
    path("segments/<int:pk>/delete/", SegmentDeleteView.as_view(), name="segment-delete"),
    
    # Unified bulk upload endpoint (works with any segment type)
    path("segments/upload/", SegmentBulkUploadView.as_view(), name="segment-bulk-upload"),



       #oracle apis for data fetch
       path("segments/load_Segments_oracle/", Download_segment_values_from_oracle.as_view(), name="segment-create"),
       path("segments/load_Segments_oracle/Funds/", Download_segment_Funds.as_view(), name="segment-create"),
  



]
