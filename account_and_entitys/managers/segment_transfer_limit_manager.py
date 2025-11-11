"""
SegmentTransferLimitManager - Phase 3 Enhancement
Manages transfer limits/rules for segment combinations.
Replaces legacy XX_ACCOUNT_ENTITY_LIMIT logic.
"""

from django.db import transaction as db_transaction
from account_and_entitys.models import XX_SegmentTransferLimit, XX_SegmentType


class SegmentTransferLimitManager:
    """
    Manager class for segment transfer limit operations.
    Handles validation of transfer permissions and tracking of usage.
    """
    
    @staticmethod
    def get_limit_for_segments(segment_combination, fiscal_year=None):
        """
        Get transfer limit for a specific segment combination.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            fiscal_year: Optional fiscal year filter
        
        Returns:
            XX_SegmentTransferLimit object or None
        """
        try:
            query = XX_SegmentTransferLimit.objects.filter(is_active=True)
            
            if fiscal_year:
                query = query.filter(fiscal_year=fiscal_year)
            
            # Find limit that matches the segment combination
            for limit in query:
                if limit.matches_segments(segment_combination):
                    return limit
            
            return None
        except Exception as e:
            print(f"Error in get_limit_for_segments: {e}")
            return None
    
    @staticmethod
    def can_transfer_from_segments(segment_combination, fiscal_year=None):
        """
        Check if transfers are allowed FROM a segment combination.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            fiscal_year: Optional fiscal year filter
        
        Returns:
            dict: {
                'allowed': bool,
                'reason': str (if not allowed),
                'limit': XX_SegmentTransferLimit (if exists)
            }
        """
        limit = SegmentTransferLimitManager.get_limit_for_segments(
            segment_combination,
            fiscal_year
        )
        
        if not limit:
            # No limit defined = allowed by default
            return {
                'allowed': True,
                'reason': None,
                'limit': None
            }
        
        if not limit.can_be_source():
            reasons = []
            if not limit.is_active:
                reasons.append("Limit is inactive")
            if not limit.is_transfer_allowed:
                reasons.append("Transfers not allowed")
            if not limit.is_transfer_allowed_as_source:
                reasons.append("Not allowed as source")
            if limit.max_source_transfers and limit.source_count and limit.source_count >= limit.max_source_transfers:
                reasons.append(f"Source limit reached ({limit.source_count}/{limit.max_source_transfers})")
            
            return {
                'allowed': False,
                'reason': "; ".join(reasons),
                'limit': limit
            }
        
        return {
            'allowed': True,
            'reason': None,
            'limit': limit
        }
    
    @staticmethod
    def can_transfer_to_segments(segment_combination, fiscal_year=None):
        """
        Check if transfers are allowed TO a segment combination.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            fiscal_year: Optional fiscal year filter
        
        Returns:
            dict: {
                'allowed': bool,
                'reason': str (if not allowed),
                'limit': XX_SegmentTransferLimit (if exists)
            }
        """
        limit = SegmentTransferLimitManager.get_limit_for_segments(
            segment_combination,
            fiscal_year
        )
        
        if not limit:
            # No limit defined = allowed by default
            return {
                'allowed': True,
                'reason': None,
                'limit': None
            }
        
        if not limit.can_be_target():
            reasons = []
            if not limit.is_active:
                reasons.append("Limit is inactive")
            if not limit.is_transfer_allowed:
                reasons.append("Transfers not allowed")
            if not limit.is_transfer_allowed_as_target:
                reasons.append("Not allowed as target")
            if limit.max_target_transfers and limit.target_count and limit.target_count >= limit.max_target_transfers:
                reasons.append(f"Target limit reached ({limit.target_count}/{limit.max_target_transfers})")
            
            return {
                'allowed': False,
                'reason': "; ".join(reasons),
                'limit': limit
            }
        
        return {
            'allowed': True,
            'reason': None,
            'limit': limit
        }
    
    @staticmethod
    def validate_transfer(from_segments, to_segments, fiscal_year=None):
        """
        Validate that a transfer is allowed from one segment combination to another.
        
        Args:
            from_segments: Dict of {segment_type_id: segment_code} for source
            to_segments: Dict of {segment_type_id: segment_code} for target
            fiscal_year: Optional fiscal year filter
        
        Returns:
            dict: {
                'valid': bool,
                'errors': list,
                'from_limit': XX_SegmentTransferLimit or None,
                'to_limit': XX_SegmentTransferLimit or None
            }
        """
        errors = []
        
        # Check source
        from_check = SegmentTransferLimitManager.can_transfer_from_segments(
            from_segments,
            fiscal_year
        )
        
        if not from_check['allowed']:
            errors.append(f"Source not allowed: {from_check['reason']}")
        
        # Check target
        to_check = SegmentTransferLimitManager.can_transfer_to_segments(
            to_segments,
            fiscal_year
        )
        
        if not to_check['allowed']:
            errors.append(f"Target not allowed: {to_check['reason']}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'from_limit': from_check['limit'],
            'to_limit': to_check['limit']
        }
    
    @staticmethod
    @db_transaction.atomic
    def record_transfer_usage(from_segments, to_segments, fiscal_year=None):
        """
        Record usage of segment combinations in a transfer.
        Increments source and target counts.
        
        Args:
            from_segments: Dict of {segment_type_id: segment_code} for source
            to_segments: Dict of {segment_type_id: segment_code} for target
            fiscal_year: Optional fiscal year filter
        
        Returns:
            dict: {'success': bool, 'errors': list}
        """
        try:
            # Get limits
            from_limit = SegmentTransferLimitManager.get_limit_for_segments(
                from_segments,
                fiscal_year
            )
            
            to_limit = SegmentTransferLimitManager.get_limit_for_segments(
                to_segments,
                fiscal_year
            )
            
            # Increment counts
            if from_limit:
                from_limit.increment_source_count()
            
            if to_limit:
                to_limit.increment_target_count()
            
            return {
                'success': True,
                'errors': []
            }
        
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    @staticmethod
    @db_transaction.atomic
    def create_limit(segment_combination, **kwargs):
        """
        Create a new transfer limit for a segment combination.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            **kwargs: Additional fields (is_transfer_allowed_as_source, etc.)
        
        Returns:
            dict: {'success': bool, 'limit': XX_SegmentTransferLimit, 'errors': list}
        """
        try:
            # Validate segment combination
            for seg_type_id, seg_code in segment_combination.items():
                try:
                    segment_type = XX_SegmentType.objects.get(segment_id=int(seg_type_id))
                except XX_SegmentType.DoesNotExist:
                    return {
                        'success': False,
                        'limit': None,
                        'errors': [f'Segment type {seg_type_id} does not exist']
                    }
            
            # Check if limit already exists
            existing = SegmentTransferLimitManager.get_limit_for_segments(
                segment_combination,
                kwargs.get('fiscal_year')
            )
            
            if existing:
                return {
                    'success': False,
                    'limit': None,
                    'errors': ['Transfer limit already exists for this segment combination']
                }
            
            # Create new limit
            limit = XX_SegmentTransferLimit.objects.create(
                segment_combination=segment_combination,
                is_transfer_allowed_as_source=kwargs.get('is_transfer_allowed_as_source', True),
                is_transfer_allowed_as_target=kwargs.get('is_transfer_allowed_as_target', True),
                is_transfer_allowed=kwargs.get('is_transfer_allowed', True),
                max_source_transfers=kwargs.get('max_source_transfers'),
                max_target_transfers=kwargs.get('max_target_transfers'),
                fiscal_year=kwargs.get('fiscal_year'),
                notes=kwargs.get('notes'),
                is_active=kwargs.get('is_active', True)
            )
            
            return {
                'success': True,
                'limit': limit,
                'errors': []
            }
        
        except Exception as e:
            return {
                'success': False,
                'limit': None,
                'errors': [str(e)]
            }
    
    @staticmethod
    def get_all_limits(fiscal_year=None, include_inactive=False):
        """
        Get all transfer limits.
        
        Args:
            fiscal_year: Optional fiscal year filter
            include_inactive: Whether to include inactive limits
        
        Returns:
            QuerySet of XX_SegmentTransferLimit
        """
        query = XX_SegmentTransferLimit.objects.all()
        
        if fiscal_year:
            query = query.filter(fiscal_year=fiscal_year)
        
        if not include_inactive:
            query = query.filter(is_active=True)
        
        return query.order_by('-created_at')
    
    @staticmethod
    def increment_source_count(segment_combination, fiscal_year=None):
        """
        Increment source transfer count for a segment combination.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            fiscal_year: Optional fiscal year filter
        
        Returns:
            dict: {'success': bool, 'count': int, 'errors': list}
        """
        try:
            limit = SegmentTransferLimitManager.get_limit_for_segments(
                segment_combination,
                fiscal_year
            )
            
            if not limit:
                return {
                    'success': False,
                    'count': 0,
                    'errors': ['No limit found for segment combination']
                }
            
            limit.increment_source_count()
            
            return {
                'success': True,
                'count': limit.source_count,
                'errors': []
            }
        
        except Exception as e:
            return {
                'success': False,
                'count': 0,
                'errors': [str(e)]
            }
    
    @staticmethod
    def increment_target_count(segment_combination, fiscal_year=None):
        """
        Increment target transfer count for a segment combination.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            fiscal_year: Optional fiscal year filter
        
        Returns:
            dict: {'success': bool, 'count': int, 'errors': list}
        """
        try:
            limit = SegmentTransferLimitManager.get_limit_for_segments(
                segment_combination,
                fiscal_year
            )
            
            if not limit:
                return {
                    'success': False,
                    'count': 0,
                    'errors': ['No limit found for segment combination']
                }
            
            limit.increment_target_count()
            
            return {
                'success': True,
                'count': limit.target_count,
                'errors': []
            }
        
        except Exception as e:
            return {
                'success': False,
                'count': 0,
                'errors': [str(e)]
            }
