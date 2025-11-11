# Dynamic Segments Architecture - Multi-Client Support

## Executive Summary

This document outlines the architecture for transforming the Tnfeez Budget Transfer System from a **hardcoded 3-segment system** (Entity, Account, Project) into a **fully dynamic multi-segment system** that can be configured per client during installation.

---

## Current State Analysis

### Hardcoded Segments (Current)
The system currently has **3 fixed segments**:
1. **Entity** (Cost Center) - `XX_Entity` model
2. **Account** - `XX_Account` model  
3. **Project** - `XX_Project` model

### Problem Statement
- **Fixed database schema**: Models hardcode `cost_center_code`, `account_code`, `project_code`
- **Fixed Oracle integration**: Balance reports hardcode `segment1`, `segment2`, `segment3`
- **No flexibility**: Cannot support clients with 2, 4, or 5 segments
- **Maintenance nightmare**: Each new client requires code changes

---

## Proposed Solution: Dynamic Segment System

### Core Concept
Replace hardcoded segment models with a **single generic segment model** that can represent ANY segment type, configured at installation time via a **client configuration file**.

### Architecture Layers

```
┌─────────────────────────────────────────────────┐
│  LAYER 1: CLIENT CONFIGURATION (Installation)   │
│  - segments_config.json                         │
│  - Defines segment types, count, names          │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  LAYER 2: GENERIC DATABASE MODELS               │
│  - XX_Segment (replaces XX_Entity/Account/Proj) │
│  - XX_SegmentType (metadata)                    │
│  - XX_TransactionSegment (links transactions)   │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  LAYER 3: DYNAMIC BUSINESS LOGIC                │
│  - SegmentManager (replaces EnvelopeManager)    │
│  - Dynamic validation rules                     │
│  - Dynamic Oracle mapping                       │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  LAYER 4: ORACLE INTEGRATION                    │
│  - Dynamic FBDI template generation             │
│  - Dynamic balance report parsing               │
│  - Configurable segment-to-column mapping       │
└─────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Configuration Layer
**Goal**: Define client segments at installation

**New File**: `config/segments_config.json`
```json
{
  "client_id": "CLIENT_XYZ",
  "client_name": "XYZ Corporation",
  "segments": [
    {
      "segment_id": 1,
      "segment_name": "Entity",
      "segment_type": "cost_center",
      "oracle_segment_number": 1,
      "is_required": true,
      "has_hierarchy": true,
      "max_length": 50
    },
    {
      "segment_id": 2,
      "segment_name": "Account",
      "segment_type": "account",
      "oracle_segment_number": 2,
      "is_required": true,
      "has_hierarchy": true,
      "max_length": 50
    },
    {
      "segment_id": 3,
      "segment_name": "Project",
      "segment_type": "project",
      "oracle_segment_number": 3,
      "is_required": false,
      "has_hierarchy": true,
      "max_length": 50
    },
    {
      "segment_id": 4,
      "segment_name": "LineItem",
      "segment_type": "line_item",
      "oracle_segment_number": 4,
      "is_required": false,
      "has_hierarchy": false,
      "max_length": 30
    }
  ],
  "oracle_config": {
    "max_segments": 30,
    "balance_report_segment_mapping": {
      "segment1": 1,
      "segment2": 2,
      "segment3": 3,
      "segment4": 4
    }
  }
}
```

### Phase 2: Generic Database Models
**Goal**: Replace hardcoded models with dynamic ones

**New Models** (in `account_and_entitys/models.py`):

```python
class XX_SegmentType(models.Model):
    """Defines segment types for this client installation"""
    segment_id = models.IntegerField(primary_key=True)
    segment_name = models.CharField(max_length=50)  # "Entity", "Account", etc.
    segment_type = models.CharField(max_length=50)  # "cost_center", "account", etc.
    oracle_segment_number = models.IntegerField()
    is_required = models.BooleanField(default=True)
    has_hierarchy = models.BooleanField(default=False)
    max_length = models.IntegerField(default=50)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = "XX_SEGMENT_TYPE_XX"

class XX_Segment(models.Model):
    """Generic segment value (replaces XX_Entity, XX_Account, XX_Project)"""
    id = models.AutoField(primary_key=True)
    segment_type = models.ForeignKey(XX_SegmentType, on_delete=models.CASCADE)
    code = models.CharField(max_length=50)  # The actual segment value
    parent_code = models.CharField(max_length=50, null=True, blank=True)
    alias = models.CharField(max_length=255, null=True, blank=True)
    level = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = "XX_SEGMENT_XX"
        unique_together = ("segment_type", "code")
        indexes = [
            models.Index(fields=["segment_type", "code"]),
            models.Index(fields=["segment_type", "parent_code"]),
        ]

class XX_TransactionSegment(models.Model):
    """Links transaction transfers to their segment values"""
    transaction_transfer = models.ForeignKey(
        'transaction.xx_TransactionTransfer', 
        on_delete=models.CASCADE,
        related_name='segments'
    )
    segment_type = models.ForeignKey(XX_SegmentType, on_delete=models.CASCADE)
    segment_value = models.ForeignKey(XX_Segment, on_delete=models.CASCADE)
    
    class Meta:
        db_table = "XX_TRANSACTION_SEGMENT_XX"
        unique_together = ("transaction_transfer", "segment_type")
```

### Phase 3: Migration Strategy
**Goal**: Migrate existing data without breaking the system

**Strategy**: Dual-mode operation during transition

1. **Keep old models** (`XX_Entity`, `XX_Account`, `XX_Project`) for backward compatibility
2. **Add new models** (`XX_Segment`, `XX_SegmentType`)
3. **Create data migration** to populate new tables from old ones
4. **Use feature flag** to switch between old/new system

**Migration Script**: `account_and_entitys/migrations/0XXX_migrate_to_dynamic_segments.py`

```python
from django.db import migrations
from django.conf import settings

def migrate_segments_forward(apps, schema_editor):
    """Migrate from old hardcoded models to new dynamic models"""
    XX_SegmentType = apps.get_model('account_and_entitys', 'XX_SegmentType')
    XX_Segment = apps.get_model('account_and_entitys', 'XX_Segment')
    XX_Entity = apps.get_model('account_and_entitys', 'XX_Entity')
    XX_Account = apps.get_model('account_and_entitys', 'XX_Account')
    XX_Project = apps.get_model('account_and_entitys', 'XX_Project')
    
    # Create segment types from config
    entity_type = XX_SegmentType.objects.create(
        segment_id=1,
        segment_name="Entity",
        segment_type="cost_center",
        oracle_segment_number=1,
        is_required=True,
        has_hierarchy=True
    )
    
    # Migrate XX_Entity records to XX_Segment
    for entity in XX_Entity.objects.all():
        XX_Segment.objects.create(
            segment_type=entity_type,
            code=entity.entity,
            parent_code=entity.parent,
            alias=entity.alias_default
        )
    
    # Repeat for accounts and projects...

class Migration(migrations.Migration):
    dependencies = [
        ('account_and_entitys', '0XXX_previous_migration'),
    ]
    
    operations = [
        migrations.RunPython(migrate_segments_forward),
    ]
```

### Phase 4: Dynamic Business Logic
**Goal**: Replace hardcoded logic with configuration-driven logic

**New Manager**: `account_and_entitys/managers/segment_manager.py`

```python
class SegmentManager:
    """Replaces EnvelopeManager with dynamic segment handling"""
    
    @staticmethod
    def get_segment_config():
        """Load segment configuration from settings"""
        return settings.SEGMENTS_CONFIG
    
    @staticmethod
    def get_segment_types():
        """Get all configured segment types for this client"""
        return XX_SegmentType.objects.all().order_by('display_order')
    
    @staticmethod
    def get_segment_by_type(segment_type_name):
        """Get segment type by name (e.g., 'Entity', 'Account')"""
        return XX_SegmentType.objects.get(segment_name=segment_type_name)
    
    @staticmethod
    def get_all_children(segment_type, parent_code, visited=None):
        """Get all descendants of a segment (hierarchical)"""
        if visited is None:
            visited = set()
        if parent_code in visited:
            return []
        visited.add(parent_code)
        
        segments = XX_Segment.objects.filter(
            segment_type=segment_type,
            parent_code=parent_code
        )
        
        result = []
        for segment in segments:
            result.append(segment.code)
            result.extend(
                SegmentManager.get_all_children(
                    segment_type, segment.code, visited
                )
            )
        return result
    
    @staticmethod
    def validate_transaction_segments(transaction_data):
        """Validate that all required segments are present"""
        required_types = XX_SegmentType.objects.filter(is_required=True)
        
        for seg_type in required_types:
            if seg_type.segment_name not in transaction_data:
                raise ValueError(
                    f"Required segment '{seg_type.segment_name}' is missing"
                )
```

### Phase 5: Dynamic Oracle Integration
**Goal**: Generate FBDI files based on client configuration

**Updated**: `test_upload_fbdi/journal_template_manager.py`

```python
def create_dynamic_journal_data(transaction, segment_config):
    """Generate journal entries with dynamic segment columns"""
    
    segments = segment_config['segments']
    journal_entry = {
        'STATUS': 'NEW',
        'LEDGER_ID': settings.FUSION_LEDGER_ID,
        'DATE_CREATED': transaction.request_date,
        # ... other fixed fields
    }
    
    # Dynamically add segment columns based on config
    for segment in segments:
        oracle_col = f"SEGMENT{segment['oracle_segment_number']}"
        segment_value = get_transaction_segment_value(
            transaction, 
            segment['segment_name']
        )
        journal_entry[oracle_col] = segment_value
    
    # Fill unused segments with NULL
    for i in range(len(segments) + 1, 31):  # Oracle supports up to 30 segments
        journal_entry[f"SEGMENT{i}"] = None
    
    return journal_entry
```

**Updated**: `account_and_entitys/utils.py` (Balance Report Parsing)

```python
def parse_balance_report_dynamic(excel_file):
    """Parse balance report with dynamic segment mapping"""
    
    segment_config = SegmentManager.get_segment_config()
    segment_mapping = segment_config['oracle_config']['balance_report_segment_mapping']
    
    df = pd.read_excel(excel_file, sheet_name='Report', skiprows=2)
    
    for _, row in df.iterrows():
        balance_record = {
            'control_budget_name': row['Control Budget Name'],
            'ledger_name': row['Ledger Name'],
            'as_of_period': row['As of Period'],
        }
        
        # Dynamically map segments based on config
        for oracle_col, segment_id in segment_mapping.items():
            if oracle_col in row:
                balance_record[f'segment_{segment_id}'] = row[oracle_col]
        
        # Store in dynamic table
        XX_DynamicBalanceReport.objects.create(**balance_record)
```

### Phase 6: Setup Script for Installation
**Goal**: Automated client-specific setup on first installation

**New File**: `management/commands/setup_client.py`

```python
from django.core.management.base import BaseCommand
from django.conf import settings
import json
from pathlib import Path

class Command(BaseCommand):
    help = 'Setup client-specific segment configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--config-file',
            type=str,
            help='Path to segments_config.json'
        )
        parser.add_argument(
            '--client-name',
            type=str,
            help='Client name for interactive setup'
        )
    
    def handle(self, *args, **options):
        if options['config_file']:
            # Load from JSON file
            config_path = Path(options['config_file'])
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            # Interactive setup
            config = self.interactive_setup(options['client_name'])
        
        # Create segment types in database
        self.create_segment_types(config)
        
        # Update Django settings
        self.update_settings(config)
        
        # Run migrations
        self.run_migrations()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Client setup complete for {config['client_name']}"
            )
        )
    
    def interactive_setup(self, client_name):
        """Interactive CLI to build configuration"""
        config = {
            'client_name': client_name,
            'segments': []
        }
        
        self.stdout.write("\n🔧 Interactive Segment Configuration\n")
        
        num_segments = int(input("How many segments does this client use? "))
        
        for i in range(num_segments):
            self.stdout.write(f"\n--- Segment {i+1} ---")
            segment = {
                'segment_id': i + 1,
                'segment_name': input("Segment name (e.g., Entity, Account): "),
                'segment_type': input("Segment type (cost_center, account, etc.): "),
                'oracle_segment_number': i + 1,
                'is_required': input("Required? (y/n): ").lower() == 'y',
                'has_hierarchy': input("Has hierarchy? (y/n): ").lower() == 'y',
            }
            config['segments'].append(segment)
        
        return config
    
    def create_segment_types(self, config):
        """Populate XX_SegmentType table"""
        from account_and_entitys.models import XX_SegmentType
        
        XX_SegmentType.objects.all().delete()  # Clear existing
        
        for segment in config['segments']:
            XX_SegmentType.objects.create(
                segment_id=segment['segment_id'],
                segment_name=segment['segment_name'],
                segment_type=segment['segment_type'],
                oracle_segment_number=segment['oracle_segment_number'],
                is_required=segment['is_required'],
                has_hierarchy=segment['has_hierarchy']
            )
```

### Phase 7: UI/API Adjustments
**Goal**: Frontend must dynamically render fields

**API Changes** (`account_and_entitys/views.py`):

```python
class SegmentConfigViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint to get client's segment configuration"""
    queryset = XX_SegmentType.objects.all()
    serializer_class = SegmentTypeSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def client_config(self, request):
        """Return full segment configuration for frontend"""
        segment_types = XX_SegmentType.objects.all().order_by('display_order')
        serializer = self.get_serializer(segment_types, many=True)
        
        return Response({
            'segments': serializer.data,
            'client_name': settings.CLIENT_NAME,
            'total_segments': segment_types.count()
        })
```

**Frontend Adaptation** (React/Vue example):
```javascript
// Fetch segment config on app load
const segmentConfig = await api.get('/api/segments/client_config/');

// Dynamically render form fields
segmentConfig.segments.forEach(segment => {
  if (segment.is_required) {
    formFields.push({
      name: segment.segment_name,
      type: segment.has_hierarchy ? 'hierarchical-select' : 'text',
      label: segment.segment_name,
      required: true
    });
  }
});
```

---

## Files Requiring Modification

### High Priority (Core Models)
| File Path | Change Type | Reason |
|-----------|-------------|---------|
| `account_and_entitys/models.py` | **Major Refactor** | Add `XX_Segment`, `XX_SegmentType`, `XX_TransactionSegment` |
| `transaction/models.py` | **Major Refactor** | Replace `cost_center_code`, `account_code`, `project_code` with FK to `XX_TransactionSegment` |
| `budget_management/models.py` | **Medium Refactor** | Update functions like `get_entities_with_children` to use `SegmentManager` |

### Medium Priority (Business Logic)
| File Path | Change Type | Reason |
|-----------|-------------|---------|
| `account_and_entitys/managers/segment_manager.py` | **New File** | Replaces `EnvelopeManager` with dynamic logic |
| `budget_management/views.py` | **Medium Refactor** | Update `DashBoard_filler_per_Project` to use dynamic segments |
| `transaction/views.py` | **Medium Refactor** | Update transaction creation to handle dynamic segments |
| `user_management/models.py` | **Minor Refactor** | Update `UserProjects` / `UserAbilities` to reference generic segments |

### Low Priority (Oracle Integration)
| File Path | Change Type | Reason |
|-----------|-------------|---------|
| `test_upload_fbdi/journal_template_manager.py` | **Medium Refactor** | Generate GL_INTERFACE with dynamic segment columns |
| `test_upload_fbdi/budget_template_manager.py` | **Medium Refactor** | Generate XCC_BUDGET_INTERFACE with dynamic segments |
| `account_and_entitys/utils.py` | **Medium Refactor** | Parse balance reports with dynamic segment mapping |
| `public_funtion/update_pivot_fund.py` | **Minor Refactor** | Update to query dynamic segments |

---

## Database Schema Changes

### New Tables
```sql
-- Segment configuration metadata
CREATE TABLE XX_SEGMENT_TYPE_XX (
    segment_id INTEGER PRIMARY KEY,
    segment_name VARCHAR(50) NOT NULL,
    segment_type VARCHAR(50) NOT NULL,
    oracle_segment_number INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT TRUE,
    has_hierarchy BOOLEAN DEFAULT FALSE,
    max_length INTEGER DEFAULT 50,
    display_order INTEGER DEFAULT 0
);

-- Generic segment values
CREATE TABLE XX_SEGMENT_XX (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    segment_type_id INTEGER NOT NULL,
    code VARCHAR(50) NOT NULL,
    parent_code VARCHAR(50),
    alias VARCHAR(255),
    level INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (segment_type_id) REFERENCES XX_SEGMENT_TYPE_XX(segment_id),
    UNIQUE (segment_type_id, code)
);

-- Link transactions to segment values
CREATE TABLE XX_TRANSACTION_SEGMENT_XX (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_transfer_id INTEGER NOT NULL,
    segment_type_id INTEGER NOT NULL,
    segment_value_id INTEGER NOT NULL,
    FOREIGN KEY (transaction_transfer_id) REFERENCES XX_TRANSACTION_TRANSFER_XX(transfer_id),
    FOREIGN KEY (segment_type_id) REFERENCES XX_SEGMENT_TYPE_XX(segment_id),
    FOREIGN KEY (segment_value_id) REFERENCES XX_SEGMENT_XX(id),
    UNIQUE (transaction_transfer_id, segment_type_id)
);

-- Dynamic balance report storage
CREATE TABLE XX_DYNAMIC_BALANCE_REPORT_XX (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    control_budget_name VARCHAR(100),
    ledger_name VARCHAR(100),
    as_of_period VARCHAR(20),
    -- Dynamic segment values stored as JSON
    segment_values TEXT,  -- JSON: {"1": "12345", "2": "67890", ...}
    encumbrance_ytd DECIMAL(20,2),
    other_ytd DECIMAL(20,2),
    actual_ytd DECIMAL(20,2),
    funds_available_asof DECIMAL(20,2),
    budget_ytd DECIMAL(20,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Deprecated Tables (Keep for backward compatibility)
- `XX_ENTITY_XX` → Migrate to `XX_SEGMENT_XX` where `segment_type_id = 1`
- `XX_ACCOUNT_XX` → Migrate to `XX_SEGMENT_XX` where `segment_type_id = 2`
- `XX_PROJECT_XX` → Migrate to `XX_SEGMENT_XX` where `segment_type_id = 3`

---

## Deployment Strategy

### Installation Workflow for New Client

```bash
# Step 1: Clone repository
git clone <repo_url>
cd Tnfeez_dynamic

# Step 2: Install dependencies
pip install -r requirements.txt

# Step 3: Run client setup (interactive)
python manage.py setup_client --client-name "ABC Corporation"

# OR with pre-configured JSON
python manage.py setup_client --config-file config/abc_segments.json

# Step 4: Run migrations
python manage.py migrate

# Step 5: Load client-specific master data
python manage.py load_client_data --data-file data/abc_segments.xlsx

# Step 6: Create superuser
python manage.py createsuperuser

# Step 7: Start server
python manage.py runserver
```

### Validation Steps
1. **Check segment types**: `python manage.py shell` → `XX_SegmentType.objects.all()`
2. **Test transaction creation**: Create a test budget transfer via API
3. **Test Oracle upload**: Run `python test_upload_fbdi/upload_soap_fbdi.py`
4. **Verify balance report**: Download and parse Oracle balance report

---

## Risk Mitigation

### Risk 1: Data Migration Failure
**Mitigation**: 
- Keep old tables for 2 releases
- Implement dual-write pattern during transition
- Create rollback script

### Risk 2: Oracle Integration Breaks
**Mitigation**:
- Test with Oracle sandbox first
- Validate FBDI CSV format matches interface loader expectations
- Keep existing Oracle utility functions as fallback

### Risk 3: Frontend Compatibility
**Mitigation**:
- API versioning (v1 = old, v2 = dynamic)
- Gradual migration with feature flags
- Backward-compatible serializers

---

## Testing Strategy

### Unit Tests
```python
# tests/test_segment_manager.py
class SegmentManagerTests(TestCase):
    def test_get_all_children_with_4_segments(self):
        """Test hierarchy traversal with 4-segment client"""
        # Setup: Create test segments
        # Assert: All descendants returned
    
    def test_validate_transaction_missing_required_segment(self):
        """Test validation fails when required segment is missing"""
        # Setup: Config with 3 required segments
        # Assert: ValidationError raised if 2 provided
```

### Integration Tests
```python
# tests/test_oracle_integration.py
class OracleIntegrationTests(TestCase):
    def test_generate_journal_with_5_segments(self):
        """Test FBDI generation for client with 5 segments"""
        # Setup: Config with 5 segments
        # Assert: GL_INTERFACE has SEGMENT1-5 populated, SEGMENT6-30 NULL
```

---

## Performance Considerations

### Query Optimization
- **Before** (3 JOINs):
  ```sql
  SELECT * FROM XX_BUDGET_TRANSFER_XX bt
  JOIN XX_TRANSACTION_TRANSFER_XX tt ON bt.transaction_id = tt.transaction_id
  JOIN XX_Entity_XX e ON tt.cost_center_code = e.id
  JOIN XX_Account_XX a ON tt.account_code = a.id
  JOIN XX_Project_XX p ON tt.project_code = p.id
  ```

- **After** (single JOIN with dynamic segments):
  ```sql
  SELECT * FROM XX_BUDGET_TRANSFER_XX bt
  JOIN XX_TRANSACTION_TRANSFER_XX tt ON bt.transaction_id = tt.transaction_id
  JOIN XX_TRANSACTION_SEGMENT_XX ts ON tt.transfer_id = ts.transaction_transfer_id
  JOIN XX_SEGMENT_XX s ON ts.segment_value_id = s.id
  WHERE ts.segment_type_id IN (1, 2, 3)
  ```

### Caching Strategy
```python
from django.core.cache import cache

def get_segment_config_cached():
    """Cache segment configuration for 1 hour"""
    config = cache.get('segment_config')
    if config is None:
        config = XX_SegmentType.objects.all()
        cache.set('segment_config', config, 3600)
    return config
```

---

## Success Criteria

### Phase 1 Success Metrics
- ✅ Configuration file loads without errors
- ✅ Segment types created in database
- ✅ Django settings updated

### Phase 2 Success Metrics
- ✅ All models migrated to new schema
- ✅ Data migration completes without loss
- ✅ Old models still functional (backward compatibility)

### Phase 3 Success Metrics
- ✅ Can create transactions with 2, 3, 4, or 5 segments
- ✅ Hierarchical queries work for all segment types
- ✅ Validation enforces required segments

### Phase 4 Success Metrics
- ✅ FBDI files generated with correct segment columns
- ✅ Oracle import succeeds
- ✅ Balance reports parsed correctly

### Final Acceptance Criteria
- ✅ System supports 2-30 segments (Oracle limit)
- ✅ No hardcoded segment references in codebase
- ✅ Installation takes < 15 minutes
- ✅ Zero downtime migration for existing clients

---

## Timeline Estimate

| Phase | Duration | Effort (Hours) |
|-------|----------|----------------|
| Phase 1: Configuration Layer | 1 week | 20 |
| Phase 2: Database Models | 2 weeks | 40 |
| Phase 3: Business Logic | 3 weeks | 60 |
| Phase 4: Oracle Integration | 2 weeks | 40 |
| Phase 5: Setup Scripts | 1 week | 20 |
| Phase 6: API/UI Updates | 2 weeks | 40 |
| Phase 7: Testing | 2 weeks | 40 |
| **Total** | **13 weeks** | **260 hours** |

---

## Next Steps

1. **Review this document** with the team
2. **Create Phase 1 implementation ticket**
3. **Set up development environment** with test clients
4. **Build PoC** with 2-segment vs 5-segment configurations
5. **Get Oracle sandbox access** for testing

---

## Appendix A: Example Configurations

### Client A (2 Segments)
```json
{
  "client_name": "Simple Corp",
  "segments": [
    {"segment_id": 1, "segment_name": "Entity", "oracle_segment_number": 1},
    {"segment_id": 2, "segment_name": "Account", "oracle_segment_number": 2}
  ]
}
```

### Client B (5 Segments)
```json
{
  "client_name": "Complex Corp",
  "segments": [
    {"segment_id": 1, "segment_name": "Entity", "oracle_segment_number": 1},
    {"segment_id": 2, "segment_name": "Account", "oracle_segment_number": 2},
    {"segment_id": 3, "segment_name": "Project", "oracle_segment_number": 3},
    {"segment_id": 4, "segment_name": "LineItem", "oracle_segment_number": 4},
    {"segment_id": 5, "segment_name": "Department", "oracle_segment_number": 5}
  ]
}
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-05  
**Author**: GitHub Copilot  
**Status**: DRAFT - Awaiting Review
