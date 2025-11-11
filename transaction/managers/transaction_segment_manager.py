"""
Transaction Segment Manager

Handles business logic for transaction segments including:
- Creating/updating transaction segment assignments
- Validating segment combinations
- Envelope balance checks
- Hierarchical segment transfers
- Oracle journal entry generation
- Legacy data synchronization

This manager works in conjunction with SegmentManager from account_and_entitys
to provide transaction-specific segment operations.
"""

from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from typing import Dict, List, Optional, Tuple


class TransactionSegmentManager:
    """Manager for transaction segment operations."""
    
    @staticmethod
    def create_transfer_with_segments(budget_transfer, transfer_data, segments_data):
        """
        Create a new transaction transfer with dynamic segment assignments.
        
        Args:
            budget_transfer: xx_BudgetTransfer instance
            transfer_data (dict): Transaction transfer fields (amount, reason, etc.)
            segments_data (dict): {segment_id: {'from_code': 'xxx', 'to_code': 'yyy'}}
        
        Returns:
            dict: {
                'success': bool,
                'transaction_transfer': xx_TransactionTransfer instance,
                'segments': list of XX_TransactionSegment instances,
                'errors': list
            }
        """
        from transaction.models import xx_TransactionTransfer
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        errors = []
        
        try:
            with db_transaction.atomic():
                # Validate segments first
                validation_result = SegmentManager.validate_transaction_segments(segments_data)
                if not validation_result['valid']:
                    return {
                        'success': False,
                        'transaction_transfer': None,
                        'segments': [],
                        'errors': validation_result['errors']
                    }
                
                # Create transaction transfer
                transaction_transfer = xx_TransactionTransfer.objects.create(
                    transaction=budget_transfer,
                    **transfer_data
                )
                
                # Create segment assignments
                segment_result = SegmentManager.create_transaction_segments(
                    transaction_transfer=transaction_transfer,
                    segments_data=segments_data
                )
                
                if not segment_result['success']:
                    raise ValidationError(segment_result['errors'])
                
                # Sync to legacy fields
                transaction_transfer.sync_dynamic_to_legacy()
                
                return {
                    'success': True,
                    'transaction_transfer': transaction_transfer,
                    'segments': segment_result['segments'],
                    'errors': []
                }
        
        except Exception as e:
            return {
                'success': False,
                'transaction_transfer': None,
                'segments': [],
                'errors': [str(e)]
            }
    
    @staticmethod
    def create_transfer_with_segments_simple(budget_transfer, transfer_data, segments_data, is_source):
        """
        Create a new transaction transfer with simplified segment format.
        
        NEW SIMPLIFIED FORMAT:
        - Each segment has only 'code' field (not from_code/to_code)
        - Direction determined by is_source parameter
        
        Args:
            budget_transfer: xx_BudgetTransfer instance
            transfer_data (dict): Transaction transfer fields (from_center, to_center, reason, etc.)
            segments_data (dict): {segment_id: {'code': 'xxx'}}
            is_source (bool): True if taking funds (from_center > 0), False if receiving (to_center > 0)
        
        Returns:
            dict: {
                'success': bool,
                'transaction_transfer': xx_TransactionTransfer instance,
                'segments': list of XX_TransactionSegment instances,
                'errors': list
            }
        """
        from transaction.models import xx_TransactionTransfer
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        errors = []
        
        try:
            with db_transaction.atomic():
                # Validate segments first
                validation_result = SegmentManager.validate_transaction_segments_simple(segments_data)
                if not validation_result['valid']:
                    return {
                        'success': False,
                        'transaction_transfer': None,
                        'segments': [],
                        'errors': validation_result['errors']
                    }
                
                # Create transaction transfer
                transaction_transfer = xx_TransactionTransfer.objects.create(
                    transaction=budget_transfer,
                    **transfer_data
                )
                
                # Create segment assignments with direction
                segment_result = SegmentManager.create_transaction_segments_simple(
                    transaction_transfer=transaction_transfer,
                    segments_data=segments_data,
                    is_source=is_source
                )
                
                if not segment_result['success']:
                    raise ValidationError(segment_result['errors'])
                
                # Sync to legacy fields
                transaction_transfer.sync_dynamic_to_legacy()
                
                return {
                    'success': True,
                    'transaction_transfer': transaction_transfer,
                    'segments': segment_result['segments'],
                    'errors': []
                }
        
        except Exception as e:
            return {
                'success': False,
                'transaction_transfer': None,
                'segments': [],
                'errors': [str(e)]
            }
    
    @staticmethod
    def update_transfer_segments_simple(transaction_transfer, segments_data, is_source):
        """
        Update segment assignments with simplified format.
        
        Args:
            transaction_transfer: xx_TransactionTransfer instance
            segments_data (dict): {segment_id: {'code': 'xxx'}}
            is_source (bool): True if taking funds, False if receiving
        
        Returns:
            dict: {'success': bool, 'segments': list, 'errors': list}
        """
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        try:
            with db_transaction.atomic():
                # Delete existing segments
                SegmentManager.delete_transaction_segments(transaction_transfer)
                
                # Create new segments with direction
                result = SegmentManager.create_transaction_segments_simple(
                    transaction_transfer=transaction_transfer,
                    segments_data=segments_data,
                    is_source=is_source
                )
                
                if result['success']:
                    # Sync to legacy fields
                    transaction_transfer.sync_dynamic_to_legacy()
                
                return result
        
        except Exception as e:
            return {
                'success': False,
                'segments': [],
                'errors': [str(e)]
            }
    
    @staticmethod
    def update_transfer_segments(transaction_transfer, segments_data):
        """
        Update segment assignments for an existing transaction transfer.
        
        Args:
            transaction_transfer: xx_TransactionTransfer instance
            segments_data (dict): {segment_id: {'from_code': 'xxx', 'to_code': 'yyy'}}
        
        Returns:
            dict: {'success': bool, 'segments': list, 'errors': list}
        """
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        try:
            with db_transaction.atomic():
                # Delete existing segments
                SegmentManager.delete_transaction_segments(transaction_transfer)
                
                # Create new segments
                result = SegmentManager.create_transaction_segments(
                    transaction_transfer=transaction_transfer,
                    segments_data=segments_data
                )
                
                if result['success']:
                    # Sync to legacy fields
                    transaction_transfer.sync_dynamic_to_legacy()
                
                return result
        
        except Exception as e:
            return {
                'success': False,
                'segments': [],
                'errors': [str(e)]
            }
    
    @staticmethod
    def validate_envelope_balance(segments_data, transfer_amount):
        """
        Check if envelope has sufficient balance for the transfer.
        
        Args:
            segments_data (dict): Segment assignments
            transfer_amount (Decimal): Amount to transfer
        
        Returns:
            dict: {
                'valid': bool,
                'from_balance': Decimal,
                'to_balance': Decimal,
                'errors': list
            }
        """
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        errors = []
        
        # Get FROM segment combination
        from_segments = {seg_id: data['from_code'] for seg_id, data in segments_data.items()}
        from_balance = SegmentManager.get_envelope_balance(from_segments)
        
        # Get TO segment combination
        to_segments = {seg_id: data['to_code'] for seg_id, data in segments_data.items()}
        to_balance = SegmentManager.get_envelope_balance(to_segments)
        
        # Validate FROM balance
        if from_balance is not None and from_balance < transfer_amount:
            errors.append(
                f"Insufficient balance in source envelope. Available: {from_balance}, Required: {transfer_amount}"
            )
        
        return {
            'valid': len(errors) == 0,
            'from_balance': from_balance,
            'to_balance': to_balance,
            'errors': errors
        }
    
    @staticmethod
    def get_transfer_summary(budget_transfer):
        """
        Get a summary of all transfers for a budget transfer with segment details.
        
        Args:
            budget_transfer: xx_BudgetTransfer instance
        
        Returns:
            list: [{
                'transfer_id': int,
                'amount': Decimal,
                'segments': {...},
                'from_balance': Decimal,
                'to_balance': Decimal
            }]
        """
        from transaction.models import xx_TransactionTransfer
        
        transfers = xx_TransactionTransfer.objects.filter(
            transaction=budget_transfer
        ).order_by('transfer_id')
        
        summary = []
        for transfer in transfers:
            segments_dict = transfer.get_segments_dict()
            
            summary.append({
                'transfer_id': transfer.transfer_id,
                'amount': transfer.from_center or Decimal('0'),
                'segments': segments_dict,
                'reason': transfer.reason,
                'file': transfer.file.url if transfer.file else None
            })
        
        return summary
    
    @staticmethod
    def validate_hierarchical_transfer(segments_data):
        """
        Validate that hierarchical segment transfers follow business rules.
        For example: Can only transfer within same parent hierarchy.
        
        Args:
            segments_data (dict): Segment assignments
        
        Returns:
            dict: {'valid': bool, 'errors': list}
        """
        from account_and_entitys.managers.segment_manager import SegmentManager
        from account_and_entitys.models import XX_SegmentType
        
        errors = []
        
        # Get segment types that have hierarchy
        hierarchical_types = XX_SegmentType.objects.filter(
            has_hierarchy=True
        )
        
        for seg_type in hierarchical_types:
            if seg_type.segment_id not in segments_data:
                continue
            
            from_code = segments_data[seg_type.segment_id].get('from_code')
            to_code = segments_data[seg_type.segment_id].get('to_code')
            
            if not from_code or not to_code:
                continue
            
            # Check if they share the same parent (business rule)
            from_parent = SegmentManager.get_parent(seg_type.segment_id, from_code)
            to_parent = SegmentManager.get_parent(seg_type.segment_id, to_code)
            
            # Rule: Both must have same parent or one must be ancestor of the other
            if from_code != to_code:
                from_parents = SegmentManager.get_all_parents(seg_type.segment_id, from_code)
                to_parents = SegmentManager.get_all_parents(seg_type.segment_id, to_code)
                
                # Check if they share any common parent
                common_parents = set(from_parents) & set(to_parents)
                
                if not common_parents:
                    errors.append(
                        f"Transfer between {seg_type.segment_name} segments {from_code} and {to_code} "
                        f"not allowed - they do not share a common parent in hierarchy"
                    )
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def generate_journal_entries(budget_transfer):
        """
        Generate Oracle journal entries for all transfers in a budget transfer.
        
        Args:
            budget_transfer: xx_BudgetTransfer instance
        
        Returns:
            list: Journal entry dictionaries for Oracle FBDI upload
        """
        from transaction.models import xx_TransactionTransfer
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        transfers = xx_TransactionTransfer.objects.filter(
            transaction=budget_transfer
        ).order_by('transfer_id')
        
        journal_entries = []
        
        for transfer in transfers:
            segments = transfer.get_segments_dict()
            oracle_mapping = SegmentManager.get_oracle_segment_mapping(segments)
            
            amount = transfer.from_center or Decimal('0')
            
            # Debit entry (FROM)
            debit_entry = {
                'STATUS': 'NEW',
                'LEDGER_ID': '',  # To be filled from config
                'ACCOUNTING_DATE': budget_transfer.transaction_date or '',
                'CURRENCY_CODE': 'SAR',
                'ACTUAL_FLAG': 'A',
                'USER_JE_SOURCE_NAME': 'Budget Transfer',
                'USER_JE_CATEGORY_NAME': 'Budget Adjustment',
                'ENTERED_DR': float(amount),
                'ENTERED_CR': 0,
            }
            
            # Add FROM segments
            for seg_num, seg_code in oracle_mapping['from'].items():
                debit_entry[f'SEGMENT{seg_num}'] = seg_code
            
            # Credit entry (TO)
            credit_entry = {
                'STATUS': 'NEW',
                'LEDGER_ID': '',  # To be filled from config
                'ACCOUNTING_DATE': budget_transfer.transaction_date or '',
                'CURRENCY_CODE': 'SAR',
                'ACTUAL_FLAG': 'A',
                'USER_JE_SOURCE_NAME': 'Budget Transfer',
                'USER_JE_CATEGORY_NAME': 'Budget Adjustment',
                'ENTERED_DR': 0,
                'ENTERED_CR': float(amount),
            }
            
            # Add TO segments
            for seg_num, seg_code in oracle_mapping['to'].items():
                credit_entry[f'SEGMENT{seg_num}'] = seg_code
            
            journal_entries.append(debit_entry)
            journal_entries.append(credit_entry)
        
        return journal_entries
    
    @staticmethod
    def bulk_migrate_legacy_transactions(batch_size=500):
        """
        Migrate legacy transaction transfers to dynamic segment structure.
        
        Args:
            batch_size (int): Number of records to process per batch
        
        Returns:
            dict: {
                'total_processed': int,
                'successful': int,
                'failed': int,
                'errors': list
            }
        """
        from transaction.models import xx_TransactionTransfer
        from account_and_entitys.models import XX_TransactionSegment
        
        # Get transactions that don't have dynamic segments yet
        transactions_to_migrate = xx_TransactionTransfer.objects.exclude(
            transfer_id__in=XX_TransactionSegment.objects.values_list(
                'transaction_transfer_id', flat=True
            ).distinct()
        )
        
        total = transactions_to_migrate.count()
        successful = 0
        failed = 0
        errors = []
        
        for i in range(0, total, batch_size):
            batch = transactions_to_migrate[i:i + batch_size]
            
            for transaction in batch:
                try:
                    transaction.sync_legacy_to_dynamic()
                    successful += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"Transaction {transaction.transfer_id}: {str(e)}")
        
        return {
            'total_processed': total,
            'successful': successful,
            'failed': failed,
            'errors': errors
        }
    
    @staticmethod
    def get_segment_transfer_report(start_date=None, end_date=None, segment_type_name=None):
        """
        Generate a report of segment transfers within a date range.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            segment_type_name: Filter by specific segment type
        
        Returns:
            dict: Statistical report of transfers
        """
        from transaction.models import xx_TransactionTransfer
        from account_and_entitys.models import XX_TransactionSegment
        from django.db.models import Sum, Count
        from django.db import models
        queryset = XX_TransactionSegment.objects.all()
        
        if segment_type_name:
            queryset = queryset.filter(segment_type__segment_name=segment_type_name)
        
        if start_date:
            queryset = queryset.filter(transaction_transfer__transaction__created_at__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(transaction_transfer__transaction__created_at__lte=end_date)
        
        # Get statistics
        stats = queryset.aggregate(
            total_transfers=Count('id'),
            unique_transactions=Count('transaction_transfer', distinct=True)
        )
        
        # Get cross-segment transfers (from != to)
        cross_transfers = queryset.exclude(
            from_segment_value=models.F('to_segment_value')
        ).count()
        
        return {
            'total_transfers': stats['total_transfers'],
            'unique_transactions': stats['unique_transactions'],
            'cross_segment_transfers': cross_transfers,
            'same_segment_transfers': stats['total_transfers'] - cross_transfers,
        }
