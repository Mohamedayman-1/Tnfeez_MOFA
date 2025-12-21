"""
URL Configuration for Django Dynamic Validation App
"""

from django.urls import path
from . import views

# Manual URL patterns instead of router to avoid format suffix conflicts
# This prevents "Converter 'drf_format_suffix' is already registered" error
urlpatterns = [
    # DataSource endpoints
    path('datasources/', views.DataSourceViewSet.as_view({'get': 'list', 'post': 'create'}), name='datasource-list'),
    path('datasources/<int:pk>/', views.DataSourceViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='datasource-detail'),
    path('datasources/<int:pk>/history/', views.DataSourceViewSet.as_view({'get': 'history'}), name='datasource-history'),
    path('datasources/types/', views.DataSourceViewSet.as_view({'get': 'types'}), name='datasource-types'),
    
    # ValidationStep endpoints
    path('steps/', views.ValidationStepViewSet.as_view({'get': 'list', 'post': 'create'}), name='validationstep-list'),
    path('steps/<int:pk>/', views.ValidationStepViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='validationstep-detail'),
    path('steps/operations/', views.ValidationStepViewSet.as_view({'get': 'operations'}), name='validationstep-operations'),
    path('steps/upload_excel/', views.ValidationStepViewSet.as_view({'post': 'upload_excel'}), name='validationstep-upload-excel'),
    path('steps/bulk_create/', views.ValidationStepViewSet.as_view({'post': 'bulk_create'}), name='validationstep-bulk-create'),
    path('steps/bulk_update/', views.ValidationStepViewSet.as_view({'put': 'bulk_update', 'patch': 'bulk_update'}), name='validationstep-bulk-update'),
    
    # ValidationWorkflow endpoints
    path('workflows/', views.ValidationWorkflowViewSet.as_view({'get': 'list', 'post': 'create'}), name='validationworkflow-list'),
    path('workflows/<int:pk>/', views.ValidationWorkflowViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='validationworkflow-detail'),
    path('workflows/<int:pk>/execute/', views.ValidationWorkflowViewSet.as_view({'post': 'execute'}), name='validationworkflow-execute'),
    path('workflows/by_execution_point/', views.ValidationWorkflowViewSet.as_view({'get': 'by_execution_point'}), name='validationworkflow-by-execution-point'),
    path('workflows/export/', views.ValidationWorkflowViewSet.as_view({'post': 'export'}), name='validationworkflow-export'),
    path('workflows/import/', views.ValidationWorkflowViewSet.as_view({'post': 'import_workflows'}), name='validationworkflow-import'),
    
    # ValidationExecution endpoints
    path('executions/', views.ValidationExecutionViewSet.as_view({'get': 'list'}), name='validationexecution-list'),
    path('executions/<int:pk>/', views.ValidationExecutionViewSet.as_view({'get': 'retrieve'}), name='validationexecution-detail'),
    
    # ValidationStepExecution endpoints
    path('step-executions/', views.ValidationStepExecutionViewSet.as_view({'get': 'list'}), name='validationstepexecution-list'),
    path('step-executions/<int:pk>/', views.ValidationStepExecutionViewSet.as_view({'get': 'retrieve'}), name='validationstepexecution-detail'),
    
    # ExecutionPoint endpoints
    path('execution-points/', views.ExecutionPointViewSet.as_view({'get': 'list'}), name='executionpoint-list'),
    path('execution-points/categories/', views.ExecutionPointViewSet.as_view({'get': 'categories'}), name='executionpoint-categories'),
    path('execution-points/<str:code>/datasources/', views.ExecutionPointViewSet.as_view({'get': 'datasources'}), name='executionpoint-datasources'),
]
