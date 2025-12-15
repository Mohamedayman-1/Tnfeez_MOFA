"""
Views for DataSource API endpoints.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import DataSource, DataSourceHistory
from .serializers import DataSourceSerializer, DataSourceHistorySerializer


class DataSourceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing DataSources.
    
    Endpoints:
        - GET /api/datasources/ - List all data sources
        - POST /api/datasources/ - Create new data source
        - GET /api/datasources/{id}/ - Get specific data source
        - PUT/PATCH /api/datasources/{id}/ - Update data source
        - DELETE /api/datasources/{id}/ - Delete data source
        - GET /api/datasources/{id}/history/ - Get change history
    """
    
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['data_type', 'name']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """Set created_by to current user if authenticated."""
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    def perform_update(self, serializer):
        """Track value changes in history."""
        old_instance = self.get_object()
        
        # If value is changing, create history entry
        if 'current_value' in serializer.validated_data:
            new_value = serializer.validated_data['current_value']
            if old_instance.current_value != new_value:
                if self.request.user and self.request.user.is_authenticated:
                    DataSourceHistory.objects.create(
                        datasource=old_instance,
                        old_value=old_instance.current_value,
                        new_value=new_value,
                        changed_by=self.request.user,
                        reason=self.request.data.get('change_reason', '')
                    )
        
        serializer.save()
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get change history for a specific data source."""
        datasource = self.get_object()
        history = datasource.history.all()
        
        page = self.paginate_queryset(history)
        if page is not None:
            serializer = DataSourceHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DataSourceHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available data types."""
        return Response(DataSource.DATA_TYPE_CHOICES)


# Import enhanced validation views with Type Validation, IN/NOT IN, and Excel upload support
from .views_validation import (
    ValidationStepViewSet,
    ValidationWorkflowViewSet,
    ValidationExecutionViewSet,
    ValidationStepExecutionViewSet,
    ExecutionPointViewSet
)
