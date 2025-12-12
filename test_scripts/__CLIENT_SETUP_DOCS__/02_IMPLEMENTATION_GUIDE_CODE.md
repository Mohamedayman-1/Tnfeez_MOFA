# Implementation Guide - Step-by-Step Code Changes

## Overview
This document provides **concrete code changes** for each file that needs modification to support dynamic segments.

---

## Phase 1: New Models (account_and_entitys/models.py)

### Step 1.1: Add New Models to End of File

Add these models **after** the existing `XX_BalanceReport` model:

```python
# ============================================
# DYNAMIC SEGMENT SYSTEM (Multi-Client Support)
# ============================================

class XX_SegmentType(models.Model):
    """
    Defines segment types for this client installation.
    Examples: Entity (Cost Center), Account, Project, Line Item, etc.
    Configured during client setup.
    """
    segment_id = models.IntegerField(primary_key=True, help_text="Unique segment identifier")
    segment_name = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Display name (e.g., 'Entity', 'Account', 'Project')"
    )
    segment_type = models.CharField(
        max_length=50,
        help_text="Technical type (e.g., 'cost_center', 'account', 'project')"
    )
    oracle_segment_number = models.IntegerField(
        help_text="Maps to Oracle SEGMENT1, SEGMENT2, etc."
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Whether this segment is required in transactions"
    )
    has_hierarchy = models.BooleanField(
        default=False,
        help_text="Whether this segment supports parent-child relationships"
    )
    max_length = models.IntegerField(
        default=50,
        help_text="Maximum code length for this segment"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Order for displaying in UI (lower = first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this segment is currently active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "XX_SEGMENT_TYPE_XX"
        verbose_name = "Segment Type"
        verbose_name_plural = "Segment Types"
        ordering = ['display_order', 'segment_id']
    
    def __str__(self):
        return f"{self.segment_name} (Segment {self.oracle_segment_number})"


class XX_Segment(models.Model):
    """
    Generic segment value model that replaces XX_Entity, XX_Account, XX_Project.
    All segment values (regardless of type) are stored here.
    """
    id = models.AutoField(primary_key=True)
    segment_type = models.ForeignKey(
        XX_SegmentType,
        on_delete=models.CASCADE,
        related_name='values',
        help_text="Which segment type this value belongs to"
    )
    code = models.CharField(
        max_length=50,
        help_text="The actual segment code/value"
    )
    parent_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Parent segment code for hierarchical segments"
    )
    alias = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Display name / description"
    )
    level = models.IntegerField(
        default=0,
        help_text="Hierarchy level (0 = root)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this segment value is active"
    )
    
    # Financial data (optional, for segments that need envelopes/limits)
    envelope_amount = models.DecimalField(
        max_digits=30,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Envelope/budget limit for this segment (if applicable)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "XX_SEGMENT_XX"
        verbose_name = "Segment Value"
        verbose_name_plural = "Segment Values"
        unique_together = ("segment_type", "code")
        indexes = [
            models.Index(fields=["segment_type", "code"]),
            models.Index(fields=["segment_type", "parent_code"]),
            models.Index(fields=["code"]),
        ]
    
    def __str__(self):
        return f"{self.segment_type.segment_name}: {self.code} ({self.alias or 'No alias'})"
    
    def get_all_children(self):
        """Get all descendant codes recursively"""
        children = list(XX_Segment.objects.filter(
            segment_type=self.segment_type,
            parent_code=self.code
        ).values_list('code', flat=True))
        
        descendants = []
        for child_code in children:
            descendants.append(child_code)
            try:
                child = XX_Segment.objects.get(
                    segment_type=self.segment_type,
                    code=child_code
                )
                descendants.extend(child.get_all_children())
            except XX_Segment.DoesNotExist:
                continue
        
        return descendants


class XX_TransactionSegment(models.Model):
    """
    Links transaction transfers to their segment values.
    Each transaction will have one record per segment type.
    """
    id = models.AutoField(primary_key=True)
    transaction_transfer = models.ForeignKey(
        'transaction.xx_TransactionTransfer',
        on_delete=models.CASCADE,
        related_name='transaction_segments',
        help_text="The transaction this segment belongs to"
    )
    segment_type = models.ForeignKey(
        XX_SegmentType,
        on_delete=models.CASCADE,
        help_text="Which segment type (Entity, Account, etc.)"
    )
    segment_value = models.ForeignKey(
        XX_Segment,
        on_delete=models.CASCADE,
        help_text="The specific segment value"
    )
    
    # For transfer transactions, store source and destination
    from_segment_value = models.ForeignKey(
        XX_Segment,
        on_delete=models.CASCADE,
        related_name='transfers_from',
        null=True,
        blank=True,
        help_text="Source segment for transfers"
    )
    to_segment_value = models.ForeignKey(
        XX_Segment,
        on_delete=models.CASCADE,
        related_name='transfers_to',
        null=True,
        blank=True,
        help_text="Destination segment for transfers"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "XX_TRANSACTION_SEGMENT_XX"
        verbose_name = "Transaction Segment"
        verbose_name_plural = "Transaction Segments"
        unique_together = ("transaction_transfer", "segment_type")
        indexes = [
            models.Index(fields=["transaction_transfer", "segment_type"]),
            models.Index(fields=["segment_value"]),
        ]
    
    def __str__(self):
        return f"Transaction {self.transaction_transfer_id} - {self.segment_type.segment_name}: {self.segment_value.code}"


class XX_DynamicBalanceReport(models.Model):
    """
    Dynamic balance report storage that supports any number of segments.
    Segment values stored as JSONField for flexibility.
    """
    id = models.AutoField(primary_key=True)
    control_budget_name = models.CharField(
        max_length=100, null=True, blank=True
    )
    ledger_name = models.CharField(
        max_length=100, null=True, blank=True
    )
    as_of_period = models.CharField(
        max_length=20, null=True, blank=True
    )
    
    # Store segment values as JSON: {"1": "12345", "2": "67890", "3": "98765"}
    # Keys are segment_type IDs, values are segment codes
    segment_values = models.JSONField(
        default=dict,
        help_text="JSON mapping of segment_type_id -> segment_code"
    )
    
    # Financial fields
    encumbrance_ytd = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    other_ytd = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    actual_ytd = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    funds_available_asof = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    budget_ytd = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "XX_DYNAMIC_BALANCE_REPORT_XX"
        verbose_name = "Dynamic Balance Report"
        verbose_name_plural = "Dynamic Balance Reports"
        indexes = [
            models.Index(fields=["control_budget_name", "as_of_period"]),
            models.Index(fields=["as_of_period"]),
        ]
    
    def __str__(self):
        segments_str = ", ".join([f"{k}:{v}" for k, v in self.segment_values.items()])
        return f"Balance Report: {self.control_budget_name} - {segments_str}"
    
    def get_segment_value(self, segment_type_id):
        """Get segment value for a specific segment type"""
        return self.segment_values.get(str(segment_type_id))
```

---

## Phase 2: Segment Manager (New File)

Create: `account_and_entitys/managers/__init__.py`
```python
# Empty file to make this a package
```

Create: `account_and_entitys/managers/segment_manager.py`

```python
"""
Segment Manager - Dynamic replacement for EnvelopeManager
Handles all segment-related business logic in a configuration-driven way.
"""

from django.conf import settings
from account_and_entitys.models import XX_SegmentType, XX_Segment, XX_TransactionSegment
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
        try:
            return XX_SegmentType.objects.get(segment_name=segment_name, is_active=True)
        except XX_SegmentType.DoesNotExist:
            return None
    
    @staticmethod
    def get_segment_type_by_id(segment_id):
        """Get segment type by ID"""
        try:
            return XX_SegmentType.objects.get(segment_id=segment_id, is_active=True)
        except XX_SegmentType.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_segment_types():
        """Get all active segment types ordered by display_order"""
        return XX_SegmentType.objects.filter(is_active=True).order_by('display_order')
    
    @staticmethod
    def get_required_segment_types():
        """Get only required segment types"""
        return XX_SegmentType.objects.filter(is_active=True, is_required=True).order_by('display_order')
    
    @staticmethod
    def validate_transaction_segments(segment_data):
        """
        Validate that all required segments are present and valid.
        
        Args:
            segment_data: Dict like {"Entity": "12345", "Account": "67890", "Project": "98765"}
        
        Returns:
            (bool, str): (is_valid, error_message)
        """
        required_types = SegmentManager.get_required_segment_types()
        
        for seg_type in required_types:
            if seg_type.segment_name not in segment_data:
                return False, f"Required segment '{seg_type.segment_name}' is missing"
            
            segment_code = segment_data[seg_type.segment_name]
            if not segment_code:
                return False, f"Required segment '{seg_type.segment_name}' cannot be empty"
            
            # Verify segment exists
            if not XX_Segment.objects.filter(
                segment_type=seg_type,
                code=segment_code,
                is_active=True
            ).exists():
                return False, f"Invalid segment code '{segment_code}' for {seg_type.segment_name}"
        
        return True, "Valid"
    
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
    def create_transaction_segments(transaction_transfer, segment_data, from_to_data=None):
        """
        Create XX_TransactionSegment records for a transaction.
        
        Args:
            transaction_transfer: xx_TransactionTransfer object
            segment_data: Dict like {"Entity": "12345", "Account": "67890"}
            from_to_data: Optional dict for transfers like {"Entity": {"from": "111", "to": "222"}}
        
        Returns:
            List of created XX_TransactionSegment objects
        """
        created_segments = []
        
        for segment_name, segment_code in segment_data.items():
            segment_type = SegmentManager.get_segment_type_by_name(segment_name)
            if not segment_type:
                continue
            
            segment_value = XX_Segment.objects.get(
                segment_type=segment_type,
                code=segment_code,
                is_active=True
            )
            
            # Handle from/to for transfers
            from_value = None
            to_value = None
            if from_to_data and segment_name in from_to_data:
                from_code = from_to_data[segment_name].get('from')
                to_code = from_to_data[segment_name].get('to')
                
                if from_code:
                    from_value = XX_Segment.objects.get(
                        segment_type=segment_type,
                        code=from_code,
                        is_active=True
                    )
                if to_code:
                    to_value = XX_Segment.objects.get(
                        segment_type=segment_type,
                        code=to_code,
                        is_active=True
                    )
            
            trans_segment = XX_TransactionSegment.objects.create(
                transaction_transfer=transaction_transfer,
                segment_type=segment_type,
                segment_value=segment_value,
                from_segment_value=from_value,
                to_segment_value=to_value
            )
            created_segments.append(trans_segment)
        
        return created_segments
    
    @staticmethod
    def get_transaction_segments(transaction_transfer):
        """
        Get all segment values for a transaction as a dict.
        
        Returns:
            Dict like {"Entity": "12345", "Account": "67890", "Project": "98765"}
        """
        segments = XX_TransactionSegment.objects.filter(
            transaction_transfer=transaction_transfer
        ).select_related('segment_type', 'segment_value')
        
        return {
            ts.segment_type.segment_name: ts.segment_value.code
            for ts in segments
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
        from account_and_entitys.models import XX_Entity, XX_Account, XX_Project
        
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
            XX_Segment.objects.get_or_create(
                segment_type=segment_type,
                code=legacy_record.entity if hasattr(legacy_record, 'entity') 
                     else legacy_record.account if hasattr(legacy_record, 'account')
                     else legacy_record.project,
                defaults={
                    'parent_code': legacy_record.parent,
                    'alias': legacy_record.alias_default,
                    'is_active': True
                }
            )
            migrated_count += 1
        
        return migrated_count
```

---

## Phase 3: Configuration File

Create: `config/segments_config.json`

```json
{
  "client_id": "DEFAULT_CLIENT",
  "client_name": "Default Configuration (3 Segments)",
  "installation_date": "2025-11-05",
  "segments": [
    {
      "segment_id": 1,
      "segment_name": "Entity",
      "segment_type": "cost_center",
      "oracle_segment_number": 1,
      "is_required": true,
      "has_hierarchy": true,
      "max_length": 50,
      "display_order": 1,
      "description": "Cost Center / Entity segment"
    },
    {
      "segment_id": 2,
      "segment_name": "Account",
      "segment_type": "account",
      "oracle_segment_number": 2,
      "is_required": true,
      "has_hierarchy": true,
      "max_length": 50,
      "display_order": 2,
      "description": "Chart of Accounts segment"
    },
    {
      "segment_id": 3,
      "segment_name": "Project",
      "segment_type": "project",
      "oracle_segment_number": 3,
      "is_required": false,
      "has_hierarchy": true,
      "max_length": 50,
      "display_order": 3,
      "description": "Project / Program segment"
    }
  ],
  "oracle_config": {
    "max_segments_supported": 30,
    "ledger_id": "CHANGE_ME",
    "balance_report_segment_mapping": {
      "segment1": 1,
      "segment2": 2,
      "segment3": 3
    }
  },
  "validation_rules": {
    "allow_cross_segment_transfers": true,
    "require_envelope_check": true,
    "enforce_hierarchy_constraints": true
  }
}
```

Example for 4-segment client:

Create: `config/segments_config_4seg.json`

```json
{
  "client_id": "CLIENT_4SEG",
  "client_name": "4-Segment Client Example",
  "segments": [
    {
      "segment_id": 1,
      "segment_name": "Entity",
      "segment_type": "cost_center",
      "oracle_segment_number": 1,
      "is_required": true,
      "has_hierarchy": true,
      "max_length": 50,
      "display_order": 1
    },
    {
      "segment_id": 2,
      "segment_name": "Account",
      "segment_type": "account",
      "oracle_segment_number": 2,
      "is_required": true,
      "has_hierarchy": true,
      "max_length": 50,
      "display_order": 2
    },
    {
      "segment_id": 3,
      "segment_name": "Project",
      "segment_type": "project",
      "oracle_segment_number": 3,
      "is_required": false,
      "has_hierarchy": true,
      "max_length": 50,
      "display_order": 3
    },
    {
      "segment_id": 4,
      "segment_name": "LineItem",
      "segment_type": "line_item",
      "oracle_segment_number": 4,
      "is_required": false,
      "has_hierarchy": false,
      "max_length": 30,
      "display_order": 4
    }
  ],
  "oracle_config": {
    "max_segments_supported": 30,
    "balance_report_segment_mapping": {
      "segment1": 1,
      "segment2": 2,
      "segment3": 3,
      "segment4": 4
    }
  }
}
```

---

## Phase 4: Setup Management Command

Create: `account_and_entitys/management/commands/setup_client.py`

```python
"""
Management command to setup client-specific segment configuration.
Usage:
    python manage.py setup_client --config-file config/segments_config.json
    python manage.py setup_client --interactive
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from account_and_entitys.models import XX_SegmentType
from account_and_entitys.managers.segment_manager import SegmentManager
import json
from pathlib import Path


class Command(BaseCommand):
    help = 'Setup client-specific segment configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--config-file',
            type=str,
            help='Path to segments_config.json file'
        )
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Run interactive setup wizard'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing configuration'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('  TNFEEZ DYNAMIC SEGMENT SETUP'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        # Check if configuration already exists
        existing_count = XX_SegmentType.objects.count()
        if existing_count > 0 and not options['overwrite']:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Found {existing_count} existing segment types.'
                )
            )
            confirm = input('Do you want to overwrite? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('❌ Setup cancelled'))
                return
        
        # Load configuration
        if options['interactive']:
            config = self.run_interactive_setup()
        elif options['config_file']:
            config = self.load_config_file(options['config_file'])
        else:
            # Try default location
            default_path = Path(settings.BASE_DIR) / 'config' / 'segments_config.json'
            if default_path.exists():
                config = self.load_config_file(str(default_path))
            else:
                raise CommandError(
                    'No configuration source provided. Use --config-file or --interactive'
                )
        
        # Create segment types
        self.create_segment_types(config)
        
        # Clear cache
        SegmentManager.clear_cache()
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('✅ CLIENT SETUP COMPLETE'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f"Client: {config['client_name']}")
        self.stdout.write(f"Segments configured: {len(config['segments'])}")
        self.stdout.write('\nSegment Types:')
        for seg in config['segments']:
            required = '✓' if seg['is_required'] else '○'
            hierarchy = '⬘' if seg['has_hierarchy'] else '-'
            self.stdout.write(
                f"  {required} {hierarchy} {seg['segment_name']} "
                f"(Oracle Segment {seg['oracle_segment_number']})"
            )
        
        self.stdout.write(self.style.SUCCESS('\n🚀 Next steps:'))
        self.stdout.write('  1. Run: python manage.py migrate')
        self.stdout.write('  2. Load segment data (entities, accounts, etc.)')
        self.stdout.write('  3. Optionally migrate from legacy models')
        self.stdout.write('     python manage.py migrate_legacy_segments\n')
    
    def load_config_file(self, file_path):
        """Load configuration from JSON file"""
        config_path = Path(file_path)
        
        if not config_path.exists():
            raise CommandError(f'Configuration file not found: {file_path}')
        
        self.stdout.write(f'📄 Loading configuration from: {file_path}')
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON in configuration file: {e}')
        
        # Validate configuration
        self.validate_config(config)
        
        return config
    
    def validate_config(self, config):
        """Validate configuration structure"""
        required_fields = ['client_name', 'segments']
        for field in required_fields:
            if field not in config:
                raise CommandError(f'Missing required field in config: {field}')
        
        if not config['segments']:
            raise CommandError('Configuration must have at least one segment')
        
        # Validate each segment
        for i, segment in enumerate(config['segments']):
            required_seg_fields = [
                'segment_id', 'segment_name', 'segment_type', 
                'oracle_segment_number', 'is_required', 'has_hierarchy'
            ]
            for field in required_seg_fields:
                if field not in segment:
                    raise CommandError(
                        f'Segment {i+1} missing required field: {field}'
                    )
    
    def run_interactive_setup(self):
        """Interactive CLI wizard for setup"""
        self.stdout.write(self.style.WARNING('\n🧙 INTERACTIVE SETUP WIZARD\n'))
        
        config = {
            'client_name': input('Enter client name: ').strip(),
            'client_id': input('Enter client ID (alphanumeric): ').strip().upper(),
            'segments': []
        }
        
        num_segments = 0
        while num_segments < 2 or num_segments > 30:
            try:
                num_segments = int(input('How many segments? (2-30): '))
            except ValueError:
                self.stdout.write(self.style.ERROR('Please enter a number'))
        
        for i in range(num_segments):
            self.stdout.write(f'\n--- Segment {i+1} ---')
            segment = {
                'segment_id': i + 1,
                'segment_name': input(f'  Name (e.g., Entity, Account, Project): ').strip(),
                'segment_type': input(f'  Type (cost_center, account, project, etc.): ').strip().lower(),
                'oracle_segment_number': i + 1,
                'is_required': input(f'  Required? (y/n): ').lower() == 'y',
                'has_hierarchy': input(f'  Has hierarchy? (y/n): ').lower() == 'y',
                'max_length': 50,
                'display_order': i + 1
            }
            config['segments'].append(segment)
        
        # Save configuration
        save_config = input('\nSave this configuration to file? (y/n): ').lower() == 'y'
        if save_config:
            filename = input('Filename (e.g., my_client_config.json): ').strip()
            config_path = Path(settings.BASE_DIR) / 'config' / filename
            config_path.parent.mkdir(exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            self.stdout.write(self.style.SUCCESS(f'💾 Configuration saved to: {config_path}'))
        
        return config
    
    def create_segment_types(self, config):
        """Create XX_SegmentType records from configuration"""
        self.stdout.write('\n📊 Creating segment types in database...\n')
        
        # Clear existing if overwriting
        if XX_SegmentType.objects.exists():
            deleted_count = XX_SegmentType.objects.all().delete()[0]
            self.stdout.write(
                self.style.WARNING(f'🗑️  Deleted {deleted_count} existing segment types')
            )
        
        created_count = 0
        for segment in config['segments']:
            seg_type = XX_SegmentType.objects.create(
                segment_id=segment['segment_id'],
                segment_name=segment['segment_name'],
                segment_type=segment['segment_type'],
                oracle_segment_number=segment['oracle_segment_number'],
                is_required=segment['is_required'],
                has_hierarchy=segment['has_hierarchy'],
                max_length=segment.get('max_length', 50),
                display_order=segment.get('display_order', segment['segment_id']),
                is_active=True
            )
            created_count += 1
            
            required_icon = '✓' if seg_type.is_required else '○'
            hierarchy_icon = '⬘' if seg_type.has_hierarchy else '-'
            self.stdout.write(
                f'  {required_icon} {hierarchy_icon} Created: {seg_type.segment_name} '
                f'(Oracle Segment {seg_type.oracle_segment_number})'
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Created {created_count} segment types')
        )
```

---

## Phase 5: Settings Configuration

Add to: `budget_transfer/settings.py`

```python
# ============================================
# DYNAMIC SEGMENTS CONFIGURATION
# ============================================

# Client-specific segment configuration
CLIENT_NAME = os.environ.get('CLIENT_NAME', 'Default Client')
CLIENT_ID = os.environ.get('CLIENT_ID', 'DEFAULT')

# Path to segment configuration file
SEGMENTS_CONFIG_FILE = os.path.join(BASE_DIR, 'config', 'segments_config.json')

# Load segment configuration at startup (optional)
def load_segments_config():
    """Load segments configuration from JSON file"""
    from pathlib import Path
    import json
    
    config_path = Path(SEGMENTS_CONFIG_FILE)
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return None

# Make config available globally
SEGMENTS_CONFIG = load_segments_config()
```

---

## Phase 6: Migration Scripts

Create: `account_and_entitys/management/commands/migrate_legacy_segments.py`

```python
"""
Migrate data from old hardcoded models (XX_Entity, XX_Account, XX_Project)
to new dynamic XX_Segment model.

Usage:
    python manage.py migrate_legacy_segments --dry-run
    python manage.py migrate_legacy_segments --execute
"""

from django.core.management.base import BaseCommand
from account_and_entitys.models import (
    XX_Entity, XX_Account, XX_Project,
    XX_SegmentType, XX_Segment
)
from account_and_entitys.managers.segment_manager import SegmentManager


class Command(BaseCommand):
    help = 'Migrate legacy segment data to dynamic segment system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Actually perform migration (default is dry-run)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without changing data'
        )
    
    def handle(self, *args, **options):
        is_dry_run = not options['execute']
        
        if is_dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No data will be changed\n'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ EXECUTE MODE - Migrating data\n'))
        
        # Check if segment types are configured
        if not XX_SegmentType.objects.exists():
            self.stdout.write(
                self.style.ERROR(
                    '❌ No segment types configured. Run setup_client first.'
                )
            )
            return
        
        # Migrate each legacy model
        migrations = [
            ('XX_Entity', 'Entity', XX_Entity),
            ('XX_Account', 'Account', XX_Account),
            ('XX_Project', 'Project', XX_Project),
        ]
        
        total_migrated = 0
        
        for model_name, segment_name, model_class in migrations:
            self.stdout.write(f'\n--- Migrating {model_name} to {segment_name} ---')
            
            # Get segment type
            try:
                segment_type = SegmentManager.get_segment_type_by_name(segment_name)
                if not segment_type:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠️  Segment type "{segment_name}" not configured, skipping {model_name}'
                        )
                    )
                    continue
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error getting segment type: {e}')
                )
                continue
            
            # Count records
            legacy_count = model_class.objects.count()
            self.stdout.write(f'Found {legacy_count} records in {model_name}')
            
            if legacy_count == 0:
                self.stdout.write(self.style.WARNING('No records to migrate'))
                continue
            
            # Migrate records
            migrated_count = 0
            skipped_count = 0
            
            for legacy_record in model_class.objects.all():
                # Extract code based on model
                if model_name == 'XX_Entity':
                    code = legacy_record.entity
                elif model_name == 'XX_Account':
                    code = legacy_record.account
                else:  # XX_Project
                    code = legacy_record.project
                
                if not is_dry_run:
                    try:
                        XX_Segment.objects.get_or_create(
                            segment_type=segment_type,
                            code=code,
                            defaults={
                                'parent_code': legacy_record.parent,
                                'alias': legacy_record.alias_default,
                                'is_active': True,
                                'level': 0  # Calculate level if needed
                            }
                        )
                        migrated_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'❌ Error migrating {code}: {e}')
                        )
                        skipped_count += 1
                else:
                    # Dry run - just count
                    migrated_count += 1
                    if migrated_count <= 5:  # Show first 5 examples
                        self.stdout.write(
                            f'  Would migrate: {code} (parent: {legacy_record.parent}, '
                            f'alias: {legacy_record.alias_default})'
                        )
            
            if migrated_count > 5:
                self.stdout.write(f'  ... and {migrated_count - 5} more')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ {"Would migrate" if is_dry_run else "Migrated"} '
                    f'{migrated_count} records'
                )
            )
            
            if skipped_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Skipped {skipped_count} records due to errors')
                )
            
            total_migrated += migrated_count
        
        # Summary
        self.stdout.write('\n' + '='*60)
        if is_dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'🔍 DRY RUN COMPLETE - Would migrate {total_migrated} total records'
                )
            )
            self.stdout.write('\nRun with --execute to perform actual migration')
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ MIGRATION COMPLETE - Migrated {total_migrated} total records'
                )
            )
        self.stdout.write('='*60 + '\n')
```

---

## Next Document: Phase 7 - API & View Updates

This implementation guide covers the foundational changes. The next document will cover:
- API endpoint modifications
- Serializer updates
- View logic changes
- Oracle integration updates

Would you like me to continue with the next phase?
