from rest_framework import serializers
from .models import (
    XX_Account, XX_Entity, XX_PivotFund, XX_TransactionAudit, 
    XX_ACCOUNT_ENTITY_LIMIT, XX_Project, XX_BalanceReport,
    XX_SegmentType, XX_Segment, XX_TransactionSegment, XX_DynamicBalanceReport,
    XX_SegmentEnvelope, XX_SegmentMapping, XX_SegmentTransferLimit
)
# XX_ACCOUNT_mapping, XX_Entity_mapping

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_Account
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_Project
        fields = "__all__"


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_Entity
        fields = '__all__'

class PivotFundSerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_PivotFund
        fields = '__all__'

class TransactionAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_TransactionAudit
        fields = '__all__'

class AccountEntityLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_ACCOUNT_ENTITY_LIMIT
        fields = '__all__'

class BalanceReportSerializer(serializers.ModelSerializer):
    """Serializer for Balance Report model"""
    
    class Meta:
        model = XX_BalanceReport
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# class AccountMappingSerializer(serializers.ModelSerializer):
#     """Serializer for Account Mapping model"""
    
#     class Meta:
#         model = XX_ACCOUNT_mapping
#         fields = '__all__'


# class EntityMappingSerializer(serializers.ModelSerializer):
#     """Serializer for Entity Mapping model"""
    
#     class Meta:
#         model = XX_Entity_mapping
#         fields = '__all__'


# ============================================================================
# DYNAMIC SEGMENT SERIALIZERS
# ============================================================================

class SegmentTypeSerializer(serializers.ModelSerializer):
    """Serializer for segment type configuration (metadata)."""
    
    class Meta:
        model = XX_SegmentType
        fields = [
            'id',
            'segment_id',
            'segment_name',
            'segment_type',
            'oracle_segment_number',
            'is_required',
            'has_hierarchy',
            'max_length',
            'display_order',
            'description',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


class SegmentTypeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for segment type list views."""
    
    class Meta:
        model = XX_SegmentType
        fields = [
            'segment_id',
            'segment_name',
            'segment_type',
            'is_required',
            'has_hierarchy',
            'display_order'
        ]


class SegmentValueSerializer(serializers.ModelSerializer):
    """Serializer for segment values (replaces Entity/Account/Project serializers)."""
    segment_type_name = serializers.CharField(source='segment_type.segment_name', read_only=True)
    segment_type_id = serializers.IntegerField(source='segment_type.segment_id', read_only=True)
    
    class Meta:
        model = XX_Segment
        fields = [
            'id',
            'segment_type',
            'segment_type_name',
            'segment_type_id',
            'code',
            'parent_code',
            'alias',
            'level',
            'envelope_amount',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def validate(self, data):
        """Validate segment data."""
        # Validate hierarchy constraints
        segment_type = data.get('segment_type')
        parent_code = data.get('parent_code')
        
        if parent_code and not segment_type.has_hierarchy:
            raise serializers.ValidationError({
                'parent_code': f'Segment type "{segment_type.segment_name}" does not support hierarchy.'
            })
        
        # Validate code uniqueness within segment type
        code = data.get('code')
        if code and segment_type:
            existing = XX_Segment.objects.filter(
                segment_type=segment_type,
                code=code
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise serializers.ValidationError({
                    'code': f'Segment code "{code}" already exists for segment type "{segment_type.segment_name}".'
                })
        
        return data


class SegmentValueListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for segment value list views."""
    segment_type_name = serializers.CharField(source='segment_type.segment_name', read_only=True)
    
    class Meta:
        model = XX_Segment
        fields = [
            'id',
            'segment_type',
            'segment_type_name',
            'code',
            'alias',
            'parent_code',
            'level',
            'is_active',
            'created_at',
            'updated_at'
        ]


class SegmentHierarchySerializer(serializers.ModelSerializer):
    """Serializer for segment hierarchy views with children."""
    segment_type_name = serializers.CharField(source='segment_type.segment_name', read_only=True)
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = XX_Segment
        fields = [
            'id',
            'segment_type_name',
            'code',
            'alias',
            'parent_code',
            'level',
            'envelope_amount',
            'is_active',
            'children'
        ]
    
    def get_children(self, obj):
        """Get direct children of this segment."""
        from account_and_entitys.managers.segment_manager import SegmentManager
        children = SegmentManager.get_direct_children(
            segment_type_id=obj.segment_type.segment_id,
            parent_code=obj.code
        )
        return SegmentValueListSerializer(children, many=True).data


class TransactionSegmentSerializer(serializers.ModelSerializer):
    """Serializer for transaction-segment linkage."""
    segment_type_name = serializers.CharField(source='segment_type.segment_name', read_only=True)
    from_segment_alias = serializers.SerializerMethodField()
    to_segment_alias = serializers.SerializerMethodField()
    
    class Meta:
        model = XX_TransactionSegment
        fields = [
            'id',
            'transaction',
            'segment_type',
            'segment_type_name',
            'from_segment_code',
            'from_segment_alias',
            'to_segment_code',
            'to_segment_alias',
            'created_at'
        ]
        read_only_fields = ('id', 'created_at')
    
    def get_from_segment_alias(self, obj):
        """Get alias for from_segment_code."""
        if not obj.from_segment_code:
            return None
        try:
            segment = XX_Segment.objects.get(
                segment_type=obj.segment_type,
                code=obj.from_segment_code
            )
            return segment.alias
        except XX_Segment.DoesNotExist:
            return None
    
    def get_to_segment_alias(self, obj):
        """Get alias for to_segment_code."""
        if not obj.to_segment_code:
            return None
        try:
            segment = XX_Segment.objects.get(
                segment_type=obj.segment_type,
                code=obj.to_segment_code
            )
            return segment.alias
        except XX_Segment.DoesNotExist:
            return None


class DynamicBalanceReportSerializer(serializers.ModelSerializer):
    """Serializer for dynamic balance reports from Oracle."""
    segments_display = serializers.SerializerMethodField()
    
    class Meta:
        model = XX_DynamicBalanceReport
        fields = [
            'id',
            'control_budget_name',
            'ledger_name',
            'as_of_period',
            'segment_values',
            'segments_display',
            'encumbrance_ytd',
            'other_ytd',
            'actual_ytd',
            'funds_available_asof',
            'budget_ytd',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_segments_display(self, obj):
        """Get human-readable segment values."""
        if not obj.segment_values:
            return {}
        
        display = {}
        for seg_id, seg_code in obj.segment_values.items():
            try:
                segment_type = XX_SegmentType.objects.get(segment_id=int(seg_id))
                try:
                    segment = XX_Segment.objects.get(
                        segment_type=segment_type,
                        code=seg_code
                    )
                    display[segment_type.segment_name] = {
                        'code': seg_code,
                        'alias': segment.alias
                    }
                except XX_Segment.DoesNotExist:
                    display[segment_type.segment_name] = {
                        'code': seg_code,
                        'alias': None
                    }
            except XX_SegmentType.DoesNotExist:
                display[f'segment_{seg_id}'] = {
                    'code': seg_code,
                    'alias': None
                }
        
        return display


class TransactionSegmentBulkSerializer(serializers.Serializer):
    """Serializer for bulk creating transaction segments."""
    transaction_id = serializers.IntegerField()
    segments = serializers.DictField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        help_text='Format: {segment_id: {from_code: "xxx", to_code: "yyy"}}'
    )
    
    def validate_segments(self, value):
        """Validate segment structure."""
        for seg_id, seg_data in value.items():
            if 'from_code' not in seg_data or 'to_code' not in seg_data:
                raise serializers.ValidationError(
                    f'Segment {seg_id} must have both from_code and to_code.'
                )
            
            # Validate segment type exists
            try:
                segment_type = XX_SegmentType.objects.get(segment_id=int(seg_id))
            except XX_SegmentType.DoesNotExist:
                raise serializers.ValidationError(
                    f'Segment type with ID {seg_id} does not exist.'
                )
        
        return value


# ============================================
# PHASE 3: ENVELOPE AND MAPPING SERIALIZERS
# ============================================

class SegmentEnvelopeSerializer(serializers.ModelSerializer):
    """Serializer for Segment Envelope model (Phase 3)."""
    
    segment_combination_display = serializers.SerializerMethodField()
    
    class Meta:
        model = XX_SegmentEnvelope
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_segment_combination_display(self, obj):
        """Get human-readable segment combination."""
        if not obj.segment_combination:
            return ""
        
        segments = []
        for seg_id, seg_code in sorted(obj.segment_combination.items(), key=lambda x: int(x[0])):
            try:
                seg_type = XX_SegmentType.objects.get(segment_id=int(seg_id))
                segments.append(f"{seg_type.segment_name}: {seg_code}")
            except XX_SegmentType.DoesNotExist:
                segments.append(f"S{seg_id}: {seg_code}")
        return " | ".join(segments)
    
    def validate_segment_combination(self, value):
        """Validate segment combination structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Segment combination must be a dictionary.")
        
        if not value:
            raise serializers.ValidationError("Segment combination cannot be empty.")
        
        # Validate each segment exists
        for seg_type_id, seg_code in value.items():
            try:
                segment_type = XX_SegmentType.objects.get(segment_id=int(seg_type_id))
                XX_Segment.objects.get(segment_type=segment_type, code=seg_code)
            except XX_SegmentType.DoesNotExist:
                raise serializers.ValidationError(
                    f"Segment type with ID {seg_type_id} does not exist."
                )
            except XX_Segment.DoesNotExist:
                raise serializers.ValidationError(
                    f"Segment with code {seg_code} does not exist for segment type {seg_type_id}."
                )
        
        return value


class SegmentMappingSerializer(serializers.ModelSerializer):
    """Serializer for Segment Mapping model (Phase 3)."""
    
    segment_type_name = serializers.CharField(source='segment_type.segment_name', read_only=True)
    source_code = serializers.CharField(source='source_segment.code', read_only=True)
    source_alias = serializers.CharField(source='source_segment.alias', read_only=True)
    target_code = serializers.CharField(source='target_segment.code', read_only=True)
    target_alias = serializers.CharField(source='target_segment.alias', read_only=True)
    
    class Meta:
        model = XX_SegmentMapping
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def validate(self, data):
        """Validate the mapping."""
        segment_type = data.get('segment_type')
        source_segment = data.get('source_segment')
        target_segment = data.get('target_segment')
        
        # Validate both segments are from the same type
        if source_segment.segment_type_id != segment_type.segment_id:
            raise serializers.ValidationError(
                "Source segment must belong to the specified segment type."
            )
        
        if target_segment.segment_type_id != segment_type.segment_id:
            raise serializers.ValidationError(
                "Target segment must belong to the specified segment type."
            )
        
        # Validate source != target
        if source_segment.id == target_segment.id:
            raise serializers.ValidationError(
                "Source and target segments cannot be the same."
            )
        
        return data


class SegmentEnvelopeCreateSerializer(serializers.Serializer):
    """Serializer for creating segment envelopes with validation."""
    
    segment_combination = serializers.DictField(
        child=serializers.CharField(),
        help_text='Format: {segment_type_id: segment_code}'
    )
    envelope_amount = serializers.DecimalField(max_digits=30, decimal_places=2)
    fiscal_year = serializers.CharField(max_length=10, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data):
        """Create envelope using EnvelopeBalanceManager."""
        from account_and_entitys.managers import EnvelopeBalanceManager
        
        result = EnvelopeBalanceManager.update_envelope_amount(
            segment_combination=validated_data['segment_combination'],
            new_amount=validated_data['envelope_amount'],
            fiscal_year=validated_data.get('fiscal_year')
        )
        
        if not result['success']:
            raise serializers.ValidationError(result['errors'])
        
        return result['envelope']


class SegmentMappingCreateSerializer(serializers.Serializer):
    """Serializer for creating segment mappings with validation."""
    
    segment_type_id = serializers.IntegerField()
    source_code = serializers.CharField(max_length=50)
    target_code = serializers.CharField(max_length=50)
    mapping_type = serializers.CharField(max_length=50, default='STANDARD')
    description = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data):
        """Create mapping using SegmentMappingManager."""
        from account_and_entitys.managers import SegmentMappingManager
        
        result = SegmentMappingManager.create_mapping(
            segment_type_id=validated_data['segment_type_id'],
            source_code=validated_data['source_code'],
            target_code=validated_data['target_code'],
            mapping_type=validated_data.get('mapping_type', 'STANDARD'),
            description=validated_data.get('description')
        )
        
        if not result['success']:
            raise serializers.ValidationError(result['errors'])
        
        return result['mapping']


class SegmentTransferLimitSerializer(serializers.ModelSerializer):
    """Serializer for Segment Transfer Limit model (Phase 3)."""
    
    segment_combination_display = serializers.SerializerMethodField()
    
    class Meta:
        model = XX_SegmentTransferLimit
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'source_count', 'target_count')
    
    def get_segment_combination_display(self, obj):
        """Get human-readable segment combination."""
        if not obj.segment_combination:
            return ""
        
        segments = []
        for seg_id, seg_code in sorted(obj.segment_combination.items(), key=lambda x: int(x[0])):
            try:
                seg_type = XX_SegmentType.objects.get(segment_id=int(seg_id))
                segments.append(f"{seg_type.segment_name}: {seg_code}")
            except XX_SegmentType.DoesNotExist:
                segments.append(f"S{seg_id}: {seg_code}")
        return " | ".join(segments)
