# Oracle FBDI Integration Module

## Overview

The **Oracle FBDI Integration** module provides a comprehensive, maintainable solution for generating and uploading File-Based Data Import (FBDI) files to Oracle Fusion Cloud ERP. This module supports:

- **Journal Entries** (GL_INTERFACE)
- **Budget Data** (XCC_BUDGET_INTERFACE)
- **Dynamic Segment Mapping** (SEGMENT1-SEGMENT30)
- **Automated Upload** via SOAP API

## 📁 Directory Structure

```
oracle_fbdi_integration/
├── __init__.py                    # Module initialization and path configuration
├── README.md                      # This file
│
├── core/                          # Core business logic
│   ├── journal_manager.py         # Journal template and data management
│   ├── budget_manager.py          # Budget template and data management
│   ├── upload_manager.py          # Oracle SOAP API integration
│   └── file_utils.py              # File conversion and ZIP utilities
│
├── utilities/                     # High-level integration utilities
│   ├── journal_integration.py     # Journal creation + upload workflow
│   └── budget_integration.py      # Budget creation + upload workflow
│
├── templates/                     # Excel FBDI templates (.xlsm)
│   ├── JournalImportTemplate.xlsm
│   └── BudgetImportTemplate.xlsm
│
└── generated_files/               # Output files (organized by type)
    ├── journals/                  # Generated journal files
    ├── budgets/                   # Generated budget files
    └── archives/                  # Old files (for cleanup)
```

## 🚀 Quick Start

### 1. Journal Entry Upload

```python
from oracle_fbdi_integration.utilities.journal_integration import create_and_upload_journal

# Create and upload journal entries from transfers
upload_result, file_path = create_and_upload_journal(
    transfers=transfer_objects,
    transaction_id=12345,
    entry_type="submit"  # or "reject"
)

if upload_result.get("success"):
    print(f"Success! Request ID: {upload_result['request_id']}")
else:
    print(f"Failed: {upload_result['error']}")
```

### 2. Budget Data Upload

```python
from oracle_fbdi_integration.utilities.budget_integration import create_and_upload_budget

# Create and upload budget data from transfers
upload_result, file_path = create_and_upload_budget(
    transfers=transfer_objects,
    transaction_id=12345
)
```

### 3. Custom Journal Entries

```python
from oracle_fbdi_integration.core.journal_manager import (
    JournalTemplateManager,
    create_balanced_journal_pair
)

# Create a balanced journal pair with custom segments
entries = create_balanced_journal_pair(
    debit_segments={1: 'E001', 2: 'A100', 3: 'P001'},
    credit_segments={1: 'E002', 2: 'A200', 3: 'P002'},
    amount=15000.00,
    debit_description="Budget transfer FROM E001",
    credit_description="Budget transfer TO E002"
)

# Fill template and create ZIP
manager = JournalTemplateManager("templates/JournalImportTemplate.xlsm")
result = manager.create_from_scratch(
    journal_data=entries,
    output_name="MyJournal",
    auto_zip=True
)
```

## 🔧 Core Modules

### JournalTemplateManager

Manages journal template operations with support for dynamic segments.

**Key Methods:**
- `create_clean_template()` - Create a blank template copy
- `fill_template()` - Populate template with data
- `create_from_scratch()` - Complete workflow (clean → fill → ZIP)

### Budget Manager (Similar to Journal)

Handles budget FBDI templates (XCC_BUDGET_INTERFACE).

### Upload Manager

Handles SOAP API communication with Oracle Fusion.

**Key Functions:**
- `upload_journal_fbdi()` - Upload journal CSV to Oracle
- `upload_budget_fbdi()` - Upload budget CSV to Oracle

### File Utilities

Provides file conversion and management:
- `excel_to_csv_and_zip()` - Convert Excel → CSV → ZIP
- `validate_csv_file()` - Validate CSV structure
- `cleanup_old_files()` - Remove old generated files

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Oracle Fusion Connection
FUSION_BASE_URL=https://your-instance.oraclecloud.com
FUSION_USER=your_username
FUSION_PASS=your_password

# Oracle Configuration
ORACLE_ACCESS_SET=300000123456789
ORACLE_LEDGER_ID=300000205309206
ORACLE_JOURNAL_SOURCE=Allocations
ORACLE_CURRENCY_CODE=AED
ORACLE_EFFECTIVE_DATE=2025-09-26
ENCUMBRANCE_TYPE_ID=300000035858125
```

## 📊 Dynamic Segment Support

The module supports Oracle's flexible chart of accounts with up to 30 segments:

```python
from oracle_fbdi_integration.core.journal_manager import create_custom_journal_entry

# Create entry with custom segments
entry = create_custom_journal_entry(
    segment_values={
        1: 'E001',  # Entity
        2: 'A100',  # Account
        3: 'P001',  # Project
        4: 'M001',  # Department
        # ... up to 30 segments
    },
    debit_amount=5000.00,
    line_description="Budget allocation"
)
```

Segments are automatically mapped using `OracleSegmentMapper` from `account_and_entitys.oracle`.

## 🔄 Migration from Old Structure

This module replaces the old `test_upload_fbdi` folder with an improved structure:

### Old Import Paths → New Import Paths

```python
# OLD
from test_upload_fbdi.journal_template_manager import create_sample_journal_data
from test_upload_fbdi.upload_soap_fbdi import upload_fbdi_to_oracle
from test_upload_fbdi.utility.creat_and_upload import submint_journal_and_upload

# NEW
from oracle_fbdi_integration.core.journal_manager import create_journal_entry_data
from oracle_fbdi_integration.core.upload_manager import upload_journal_fbdi
from oracle_fbdi_integration.utilities.journal_integration import create_and_upload_journal
```

### Function Name Changes

| Old Function | New Function |
|--------------|--------------|
| `create_sample_journal_data()` | `create_journal_entry_data()` |
| `upload_fbdi_to_oracle()` | `upload_journal_fbdi()` |
| `submint_journal_and_upload()` | `create_and_upload_journal()` |
| `submit_budget_and_upload()` | `create_and_upload_budget()` |

## 📦 Generated Files Organization

Files are now organized by type in `generated_files/`:

```
generated_files/
├── journals/
│   ├── Journal_TXN12345_20250916_143022.xlsm
│   ├── Journal_TXN12345_20250916_143022.zip
│   └── GL_INTERFACE.csv
│
├── budgets/
│   ├── Budget_TXN67890_20250916_143045.xlsm
│   ├── Budget_TXN67890_20250916_143045.zip
│   └── XccBudgetInterface.csv
│
└── archives/
    └── (old files moved here for cleanup)
```

## 🧪 Testing

Run integration tests:

```python
# Test journal creation
python -m oracle_fbdi_integration.core.journal_manager

# Test file utilities
python -m oracle_fbdi_integration.core.file_utils
```

## 📝 Best Practices

1. **Use high-level utilities** (`journal_integration.py`, `budget_integration.py`) for common workflows
2. **Use core modules** for custom integration scenarios
3. **Clean up old files** periodically using `cleanup_old_files()`
4. **Validate CSV** before upload using `validate_csv_file()`
5. **Check upload results** - always verify `success` field in response

## 🐛 Troubleshooting

### Template Not Found
- Ensure templates are in `oracle_fbdi_integration/templates/`
- Check file permissions

### Upload Failures
- Verify environment variables in `.env`
- Check Oracle Fusion connectivity
- Review request logs in Oracle ERP

### Segment Mapping Issues
- Verify `OracleSegmentMapper` configuration
- Check segment type IDs match Oracle setup

## 📚 Additional Documentation

See `__CLIENT_SETUP_DOCS__/` for detailed documentation:
- `04_ORACLE_INTEGRATION_DEPLOYMENT.md` - Deployment guide
- `DYNAMIC_SEGMENT_API_GUIDE.md` - Segment mapping details

## 🔐 Security Notes

- Never commit `.env` files with credentials
- Use environment-specific configuration
- Rotate Oracle credentials regularly

## 📞 Support

For issues or questions, contact the Tnfeez MOFA Development Team.

---

**Version:** 2.0.0  
**Last Updated:** November 2025
