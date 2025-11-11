# Oracle Integration Updates - Dynamic Segments

## Overview
This document details how to update Oracle Fusion integration (FBDI uploads and balance reports) to work with dynamic segments.

---

## Part 1: Dynamic Journal Template Manager

### File: `test_upload_fbdi/journal_template_manager.py`

Update the `create_sample_journal_data()` function:

```python
import pandas as pd
import openpyxl
from openpyxl import load_workbook
import shutil
from pathlib import Path
import time
from typing import Dict, List, Any
from account_and_entitys.managers.segment_manager import SegmentManager
from account_and_entitys.models import XX_SegmentType


def create_sample_journal_data_dynamic(
    transaction_transfer,
    ledger_id,
    data_access_set_id,
    je_category="Adjustment",
    je_source="Manual"
):
    """
    Create journal entry data with DYNAMIC segment columns.
    Works with any number of segments (2-30).
    
    Args:
        transaction_transfer: xx_TransactionTransfer object
        ledger_id: Oracle Ledger ID
        data_access_set_id: Oracle DAS ID
        je_category: Journal entry category
        je_source: Journal entry source
    
    Returns:
        List of dicts with GL_INTERFACE format
    """
    from datetime import datetime
    from account_and_entitys.models import XX_TransactionSegment
    
    # Get client's segment configuration
    segment_types = SegmentManager.get_all_segment_types()
    
    # Get segment values for this transaction
    transaction_segments = XX_TransactionSegment.objects.filter(
        transaction_transfer=transaction_transfer
    ).select_related('segment_type', 'segment_value', 'from_segment_value', 'to_segment_value')
    
    # Build segment value map
    segment_map = {}
    from_segment_map = {}
    to_segment_map = {}
    
    for ts in transaction_segments:
        oracle_seg_num = ts.segment_type.oracle_segment_number
        segment_map[oracle_seg_num] = ts.segment_value.code
        
        if ts.from_segment_value:
            from_segment_map[oracle_seg_num] = ts.from_segment_value.code
        if ts.to_segment_value:
            to_segment_map[oracle_seg_num] = ts.to_segment_value.code
    
    # Get transaction details
    budget_transfer = transaction_transfer.transaction
    amount = float(transaction_transfer.from_center or 0)
    
    # Generate unique batch and header names
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    batch_name = f"BATCH_{budget_transfer.transaction_id}_{timestamp}"
    journal_name = f"JE_{budget_transfer.transaction_id}_{timestamp}"
    
    # Create journal entries (debit and credit lines)
    journal_lines = []
    
    # Helper function to build a line with dynamic segments
    def build_journal_line(line_number, account_type, amount_value, segment_values):
        """Build a single journal line with dynamic segment columns"""
        line = {
            'STATUS': 'NEW',
            'LEDGER_ID': ledger_id,
            'DATA_ACCESS_SET_ID': data_access_set_id,
            'DATE_CREATED': datetime.now().strftime("%Y-%m-%d"),
            'CREATED_BY': budget_transfer.requested_by or 'SYSTEM',
            'ACTUAL_FLAG': 'A',
            'USER_JE_CATEGORY_NAME': je_category,
            'USER_JE_SOURCE_NAME': je_source,
            'CURRENCY_CODE': 'SAR',
            'BATCH_NAME': batch_name,
            'JOURNAL_NAME': journal_name,
            'LINE_NUMBER': line_number,
            'ENTERED_DR': amount_value if account_type == 'DR' else None,
            'ENTERED_CR': amount_value if account_type == 'CR' else None,
            'ACCOUNTED_DR': amount_value if account_type == 'DR' else None,
            'ACCOUNTED_CR': amount_value if account_type == 'CR' else None,
        }
        
        # Add dynamic segments (SEGMENT1 through SEGMENT30)
        for seg_num in range(1, 31):
            segment_key = f'SEGMENT{seg_num}'
            if seg_num in segment_values:
                line[segment_key] = segment_values[seg_num]
            else:
                line[segment_key] = None  # Oracle requires NULL for unused segments
        
        return line
    
    # Line 1: Debit (from source)
    journal_lines.append(
        build_journal_line(1, 'DR', amount, from_segment_map if from_segment_map else segment_map)
    )
    
    # Line 2: Credit (to destination)
    journal_lines.append(
        build_journal_line(2, 'CR', amount, to_segment_map if to_segment_map else segment_map)
    )
    
    return journal_lines


def fill_journal_template_dynamic(
    template_path: str,
    transaction_transfers: List,
    ledger_id: str,
    data_access_set_id: str,
    output_path: str = None,
    auto_zip: bool = False
) -> str:
    """
    Fill journal template with data from multiple transactions.
    Automatically adapts to client's segment configuration.
    
    Args:
        template_path: Path to JournalImportTemplate.xlsm
        transaction_transfers: List of xx_TransactionTransfer objects
        ledger_id: Oracle Ledger ID
        data_access_set_id: Oracle DAS ID
        output_path: Output file path (optional)
        auto_zip: Whether to create ZIP file
    
    Returns:
        Path to filled template (or ZIP if auto_zip=True)
    """
    template_file = Path(template_path)
    
    if not template_file.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    # Generate output path if not provided
    if output_path is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = template_file.parent / f"JournalImport_Dynamic_{timestamp}.xlsm"
    else:
        output_path = Path(output_path)
    
    # Create a copy for filling
    shutil.copy2(template_file, output_path)
    
    # Open the workbook
    wb = load_workbook(output_path)
    gl_sheet = wb["GL_INTERFACE"]
    
    # Clear existing data (keep header row 4)
    if gl_sheet.max_row > 4:
        gl_sheet.delete_rows(5, gl_sheet.max_row - 4)
    
    # Generate journal data for all transactions
    all_journal_lines = []
    for transfer in transaction_transfers:
        lines = create_sample_journal_data_dynamic(
            transfer,
            ledger_id,
            data_access_set_id
        )
        all_journal_lines.extend(lines)
    
    # Write data to sheet (starting at row 5)
    current_row = 5
    
    # Get header mapping from row 4
    headers = []
    for col in range(1, gl_sheet.max_column + 1):
        header_cell = gl_sheet.cell(row=4, column=col)
        headers.append(header_cell.value)
    
    # Write each journal line
    for journal_line in all_journal_lines:
        for col_idx, header in enumerate(headers, start=1):
            if header in journal_line:
                gl_sheet.cell(row=current_row, column=col_idx, value=journal_line[header])
        current_row += 1
    
    # Save workbook
    wb.save(output_path)
    wb.close()
    
    print(f"✅ Created journal template with {len(all_journal_lines)} lines: {output_path}")
    
    # Optionally create ZIP
    if auto_zip:
        from test_upload_fbdi.zip_fbdi import excel_to_csv_and_zip
        zip_path = excel_to_csv_and_zip(str(output_path))
        print(f"📦 Created ZIP file: {zip_path}")
        return zip_path
    
    return str(output_path)
```

---

## Part 2: Dynamic Budget Template Manager

### File: `test_upload_fbdi/budget_template_manager.py`

Update budget import functions:

```python
def create_sample_budget_data_dynamic(
    transaction_transfer,
    ledger_id,
    budget_version_id="ORIGINAL",
    period_name="FY25-01"
):
    """
    Create budget entry data with DYNAMIC segments.
    
    Args:
        transaction_transfer: xx_TransactionTransfer object
        ledger_id: Oracle Ledger ID
        budget_version_id: Budget version
        period_name: Period name (e.g., FY25-01)
    
    Returns:
        List of dicts with XCC_BUDGET_INTERFACE format
    """
    from datetime import datetime
    from account_and_entitys.models import XX_TransactionSegment
    from account_and_entitys.managers.segment_manager import SegmentManager
    
    # Get segment configuration
    segment_types = SegmentManager.get_all_segment_types()
    
    # Get segment values for this transaction
    transaction_segments = XX_TransactionSegment.objects.filter(
        transaction_transfer=transaction_transfer
    ).select_related('segment_type', 'segment_value')
    
    # Build segment value map
    segment_map = {}
    for ts in transaction_segments:
        oracle_seg_num = ts.segment_type.oracle_segment_number
        segment_map[oracle_seg_num] = ts.segment_value.code
    
    # Get transaction details
    budget_transfer = transaction_transfer.transaction
    amount = float(transaction_transfer.from_center or 0)
    
    # Create budget entry
    budget_entry = {
        'LEDGER_ID': ledger_id,
        'BUDGET_VERSION_ID': budget_version_id,
        'PERIOD_NAME': period_name,
        'CURRENCY_CODE': 'SAR',
        'AMOUNT': amount,
        'STATUS': 'NEW',
        'CREATED_BY': budget_transfer.requested_by or 'SYSTEM',
        'DATE_CREATED': datetime.now().strftime("%Y-%m-%d"),
    }
    
    # Add dynamic segments (SEGMENT1 through SEGMENT30)
    for seg_num in range(1, 31):
        segment_key = f'SEGMENT{seg_num}'
        if seg_num in segment_map:
            budget_entry[segment_key] = segment_map[seg_num]
        else:
            budget_entry[segment_key] = None
    
    return [budget_entry]


def fill_budget_template_dynamic(
    template_path: str,
    transaction_transfers: List,
    ledger_id: str,
    budget_version_id: str = "ORIGINAL",
    period_name: str = "FY25-01",
    output_path: str = None,
    auto_zip: bool = False
) -> str:
    """
    Fill budget template with dynamic segment data.
    
    Similar structure to journal template manager.
    """
    template_file = Path(template_path)
    
    if not template_file.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    # Generate output path
    if output_path is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = template_file.parent / f"BudgetImport_Dynamic_{timestamp}.xlsm"
    else:
        output_path = Path(output_path)
    
    # Copy template
    shutil.copy2(template_file, output_path)
    
    # Open workbook
    wb = load_workbook(output_path)
    budget_sheet = wb["XCC_BUDGET_INTERFACE"]
    
    # Clear existing data
    if budget_sheet.max_row > 4:
        budget_sheet.delete_rows(5, budget_sheet.max_row - 4)
    
    # Generate budget data
    all_budget_lines = []
    for transfer in transaction_transfers:
        lines = create_sample_budget_data_dynamic(
            transfer,
            ledger_id,
            budget_version_id,
            period_name
        )
        all_budget_lines.extend(lines)
    
    # Write to sheet (starting at row 5)
    current_row = 5
    
    # Get headers from row 4
    headers = []
    for col in range(1, budget_sheet.max_column + 1):
        header_cell = budget_sheet.cell(row=4, column=col)
        headers.append(header_cell.value)
    
    # Write budget lines
    for budget_line in all_budget_lines:
        for col_idx, header in enumerate(headers, start=1):
            if header in budget_line:
                budget_sheet.cell(row=current_row, column=col_idx, value=budget_line[header])
        current_row += 1
    
    # Save
    wb.save(output_path)
    wb.close()
    
    print(f"✅ Created budget template with {len(all_budget_lines)} lines: {output_path}")
    
    if auto_zip:
        from test_upload_fbdi.zip_fbdi import excel_to_csv_and_zip
        zip_path = excel_to_csv_and_zip(str(output_path))
        print(f"📦 Created ZIP file: {zip_path}")
        return zip_path
    
    return str(output_path)
```

---

## Part 3: Dynamic Balance Report Parsing

### File: `account_and_entitys/utils.py`

Update balance report parsing to handle dynamic segments:

```python
import pandas as pd
from account_and_entitys.models import XX_DynamicBalanceReport, XX_SegmentType
from account_and_entitys.managers.segment_manager import SegmentManager


def parse_balance_report_dynamic(excel_file_path, clear_existing=True):
    """
    Parse Oracle balance report with dynamic segment mapping.
    Automatically detects client's segment configuration and maps columns.
    
    Args:
        excel_file_path: Path to Excel file from Oracle
        clear_existing: Whether to clear existing balance report data
    
    Returns:
        Dict with statistics
    """
    print(f"\n📊 Parsing Balance Report (Dynamic Segments)")
    print(f"File: {excel_file_path}")
    
    # Get client's segment configuration
    segment_types = list(SegmentManager.get_all_segment_types())
    print(f"Client has {len(segment_types)} segment types configured:")
    for st in segment_types:
        print(f"  - {st.segment_name} (Oracle Segment {st.oracle_segment_number})")
    
    # Clear existing data if requested
    if clear_existing:
        deleted_count = XX_DynamicBalanceReport.objects.all().delete()[0]
        print(f"🗑️  Deleted {deleted_count} existing balance report records")
    
    # Load Excel file
    try:
        # Try different sheet names
        for sheet_name in ['Report', 'Sheet1', 'Balance Report']:
            try:
                df = pd.read_excel(excel_file_path, sheet_name=sheet_name, skiprows=2)
                print(f"✅ Loaded sheet: {sheet_name}")
                break
            except:
                continue
        else:
            # No sheet found
            df = pd.read_excel(excel_file_path, skiprows=2)
    except Exception as e:
        print(f"❌ Error loading Excel file: {e}")
        return {'error': str(e)}
    
    print(f"Found {len(df)} rows in balance report")
    
    # Detect segment columns in Excel
    # Oracle typically names them: "Segment1", "Segment2", etc.
    segment_column_map = {}
    for col in df.columns:
        col_lower = str(col).lower()
        if 'segment' in col_lower:
            # Extract number from column name (e.g., "Segment1" -> 1)
            import re
            match = re.search(r'segment\s*(\d+)', col_lower)
            if match:
                seg_num = int(match.group(1))
                segment_column_map[seg_num] = col
    
    print(f"Detected {len(segment_column_map)} segment columns in Excel:")
    for seg_num, col_name in sorted(segment_column_map.items()):
        # Find corresponding segment type
        seg_type = next((st for st in segment_types if st.oracle_segment_number == seg_num), None)
        type_name = seg_type.segment_name if seg_type else "Unknown"
        print(f"  - Segment{seg_num} ({col_name}) -> {type_name}")
    
    # Parse rows
    created_count = 0
    error_count = 0
    
    for idx, row in df.iterrows():
        try:
            # Extract segment values
            segment_values = {}
            for seg_num, col_name in segment_column_map.items():
                if col_name in row and pd.notna(row[col_name]):
                    segment_values[str(seg_num)] = str(row[col_name])
            
            # Extract financial fields (standard Oracle report columns)
            balance_record = XX_DynamicBalanceReport(
                control_budget_name=str(row.get('Control Budget Name', '')),
                ledger_name=str(row.get('Ledger Name', '')),
                as_of_period=str(row.get('As of Period', '')),
                segment_values=segment_values,  # JSONField
                encumbrance_ytd=_parse_decimal(row.get('Encumbrance YTD')),
                other_ytd=_parse_decimal(row.get('Other YTD')),
                actual_ytd=_parse_decimal(row.get('Actual YTD')),
                funds_available_asof=_parse_decimal(row.get('Funds Available As Of')),
                budget_ytd=_parse_decimal(row.get('Budget YTD'))
            )
            
            balance_record.save()
            created_count += 1
            
            # Show first 3 records as examples
            if created_count <= 3:
                print(f"\n  Record {created_count}:")
                print(f"    Period: {balance_record.as_of_period}")
                print(f"    Segments: {segment_values}")
                print(f"    Budget YTD: {balance_record.budget_ytd}")
        
        except Exception as e:
            error_count += 1
            if error_count <= 5:  # Show first 5 errors
                print(f"❌ Error parsing row {idx}: {e}")
    
    print(f"\n✅ Balance Report Import Complete")
    print(f"   Created: {created_count} records")
    print(f"   Errors: {error_count} records")
    
    return {
        'created_count': created_count,
        'error_count': error_count,
        'total_rows': len(df),
        'segment_types_found': len(segment_column_map)
    }


def _parse_decimal(value):
    """Helper to parse decimal values from Excel"""
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def query_balance_by_segments(segment_filters, as_of_period=None):
    """
    Query balance report by segment values.
    
    Args:
        segment_filters: Dict like {1: "12345", 2: "67890"} 
                        (keys are segment_type IDs)
        as_of_period: Optional period filter
    
    Returns:
        QuerySet of XX_DynamicBalanceReport
    """
    from django.db.models import Q
    
    queryset = XX_DynamicBalanceReport.objects.all()
    
    # Filter by period
    if as_of_period:
        queryset = queryset.filter(as_of_period=as_of_period)
    
    # Filter by segments using JSONField queries
    for seg_type_id, seg_code in segment_filters.items():
        # PostgreSQL: queryset = queryset.filter(segment_values__contains={str(seg_type_id): seg_code})
        # SQLite (for development): Manual filter
        matching_ids = []
        for record in queryset:
            if record.segment_values.get(str(seg_type_id)) == seg_code:
                matching_ids.append(record.id)
        queryset = queryset.filter(id__in=matching_ids)
    
    return queryset
```

---

## Part 4: Update Pivot Fund Function

### File: `public_funtion/update_pivot_fund.py`

Update to query dynamic balance reports:

```python
from account_and_entitys.models import XX_DynamicBalanceReport, XX_PivodFund
from account_and_entitys.managers.segment_manager import SegmentManager
from account_and_entitys.utils import query_balance_by_segments


def update_pivot_fund_dynamic(as_of_period=None):
    """
    Update XX_PivodFund table from dynamic balance reports.
    Works with any segment configuration.
    
    Args:
        as_of_period: Period to update (e.g., "Sep-25")
    """
    print(f"\n🔄 Updating Pivot Fund from Dynamic Balance Reports")
    
    # Get segment configuration
    segment_types = list(SegmentManager.get_all_segment_types())
    print(f"Client has {len(segment_types)} segment types")
    
    # Get balance reports
    if as_of_period:
        balance_reports = XX_DynamicBalanceReport.objects.filter(
            as_of_period=as_of_period
        )
    else:
        # Get latest period
        latest_period = XX_DynamicBalanceReport.objects.order_by(
            '-as_of_period'
        ).values_list('as_of_period', flat=True).first()
        balance_reports = XX_DynamicBalanceReport.objects.filter(
            as_of_period=latest_period
        )
        print(f"Using latest period: {latest_period}")
    
    print(f"Found {balance_reports.count()} balance report records")
    
    # Update pivot fund records
    updated_count = 0
    created_count = 0
    
    for balance_record in balance_reports:
        # Extract segment codes from JSONField
        segment_values = balance_record.segment_values
        
        # Get primary segments (usually first 3)
        entity_code = segment_values.get('1')  # Segment 1 = Entity
        account_code = segment_values.get('2')  # Segment 2 = Account
        project_code = segment_values.get('3')  # Segment 3 = Project (if exists)
        
        if not entity_code or not account_code:
            continue  # Skip incomplete records
        
        # Update or create pivot fund record
        pivot_fund, created = XX_PivodFund.objects.update_or_create(
            entity=entity_code,
            account=account_code,
            project=project_code or "",
            defaults={
                'available_budget': balance_record.funds_available_asof or 0,
                'approved_budget': balance_record.budget_ytd or 0,
                'actual': balance_record.actual_ytd or 0,
                'encumbrance': balance_record.encumbrance_ytd or 0,
                'budget_adjustments': balance_record.other_ytd or 0,
            }
        )
        
        if created:
            created_count += 1
        else:
            updated_count += 1
    
    print(f"\n✅ Pivot Fund Update Complete")
    print(f"   Created: {created_count} records")
    print(f"   Updated: {updated_count} records")
    
    return {
        'created': created_count,
        'updated': updated_count
    }
```

---

## Part 5: Deployment & Migration Checklist

### File: `__CLIENT_SETUP_DOCS__/04_DEPLOYMENT_CHECKLIST.md`

Create comprehensive deployment guide:

```markdown
# Deployment Checklist - Dynamic Segments

## Pre-Installation Preparation

### 1. Gather Client Requirements
- [ ] How many segments does the client use? (2-30)
- [ ] What are the segment names? (Entity, Account, Project, LineItem, etc.)
- [ ] Which segments are required?
- [ ] Which segments have hierarchies?
- [ ] Obtain sample Oracle balance report

### 2. Prepare Configuration File
- [ ] Create `config/client_segments.json` based on template
- [ ] Validate JSON structure
- [ ] Set correct Oracle segment numbers

### 3. Prepare Master Data
- [ ] Export segment values from client's Oracle
- [ ] Format as Excel/CSV (columns: segment_type, code, parent_code, alias)
- [ ] Validate data completeness

---

## Installation Steps

### Step 1: Clone and Setup
```powershell
# Clone repository
git clone <repo_url>
cd Tnfeez_dynamic

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Client Segments
```powershell
# Interactive setup (recommended for first installation)
python manage.py setup_client --interactive

# OR: Use pre-configured JSON
python manage.py setup_client --config-file config/client_segments.json

# Verify configuration
python manage.py shell
>>> from account_and_entitys.models import XX_SegmentType
>>> XX_SegmentType.objects.all()
```

### Step 3: Run Migrations
```powershell
# Create migration files
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Verify tables created
python manage.py dbshell
sqlite> .tables
# Should see: XX_SEGMENT_TYPE_XX, XX_SEGMENT_XX, XX_TRANSACTION_SEGMENT_XX
```

### Step 4: Load Master Data
```powershell
# Create superuser first
python manage.py createsuperuser

# Option A: Load via Django admin
python manage.py runserver
# Navigate to http://localhost:8000/admin/
# Import segment values

# Option B: Load via script
python manage.py load_segments --file data/client_segments.xlsx
```

### Step 5: Migrate Legacy Data (If Upgrading)
```powershell
# Dry run first
python manage.py migrate_legacy_segments --dry-run

# Review output, then execute
python manage.py migrate_legacy_segments --execute

# Verify migration
python manage.py shell
>>> from account_and_entitys.models import XX_Segment
>>> XX_Segment.objects.count()
```

### Step 6: Configure Oracle Integration
```powershell
# Update .env file in test_upload_fbdi/
FUSION_BASE_URL=https://client.fa.oracle.com
FUSION_USER=integration_user
FUSION_PASS=<password>
FUSION_LEDGER_ID=<ledger_id>
FUSION_DAS_ID=<das_id>

# Test connection
cd test_upload_fbdi
python test_oracle_connection.py
```

### Step 7: Test System
```powershell
# Start server
python manage.py runserver

# Run test transaction creation
python manage.py shell
>>> from transaction.models import xx_TransactionTransfer
>>> from budget_management.models import xx_BudgetTransfer
>>> # Create test transaction
>>> # (see testing guide)

# Test FBDI generation
cd test_upload_fbdi
python test_journal_upload_dynamic.py
```

### Step 8: Load Balance Report
```powershell
# Download balance report from Oracle
# Place in account_and_entitys/data/balance_report.xlsx

# Parse and load
python manage.py shell
>>> from account_and_entitys.utils import parse_balance_report_dynamic
>>> parse_balance_report_dynamic('path/to/balance_report.xlsx')

# Update pivot fund
>>> from public_funtion.update_pivot_fund import update_pivot_fund_dynamic
>>> update_pivot_fund_dynamic()
```

---

## Post-Installation Verification

### Database Checks
```sql
-- Check segment types
SELECT * FROM XX_SEGMENT_TYPE_XX;

-- Check segment values count
SELECT segment_type_id, COUNT(*) 
FROM XX_SEGMENT_XX 
GROUP BY segment_type_id;

-- Check balance report
SELECT COUNT(*) FROM XX_DYNAMIC_BALANCE_REPORT_XX;
```

### API Checks
```powershell
# Test segment configuration endpoint
curl http://localhost:8000/api/segments/types/config/

# Expected response:
{
  "client_name": "Client XYZ",
  "total_segments": 4,
  "segments": [...]
}
```

### Frontend Checks
- [ ] Login works
- [ ] Dashboard displays correctly
- [ ] Transaction form shows correct segments
- [ ] Dropdown values populate
- [ ] Hierarchical selects work (if applicable)

---

## Rollback Plan

If issues occur:

### Option 1: Revert to Legacy System
```powershell
# Restore database backup
python manage.py loaddata backup.json

# Switch feature flag (if implemented)
# In settings.py: USE_DYNAMIC_SEGMENTS = False
```

### Option 2: Re-run Setup
```powershell
# Clear segment configuration
python manage.py setup_client --overwrite --config-file config/new_config.json

# Re-migrate
python manage.py migrate
```

---

## Performance Tuning

### Database Indexes
```sql
-- Ensure these indexes exist
CREATE INDEX idx_segment_type_code ON XX_SEGMENT_XX(segment_type_id, code);
CREATE INDEX idx_trans_segment ON XX_TRANSACTION_SEGMENT_XX(transaction_transfer_id, segment_type_id);
CREATE INDEX idx_balance_period ON XX_DYNAMIC_BALANCE_REPORT_XX(as_of_period);
```

### Caching
```python
# In settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

---

## Monitoring

### Key Metrics
- Segment type count: Should match client configuration
- Segment value count: Should match master data
- Transaction segment records: Should equal transactions × required segments
- Balance report records: Should update daily/weekly

### Log Files
- `logs/segment_manager.log` - Segment operations
- `logs/oracle_integration.log` - FBDI uploads
- `logs/balance_report.log` - Balance report parsing

---

## Troubleshooting

### Issue: Segment validation fails
**Solution**: Check XX_SegmentType table, ensure is_required=True for mandatory segments

### Issue: Oracle upload fails with segment errors
**Solution**: Verify segment_values in database match Oracle chart of accounts

### Issue: Balance report parsing fails
**Solution**: Check Excel column names, ensure they match "Segment1", "Segment2" format

### Issue: Hierarchical queries slow
**Solution**: Add indexes on parent_code field, implement caching

---

## Support

For issues during installation:
1. Check logs in `logs/` directory
2. Run: `python manage.py check --deploy`
3. Contact: support@example.com
```

---

## Summary

This document covered:

1. **Dynamic Journal Template Manager** - Generates GL_INTERFACE with any number of segments
2. **Dynamic Budget Template Manager** - Handles budget imports
3. **Dynamic Balance Report Parsing** - Auto-detects segment columns
4. **Pivot Fund Updates** - Works with dynamic balance reports
5. **Deployment Checklist** - Complete installation guide

## Complete File List

All documentation is now in `__CLIENT_SETUP_DOCS__/`:

1. `01_DYNAMIC_SEGMENTS_ARCHITECTURE.md` - Overall architecture and design
2. `02_IMPLEMENTATION_GUIDE_CODE.md` - New models, managers, setup scripts
3. `03_TRANSACTION_API_UPDATES.md` - Transaction handling, serializers, APIs
4. `04_ORACLE_INTEGRATION_DEPLOYMENT.md` - This file (Oracle & deployment)

**Total estimated implementation time: 13 weeks (260 hours)**

Would you like me to create any additional guides (e.g., frontend integration, testing strategy, or migration scripts)?
