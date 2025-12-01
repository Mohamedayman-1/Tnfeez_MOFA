from decimal import Decimal
from rest_framework import serializers

from account_and_entitys.models import XX_ACCOUNT_ENTITY_LIMIT
from .models import xx_TransactionTransfer


class TransactionTransferSerializer(serializers.ModelSerializer):
    """Legacy serializer with all fields."""
    class Meta:
        model = xx_TransactionTransfer
        fields = "__all__"


# ============================================================================
# DYNAMIC SEGMENT SERIALIZERS
# ============================================================================

class TransactionTransferDynamicSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer with dynamic segment support.
    Includes both legacy fields and dynamic segment assignments.
    """
    segments = serializers.SerializerMethodField()
    segment_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = xx_TransactionTransfer
        fields = [
            'transfer_id',
            'transaction',
            'reason',
            # Legacy segment fields (backward compatibility)
            'account_code',
            'account_name',
            'project_code',
            'project_name',
            'cost_center_code',
            'cost_center_name',
            # Financial fields
            'done',
            'encumbrance',
            'actual',
            'approved_budget',
            'available_budget',
            'from_center',
            'to_center',
            'commitments',
            'expenditures',
            'obligations',
            'other_consumption',
            'file',
            # Dynamic segment fields
            'segments',
            'segment_summary',
            'total_budget',
            'initial_budget',
            'budget_adjustments'
        ]
        read_only_fields = ('transfer_id', 'segments', 'segment_summary')
    
    def get_segments(self, obj):
        """Get full segment details."""
        return obj.get_segments_dict()
    
    def get_segment_summary(self, obj):
        """Get a concise summary of segment transfers."""
        segments = obj.get_segments_dict()
        summary = []
        
        for seg_id, seg_data in sorted(segments.items()):
            if seg_data['from_code'] == seg_data['to_code']:
                summary.append(f"{seg_data['segment_name']}: {seg_data['from_code']}")
            else:
                summary.append(
                    f"{seg_data['segment_name']}: {seg_data['from_code']} → {seg_data['to_code']}"
                )
        
        return " | ".join(summary)


class TransactionTransferCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new transaction transfers with dynamic segments.
    
    NEW SIMPLIFIED FORMAT:
    - Each transfer has EITHER from_center OR to_center (not both)
    - Segments only have 'code' field (not from_code/to_code)
    - Direction is determined by which center field is filled
    
    Example:
    {
        "transaction": 123,
        "from_center": "10000.00",  # Taking funds
        "to_center": "0.00",        # Must be 0 or empty
        "reason": "Transfer OUT",
        "segments": {
            "1": {"code": "10000"},  # Entity code
            "2": {"code": "50000"},  # Account code
            "3": {"code": "10000"}   # Project code
        }
    }
    """
    segments = serializers.DictField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        write_only=True,
        help_text="Format: {segment_id: {'code': 'xxx'}}"
    )
    
    class Meta:
        model = xx_TransactionTransfer
        fields = [
            'transaction',
            'reason',
            'from_center',
            'to_center',
            'file',
            'segments'
        ]
    
    def validate(self, data):
        """Validate that only ONE of from_center or to_center is filled."""
        from_center = data.get('from_center', 0)
        to_center = data.get('to_center', 0)
        
        # Convert to float for comparison
        from_val = float(from_center) if from_center not in [None, ''] else 0.0
        to_val = float(to_center) if to_center not in [None, ''] else 0.0
        
        # Both cannot be positive
        if from_val > 0 and to_val > 0:
            raise serializers.ValidationError(
                "لا يمكن أن يكون كل من 'من المركز' و'إلى المركز' قيم موجبة. "
                "يجب أن يكون كل صف تحويل إما مصدر (من المركز > 0) أو وجهة (إلى المركز > 0)."
            )
        
        # At least one must be positive
        if from_val <= 0 and to_val <= 0:
            raise serializers.ValidationError(
                "يجب أن يكون 'من المركز' أو 'إلى المركز' أكبر من 0."
            )
        
        return data
    
    def validate_segments(self, value):
        """Validate segment structure."""
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        # Validate segment data with new simplified format
        validation_result = SegmentManager.validate_transaction_segments_simple(value)
        if not validation_result['valid']:
            raise serializers.ValidationError(validation_result['errors'])
        
        return value
    
    def create(self, validated_data):
        """Create transaction transfer with segments."""
        from transaction.managers import TransactionSegmentManager
        
        segments_data = validated_data.pop('segments')
        
        # Extract budget_transfer
        budget_transfer = validated_data.pop('transaction')
        
        # Determine direction based on which center is filled
        from_center = float(validated_data.get('from_center', 0) or 0)
        to_center = float(validated_data.get('to_center', 0) or 0)
        is_source = from_center > 0  # True if taking funds, False if receiving
        
        # Create transfer with segments (simplified format)
        result = TransactionSegmentManager.create_transfer_with_segments_simple(
            budget_transfer=budget_transfer,
            transfer_data=validated_data,
            segments_data=segments_data,
            is_source=is_source
        )
        
        if not result['success']:
            raise serializers.ValidationError(result['errors'])
        
        return result['transaction_transfer']


class TransactionTransferUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing transaction transfers with dynamic segments.
    
    NEW SIMPLIFIED FORMAT:
    - Segments only have 'code' field (not from_code/to_code)
    - Direction determined by which center field is filled
    """
    segments = serializers.DictField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        write_only=True,
        required=False,
        help_text="Format: {segment_id: {'code': 'xxx'}}"
    )
    
    class Meta:
        model = xx_TransactionTransfer
        fields = [
            'reason',
            'from_center',
            'to_center',
            'file',
            'segments'
        ]
    
    def validate(self, data):
        """Validate that only ONE of from_center or to_center is filled."""
        # Get current values from instance if not in data
        from_center = data.get('from_center', self.instance.from_center if self.instance else 0)
        to_center = data.get('to_center', self.instance.to_center if self.instance else 0)
        
        # Convert to float for comparison
        from_val = float(from_center) if from_center not in [None, ''] else 0.0
        to_val = float(to_center) if to_center not in [None, ''] else 0.0
        
        # Both cannot be positive
        if from_val > 0 and to_val > 0:
            raise serializers.ValidationError(
                "لا يمكن أن يكون كل من 'من المركز' و'إلى المركز' قيم موجبة. "
                "يجب أن يكون كل صف تحويل إما مصدر (من المركز > 0) أو وجهة (إلى المركز > 0)."
            )
        
        # At least one must be positive
        if from_val <= 0 and to_val <= 0:
            raise serializers.ValidationError(
                "يجب أن يكون 'من المركز' أو 'إلى المركز' أكبر من 0."
            )
        
        return data
    
    def validate_segments(self, value):
        """Validate segment structure."""
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        # Validate segment data with new simplified format
        validation_result = SegmentManager.validate_transaction_segments_simple(value)
        if not validation_result['valid']:
            raise serializers.ValidationError(validation_result['errors'])
        
        return value
    
    def update(self, instance, validated_data):
        """Update transaction transfer and optionally update segments."""
        from transaction.managers import TransactionSegmentManager
        
        segments_data = validated_data.pop('segments', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update segments if provided
        if segments_data:
            # Determine direction based on which center is filled
            from_center = float(instance.from_center or 0)
            to_center = float(instance.to_center or 0)
            is_source = from_center > 0  # True if taking funds, False if receiving
            
            result = TransactionSegmentManager.update_transfer_segments_simple(
                transaction_transfer=instance,
                segments_data=segments_data,
                is_source=is_source
            )
            
            if not result['success']:
                raise serializers.ValidationError(result['errors'])
        
        return instance


class TransactionTransferListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views with segment summary.
    """
    segment_summary = serializers.SerializerMethodField()
    transaction_code = serializers.CharField(source='transaction.code', read_only=True)
    
    class Meta:
        model = xx_TransactionTransfer
        fields = [
            'transfer_id',
            'transaction',
            'transaction_code',
            'from_center',
            'to_center',
            'segment_summary',
            'reason'
        ]
    
    def get_segment_summary(self, obj):
        """Get concise segment summary."""
        segments = obj.get_segments_dict()
        summary = []
        
        for seg_id, seg_data in sorted(segments.items()):
            if seg_data['from_code'] != seg_data['to_code']:
                summary.append(f"{seg_data['from_code']}→{seg_data['to_code']}")
            else:
                summary.append(seg_data['from_code'])
        
        return " | ".join(summary) if summary else "No segments"


class TransactionSegmentValidationSerializer(serializers.Serializer):
    """
    Serializer for validating segment combinations before creating a transfer.
    """
    segments = serializers.DictField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        help_text="Format: {segment_id: {'from_code': 'xxx', 'to_code': 'yyy'}}"
    )
    transfer_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        help_text="Optional: Amount to validate against envelope balance"
    )
    
    def validate(self, data):
        """Validate segment combination."""
        from account_and_entitys.managers.segment_manager import SegmentManager
        from transaction.managers import TransactionSegmentManager
        
        segments_data = data['segments']
        
        # Validate segments exist and are valid
        validation_result = SegmentManager.validate_transaction_segments(segments_data)
        if not validation_result['valid']:
            raise serializers.ValidationError({
                'segments': validation_result['errors']
            })
        
        # Validate hierarchical rules if applicable
        hierarchy_result = TransactionSegmentManager.validate_hierarchical_transfer(segments_data)
        if not hierarchy_result['valid']:
            raise serializers.ValidationError({
                'segments': hierarchy_result['errors']
            })
        
        # Validate envelope balance if amount provided
        if 'transfer_amount' in data:
            balance_result = TransactionSegmentManager.validate_envelope_balance(
                segments_data,
                data['transfer_amount']
            )
            if not balance_result['valid']:
                raise serializers.ValidationError({
                    'envelope': balance_result['errors']
                })
            
            data['balance_info'] = {
                'from_balance': str(balance_result['from_balance']),
                'to_balance': str(balance_result['to_balance'])
            }
        
        return data
