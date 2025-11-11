"""
EnvelopeBalanceManager - Phase 3
Manages envelope balance operations with dynamic segment support.
Replaces legacy EnvelopeManager project-specific logic.
"""

from decimal import Decimal
from django.db import transaction as db_transaction
from django.db.models import Sum, Q, F, Value
from django.db.models.functions import Coalesce
from account_and_entitys.models import (
    XX_SegmentEnvelope,
    XX_SegmentType,
    XX_Segment,
    XX_TransactionSegment
)
from account_and_entitys.managers.segment_manager import SegmentManager


class EnvelopeBalanceManager:
    """
    Manager class for envelope balance operations with dynamic segments.
    Handles envelope lookups, balance calculations, and updates.
    """
    
    @staticmethod
    def get_envelope_for_segments(segment_combination, fiscal_year=None, use_hierarchy=True):
        """
        Get envelope for a specific segment combination.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
                Example: {1: 'E001', 2: 'A100', 3: 'P001'}
            fiscal_year: Optional fiscal year filter
            use_hierarchy: If True (default), walks up parent hierarchy to find envelope
        
        Returns:
            XX_SegmentEnvelope object or None
        """
        try:
            query = XX_SegmentEnvelope.objects.filter(is_active=True)
            
            if fiscal_year:
                query = query.filter(fiscal_year=fiscal_year)
            
            # Find envelope that matches the segment combination (exact match)
            for envelope in query:
                if envelope.matches_segments(segment_combination):
                    return envelope
            
            # If not found and hierarchy enabled, try parent hierarchy
            if use_hierarchy:
                parent_combination, _ = EnvelopeBalanceManager.get_hierarchical_envelope(
                    segment_combination,
                    fiscal_year
                )
                if parent_combination and parent_combination != segment_combination:
                    # Found parent envelope, get it
                    for envelope in query:
                        if envelope.matches_segments(parent_combination):
                            return envelope
            
            return None
        except Exception as e:
            print(f"Error in get_envelope_for_segments: {e}")
            return None
    
    @staticmethod
    def get_envelope_amount(segment_combination, fiscal_year=None, use_hierarchy=True):
        """
        Get envelope amount for a segment combination.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            fiscal_year: Optional fiscal year filter
            use_hierarchy: If True (default), checks parent hierarchy
        
        Returns:
            Decimal: Envelope amount or 0 if not found
        """
        envelope = EnvelopeBalanceManager.get_envelope_for_segments(
            segment_combination,
            fiscal_year,
            use_hierarchy
        )
        return envelope.envelope_amount if envelope else Decimal('0.00')
    
    @staticmethod
    def has_envelope(segment_combination, fiscal_year=None, use_hierarchy=True):
        """
        Check if an envelope exists for a segment combination.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            fiscal_year: Optional fiscal year filter
            use_hierarchy: If True (default), checks parent hierarchy
        
        Returns:
            bool: True if envelope exists
        """
        return EnvelopeBalanceManager.get_envelope_for_segments(
            segment_combination,
            fiscal_year,
            use_hierarchy
        ) is not None
    
    @staticmethod
    def check_balance_available(segment_combination, required_amount, fiscal_year=None, use_hierarchy=True):
        """
        Check if sufficient balance is available in envelope for a transfer.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            required_amount: Decimal amount needed
            fiscal_year: Optional fiscal year filter
            use_hierarchy: If True (default), checks parent hierarchy
        
        Returns:
            dict: {
                'available': bool,
                'envelope_amount': Decimal,
                'consumed_amount': Decimal,
                'remaining_balance': Decimal,
                'sufficient': bool,
                'envelope_source': str ('exact', 'parent', or 'none'),
                'envelope_segment_combination': dict (actual envelope combination)
            }
        """
        try:
            # Track where envelope was found
            envelope_source = 'exact'
            actual_segment_combination = segment_combination
            
            # Try exact match first
            envelope = EnvelopeBalanceManager.get_envelope_for_segments(
                segment_combination,
                fiscal_year,
                use_hierarchy=False  # Don't use hierarchy in initial lookup
            )
            
            # If not found and hierarchy enabled, try parent
            if not envelope and use_hierarchy:
                parent_combination, _ = EnvelopeBalanceManager.get_hierarchical_envelope(
                    segment_combination,
                    fiscal_year
                )
                if parent_combination and parent_combination != segment_combination:
                    envelope = EnvelopeBalanceManager.get_envelope_for_segments(
                        parent_combination,
                        fiscal_year,
                        use_hierarchy=False
                    )
                    if envelope:
                        envelope_source = 'parent'
                        actual_segment_combination = parent_combination
            
            if not envelope:
                return {
                    'available': False,
                    'envelope_amount': Decimal('0.00'),
                    'consumed_amount': Decimal('0.00'),
                    'remaining_balance': Decimal('0.00'),
                    'sufficient': False,
                    'envelope_source': 'none',
                    'error': 'No envelope found for segment combination (tried hierarchy if enabled)'
                }
            
            # Calculate consumed amount from transactions using ACTUAL envelope combination
            consumed = EnvelopeBalanceManager.calculate_consumed_balance(
                actual_segment_combination,
                fiscal_year
            )
            
            remaining = envelope.envelope_amount - consumed
            sufficient = remaining >= required_amount
            
            return {
                'available': True,
                'envelope_amount': envelope.envelope_amount,
                'consumed_amount': consumed,
                'remaining_balance': remaining,
                'sufficient': sufficient,
                'envelope_source': envelope_source,
                'envelope_segment_combination': actual_segment_combination
            }
        
        except Exception as e:
            return {
                'available': False,
                'envelope_amount': Decimal('0.00'),
                'consumed_amount': Decimal('0.00'),
                'remaining_balance': Decimal('0.00'),
                'sufficient': False,
                'envelope_source': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def calculate_consumed_balance(segment_combination, fiscal_year=None):
        """
        Calculate the consumed balance from approved transactions.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            fiscal_year: Optional fiscal year filter
        
        Returns:
            Decimal: Total consumed amount
        """
        try:
            from budget_management.models import xx_BudgetTransfer
            from transaction.models import xx_TransactionTransfer
            
            # Build query for transactions matching this segment combination
            # Get all transaction transfers that have matching "from" segments
            
            consumed_total = Decimal('0.00')
            
            # Get all approved budget transfers
            approved_transfers = xx_BudgetTransfer.objects.filter(
                status__in=['Approved', 'APPROVED']
            )
            
            # TODO: Add fiscal year filter if needed
            # if fiscal_year:
            #     approved_transfers = approved_transfers.filter(fiscal_year=fiscal_year)
            
            # For each approved budget transfer, check its transaction lines
            for budget_transfer in approved_transfers:
                for transaction in budget_transfer.transfers.all():
                    # Check if this transaction's FROM segments match our combination
                    segments_dict = transaction.get_segments_dict()
                    
                    matches = True
                    for seg_type_id, seg_code in segment_combination.items():
                        seg_data = segments_dict.get(int(seg_type_id))
                        if seg_data and seg_data.get('from_code') != seg_code:
                            matches = False
                            break
                    
                    if matches:
                        # This transaction takes FROM our segment combination
                        consumed_total += transaction.from_center or Decimal('0.00')
            
            return consumed_total
        
        except Exception as e:
            print(f"Error calculating consumed balance: {e}")
            return Decimal('0.00')
    
    @staticmethod
    def get_hierarchical_envelope(segment_combination, fiscal_year=None):
        """
        Get envelope by walking up the hierarchy if not found at current level.
        Similar to Get_First_Parent_Envelope but for dynamic segments.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            fiscal_year: Optional fiscal year filter
        
        Returns:
            tuple: (segment_combination_dict, envelope_amount) or (None, None)
        """
        try:
            # First try exact match (WITHOUT hierarchy to avoid recursion)
            envelope = EnvelopeBalanceManager.get_envelope_for_segments(
                segment_combination,
                fiscal_year,
                use_hierarchy=False  # CRITICAL: Prevent recursion loop
            )
            
            if envelope:
                return segment_combination, envelope.envelope_amount
            
            # Try walking up hierarchy for each segment
            # Get parent segments and retry
            for seg_type_id, seg_code in list(segment_combination.items()):
                segment_type = XX_SegmentType.objects.get(segment_id=seg_type_id)
                
                if segment_type.has_hierarchy:
                    # Get parent segment
                    try:
                        segment = XX_Segment.objects.get(
                            segment_type_id=seg_type_id,
                            code=seg_code
                        )
                        
                        if segment.parent_code:
                            # Try with parent
                            parent_combination = segment_combination.copy()
                            parent_combination[seg_type_id] = segment.parent_code
                            
                            # Recursive call with parent
                            return EnvelopeBalanceManager.get_hierarchical_envelope(
                                parent_combination,
                                fiscal_year
                            )
                    except XX_Segment.DoesNotExist:
                        continue
            
            return None, None
        
        except Exception as e:
            print(f"Error in get_hierarchical_envelope: {e}")
            return None, None
    
    @staticmethod
    @db_transaction.atomic
    def update_envelope_amount(segment_combination, new_amount, fiscal_year=None):
        """
        Update or create envelope for a segment combination.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            new_amount: Decimal new envelope amount
            fiscal_year: Optional fiscal year
        
        Returns:
            dict: {'success': bool, 'envelope': XX_SegmentEnvelope, 'errors': list}
        """
        try:
            # Try to find existing envelope
            envelope = EnvelopeBalanceManager.get_envelope_for_segments(
                segment_combination,
                fiscal_year
            )
            
            if envelope:
                # Update existing
                envelope.envelope_amount = new_amount
                envelope.save()
                
                return {
                    'success': True,
                    'envelope': envelope,
                    'errors': [],
                    'action': 'updated'
                }
            else:
                # Create new
                envelope = XX_SegmentEnvelope.objects.create(
                    segment_combination=segment_combination,
                    envelope_amount=new_amount,
                    fiscal_year=fiscal_year,
                    is_active=True
                )
                
                return {
                    'success': True,
                    'envelope': envelope,
                    'errors': [],
                    'action': 'created'
                }
        
        except Exception as e:
            return {
                'success': False,
                'envelope': None,
                'errors': [str(e)]
            }
    
    @staticmethod
    def get_all_envelopes_for_segment_type(segment_type_id, fiscal_year=None):
        """
        Get all envelopes that include a specific segment type.
        
        Args:
            segment_type_id: ID of segment type to filter by
            fiscal_year: Optional fiscal year filter
        
        Returns:
            QuerySet of XX_SegmentEnvelope
        """
        query = XX_SegmentEnvelope.objects.filter(is_active=True)
        
        if fiscal_year:
            query = query.filter(fiscal_year=fiscal_year)
        
        # Filter envelopes that have this segment type in their combination
        result = []
        for envelope in query:
            if str(segment_type_id) in envelope.segment_combination:
                result.append(envelope)
        
        return result
    
    @staticmethod
    def get_envelope_summary(segment_combination, fiscal_year=None, use_hierarchy=True):
        """
        Get comprehensive envelope summary with consumed/remaining balances.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            fiscal_year: Optional fiscal year filter
            use_hierarchy: If True (default), checks parent hierarchy
        
        Returns:
            dict: Complete envelope information
        """
        # Track where envelope was found
        envelope_source = 'exact'
        actual_segment_combination = segment_combination
        requested_segment_combination = segment_combination.copy()
        
        # Try exact match first
        envelope = EnvelopeBalanceManager.get_envelope_for_segments(
            segment_combination,
            fiscal_year,
            use_hierarchy=False
        )
        
        # If not found and hierarchy enabled, try parent
        if not envelope and use_hierarchy:
            parent_combination, _ = EnvelopeBalanceManager.get_hierarchical_envelope(
                segment_combination,
                fiscal_year
            )
            if parent_combination and parent_combination != segment_combination:
                envelope = EnvelopeBalanceManager.get_envelope_for_segments(
                    parent_combination,
                    fiscal_year,
                    use_hierarchy=False
                )
                if envelope:
                    envelope_source = 'parent'
                    actual_segment_combination = parent_combination
        
        if not envelope:
            return {
                'exists': False,
                'requested_segment_combination': requested_segment_combination,
                'actual_segment_combination': None,
                'envelope_source': 'none',
                'segment_combination': segment_combination,
                'envelope_amount': Decimal('0.00'),
                'consumed_amount': Decimal('0.00'),
                'remaining_balance': Decimal('0.00'),
                'utilization_percent': 0
            }
        
        consumed = EnvelopeBalanceManager.calculate_consumed_balance(
            actual_segment_combination,
            fiscal_year
        )
        remaining = envelope.envelope_amount - consumed
        utilization = (consumed / envelope.envelope_amount * 100) if envelope.envelope_amount > 0 else 0
        
        return {
            'exists': True,
            'envelope_id': envelope.id,
            'requested_segment_combination': requested_segment_combination,
            'actual_segment_combination': actual_segment_combination,
            'envelope_source': envelope_source,
            'segment_combination': segment_combination,
            'envelope_amount': float(envelope.envelope_amount),
            'consumed_amount': float(consumed),
            'remaining_balance': float(remaining),
            'utilization_percent': float(utilization),
            'fiscal_year': envelope.fiscal_year,
            'description': envelope.description
        }
