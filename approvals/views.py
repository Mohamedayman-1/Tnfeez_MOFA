from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from approvals.pagination import LargeResultsSetPagination, SmallResultsSetPagination
from user_management.permissions import IsSuperAdmin
from .models import ApprovalWorkflowStageTemplate, ApprovalWorkflowTemplate
from .serializers import (
    ApprovalWorkflowStageTemplateSerializer,
    ApprovalWorkflowTemplateSerializer,
    ApprovalWorkflowTemplateDetailSerializer,
)


class ApprovalWorkflowTemplateViewSet(viewsets.ModelViewSet):
    queryset = ApprovalWorkflowTemplate.objects.all()
    serializer_class = ApprovalWorkflowTemplateSerializer
    pagination_class = SmallResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active", "transfer_type", "version"]
    search_fields = ["name", "description", "code", "transfer_type"]
    ordering_fields = ["created_at", "updated_at", "version"]

    def get_serializer_class(self):
        if self.action in ["retrieve", "create", "update", "partial_update"]:
            return ApprovalWorkflowTemplateDetailSerializer
        return ApprovalWorkflowTemplateSerializer



class ApprovalWorkflowStageTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = ApprovalWorkflowStageTemplate.objects.all()
    serializer_class = ApprovalWorkflowStageTemplateSerializer
    pagination_class = LargeResultsSetPagination


# -------------------------------
# Workflow Template Assignment Views (Phase 6)
# -------------------------------
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import XX_WorkflowTemplateAssignment, ApprovalWorkflowTemplate
from user_management.models import XX_SecurityGroup
from .serializers import WorkflowTemplateAssignmentSerializer, BulkAssignWorkflowsSerializer


class WorkflowTemplateAssignmentListView(APIView):
    """
    GET: List all workflow assignments (optionally filtered by security_group)
    POST: Create a new workflow assignment
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        security_group_id = request.query_params.get('security_group')
        
        queryset = XX_WorkflowTemplateAssignment.objects.select_related(
            'security_group',
            'workflow_template',
            'created_by'
        ).order_by('security_group', 'execution_order')
        
        if security_group_id:
            queryset = queryset.filter(security_group_id=security_group_id)
        
        serializer = WorkflowTemplateAssignmentSerializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'assignments': serializer.data
        })
    
    def post(self, request):
        serializer = WorkflowTemplateAssignmentSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response({
                'success': True,
                'message': 'Workflow assignment created successfully',
                'assignment': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class WorkflowTemplateAssignmentDetailView(APIView):
    """
    GET: Retrieve a specific assignment
    PUT/PATCH: Update an assignment
    DELETE: Delete an assignment
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_WorkflowTemplateAssignment.objects.select_related(
                'security_group',
                'workflow_template'
            ).get(pk=pk)
        except XX_WorkflowTemplateAssignment.DoesNotExist:
            return None
    
    def get(self, request, pk):
        assignment = self.get_object(pk)
        if not assignment:
            return Response({
                'success': False,
                'error': 'Assignment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = WorkflowTemplateAssignmentSerializer(assignment)
        return Response({
            'success': True,
            'assignment': serializer.data
        })
    
    def put(self, request, pk):
        assignment = self.get_object(pk)
        if not assignment:
            return Response({
                'success': False,
                'error': 'Assignment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = WorkflowTemplateAssignmentSerializer(assignment, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Assignment updated successfully',
                'assignment': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        assignment = self.get_object(pk)
        if not assignment:
            return Response({
                'success': False,
                'error': 'Assignment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Store info before deletion
        group_name = assignment.security_group.group_name
        workflow_code = assignment.workflow_template.code
        
        assignment.delete()
        
        return Response({
            'success': True,
            'message': f'Removed workflow "{workflow_code}" from security group "{group_name}"'
        })


class BulkAssignWorkflowsView(APIView):
    """
    POST: Assign multiple workflows to a security group at once
    Replaces existing assignments for that group
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        serializer = BulkAssignWorkflowsSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        security_group_id = serializer.validated_data['security_group_id']
        workflow_assignments = serializer.validated_data['workflow_assignments']
        
        # Get security group
        security_group = XX_SecurityGroup.objects.get(id=security_group_id)
        
        # Delete existing assignments for this group
        deleted_count = XX_WorkflowTemplateAssignment.objects.filter(
            security_group_id=security_group_id
        ).delete()[0]
        
        # Create new assignments
        created_assignments = []
        for item in workflow_assignments:
            workflow_template = ApprovalWorkflowTemplate.objects.get(
                id=item['workflow_template_id']
            )
            
            # Get transaction_code_filter (optional)
            transaction_code_filter = item.get('transaction_code_filter')
            if transaction_code_filter == '':  # Empty string = null
                transaction_code_filter = None
            
            assignment = XX_WorkflowTemplateAssignment.objects.create(
                security_group=security_group,
                workflow_template=workflow_template,
                execution_order=item['execution_order'],
                transaction_code_filter=transaction_code_filter,
                is_active=True,
                created_by=request.user
            )
            created_assignments.append(assignment)
        
        serializer = WorkflowTemplateAssignmentSerializer(created_assignments, many=True)
        
        return Response({
            'success': True,
            'message': f'Assigned {len(created_assignments)} workflow(s) to "{security_group.group_name}"',
            'deleted_count': deleted_count,
            'created_count': len(created_assignments),
            'assignments': serializer.data
        }, status=status.HTTP_201_CREATED)


class ReorderWorkflowAssignmentsView(APIView):
    """
    PUT: Reorder workflow assignments for a security group
    Body: {security_group_id: int, assignment_orders: [{assignment_id: int, execution_order: int}]}
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def put(self, request):
        security_group_id = request.data.get('security_group_id')
        assignment_orders = request.data.get('assignment_orders', [])
        
        if not security_group_id or not assignment_orders:
            return Response({
                'success': False,
                'error': 'security_group_id and assignment_orders are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate security group exists
        if not XX_SecurityGroup.objects.filter(id=security_group_id).exists():
            return Response({
                'success': False,
                'error': 'Security group not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update each assignment's execution_order
        updated_count = 0
        for item in assignment_orders:
            assignment_id = item.get('assignment_id')
            execution_order = item.get('execution_order')
            
            if assignment_id and execution_order:
                XX_WorkflowTemplateAssignment.objects.filter(
                    id=assignment_id,
                    security_group_id=security_group_id
                ).update(execution_order=execution_order)
                updated_count += 1
        
        # Get updated assignments
        assignments = XX_WorkflowTemplateAssignment.objects.filter(
            security_group_id=security_group_id
        ).order_by('execution_order')
        
        serializer = WorkflowTemplateAssignmentSerializer(assignments, many=True)
        
        return Response({
            'success': True,
            'message': f'Reordered {updated_count} workflow assignment(s)',
            'assignments': serializer.data
        })
