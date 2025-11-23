"""
Segment Manager - Dynamic replacement for EnvelopeManager
Handles all segment-related business logic in a configuration-driven way.
"""

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
import json
from pathlib import Path


class SegmentManager:
    """
    Central manager for dynamic segment operations.
    Replaces hardcoded segment logic in EnvelopeManager.
    """
    
    # Cache keys
    CACHE_KEY_SEGMENT_CONFIG = 'segment_config_types'
    CACHE_KEY_SEGMENT_MAP = 'segment_type_map'
    CACHE_TIMEOUT = 3600  # 1 hour
    
    @staticmethod
    def get_segment_config():
        """
        Load segment configuration from database (cached).
        Returns: QuerySet of XX_SegmentType objects
        """
        from account_and_entitys.models import XX_SegmentType
        
        config = cache.get(SegmentManager.CACHE_KEY_SEGMENT_CONFIG)
        if config is None:
            config = list(XX_SegmentType.objects.filter(is_active=True).order_by('display_order'))
            cache.set(SegmentManager.CACHE_KEY_SEGMENT_CONFIG, config, SegmentManager.CACHE_TIMEOUT)
        return config
    
    @staticmethod
    def clear_cache():
        """Clear all segment-related caches"""
        cache.delete(SegmentManager.CACHE_KEY_SEGMENT_CONFIG)
        cache.delete(SegmentManager.CACHE_KEY_SEGMENT_MAP)
    
    @staticmethod
    def get_segment_type_by_name(segment_name):
        """
        Get segment type by name (e.g., 'Entity', 'Account', 'Project')
        Returns: XX_SegmentType object or None
        """
        from account_and_entitys.models import XX_SegmentType
        
        try:
            return XX_SegmentType.objects.get(segment_name=segment_name, is_active=True)
        except XX_SegmentType.DoesNotExist:
            return None
    
    @staticmethod
    def get_segment_type_by_id(segment_id):
        """Get segment type by ID"""
        from account_and_entitys.models import XX_SegmentType
        
        try:
            return XX_SegmentType.objects.get(segment_id=segment_id, is_active=True)
        except XX_SegmentType.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_segment_types():
        """Get all active segment types ordered by display_order"""
        from account_and_entitys.models import XX_SegmentType
        
        return XX_SegmentType.objects.filter(is_active=True).order_by('display_order')
    
    @staticmethod
    def get_required_segment_types():
        """Get only required segment types"""
        from account_and_entitys.models import XX_SegmentType
        
        return XX_SegmentType.objects.filter(is_active=True, is_required=True).order_by('display_order')
    
    @staticmethod
    def validate_transaction_segments(segments_data):
        """
        Validate that all required segments are present and valid.
        
        Args:
            segments_data: Dict like {segment_id: {'from_code': 'xxx', 'to_code': 'yyy'}}
                          OR {segment_name: code} for backward compatibility
                          segment_id can be int or string (JSON keys are always strings)
        
        Returns:
            dict: {'valid': bool, 'errors': list}
        """
        from account_and_entitys.models import XX_Segment, XX_SegmentType
        
        errors = []
        required_types = SegmentManager.get_required_segment_types()
        
        # Detect format - if keys are integers OR numeric strings, it's {segment_id: {...}} format
        sample_key = next(iter(segments_data.keys())) if segments_data else None
        is_id_format = isinstance(sample_key, int) or (isinstance(sample_key, str) and sample_key.isdigit())
        
        # Normalize keys to integers if in ID format
        if is_id_format and isinstance(sample_key, str):
            # Convert string keys to integers for consistent processing
            segments_data = {int(k): v for k, v in segments_data.items()}
        
        # Validate all required segments are present
        for seg_type in required_types:
            if is_id_format:
                # Format: {segment_id: {'from_code': 'xxx', 'to_code': 'yyy'}} OR {segment_id: {'code': 'xxx'}}
                if seg_type.segment_id not in segments_data:
                    errors.append(f"Required segment '{seg_type.segment_name}' (ID {seg_type.segment_id}) is missing")
                    continue
                
                seg_data = segments_data[seg_type.segment_id]
                
                # Check if using NEW SIMPLIFIED FORMAT (single 'code' field)
                if 'code' in seg_data:
                    # NEW FORMAT: Only 'code' field
                    code = seg_data.get('code')
                    if not code:
                        errors.append(f"Required segment '{seg_type.segment_name}' code cannot be empty")
                    else:
                        # Verify code exists
                        if not XX_Segment.objects.filter(
                            segment_type=seg_type,
                            code=code,
                            is_active=True
                        ).exists():
                            errors.append(f"Invalid code '{code}' for {seg_type.segment_name}")
                else:
                    # OLD FORMAT: from_code and to_code fields
                    from_code = seg_data.get('from_code') or seg_data.get('from')
                    to_code = seg_data.get('to_code') or seg_data.get('to')
                    
                    if not from_code:
                        errors.append(f"Required segment '{seg_type.segment_name}' from_code cannot be empty")
                    if not to_code:
                        errors.append(f"Required segment '{seg_type.segment_name}' to_code cannot be empty")
                    if not to_code:
                        errors.append(f"Required segment '{seg_type.segment_name}' to_code cannot be empty")
                    
                    # Verify from_code exists
                    if from_code and not XX_Segment.objects.filter(
                        segment_type=seg_type,
                        code=from_code,
                        is_active=True
                    ).exists():
                        errors.append(f"Invalid from_code '{from_code}' for {seg_type.segment_name}")
                    
                    # Verify to_code exists
                    if to_code and not XX_Segment.objects.filter(
                        segment_type=seg_type,
                        code=to_code,
                        is_active=True
                    ).exists():
                        errors.append(f"Invalid to_code '{to_code}' for {seg_type.segment_name}")
            else:
                # Format: {segment_name: code} (backward compatibility)
                if seg_type.segment_name not in segments_data:
                    errors.append(f"Required segment '{seg_type.segment_name}' is missing")
                    continue
                
                segment_code = segments_data[seg_type.segment_name]
                if not segment_code:
                    errors.append(f"Required segment '{seg_type.segment_name}' cannot be empty")
                    continue
                
                # Verify segment exists
                if not XX_Segment.objects.filter(
                    segment_type=seg_type,
                    code=segment_code,
                    is_active=True
                ).exists():
                    errors.append(f"Invalid segment code '{segment_code}' for {seg_type.segment_name}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def validate_transaction_segments_simple(segments_data):
        """
        Validate transaction segments with simplified format (single code per segment).
        
        NEW SIMPLIFIED FORMAT:
        - Each segment has only 'code' field (not from_code/to_code)
        - Direction is determined externally by from_center vs to_center
        
        Args:
            segments_data: Dict like {segment_id: {'code': 'xxx'}}
                          segment_id can be int or string (JSON keys are always strings)
        
        Returns:
            dict: {'valid': bool, 'errors': list}
        """
        from account_and_entitys.models import XX_Segment, XX_SegmentType
        
        errors = []
        required_types = SegmentManager.get_required_segment_types()
        
        # Detect if keys are numeric strings and normalize to integers
        sample_key = next(iter(segments_data.keys())) if segments_data else None
        if isinstance(sample_key, str) and sample_key.isdigit():
            # Convert string keys to integers for consistent processing
            segments_data = {int(k): v for k, v in segments_data.items()}
        
        # Validate all required segments are present
        for seg_type in required_types:
            # Check if segment_id is present
            if seg_type.segment_id not in segments_data:
                errors.append(f"Required segment '{seg_type.segment_name}' (ID {seg_type.segment_id}) is missing")
                continue
            
            seg_data = segments_data[seg_type.segment_id]
            
            # Validate format - should be a dict
            if not isinstance(seg_data, dict):
                errors.append(f"Segment '{seg_type.segment_name}' must be a dictionary with 'code' field")
                continue
            
            # Get code
            code = seg_data.get('code')
            
            if not code:
                errors.append(f"Required segment '{seg_type.segment_name}' code cannot be empty")
                continue
            
            # Verify code exists
            if not XX_Segment.objects.filter(
                segment_type=seg_type,
                code=code,
                is_active=True
            ).exists():
                errors.append(f"Invalid code '{code}' for {seg_type.segment_name}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def get_all_children(segment_type, parent_code, visited=None):
        """
        Get all descendants of a segment code (recursive).
        Works like the old EnvelopeManager.get_all_children but dynamic.
        
        Args:
            segment_type: XX_SegmentType object or segment_name string
            parent_code: Parent segment code
            visited: Set of visited codes (for cycle detection)
        
        Returns:
            List of descendant codes
        """
        from account_and_entitys.models import XX_Segment
        
        if visited is None:
            visited = set()
        
        if parent_code in visited:
            return []
        
        visited.add(parent_code)
        
        # Convert string to object if needed
        if isinstance(segment_type, str):
            segment_type = SegmentManager.get_segment_type_by_name(segment_type)
            if not segment_type:
                return []
        
        # Get direct children
        direct_children = XX_Segment.objects.filter(
            segment_type=segment_type,
            parent_code=parent_code,
            is_active=True
        ).values_list('code', flat=True)
        
        descendants = []
        for child_code in direct_children:
            if child_code in visited:
                continue
            descendants.append(child_code)
            descendants.extend(
                SegmentManager.get_all_children(segment_type, child_code, visited)
            )
        
        return descendants
    
    @staticmethod
    def get_leaf_descendants(segment_type, parent_code):
        """
        Get only leaf nodes (segments with no children) under a parent.
        Equivalent to old __get_all_level_zero_children_code.
        """
        from account_and_entitys.models import XX_Segment
        
        if isinstance(segment_type, str):
            segment_type = SegmentManager.get_segment_type_by_name(segment_type)
            if not segment_type:
                return []
        
        # Get all descendants
        all_descendants = SegmentManager.get_all_children(segment_type, parent_code)
        
        # Get set of all parent codes
        parent_codes = set(
            XX_Segment.objects.filter(
                segment_type=segment_type,
                is_active=True
            ).exclude(
                parent_code__isnull=True
            ).values_list('parent_code', flat=True)
        )
        
        # Return only descendants that are not parents
        leaf_nodes = [code for code in all_descendants if code not in parent_codes]
        return leaf_nodes
    
    @staticmethod
    def get_segment_hierarchy_tree(segment_type_name):
        """
        Build a hierarchical tree structure for a segment type.
        
        Returns:
            List of dicts with structure:
            [
                {
                    "code": "001",
                    "alias": "Main Department",
                    "level": 0,
                    "children": [
                        {"code": "001-A", "alias": "Sub Department", "level": 1, "children": []}
                    ]
                }
            ]
        """
        from account_and_entitys.models import XX_Segment
        
        segment_type = SegmentManager.get_segment_type_by_name(segment_type_name)
        if not segment_type or not segment_type.has_hierarchy:
            return []
        
        # Get all segments for this type
        segments = XX_Segment.objects.filter(
            segment_type=segment_type,
            is_active=True
        ).order_by('code')
        
        # Build parent-child map
        segment_map = {seg.code: seg for seg in segments}
        tree = []
        
        def build_node(segment):
            children = [
                build_node(child) 
                for child in segments 
                if child.parent_code == segment.code
            ]
            return {
                "code": segment.code,
                "alias": segment.alias,
                "level": segment.level,
                "envelope_amount": float(segment.envelope_amount) if segment.envelope_amount else None,
                "children": children
            }
        
        # Build tree from root nodes (no parent)
        for segment in segments:
            if not segment.parent_code or segment.parent_code not in segment_map:
                tree.append(build_node(segment))
        
        return tree
    
    @staticmethod
    def get_envelope_amount(segment_type_name, segment_code):
        """
        Get envelope/budget limit for a segment.
        Looks up the hierarchy if not found at current level.
        """
        from account_and_entitys.models import XX_Segment
        
        segment_type = SegmentManager.get_segment_type_by_name(segment_type_name)
        if not segment_type:
            return None
        
        current_code = segment_code
        while current_code:
            try:
                segment = XX_Segment.objects.get(
                    segment_type=segment_type,
                    code=current_code,
                    is_active=True
                )
                
                if segment.envelope_amount is not None:
                    return segment.envelope_amount
                
                # Move to parent
                current_code = segment.parent_code
            except XX_Segment.DoesNotExist:
                break
        
        return None
    
    @staticmethod
    def delete_transaction_segments(transaction_transfer):
        """
        Delete all XX_TransactionSegment records for a transaction.
        
        Args:
            transaction_transfer: xx_TransactionTransfer object
        
        Returns:
            int: Number of segments deleted
        """
        from account_and_entitys.models import XX_TransactionSegment
        
        count, _ = XX_TransactionSegment.objects.filter(
            transaction_transfer=transaction_transfer
        ).delete()
        
        return count
    
    @staticmethod
    def create_transaction_segments(transaction_transfer, segments_data):
        """
        Create XX_TransactionSegment records for a transaction.
        
        Args:
            transaction_transfer: xx_TransactionTransfer object
            segments_data: Dict like {segment_id: {'from_code': 'xxx', 'to_code': 'yyy'}}
        
        Returns:
            dict: {'success': bool, 'segments': list, 'errors': list}
        """
        from account_and_entitys.models import XX_Segment, XX_TransactionSegment, XX_SegmentType
        
        created_segments = []
        errors = []
        
        try:
            for seg_id, seg_data in segments_data.items():
                try:
                    # Get segment type
                    segment_type = XX_SegmentType.objects.get(segment_id=int(seg_id))
                except XX_SegmentType.DoesNotExist:
                    errors.append(f"Segment type {seg_id} does not exist")
                    continue
                
                from_code = seg_data.get('from_code') or seg_data.get('from')
                to_code = seg_data.get('to_code') or seg_data.get('to')
                
                if not from_code or not to_code:
                    errors.append(f"Missing from_code or to_code for segment {segment_type.segment_name}")
                    continue
                
                # Get segment values
                try:
                    from_value = XX_Segment.objects.get(
                        segment_type=segment_type,
                        code=from_code,
                        is_active=True
                    )
                except XX_Segment.DoesNotExist:
                    errors.append(f"Segment value {from_code} not found for {segment_type.segment_name}")
                    continue
                
                try:
                    to_value = XX_Segment.objects.get(
                        segment_type=segment_type,
                        code=to_code,
                        is_active=True
                    )
                except XX_Segment.DoesNotExist:
                    errors.append(f"Segment value {to_code} not found for {segment_type.segment_name}")
                    continue
                
                # Use from_value as the main segment_value
                trans_segment = XX_TransactionSegment.objects.create(
                    transaction_transfer=transaction_transfer,
                    segment_type=segment_type,
                    segment_value=from_value,
                    from_segment_value=from_value,
                    to_segment_value=to_value
                )
                created_segments.append(trans_segment)
            
            return {
                'success': len(errors) == 0,
                'segments': created_segments,
                'errors': errors
            }
        
        except Exception as e:
            return {
                'success': False,
                'segments': created_segments,
                'errors': [str(e)]
            }
    
    @staticmethod
    def create_transaction_segments_simple(transaction_transfer, segments_data, is_source):
        """
        Create XX_TransactionSegment records with simplified format.
        
        NEW SIMPLIFIED FORMAT:
        - Each segment has only 'code' field
        - Direction determined by is_source parameter
        
        Args:
            transaction_transfer: xx_TransactionTransfer object
            segments_data: Dict like {segment_id: {'code': 'xxx'}}
            is_source: bool - True if taking funds (from_center > 0), False if receiving (to_center > 0)
        
        Returns:
            dict: {'success': bool, 'segments': list, 'errors': list}
        """
        from account_and_entitys.models import XX_Segment, XX_TransactionSegment, XX_SegmentType
        
        created_segments = []
        errors = []
        
        try:
            for seg_id, seg_data in segments_data.items():
                try:
                    # Get segment type
                    segment_type = XX_SegmentType.objects.get(segment_id=int(seg_id))
                except XX_SegmentType.DoesNotExist:
                    errors.append(f"Segment type {seg_id} does not exist")
                    continue
                
                code = seg_data.get('code')
                
                if not code:
                    errors.append(f"Missing code for segment {segment_type.segment_name}")
                    continue
                
                # Get segment value
                try:
                    segment_value = XX_Segment.objects.get(
                        segment_type=segment_type,
                        code=code,
                        is_active=True
                    )
                except XX_Segment.DoesNotExist:
                    errors.append(f"Segment value {code} not found for {segment_type.segment_name}")
                    continue
                
                # Determine from/to based on direction
                if is_source:
                    # Taking funds FROM this segment
                    from_value = segment_value
                    to_value = None  # Will be set to null or could keep same value
                else:
                    # Giving funds TO this segment
                    from_value = None
                    to_value = segment_value
                
                # Create transaction segment
                trans_segment = XX_TransactionSegment.objects.create(
                    transaction_transfer=transaction_transfer,
                    segment_type=segment_type,
                    segment_value=segment_value,  # Main segment value
                    from_segment_value=from_value,
                    to_segment_value=to_value
                )
                created_segments.append(trans_segment)
            
            return {
                'success': len(errors) == 0,
                'segments': created_segments,
                'errors': errors
            }
        
        except Exception as e:
            return {
                'success': False,
                'segments': created_segments,
                'errors': [str(e)]
            }

    @staticmethod
    def get_transaction_segments(transaction_transfer):
        """
        Get all segment values for a transaction as a dict.
        
        Returns:
            Dict like {"Entity": "12345", "Account": "67890", "Project": "98765"}
        """
        from account_and_entitys.models import XX_TransactionSegment
        
        segments = XX_TransactionSegment.objects.filter(
            transaction_transfer=transaction_transfer
        ).select_related('segment_type', 'segment_value')
        
        return {
            ts.segment_type.segment_name: ts.segment_value.code
            for ts in segments
        }
    
    @staticmethod
    def get_oracle_segment_mapping(segments_dict):
        """
        Map segments to Oracle SEGMENT1-SEGMENT30 columns.
        
        Args:
            segments_dict: Dict from get_segments_dict() with segment info
        
        Returns:
            dict: {
                'from': {1: 'E001', 2: 'A100', ...},  # FROM segment values
                'to': {1: 'E002', 2: 'A200', ...}      # TO segment values
            }
        """
        from_mapping = {}
        to_mapping = {}
        
        for seg_id, seg_data in segments_dict.items():
            # Get oracle segment number from SegmentType
            from account_and_entitys.models import XX_SegmentType
            try:
                segment_type = XX_SegmentType.objects.get(segment_id=seg_id)
                oracle_num = segment_type.oracle_segment_number
                
                from_mapping[oracle_num] = seg_data.get('from_code')
                to_mapping[oracle_num] = seg_data.get('to_code')
            except XX_SegmentType.DoesNotExist:
                continue
        
        return {
            'from': from_mapping,
            'to': to_mapping
        }
    
    @staticmethod
    def migrate_legacy_segment_to_dynamic(legacy_model_name, segment_type_id):
        """
        Utility to migrate data from old models (XX_Entity, XX_Account, XX_Project)
        to new XX_Segment model.
        
        Args:
            legacy_model_name: 'XX_Entity', 'XX_Account', or 'XX_Project'
            segment_type_id: Target segment type ID
        """
        from account_and_entitys.models import (
            XX_Entity, XX_Account, XX_Project, 
            XX_SegmentType, XX_Segment
        )
        
        segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id)
        
        # Map model names to model classes
        model_map = {
            'XX_Entity': XX_Entity,
            'XX_Account': XX_Account,
            'XX_Project': XX_Project
        }
        
        legacy_model = model_map.get(legacy_model_name)
        if not legacy_model:
            raise ValueError(f"Unknown legacy model: {legacy_model_name}")
        
        # Migrate records
        migrated_count = 0
        for legacy_record in legacy_model.objects.all():
            # Extract code based on model
            if legacy_model_name == 'XX_Entity':
                code = legacy_record.entity
            elif legacy_model_name == 'XX_Account':
                code = legacy_record.account
            else:  # XX_Project
                code = legacy_record.project
            
            XX_Segment.objects.get_or_create(
                segment_type=segment_type,
                code=code,
                defaults={
                    'parent_code': legacy_record.parent,
                    'alias': legacy_record.alias_default,
                    'is_active': True
                }
            )
            migrated_count += 1
        
        return migrated_count
    
    @staticmethod
    def get_segment_by_code(segment_type_name, code):
        """
        Get a specific segment by type name and code.
        
        Args:
            segment_type_name: Name of segment type (e.g., 'Entity', 'Account')
            code: Segment code
        
        Returns:
            XX_Segment object or None
        """
        from account_and_entitys.models import XX_Segment
        
        segment_type = SegmentManager.get_segment_type_by_name(segment_type_name)
        if not segment_type:
            return None
        
        try:
            return XX_Segment.objects.get(
                segment_type=segment_type,
                code=code,
                is_active=True
            )
        except XX_Segment.DoesNotExist:
            return None
    
    @staticmethod
    def get_segments_by_type(segment_type_name, parent_code=None):
        """
        Get all segments of a specific type, optionally filtered by parent.
        
        Args:
            segment_type_name: Name of segment type
            parent_code: Optional parent code to filter by
        
        Returns:
            QuerySet of XX_Segment objects
        """
        from account_and_entitys.models import XX_Segment
        
        segment_type = SegmentManager.get_segment_type_by_name(segment_type_name)
        if not segment_type:
            return XX_Segment.objects.none()
        
        queryset = XX_Segment.objects.filter(
            segment_type=segment_type,
            is_active=True
        )
        
        if parent_code is not None:
            queryset = queryset.filter(parent_code=parent_code)
        
        return queryset.order_by('code')
