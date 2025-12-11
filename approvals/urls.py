from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    ApprovalWorkflowTemplateViewSet,
    ApprovalWorkflowStageTemplateViewSet,
    WorkflowTemplateAssignmentListView,
    WorkflowTemplateAssignmentDetailView,
    BulkAssignWorkflowsView,
    ReorderWorkflowAssignmentsView,
)

router = DefaultRouter()
router.register(r'workflow-templates', ApprovalWorkflowTemplateViewSet, basename='workflowtemplate')
router.register(r'stage-templates', ApprovalWorkflowStageTemplateViewSet, basename='stagetemplate')

urlpatterns = [
    path('', include(router.urls)),
    
    # Workflow Template Assignment endpoints (Phase 6)
    path('workflow-assignments/', WorkflowTemplateAssignmentListView.as_view(), name='workflow-assignments-list'),
    path('workflow-assignments/<int:pk>/', WorkflowTemplateAssignmentDetailView.as_view(), name='workflow-assignments-detail'),
    path('workflow-assignments/bulk-assign/', BulkAssignWorkflowsView.as_view(), name='workflow-assignments-bulk'),
    path('workflow-assignments/reorder/', ReorderWorkflowAssignmentsView.as_view(), name='workflow-assignments-reorder'),
]
