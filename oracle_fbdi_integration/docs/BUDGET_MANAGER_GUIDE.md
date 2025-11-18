# Budget Manager Guide

## Overview

The Budget Manager module provides core functionality for creating and uploading Oracle Budget FBDI (File-Based Data Import) files. It has been migrated from `test_upload_fbdi` to `oracle_fbdi_integration/core` for production use.

## Module Location

```
oracle_fbdi_integration/
├── core/
│   ├── budget_manager.py      # Core budget template management
│   ├── journal_manager.py     # Core journal template management
│   └── __init__.py            # Exports all manager functions
├── utilities/
│   ├── budget_integration.py  # High-level budget workflow
│   └── journal_integration.py # High-level journal workflow
└── templates/
    └── BudgetImportTemplate.xlsm
```

## Quick Start

### Basic Usage - Create and Upload Budget

```python
from oracle_fbdi_integration.utilities.budget_integration import create_and_upload_budget

# Create and upload budget from transaction transfers
upload_result, file_path = create_and_upload_budget(
    transfers=transaction_transfers,  # List of XX_TransactionTransfer objects
    transaction_id=123,
    entry_type="submit"  # or "reject"
)

if upload_result.get("success"):
    print(f"✅ Budget uploaded successfully!")
    print(f"Request ID: {upload_result.get('request_id')}")
else:
    print(f"❌ Upload failed: {upload_result.get('error')}")
```

## Core Classes and Functions

### BudgetTemplateManager Class

Manages Oracle Budget FBDI template operations.

```python
from oracle_fbdi_integration.core.budget_manager import BudgetTemplateManager

# Initialize with template path
manager = BudgetTemplateManager("path/to/BudgetImportTemplate.xlsm")

# Create clean template
clean_template = manager.create_clean_template()

# Fill template with data
filled_template = manager.fill_template(
    template_path=clean_template,
    budget_data=budget_entries,
    auto_zip=True
)

# Complete workflow (clean + fill + zip)
result_path = manager.create_from_scratch(
    budget_data=budget_entries,
    output_name="XccBudgetInterface_20250101",
    auto_zip=True
)
```

### Helper Functions

#### 1. Create Budget Entry Data from Transfers

Automatically converts transaction transfers to budget entries with dynamic segments:

```python
from oracle_fbdi_integration.core.budget_manager import create_budget_entry_data

budget_entries = create_budget_entry_data(
    transfers=transaction_transfers,
    transaction_id=123,
    source_budget_type="HYPERION",
    source_budget_name="MIC_HQ_MONTHLY",
    period_name="Sep-25",
    currency_code="AED"
)
```

**Features:**
- Automatically builds FROM (negative) and TO (positive) entries
- Uses `OracleSegmentMapper` for dynamic SEGMENT1-SEGMENT30 columns
- Supports 2-30 segments based on configuration

#### 2. Create Custom Budget Entry

Create a single budget entry with custom segment values:

```python
from oracle_fbdi_integration.core.budget_manager import create_budget_entry_with_segments

entry = create_budget_entry_with_segments(
    segment_values={
        1: 'E001',  # Entity
        2: 'A100',  # Account
        3: 'P001',  # Project
    },
    amount=10000.00,
    budget_name="Q3_BUDGET_ADJUSTMENT",
    line_number=1,
    period_name="Sep-25"
)
```

#### 3. Create Balanced Transfer Pair

Create FROM/TO budget transfer entries:

```python
from oracle_fbdi_integration.core.budget_manager import create_budget_transfer_pair

entries = create_budget_transfer_pair(
    from_segments={1: 'E001', 2: 'A100', 3: 'P001'},
    to_segments={1: 'E002', 2: 'A200', 3: 'P002'},
    amount=5000.00,
    budget_name="MONTHLY_REALLOCATION",
    period_name="Sep-25"
)
# Returns [from_entry (negative), to_entry (positive)]
```

## File Structure

### Generated Files Location

All budget files are generated in:
```
oracle_fbdi_integration/generated_files/budgets/
```

### Output Format

The workflow creates:
1. **Excel file** (`XccBudgetInterface_*.xlsm`) - Filled template
2. **CSV file** (`XccBudgetInterface.csv`) - Extracted data
3. **ZIP file** (`XccBudgetInterface_*.zip`) - CSV packaged for upload

### Naming Convention

Files follow Oracle's required naming:
```
XccBudgetInterface_TXN{transaction_id}_{timestamp}.xlsm
XccBudgetInterface_TXN{transaction_id}_{timestamp}.zip
```

## Budget Entry Structure

Each budget entry must have:

```python
{
    "Source Budget Type": "HYPERION",
    "Source Budget Name": "MIC_HQ_MONTHLY",
    "Budget Entry Name": "MIC_HQ_MONTHLY_123",
    "Line Number": 1,
    "Amount": 10000.00,  # Positive = increase, Negative = decrease
    "Currency Code": "AED",
    "Period Name": "Sep-25",
    "Segment1": "E001",  # Dynamic segments 1-30
    "Segment2": "A100",
    "Segment3": "P001",
    # ... up to Segment30 (based on configuration)
}
```

## Dynamic Segment Support

The budget manager supports 2-30 segments using `OracleSegmentMapper`:

```python
from account_and_entitys.oracle import OracleSegmentMapper

mapper = OracleSegmentMapper()

# Get active segments
active_fields = mapper.get_active_oracle_fields()
# Returns: ['Segment1', 'Segment2', 'Segment3', ...]

# Build FBDI row with segments
entry = mapper.build_fbdi_row(
    transaction_transfer=transfer,
    base_row=base_entry,
    include_from_to='from'  # or 'to'
)
```

## Integration with Upload Workflow

The budget integration automatically handles the complete Oracle upload workflow:

1. **Template Creation** - Clean and fill BudgetImportTemplate.xlsm
2. **ZIP Creation** - Package CSV for Oracle UCM
3. **UCM Upload** - Upload to Oracle Universal Content Management
4. **Budget Import** - Submit Budget Import ESS job
5. **Audit Tracking** - Record progress in `xx_budget_integration_audit`

```python
from oracle_fbdi_integration.utilities.budget_integration import create_and_upload_budget

upload_result, file_path = create_and_upload_budget(
    transfers=transaction_transfers,
    transaction_id=123
)

# Returns:
# upload_result = {
#     "success": True/False,
#     "request_id": "12345678",
#     "group_id": "20250119123045",
#     "error": "Error message if failed"
# }
```

## Migration from test_upload_fbdi

Old code (test folder):
```python
from test_upload_fbdi.budget_template_manager import create_budget_from_scratch
```

New code (production):
```python
from oracle_fbdi_integration.core.budget_manager import BudgetTemplateManager

manager = BudgetTemplateManager(template_path)
result = manager.create_from_scratch(budget_data=data, auto_zip=True)
```

## Related Modules

- **Journal Manager**: `oracle_fbdi_integration/core/journal_manager.py`
- **Upload Workflow**: `oracle_fbdi_integration/utilities/Upload_essjob_api_budget.py`
- **Segment Mapping**: `account_and_entitys/oracle.py` (`OracleSegmentMapper`)
- **Audit Models**: `budget_management/models.py` (`xx_budget_integration_audit`)

## Best Practices

1. **Always use BUDGETS_DIR** for output location
2. **Use unique transaction_id** for tracking
3. **Validate segment configuration** before creating entries
4. **Check upload_result** for errors before proceeding
5. **Monitor audit records** in `xx_budget_integration_audit` table

## Example: Complete Workflow

```python
from oracle_fbdi_integration.utilities.budget_integration import create_and_upload_budget
from budget_management.models import XX_TransactionTransfer

# Get transaction transfers
transfers = XX_TransactionTransfer.objects.filter(transaction_id=123)

# Create and upload budget
upload_result, file_path = create_and_upload_budget(
    transfers=transfers,
    transaction_id=123,
    entry_type="submit"
)

if upload_result.get("success"):
    print(f"✅ Budget uploaded successfully!")
    print(f"📄 File: {file_path}")
    print(f"🔢 Request ID: {upload_result.get('request_id')}")
    print(f"🆔 Group ID: {upload_result.get('group_id')}")
else:
    print(f"❌ Upload failed: {upload_result.get('error')}")
```

## Troubleshooting

### Common Issues

1. **Template not found**
   - Check `oracle_fbdi_integration/templates/BudgetImportTemplate.xlsm` exists
   - Fallback checks `test_upload_fbdi/BudgetImportTemplate.xlsm`

2. **Segment mismatch**
   - Verify `OracleSegmentMapper` configuration matches Oracle setup
   - Check `account_and_entitys.models.Segment_mapper` table

3. **Upload fails**
   - Verify Oracle credentials in `.env` file
   - Check network connectivity to Oracle Fusion
   - Review audit records for detailed error messages

4. **ZIP file missing CSV**
   - Ensure `excel_to_csv_and_zip` function in `file_utils.py` is working
   - Check permissions on generated_files/budgets directory

## See Also

- [Journal Manager Guide](JOURNAL_MANAGER_GUIDE.md) - Similar workflow for GL journals
- [Oracle Integration Deployment](../../__CLIENT_SETUP_DOCS__/04_ORACLE_INTEGRATION_DEPLOYMENT.md)
- [Dynamic Segment API Guide](../../__CLIENT_SETUP_DOCS__/DYNAMIC_SEGMENT_API_GUIDE.md)
