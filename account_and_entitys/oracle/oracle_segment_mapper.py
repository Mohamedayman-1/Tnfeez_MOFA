"""
Oracle Segment Mapper

Maps Django dynamic segments (XX_Segment) to Oracle Fusion segment fields (SEGMENT1-SEGMENT30).
Provides bidirectional mapping for:
- FBDI uploads (journals, budgets)
- Balance report parsing
- Data synchronization

Phase 5: Oracle Fusion Integration Update
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.db import models
from account_and_entitys.models import XX_SegmentType, XX_Segment, XX_TransactionSegment


class OracleSegmentMapper:
    """
    Manager for mapping between Django segments and Oracle SEGMENT1-SEGMENT30 fields.
    
    Handles:
    - Django segment → Oracle field number
    - Oracle field data → Django segment instances
    - Dynamic FBDI column generation
    - Balance report parsing
    """
    
    @staticmethod
    def get_oracle_field_name(segment_type_or_id) -> str:
        """
        Get Oracle field name (e.g., 'SEGMENT1') for a segment type.
        
        Args:
            segment_type_or_id: XX_SegmentType instance or segment_id (int)
            
        Returns:
            str: Oracle field name like 'Segment1', 'Segment2', etc.
            
        Example:
            >>> OracleSegmentMapper.get_oracle_field_name(1)
            'Segment1'
            >>> OracleSegmentMapper.get_oracle_field_name(entity_type)
            'Segment1'
        """
        if isinstance(segment_type_or_id, int):
            segment_type = XX_SegmentType.objects.get(segment_id=segment_type_or_id)
        else:
            segment_type = segment_type_or_id
        
        return f"Segment{segment_type.oracle_segment_number}"
    
    @staticmethod
    def get_oracle_field_number(segment_type_or_id) -> int:
        """
        Get Oracle segment number for a segment type.
        
        Args:
            segment_type_or_id: XX_SegmentType instance or segment_id (int)
            
        Returns:
            int: Oracle segment number (1-30)
            
        Example:
            >>> OracleSegmentMapper.get_oracle_field_number(entity_type)
            1
        """
        if isinstance(segment_type_or_id, int):
            segment_type = XX_SegmentType.objects.get(segment_id=segment_type_or_id)
        else:
            segment_type = segment_type_or_id
        
        return segment_type.oracle_segment_number
    
    @staticmethod
    def get_segment_type_by_oracle_number(oracle_segment_number: int) -> Optional[XX_SegmentType]:
        """
        Get Django segment type by Oracle segment number.
        
        Args:
            oracle_segment_number: Oracle segment number (1-30)
            
        Returns:
            XX_SegmentType instance or None
            
        Example:
            >>> OracleSegmentMapper.get_segment_type_by_oracle_number(1)
            <XX_SegmentType: Entity (Segment 1)>
        """
        try:
            return XX_SegmentType.objects.get(oracle_segment_number=oracle_segment_number)
        except XX_SegmentType.DoesNotExist:
            return None
    
    @staticmethod
    def build_oracle_segment_dict(transaction_transfer, include_from_to=False) -> Dict[str, Any]:
        """
        Build Oracle segment dictionary for a transaction transfer.
        Returns dict with keys like 'SEGMENT1', 'SEGMENT2', etc.
        
        Args:
            transaction_transfer: xx_TransactionTransfer instance
            include_from_to: If True, include FROM_SEGMENT1, TO_SEGMENT1, etc.
            
        Returns:
            dict: Oracle segment values
                  Format: {'SEGMENT1': 'E001', 'SEGMENT2': 'A100', ...}
                  With from/to: {'SEGMENT1': 'E001', 'FROM_SEGMENT1': 'E001', 'TO_SEGMENT1': 'E002', ...}
        
        Example:
            >>> segments = OracleSegmentMapper.build_oracle_segment_dict(transfer)
            >>> print(segments)
            {'SEGMENT1': 'E001', 'SEGMENT2': 'A100', 'SEGMENT3': 'P001'}
        """
        from account_and_entitys.models import XX_TransactionSegment
        
        oracle_dict = {}
        
        # Get all transaction segments
        transaction_segments = XX_TransactionSegment.objects.filter(
            transaction_transfer=transaction_transfer
        ).select_related('segment_type', 'segment_value', 'from_segment_value', 'to_segment_value')
        
        for ts in transaction_segments:
            oracle_field = OracleSegmentMapper.get_oracle_field_name(ts.segment_type)
            
            # Primary segment value
            if ts.segment_value:
                oracle_dict[oracle_field] = ts.segment_value.code
            
            # From/To segments (for transfers)
            if include_from_to:
                if ts.from_segment_value:
                    oracle_dict[f'FROM_{oracle_field}'] = ts.from_segment_value.code
                if ts.to_segment_value:
                    oracle_dict[f'TO_{oracle_field}'] = ts.to_segment_value.code
        
        return oracle_dict
    
    @staticmethod
    def build_all_oracle_fields(num_segments: int = 30) -> List[str]:
        """
        Build list of all possible Oracle segment field names (SEGMENT1-SEGMENT30).
        
        Args:
            num_segments: Number of segments to generate (default 30)
            
        Returns:
            list: ['Segment1', 'Segment2', ..., 'Segment30']
        """
        return [f'Segment{i}' for i in range(1, num_segments + 1)]
    
    @staticmethod
    def get_active_oracle_fields() -> List[str]:
        """
        Get list of Oracle field names for currently active segment types.
        Only returns fields that are actually configured in the system.
        
        Returns:
            list: Oracle field names for active segments
                  Example: ['SEGMENT1', 'SEGMENT2', 'SEGMENT3']
        """
        segment_types = XX_SegmentType.objects.filter(is_active=True).order_by('oracle_segment_number')
        return [OracleSegmentMapper.get_oracle_field_name(st) for st in segment_types]
    
    @staticmethod
    def parse_oracle_record_to_segments(oracle_record: Dict[str, Any]) -> Dict[int, str]:
        """
        Parse Oracle record (from balance report or API) into segment type → code mapping.
        
        Args:
            oracle_record: Dict with SEGMENT1, SEGMENT2, etc. keys
            
        Returns:
            dict: {segment_type_id: segment_code}
                  Example: {1: 'E001', 2: 'A100', 3: 'P001'}
        
        Example:
            >>> record = {'SEGMENT1': 'E001', 'SEGMENT2': 'A100', 'SEGMENT3': 'P001'}
            >>> segments = OracleSegmentMapper.parse_oracle_record_to_segments(record)
            >>> print(segments)
            {1: 'E001', 2: 'A100', 3: 'P001'}
        """
        segment_map = {}
        
        # Iterate through all possible segment fields
        for oracle_num in range(1, 31):
            oracle_field = f'Segment{oracle_num}'
            
            if oracle_field in oracle_record:
                value = oracle_record[oracle_field]
                
                # Skip empty/null values
                if value is None or value == '' or str(value).strip() == '':
                    continue
                
                # Get segment type for this Oracle number
                segment_type = OracleSegmentMapper.get_segment_type_by_oracle_number(oracle_num)
                
                if segment_type:
                    # Convert value to string and strip whitespace
                    segment_code = str(value).strip()
                    segment_map[segment_type.segment_id] = segment_code
        
        return segment_map
    
    @staticmethod
    def validate_oracle_segments(oracle_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate Oracle segment values against Django segment master data.
        
        Args:
            oracle_dict: Dict with SEGMENT1, SEGMENT2, etc. keys
            
        Returns:
            dict: {
                'valid': bool,
                'errors': list of error messages,
                'validated_segments': dict of valid segment_type_id → segment instance
            }
        """
        errors = []
        validated_segments = {}
        
        # Parse Oracle record to segment map
        segment_map = OracleSegmentMapper.parse_oracle_record_to_segments(oracle_dict)
        
        # Validate each segment
        for segment_type_id, segment_code in segment_map.items():
            try:
                # Get segment type
                segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id)
                
                # Check if segment exists
                segment = XX_Segment.objects.get(
                    segment_type=segment_type,
                    code=segment_code,
                    is_active=True
                )
                
                validated_segments[segment_type_id] = segment
                
            except XX_SegmentType.DoesNotExist:
                errors.append(f"Segment type {segment_type_id} not found in system")
            except XX_Segment.DoesNotExist:
                errors.append(f"Segment code '{segment_code}' not found for {segment_type.segment_name}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'validated_segments': validated_segments
        }
    
    @staticmethod
    def build_oracle_where_clause(segment_filters: Dict[int, str]) -> str:
        """
        Build SQL WHERE clause for Oracle queries with dynamic segments.
        
        Args:
            segment_filters: Dict of {segment_type_id: segment_code}
            
        Returns:
            str: SQL WHERE clause fragment
                 Example: "SEGMENT1 = 'E001' AND SEGMENT2 = 'A100'"
        """
        clauses = []
        
        for segment_type_id, segment_code in segment_filters.items():
            oracle_field = OracleSegmentMapper.get_oracle_field_name(segment_type_id)
            # Escape single quotes in segment code
            escaped_code = str(segment_code).replace("'", "''")
            clauses.append(f"{oracle_field} = '{escaped_code}'")
        
        return " AND ".join(clauses) if clauses else "1=1"
    
    @staticmethod
    def build_fbdi_row(transaction_transfer, base_row: Dict[str, Any], include_from_to: str = 'from',fill_all=False) -> Dict[str, Any]:
        """
        Build complete FBDI row with dynamic segments for journal/budget import.
        
        Args:
            transaction_transfer: xx_TransactionTransfer instance
            base_row: Dict with non-segment fields (LEDGER_ID, AMOUNT, etc.)
            include_from_to: Which segments to use - 'from', 'to', or 'both' (default: 'from')
            
        Returns:
            dict: Complete row with SEGMENT1-SEGMENT30 fields populated
            
        Example:
            >>> # Use FROM segments for debit entry
            >>> debit_row = mapper.build_fbdi_row(transfer, base_row, include_from_to='from')
            >>> # Use TO segments for credit entry
            >>> credit_row = mapper.build_fbdi_row(transfer, base_row, include_from_to='to')
        """
        from account_and_entitys.models import XX_TransactionSegment
        
        # Start with base row
        fbdi_row = base_row.copy()
        
        # Get transaction segments based on include_from_to parameter
        transaction_segments = XX_TransactionSegment.objects.filter(
            transaction_transfer=transaction_transfer
        ).select_related('segment_type', 'from_segment_value', 'to_segment_value')
        
        # Build segment values based on include_from_to
        for ts in transaction_segments:
            oracle_field = OracleSegmentMapper.get_oracle_field_name(ts.segment_type)
            print("segment type")
            print(ts.segment_type.segment_name,include_from_to)
            print(ts.segment_type)

            
            if include_from_to == 'from' and ts.from_segment_value:
                fbdi_row[oracle_field] = ts.from_segment_value.code
            elif include_from_to == 'to' and ts.to_segment_value:
                fbdi_row[oracle_field] = ts.to_segment_value.code
            elif include_from_to == 'both':
                # For 'both', prioritize from_segment_value, fall back to to_segment_value
                if ts.from_segment_value:
                    fbdi_row[oracle_field] = ts.from_segment_value.code
                elif ts.to_segment_value:
                    fbdi_row[oracle_field] = ts.to_segment_value.code
        
        # Fill remaining segments with empty/None values for unused segments
        for i in range(1, 31):
            segment_field = f'Segment{i}'
            if segment_field not in fbdi_row:
                # get default values from segments
                print(f"fill_all: {fill_all}")
                if fill_all == True:
                    seg_type = XX_SegmentType.objects.filter(oracle_segment_number=i, is_active=True).first()
                    if seg_type:
                        seg = XX_Segment.objects.filter(segment_type=seg_type.segment_id, is_active=True).first()
                        fbdi_row[segment_field] = seg.code if seg else None
                    else:
                        fbdi_row[segment_field] = None
                else:
                    fbdi_row[segment_field] = None
        
        return fbdi_row
    
    @staticmethod
    def get_segment_configuration_summary() -> Dict[str, Any]:
        """
        Get summary of current segment configuration for Oracle integration.
        Useful for debugging and validation.
        
        Returns:
            dict: Configuration summary with Oracle mapping details
        """
        segment_types = XX_SegmentType.objects.filter(is_active=True).order_by('oracle_segment_number')
        
        config = {
            'total_segments': segment_types.count(),
            'oracle_fields_used': [],
            'segment_mapping': [],
            'unused_oracle_fields': []
        }
        
        used_oracle_numbers = set()
        
        for st in segment_types:
            oracle_field = OracleSegmentMapper.get_oracle_field_name(st)
            config['oracle_fields_used'].append(oracle_field)
            used_oracle_numbers.add(st.oracle_segment_number)
            
            config['segment_mapping'].append({
                'segment_id': st.segment_id,
                'segment_name': st.segment_name,
                'segment_type': st.segment_type,
                'oracle_segment_number': st.oracle_segment_number,
                'oracle_field': oracle_field,
                'is_required': st.is_required,
                'has_hierarchy': st.has_hierarchy,
                'value_count': XX_Segment.objects.filter(segment_type=st, is_active=True).count()
            })
        
        # Find unused Oracle fields
        for i in range(1, 31):
            if i not in used_oracle_numbers:
                config['unused_oracle_fields'].append(f'SEGMENT{i}')
        
        return config
