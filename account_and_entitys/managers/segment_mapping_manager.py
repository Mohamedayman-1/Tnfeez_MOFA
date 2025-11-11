"""
SegmentMappingManager - Phase 3
Manages segment-to-segment mapping operations with dynamic segment support.
Replaces legacy Account_Mapping and Entity_mapping logic.
"""

from django.db import transaction as db_transaction
from account_and_entitys.models import (
    XX_SegmentMapping,
    XX_SegmentType,
    XX_Segment
)


class SegmentMappingManager:
    """
    Manager class for segment mapping operations.
    Handles cross-segment mappings, hierarchical lookups, and validation.
    """
    
    @staticmethod
    def get_mapping(segment_type_id, source_code, target_code=None):
        """
        Get mapping for a specific source segment.
        
        Args:
            segment_type_id: ID of segment type
            source_code: Source segment code
            target_code: Optional target code to get specific mapping
        
        Returns:
            XX_SegmentMapping object(s) or None
        """
        try:
            source_segment = XX_Segment.objects.get(
                segment_type_id=segment_type_id,
                code=source_code
            )
            
            query = XX_SegmentMapping.objects.filter(
                segment_type_id=segment_type_id,
                source_segment=source_segment,
                is_active=True
            )
            
            if target_code:
                target_segment = XX_Segment.objects.get(
                    segment_type_id=segment_type_id,
                    code=target_code
                )
                return query.filter(target_segment=target_segment).first()
            else:
                return query.all()
        
        except XX_Segment.DoesNotExist:
            return None
        except Exception as e:
            print(f"Error in get_mapping: {e}")
            return None
    
    @staticmethod
    def get_target_segments(segment_type_id, source_code):
        """
        Get all target segments that a source segment maps to.
        
        Args:
            segment_type_id: ID of segment type
            source_code: Source segment code
        
        Returns:
            list: List of target segment codes
        """
        try:
            mappings = SegmentMappingManager.get_mapping(
                segment_type_id,
                source_code
            )
            
            if not mappings:
                return []
            
            return [mapping.target_segment.code for mapping in mappings]
        
        except Exception as e:
            print(f"Error in get_target_segments: {e}")
            return []
    
    @staticmethod
    def get_source_segments(segment_type_id, target_code):
        """
        Get all source segments that map to a target segment.
        (Reverse mapping lookup)
        
        Args:
            segment_type_id: ID of segment type
            target_code: Target segment code
        
        Returns:
            list: List of source segment codes
        """
        try:
            target_segment = XX_Segment.objects.get(
                segment_type_id=segment_type_id,
                code=target_code
            )
            
            mappings = XX_SegmentMapping.objects.filter(
                segment_type_id=segment_type_id,
                target_segment=target_segment,
                is_active=True
            )
            
            return [mapping.source_segment.code for mapping in mappings]
        
        except XX_Segment.DoesNotExist:
            return []
        except Exception as e:
            print(f"Error in get_source_segments: {e}")
            return []
    
    @staticmethod
    def validate_mapping_exists(segment_type_id, source_code, target_code):
        """
        Check if a mapping exists between source and target.
        
        Args:
            segment_type_id: ID of segment type
            source_code: Source segment code
            target_code: Target segment code
        
        Returns:
            bool: True if mapping exists
        """
        mapping = SegmentMappingManager.get_mapping(
            segment_type_id,
            source_code,
            target_code
        )
        return mapping is not None
    
    @staticmethod
    @db_transaction.atomic
    def create_mapping(segment_type_id, source_code, target_code, mapping_type='STANDARD', description=None):
        """
        Create a new segment mapping.
        
        Args:
            segment_type_id: ID of segment type
            source_code: Source segment code
            target_code: Target segment code
            mapping_type: Type of mapping (default: 'STANDARD')
            description: Optional description
        
        Returns:
            dict: {'success': bool, 'mapping': XX_SegmentMapping, 'errors': list}
        """
        try:
            # Validate segment type exists
            segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id)
            
            # Get source and target segments
            source_segment = XX_Segment.objects.get(
                segment_type_id=segment_type_id,
                code=source_code
            )
            
            target_segment = XX_Segment.objects.get(
                segment_type_id=segment_type_id,
                code=target_code
            )
            
            # Check if mapping already exists
            existing = XX_SegmentMapping.objects.filter(
                segment_type=segment_type,
                source_segment=source_segment,
                target_segment=target_segment
            ).first()
            
            if existing:
                if not existing.is_active:
                    # Reactivate
                    existing.is_active = True
                    existing.save()
                    return {
                        'success': True,
                        'mapping': existing,
                        'errors': [],
                        'action': 'reactivated'
                    }
                else:
                    return {
                        'success': False,
                        'mapping': None,
                        'errors': ['Mapping already exists']
                    }
            
            # Create new mapping
            mapping = XX_SegmentMapping.objects.create(
                segment_type=segment_type,
                source_segment=source_segment,
                target_segment=target_segment,
                mapping_type=mapping_type,
                description=description,
                is_active=True
            )
            
            return {
                'success': True,
                'mapping': mapping,
                'errors': [],
                'action': 'created'
            }
        
        except XX_SegmentType.DoesNotExist:
            return {
                'success': False,
                'mapping': None,
                'errors': [f'Segment type {segment_type_id} does not exist']
            }
        except XX_Segment.DoesNotExist as e:
            return {
                'success': False,
                'mapping': None,
                'errors': [f'Segment not found: {str(e)}']
            }
        except Exception as e:
            return {
                'success': False,
                'mapping': None,
                'errors': [str(e)]
            }
    
    @staticmethod
    @db_transaction.atomic
    def delete_mapping(segment_type_id, source_code, target_code, soft_delete=True):
        """
        Delete (or deactivate) a segment mapping.
        
        Args:
            segment_type_id: ID of segment type
            source_code: Source segment code
            target_code: Target segment code
            soft_delete: If True, deactivate instead of deleting
        
        Returns:
            dict: {'success': bool, 'errors': list}
        """
        try:
            mapping = SegmentMappingManager.get_mapping(
                segment_type_id,
                source_code,
                target_code
            )
            
            if not mapping:
                return {
                    'success': False,
                    'errors': ['Mapping not found']
                }
            
            if soft_delete:
                mapping.is_active = False
                mapping.save()
                action = 'deactivated'
            else:
                mapping.delete()
                action = 'deleted'
            
            return {
                'success': True,
                'errors': [],
                'action': action
            }
        
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    @staticmethod
    def get_all_mappings_for_segment_type(segment_type_id, include_inactive=False):
        """
        Get all mappings for a specific segment type.
        
        Args:
            segment_type_id: ID of segment type
            include_inactive: Whether to include inactive mappings
        
        Returns:
            QuerySet of XX_SegmentMapping
        """
        query = XX_SegmentMapping.objects.filter(
            segment_type_id=segment_type_id
        ).select_related('source_segment', 'target_segment', 'segment_type')
        
        if not include_inactive:
            query = query.filter(is_active=True)
        
        return query
    
    @staticmethod
    def get_mapped_children_with_hierarchy(segment_type_id, segment_code):
        """
        Get all child segments (hierarchical) + mapped segments.
        Combines hierarchy traversal with mapping lookups.
        
        Args:
            segment_type_id: ID of segment type
            segment_code: Segment code to start from
        
        Returns:
            list: List of segment codes (children + mapped)
        """
        try:
            from account_and_entitys.managers.segment_manager import SegmentManager
            
            result = []
            
            # Get hierarchical children
            children = SegmentManager.get_segment_children(
                segment_type_id,
                segment_code,
                include_descendants=True
            )
            result.extend([child['code'] for child in children])
            
            # Get mapped targets
            mapped = SegmentMappingManager.get_target_segments(
                segment_type_id,
                segment_code
            )
            result.extend(mapped)
            
            # Remove duplicates
            return list(set(result))
        
        except Exception as e:
            print(f"Error in get_mapped_children_with_hierarchy: {e}")
            return []
    
    @staticmethod
    def apply_mapping_rules(segment_type_id, segment_codes, direction='target'):
        """
        Apply mapping rules to a list of segment codes.
        
        Args:
            segment_type_id: ID of segment type
            segment_codes: List of segment codes
            direction: 'target' (get targets) or 'source' (get sources)
        
        Returns:
            list: Expanded list including mapped segments
        """
        try:
            result = list(segment_codes)  # Start with original codes
            
            for code in segment_codes:
                if direction == 'target':
                    mapped = SegmentMappingManager.get_target_segments(
                        segment_type_id,
                        code
                    )
                else:  # source
                    mapped = SegmentMappingManager.get_source_segments(
                        segment_type_id,
                        code
                    )
                
                result.extend(mapped)
            
            # Remove duplicates
            return list(set(result))
        
        except Exception as e:
            print(f"Error in apply_mapping_rules: {e}")
            return segment_codes
    
    @staticmethod
    def get_mapping_chain(segment_type_id, start_code, max_depth=10):
        """
        Get the full mapping chain starting from a segment.
        Handles A→B→C→D chains.
        
        Args:
            segment_type_id: ID of segment type
            start_code: Starting segment code
            max_depth: Maximum chain depth to prevent infinite loops
        
        Returns:
            list: Ordered list of segment codes in the chain
        """
        try:
            chain = [start_code]
            visited = {start_code}
            current_code = start_code
            depth = 0
            
            while depth < max_depth:
                targets = SegmentMappingManager.get_target_segments(
                    segment_type_id,
                    current_code
                )
                
                # Take first target not yet visited
                next_code = None
                for target in targets:
                    if target not in visited:
                        next_code = target
                        break
                
                if not next_code:
                    break
                
                chain.append(next_code)
                visited.add(next_code)
                current_code = next_code
                depth += 1
            
            return chain
        
        except Exception as e:
            print(f"Error in get_mapping_chain: {e}")
            return [start_code]
    
    @staticmethod
    def validate_no_circular_mapping(segment_type_id, source_code, target_code):
        """
        Validate that creating a mapping won't create a circular reference.
        
        Args:
            segment_type_id: ID of segment type
            source_code: Proposed source segment
            target_code: Proposed target segment
        
        Returns:
            dict: {'valid': bool, 'errors': list}
        """
        try:
            # Check if target already maps back to source (direct or indirect)
            chain_from_target = SegmentMappingManager.get_mapping_chain(
                segment_type_id,
                target_code
            )
            
            if source_code in chain_from_target:
                return {
                    'valid': False,
                    'errors': [f'Circular mapping detected: {source_code} would eventually map back to itself via {target_code}']
                }
            
            return {
                'valid': True,
                'errors': []
            }
        
        except Exception as e:
            return {
                'valid': False,
                'errors': [str(e)]
            }
    
    @staticmethod
    def apply_mapping_to_combination(segment_combination, mapping_type=None):
        """
        Apply all applicable mappings to a segment combination.
        
        Args:
            segment_combination: Dict of {segment_type_id: segment_code}
            mapping_type: Optional filter by mapping type
        
        Returns:
            dict: New segment combination with mappings applied
        """
        try:
            result = segment_combination.copy()
            
            # Apply mapping for each segment in the combination
            for seg_type_id_str, seg_code in list(segment_combination.items()):
                seg_type_id = int(seg_type_id_str)
                
                # Get target segments for this source
                targets = SegmentMappingManager.get_target_segments(
                    seg_type_id,
                    seg_code
                )
                
                # If mapping exists, use first target
                if targets and len(targets) > 0:
                    result[seg_type_id_str] = targets[0]
            
            return result
        
        except Exception as e:
            print(f"Error in apply_mapping_to_combination: {e}")
            return segment_combination
