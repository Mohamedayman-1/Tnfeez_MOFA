from django.urls import path
from .views import (
    TransactionTransferCreateView,
    TransactionTransferListView,
    TransactionTransferDetailView,
    TransactionTransferUpdateView,
    TransactionTransferDeleteView,
    transcationtransferSubmit,
    transcationtransfer_Reopen,
    TransactionTransferExcelUploadView,
    TransactionTransferExcelTemplateView,
    # BudgetQuestionAnswerView,
)
from .transfer_details_view import TransactionTransferDetailsView
from .transaction_report_view import TransactionComprehensiveReportView

urlpatterns = [
    # List and create endpoints
    path("", TransactionTransferListView.as_view(), name="transfer-list"),
    path("create/", TransactionTransferCreateView.as_view(), name="transfer-create"),
    # Detail, update, delete endpoints
    path('<int:pk>/', TransactionTransferDetailView.as_view(), name='transfer-detail'),
    path("<int:pk>/update/",TransactionTransferUpdateView.as_view(),name="transfer-update",),
    path("<int:pk>/delete/",TransactionTransferDeleteView.as_view(),name="transfer-delete",),
    # Submit and reopen endpoints
    path("submit/", transcationtransferSubmit.as_view(), name="transfer-submit"),
    path("reopen/", transcationtransfer_Reopen.as_view(), name="transfer-reopen"),
    # Transfer details endpoint (supports single or multiple transaction IDs)
    path("transfer-details/", TransactionTransferDetailsView.as_view(), name="transfer-details"),
    # Comprehensive report endpoint
    path("report/", TransactionComprehensiveReportView.as_view(), name="transaction-report"),
    # Excel template and upload endpoints
    path("excel-template/", TransactionTransferExcelTemplateView.as_view(), name="transfer-excel-template"),
    path("excel-upload/",TransactionTransferExcelUploadView.as_view(),name="transfer-excel-upload",),
    # Budget Q&A endpoint
    #path("budget-qa/",BudgetQuestionAnswerView.as_view(),name="budget-question-answer",),
]
