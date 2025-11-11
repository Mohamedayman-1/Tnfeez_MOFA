# Transaction & API Updates Guide

## Overview
This document covers modifications to transaction handling, API endpoints, serializers, and views to support dynamic segments.

---

## Part 1: Transaction Model Updates

### File: `transaction/models.py`

**Current State**: Hardcoded fields for `cost_center_code`, `account_code`, `project_code`

**Strategy**: Keep old fields for backward compatibility, add relationship to dynamic segments

```python
from django.db import models

class xx_TransactionTransfer(models.Model):
    """Model for ADJD transaction transfers - Updated for dynamic segments"""

    transfer_id = models.AutoField(primary_key=True)
    transaction = models.ForeignKey(
        'budget_management.xx_BudgetTransfer', 
        on_delete=models.CASCADE, 
        db_column="transaction_id", 
        null=True, 
        blank=True, 
        related_name="transfers"
    )
    reason = models.TextField(null=True, blank=True)
    
    # ============================================
    # LEGACY FIELDS (Keep for backward compatibility during migration)
    # ============================================
    account_code = models.IntegerField(null=True, blank=True)
    account_name = models.TextField(null=True, blank=True)
    project_code = models.TextField(null=True, blank=True)
    project_name = models.TextField(null=True, blank=True)
    cost_center_code = models.IntegerField(null=True, blank=True)
    cost_center_name = models.TextField(null=True, blank=True)
    
    # ============================================
    # DYNAMIC SEGMENT SUPPORT
    # New: Segments stored in XX_TransactionSegment (many-to-many through table)
    # Access via: transaction_transfer.transaction_segments.all()
    # ============================================
    
    # Financial fields (remain unchanged)
    done = models.IntegerField(default=1)
    encumbrance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    actual = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    approved_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    available_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    from_center = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    to_center = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    budget_adjustments = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, default=0)
    commitments = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, default=0)
    expenditures = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, default=0)
    initial_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    obligations = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    other_consumption = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, default=0)
    
    file = models.FileField(upload_to="transfers/", null=True, blank=True)

    class Meta:
        db_table = "XX_TRANSACTION_TRANSFER_XX"

    def __str__(self):
        return f"ADJD Transfer {self.transfer_id}"
    
    # ============================================
    # NEW HELPER METHODS FOR DYNAMIC SEGMENTS
    # ============================================
    
    def get_segments_dict(self):
        """
        Get all segment values as a dictionary.
        Returns: {"Entity": "12345", "Account": "67890", "Project": "98765"}
        """
        from account_and_entitys.models import XX_TransactionSegment
        
        segments = XX_TransactionSegment.objects.filter(
            transaction_transfer=self
        ).select_related('segment_type', 'segment_value')
        
        return {
            ts.segment_type.segment_name: ts.segment_value.code
            for ts in segments
        }
    
    def get_segment_value(self, segment_name):
        """
        Get a specific segment value by name.
        Args:
            segment_name: "Entity", "Account", "Project", etc.
        Returns:
            Segment code (str) or None
        """
        from account_and_entitys.models import XX_TransactionSegment
        
        try:
            ts = XX_TransactionSegment.objects.select_related(
                'segment_type', 'segment_value'
            ).get(
                transaction_transfer=self,
                segment_type__segment_name=segment_name
            )
            return ts.segment_value.code
        except XX_TransactionSegment.DoesNotExist:
            return None
    
    def set_segments(self, segment_data):
        """
        Set segment values for this transaction.
        Args:
            segment_data: Dict like {"Entity": "12345", "Account": "67890"}
        """
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        # Clear existing segments
        self.transaction_segments.all().delete()
        
        # Create new segments
        SegmentManager.create_transaction_segments(self, segment_data)
    
    def get_legacy_segments(self):
        """
        Return legacy segment fields for backward compatibility.
        Returns: Dict with 'entity', 'account', 'project' keys
        """
        return {
            'entity': str(self.cost_center_code) if self.cost_center_code else None,
            'account': str(self.account_code) if self.account_code else None,
            'project': str(self.project_code) if self.project_code else None,
        }
    
    def sync_legacy_to_dynamic(self):
        """
        Sync legacy fields to dynamic segment system.
        Call this during migration to populate XX_TransactionSegment from old fields.
        """
        from account_and_entitys.managers.segment_manager import SegmentManager
        from account_and_entitys.models import XX_SegmentType
        
        segment_data = {}
        
        # Map legacy fields to segment types
        if self.cost_center_code:
            segment_data['Entity'] = str(self.cost_center_code)
        if self.account_code:
            segment_data['Account'] = str(self.account_code)
        if self.project_code:
            segment_data['Project'] = str(self.project_code)
        
        if segment_data:
            try:
                SegmentManager.create_transaction_segments(self, segment_data)
            except Exception as e:
                print(f"Error syncing segments for transfer {self.transfer_id}: {e}")
```

---

## Part 2: Serializers

### File: `transaction/serializers.py`

Create or update this file:

```python
from rest_framework import serializers
from transaction.models import xx_TransactionTransfer
from account_and_entitys.models import XX_TransactionSegment, XX_SegmentType
from account_and_entitys.managers.segment_manager import SegmentManager


class TransactionSegmentSerializer(serializers.Serializer):
    """Serializer for individual segment in a transaction"""
    segment_name = serializers.CharField()
    segment_code = serializers.CharField()
    segment_alias = serializers.CharField(allow_null=True, required=False)
    from_code = serializers.CharField(allow_null=True, required=False)
    to_code = serializers.CharField(allow_null=True, required=False)


class xx_TransactionTransferSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer with dynamic segment support.
    
    Request format (creating/updating):
    {
        "transaction_id": 123,
        "reason": "Budget adjustment",
        "segments": {
            "Entity": "12345",
            "Account": "67890",
            "Project": "98765",
            "LineItem": "ABC123"  // If client has 4 segments
        },
        "from_center": 1000,
        "to_center": 500,
        ...
    }
    
    Response format (reading):
    {
        "transfer_id": 456,
        "segments": {
            "Entity": {
                "code": "12345",
                "alias": "Main Department",
                "from_code": null,
                "to_code": null
            },
            "Account": {...},
            ...
        },
        "legacy_segments": {  // For backward compatibility
            "entity": "12345",
            "account": "67890",
            "project": "98765"
        },
        ...
    }
    """
    
    # Dynamic segments field (read/write)
    segments = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        help_text="Dict of segment_name: segment_code"
    )
    
    # Detailed segment information (read-only)
    segments_detailed = serializers.SerializerMethodField()
    
    # Legacy fields (read-only for backward compatibility)
    legacy_segments = serializers.SerializerMethodField()
    
    class Meta:
        model = xx_TransactionTransfer
        fields = '__all__'
        read_only_fields = ['transfer_id', 'segments_detailed', 'legacy_segments']
    
    def get_segments_detailed(self, obj):
        """Get detailed segment information including aliases"""
        transaction_segments = XX_TransactionSegment.objects.filter(
            transaction_transfer=obj
        ).select_related('segment_type', 'segment_value', 'from_segment_value', 'to_segment_value')
        
        result = {}
        for ts in transaction_segments:
            result[ts.segment_type.segment_name] = {
                'code': ts.segment_value.code,
                'alias': ts.segment_value.alias,
                'from_code': ts.from_segment_value.code if ts.from_segment_value else None,
                'to_code': ts.to_segment_value.code if ts.to_segment_value else None,
            }
        
        return result
    
    def get_legacy_segments(self, obj):
        """Return legacy segment fields for backward compatibility"""
        return obj.get_legacy_segments()
    
    def validate_segments(self, value):
        """Validate that all required segments are provided"""
        is_valid, error_msg = SegmentManager.validate_transaction_segments(value)
        if not is_valid:
            raise serializers.ValidationError(error_msg)
        return value
    
    def create(self, validated_data):
        """Create transaction with dynamic segments"""
        segments_data = validated_data.pop('segments', {})
        
        # Create transaction transfer
        transaction_transfer = xx_TransactionTransfer.objects.create(**validated_data)
        
        # Create segment associations
        if segments_data:
            try:
                SegmentManager.create_transaction_segments(
                    transaction_transfer, 
                    segments_data
                )
                
                # Also populate legacy fields for backward compatibility
                self._populate_legacy_fields(transaction_transfer, segments_data)
                transaction_transfer.save()
                
            except Exception as e:
                # Rollback transaction creation if segment creation fails
                transaction_transfer.delete()
                raise serializers.ValidationError(f"Error creating segments: {str(e)}")
        
        return transaction_transfer
    
    def update(self, instance, validated_data):
        """Update transaction and segments"""
        segments_data = validated_data.pop('segments', None)
        
        # Update transaction fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update segments if provided
        if segments_data is not None:
            instance.set_segments(segments_data)
            self._populate_legacy_fields(instance, segments_data)
            instance.save()
        
        return instance
    
    def _populate_legacy_fields(self, transaction_transfer, segments_data):
        """
        Populate legacy fields from segment data for backward compatibility.
        This ensures old code still works during migration period.
        """
        if 'Entity' in segments_data:
            try:
                transaction_transfer.cost_center_code = int(segments_data['Entity'])
            except (ValueError, TypeError):
                transaction_transfer.cost_center_code = None
        
        if 'Account' in segments_data:
            try:
                transaction_transfer.account_code = int(segments_data['Account'])
            except (ValueError, TypeError):
                transaction_transfer.account_code = None
        
        if 'Project' in segments_data:
            transaction_transfer.project_code = segments_data['Project']


class SegmentTypeSerializer(serializers.ModelSerializer):
    """Serializer for segment type configuration"""
    
    class Meta:
        model = XX_SegmentType
        fields = [
            'segment_id', 'segment_name', 'segment_type', 
            'oracle_segment_number', 'is_required', 'has_hierarchy',
            'max_length', 'display_order', 'is_active'
        ]
```

---

## Part 3: API Views

### File: `account_and_entitys/views.py`

Add these new viewsets:

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from account_and_entitys.models import XX_SegmentType, XX_Segment
from account_and_entitys.managers.segment_manager import SegmentManager
from transaction.serializers import SegmentTypeSerializer
from django.db.models import Q


class SegmentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for segment type configuration.
    Read-only because segment types are configured during installation.
    
    Endpoints:
    - GET /api/segments/types/ - List all segment types
    - GET /api/segments/types/{id}/ - Get specific segment type
    - GET /api/segments/types/config/ - Get full client configuration
    """
    
    queryset = XX_SegmentType.objects.all()
    serializer_class = SegmentTypeSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        """
        Return full segment configuration for this client.
        Frontend uses this to dynamically build forms.
        """
        segment_types = XX_SegmentType.objects.filter(
            is_active=True
        ).order_by('display_order')
        
        serializer = self.get_serializer(segment_types, many=True)
        
        return Response({
            'client_name': getattr(settings, 'CLIENT_NAME', 'Unknown'),
            'total_segments': segment_types.count(),
            'segments': serializer.data,
            'validation_rules': {
                'allow_cross_segment_transfers': True,
                'require_envelope_check': True,
                'enforce_hierarchy_constraints': True
            }
        })
    
    @action(detail=True, methods=['get'])
    def values(self, request, pk=None):
        """
        Get all values for a specific segment type.
        
        GET /api/segments/types/1/values/?search=dept&parent=100
        """
        segment_type = self.get_object()
        
        # Query parameters
        search = request.query_params.get('search', None)
        parent = request.query_params.get('parent', None)
        
        # Build query
        queryset = XX_Segment.objects.filter(
            segment_type=segment_type,
            is_active=True
        )
        
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) | Q(alias__icontains=search)
            )
        
        if parent:
            queryset = queryset.filter(parent_code=parent)
        
        queryset = queryset.order_by('code')[:100]  # Limit to 100 results
        
        # Serialize
        data = [
            {
                'code': seg.code,
                'alias': seg.alias,
                'parent_code': seg.parent_code,
                'level': seg.level,
                'envelope_amount': float(seg.envelope_amount) if seg.envelope_amount else None
            }
            for seg in queryset
        ]
        
        return Response({
            'segment_type': segment_type.segment_name,
            'count': len(data),
            'values': data
        })
    
    @action(detail=True, methods=['get'])
    def hierarchy(self, request, pk=None):
        """
        Get hierarchical tree for a segment type.
        
        GET /api/segments/types/1/hierarchy/
        """
        segment_type = self.get_object()
        
        if not segment_type.has_hierarchy:
            return Response(
                {'error': 'This segment type does not support hierarchy'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tree = SegmentManager.get_segment_hierarchy_tree(segment_type.segment_name)
        
        return Response({
            'segment_type': segment_type.segment_name,
            'hierarchy': tree
        })


class SegmentValueViewSet(viewsets.ModelViewSet):
    """
    API endpoint for segment values (codes).
    
    Endpoints:
    - GET /api/segments/values/ - List all segment values (filtered)
    - POST /api/segments/values/ - Create new segment value
    - GET /api/segments/values/{id}/ - Get specific segment
    - PUT /api/segments/values/{id}/ - Update segment
    - DELETE /api/segments/values/{id}/ - Deactivate segment
    """
    
    queryset = XX_Segment.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        # Simple dict serializer for now
        return None
    
    def get_queryset(self):
        """Filter by segment type if provided"""
        queryset = XX_Segment.objects.filter(is_active=True)
        
        segment_type_id = self.request.query_params.get('segment_type', None)
        if segment_type_id:
            queryset = queryset.filter(segment_type_id=segment_type_id)
        
        return queryset.select_related('segment_type')
    
    def list(self, request):
        """List segment values with filtering"""
        queryset = self.get_queryset()
        
        # Additional filters
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) | Q(alias__icontains=search)
            )
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self._serialize_segments(page)
            return self.get_paginated_response(data)
        
        data = self._serialize_segments(queryset)
        return Response(data)
    
    def retrieve(self, request, pk=None):
        """Get single segment value"""
        segment = self.get_object()
        return Response(self._serialize_segment(segment))
    
    def create(self, request):
        """Create new segment value"""
        segment_type_id = request.data.get('segment_type_id')
        code = request.data.get('code')
        parent_code = request.data.get('parent_code')
        alias = request.data.get('alias')
        envelope_amount = request.data.get('envelope_amount')
        
        # Validate
        if not segment_type_id or not code:
            return Response(
                {'error': 'segment_type_id and code are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id)
        except XX_SegmentType.DoesNotExist:
            return Response(
                {'error': 'Invalid segment_type_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check for duplicates
        if XX_Segment.objects.filter(segment_type=segment_type, code=code).exists():
            return Response(
                {'error': f'Segment code {code} already exists for {segment_type.segment_name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create
        segment = XX_Segment.objects.create(
            segment_type=segment_type,
            code=code,
            parent_code=parent_code,
            alias=alias,
            envelope_amount=envelope_amount,
            is_active=True
        )
        
        return Response(
            self._serialize_segment(segment),
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, pk=None):
        """Update segment value"""
        segment = self.get_object()
        
        # Update fields
        if 'alias' in request.data:
            segment.alias = request.data['alias']
        if 'parent_code' in request.data:
            segment.parent_code = request.data['parent_code']
        if 'envelope_amount' in request.data:
            segment.envelope_amount = request.data['envelope_amount']
        if 'is_active' in request.data:
            segment.is_active = request.data['is_active']
        
        segment.save()
        
        return Response(self._serialize_segment(segment))
    
    def destroy(self, request, pk=None):
        """Soft delete segment (deactivate)"""
        segment = self.get_object()
        segment.is_active = False
        segment.save()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """Get all children of a segment"""
        segment = self.get_object()
        
        if not segment.segment_type.has_hierarchy:
            return Response(
                {'error': 'This segment type does not support hierarchy'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        children_codes = SegmentManager.get_all_children(
            segment.segment_type,
            segment.code
        )
        
        children = XX_Segment.objects.filter(
            segment_type=segment.segment_type,
            code__in=children_codes,
            is_active=True
        )
        
        return Response({
            'parent': self._serialize_segment(segment),
            'children_count': len(children_codes),
            'children': self._serialize_segments(children)
        })
    
    def _serialize_segment(self, segment):
        """Helper to serialize a single segment"""
        return {
            'id': segment.id,
            'segment_type': {
                'id': segment.segment_type.segment_id,
                'name': segment.segment_type.segment_name
            },
            'code': segment.code,
            'alias': segment.alias,
            'parent_code': segment.parent_code,
            'level': segment.level,
            'envelope_amount': float(segment.envelope_amount) if segment.envelope_amount else None,
            'is_active': segment.is_active
        }
    
    def _serialize_segments(self, segments):
        """Helper to serialize list of segments"""
        return [self._serialize_segment(seg) for seg in segments]
```

---

## Part 4: URL Configuration

### File: `account_and_entitys/urls.py`

Add new routes:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from account_and_entitys import views

router = DefaultRouter()

# Existing routes
# ... (keep your existing routes)

# New dynamic segment routes
router.register(r'segments/types', views.SegmentTypeViewSet, basename='segment-type')
router.register(r'segments/values', views.SegmentValueViewSet, basename='segment-value')

urlpatterns = [
    path('', include(router.urls)),
    # ... (other existing paths)
]
```

---

## Part 5: Transaction Views Update

### File: `transaction/views.py`

Update transaction creation logic to use dynamic segments:

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from transaction.models import xx_TransactionTransfer
from transaction.serializers import xx_TransactionTransferSerializer
from account_and_entitys.managers.segment_manager import SegmentManager


class xx_TransactionTransferViewSet(viewsets.ModelViewSet):
    """
    ViewSet for transaction transfers with dynamic segment support.
    """
    
    queryset = xx_TransactionTransfer.objects.all()
    serializer_class = xx_TransactionTransferSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create transaction with dynamic segments.
        
        Request body:
        {
            "transaction_id": 123,
            "segments": {
                "Entity": "12345",
                "Account": "67890",
                "Project": "98765"
            },
            "from_center": 1000,
            "to_center": 500,
            "reason": "Budget adjustment"
        }
        """
        
        # Validate segments before creating transaction
        segments_data = request.data.get('segments', {})
        if segments_data:
            is_valid, error_msg = SegmentManager.validate_transaction_segments(segments_data)
            if not is_valid:
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Use serializer to create
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Create multiple transactions at once.
        
        Request body:
        {
            "transactions": [
                {"segments": {...}, "from_center": 100, ...},
                {"segments": {...}, "from_center": 200, ...}
            ]
        }
        """
        transactions_data = request.data.get('transactions', [])
        
        if not transactions_data:
            return Response(
                {'error': 'No transactions provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_transactions = []
        errors = []
        
        for idx, trans_data in enumerate(transactions_data):
            try:
                # Validate segments
                segments_data = trans_data.get('segments', {})
                is_valid, error_msg = SegmentManager.validate_transaction_segments(segments_data)
                if not is_valid:
                    errors.append({
                        'index': idx,
                        'error': error_msg
                    })
                    continue
                
                # Create transaction
                serializer = self.get_serializer(data=trans_data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                created_transactions.append(serializer.data)
                
            except Exception as e:
                errors.append({
                    'index': idx,
                    'error': str(e)
                })
        
        return Response({
            'created_count': len(created_transactions),
            'error_count': len(errors),
            'created': created_transactions,
            'errors': errors
        })
    
    @action(detail=True, methods=['get'])
    def segments(self, request, pk=None):
        """
        Get detailed segment information for a transaction.
        
        GET /api/transfers/{id}/segments/
        """
        transaction = self.get_object()
        segments_dict = transaction.get_segments_dict()
        
        # Get detailed info
        from account_and_entitys.models import XX_TransactionSegment
        segments_detailed = XX_TransactionSegment.objects.filter(
            transaction_transfer=transaction
        ).select_related('segment_type', 'segment_value', 'from_segment_value', 'to_segment_value')
        
        detailed_data = []
        for ts in segments_detailed:
            detailed_data.append({
                'segment_type': ts.segment_type.segment_name,
                'segment_code': ts.segment_value.code,
                'segment_alias': ts.segment_value.alias,
                'from_code': ts.from_segment_value.code if ts.from_segment_value else None,
                'to_code': ts.to_segment_value.code if ts.to_segment_value else None,
            })
        
        return Response({
            'transfer_id': transaction.transfer_id,
            'segments': segments_dict,
            'segments_detailed': detailed_data
        })
```

---

## Part 6: Budget Management Updates

### File: `budget_management/views.py`

Update dashboard and filter functions to use dynamic segments:

```python
from account_and_entitys.managers.segment_manager import SegmentManager
from account_and_entitys.models import XX_Segment, XX_SegmentType


def DashBoard_filler_per_Project(request):
    """
    Updated dashboard filter that works with dynamic segments.
    Now handles any segment type, not just hardcoded Project.
    """
    
    # Get segment type for filtering (from query param or default to first hierarchical segment)
    segment_type_name = request.GET.get('segment_type', None)
    
    if not segment_type_name:
        # Default to first hierarchical segment type
        segment_type = XX_SegmentType.objects.filter(
            has_hierarchy=True,
            is_active=True
        ).order_by('display_order').first()
    else:
        segment_type = SegmentManager.get_segment_type_by_name(segment_type_name)
    
    if not segment_type:
        return Response(
            {'error': 'No hierarchical segment type found'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get user's accessible segments (replace old project-based logic)
    user = request.user
    user_segment_codes = get_user_accessible_segments(user, segment_type)
    
    # Get all children for these segments
    all_segment_codes = set()
    for code in user_segment_codes:
        all_segment_codes.add(code)
        children = SegmentManager.get_all_children(segment_type, code)
        all_segment_codes.update(children)
    
    # Filter transactions by these segments
    from account_and_entitys.models import XX_TransactionSegment
    
    filtered_transfers = xx_TransactionTransfer.objects.filter(
        transaction_segments__segment_type=segment_type,
        transaction_segments__segment_value__code__in=all_segment_codes
    ).distinct()
    
    # Aggregate data...
    # (rest of dashboard logic)
    
    return Response({
        'segment_type': segment_type.segment_name,
        'filtered_count': filtered_transfers.count(),
        # ... other dashboard data
    })


def get_user_accessible_segments(user, segment_type):
    """
    Get list of segment codes that user has access to.
    Replace old get_entities_with_children logic.
    """
    from user_management.models import UserAbilities
    
    # Get user's abilities filtered by segment type
    abilities = UserAbilities.objects.filter(
        user=user,
        segment_type=segment_type,
        is_active=True
    ).values_list('segment_code', flat=True)
    
    return list(abilities)
```

---

## Part 7: User Management Updates

### File: `user_management/models.py`

Update to support dynamic segments in user abilities:

```python
class UserAbilities(models.Model):
    """
    Updated to support dynamic segments instead of hardcoded projects.
    Each user can have abilities for different segment types.
    """
    
    user = models.ForeignKey('xx_User', on_delete=models.CASCADE, related_name='abilities')
    
    # NEW: Support for dynamic segments
    segment_type = models.ForeignKey(
        'account_and_entitys.XX_SegmentType',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Which segment type this ability applies to"
    )
    segment_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="The segment code user has access to"
    )
    
    # LEGACY: Keep old project field for backward compatibility
    project = models.ForeignKey(
        'account_and_entitys.XX_Project',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "XX_USER_ABILITIES_XX"
        unique_together = ("user", "segment_type", "segment_code")
    
    def __str__(self):
        if self.segment_type:
            return f"{self.user.username} - {self.segment_type.segment_name}: {self.segment_code}"
        return f"{self.user.username} - Project: {self.project}"
```

---

## Part 8: Testing the New System

Create: `account_and_entitys/tests/test_dynamic_segments.py`

```python
from django.test import TestCase
from account_and_entitys.models import XX_SegmentType, XX_Segment
from account_and_entitys.managers.segment_manager import SegmentManager
from transaction.models import xx_TransactionTransfer


class DynamicSegmentTests(TestCase):
    """Test dynamic segment system"""
    
    def setUp(self):
        """Create test segment types"""
        self.entity_type = XX_SegmentType.objects.create(
            segment_id=1,
            segment_name="Entity",
            segment_type="cost_center",
            oracle_segment_number=1,
            is_required=True,
            has_hierarchy=True
        )
        
        self.account_type = XX_SegmentType.objects.create(
            segment_id=2,
            segment_name="Account",
            segment_type="account",
            oracle_segment_number=2,
            is_required=True,
            has_hierarchy=True
        )
    
    def test_create_segment_values(self):
        """Test creating segment values"""
        entity = XX_Segment.objects.create(
            segment_type=self.entity_type,
            code="12345",
            alias="Test Entity"
        )
        
        self.assertEqual(entity.code, "12345")
        self.assertEqual(entity.segment_type.segment_name, "Entity")
    
    def test_segment_hierarchy(self):
        """Test hierarchical segment relationships"""
        parent = XX_Segment.objects.create(
            segment_type=self.entity_type,
            code="100",
            alias="Parent Dept"
        )
        
        child1 = XX_Segment.objects.create(
            segment_type=self.entity_type,
            code="101",
            parent_code="100",
            alias="Child Dept 1"
        )
        
        child2 = XX_Segment.objects.create(
            segment_type=self.entity_type,
            code="102",
            parent_code="100",
            alias="Child Dept 2"
        )
        
        # Test get_all_children
        children = SegmentManager.get_all_children(self.entity_type, "100")
        self.assertIn("101", children)
        self.assertIn("102", children)
    
    def test_validate_transaction_segments(self):
        """Test segment validation"""
        # Create segments
        XX_Segment.objects.create(
            segment_type=self.entity_type,
            code="12345"
        )
        XX_Segment.objects.create(
            segment_type=self.account_type,
            code="67890"
        )
        
        # Valid case
        is_valid, msg = SegmentManager.validate_transaction_segments({
            "Entity": "12345",
            "Account": "67890"
        })
        self.assertTrue(is_valid)
        
        # Missing required segment
        is_valid, msg = SegmentManager.validate_transaction_segments({
            "Entity": "12345"
            # Missing Account
        })
        self.assertFalse(is_valid)
        self.assertIn("Account", msg)
```

---

## Summary

This document covered:

1. **Transaction model updates** - Added helper methods, kept legacy fields
2. **Serializers** - Dynamic segment serialization
3. **API ViewSets** - New endpoints for segment configuration and values
4. **URL routing** - New API routes
5. **Transaction views** - Updated to use SegmentManager
6. **Budget management** - Dashboard updates for dynamic segments
7. **User management** - Abilities updated for dynamic segments
8. **Testing** - Unit tests for new functionality

**Next Steps:**
1. Implement Oracle integration updates (FBDI generation with dynamic segments)
2. Create data migration scripts
3. Update frontend to consume new APIs

Would you like me to create the Oracle integration guide next?
