# Oracle FBDI Integration - Quick Reference

## 📁 New Folder Structure

```
oracle_fbdi_integration/
├── core/                      # Core modules (don't modify unless needed)
│   ├── journal_manager.py     # Journal creation & templates
│   ├── upload_manager.py      # Oracle SOAP upload
│   └── file_utils.py          # CSV/ZIP utilities
│
├── utilities/                 # ⭐ USE THESE for integration
│   ├── journal_integration.py # Complete journal workflow
│   └── budget_integration.py  # Complete budget workflow
│
├── templates/                 # Excel templates
│   ├── JournalImportTemplate.xlsm
│   └── BudgetImportTemplate.xlsm
│
└── generated_files/          # Auto-organized outputs
    ├── journals/             # Journal files (.xlsm, .zip, .csv)
    ├── budgets/              # Budget files (.xlsm, .zip, .csv)
    └── archives/             # Old files
```

## ⚡ Quick Usage

### Journal Upload (Most Common)

```python
from oracle_fbdi_integration.utilities.journal_integration import create_and_upload_journal

# In your view:
upload_result, file_path = create_and_upload_journal(
    transfers=transfers,
    transaction_id=12345,
    entry_type="submit"  # or "reject"
)

if upload_result.get("success"):
    print(f"✅ Success! Request ID: {upload_result['request_id']}")
else:
    print(f"❌ Failed: {upload_result['error']}")
```

### Budget Upload

```python
from oracle_fbdi_integration.utilities.budget_integration import create_and_upload_budget

upload_result, file_path = create_and_upload_budget(
    transfers=transfers,
    transaction_id=67890
)
```

## 🔄 Migration from Old Code

| Old Code | New Code |
|----------|----------|
| `submint_journal_and_upload(transfers, txn_id, type="submit")` | `create_and_upload_journal(transfers, txn_id, entry_type="submit")` |
| `submit_budget_and_upload(transfers, txn_id)` | `create_and_upload_budget(transfers, txn_id)` |

**Key Changes:**
- ✅ Fixed typo: `submint` → proper function name
- ✅ Parameter renamed: `type` → `entry_type` (clearer naming)
- ✅ Imports from `oracle_fbdi_integration.utilities.*`

## 📂 Where Files Go

### Generated Files (Auto-created)

| File Type | Location | Example |
|-----------|----------|---------|
| Journal Excel | `generated_files/journals/` | `Journal_TXN12345_20251116_143022.xlsm` |
| Journal ZIP | `generated_files/journals/` | `Journal_TXN12345_20251116_143022.zip` |
| Journal CSV | `generated_files/journals/` | `GL_INTERFACE.csv` |
| Budget Excel | `generated_files/budgets/` | `Budget_TXN67890_20251116_143045.xlsm` |
| Budget ZIP | `generated_files/budgets/` | `Budget_TXN67890_20251116_143045.zip` |
| Budget CSV | `generated_files/budgets/` | `XccBudgetInterface.csv` |

### Templates (Read-only, versioned)

- `templates/JournalImportTemplate.xlsm` - Base template for journals
- `templates/BudgetImportTemplate.xlsm` - Base template for budgets

## 🔧 Environment Variables (.env)

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
ORACLE_EFFECTIVE_DATE=2025/01/01
ENCUMBRANCE_TYPE_ID=300000035858125
```

## 🐛 Troubleshooting

### Import Error
```
ModuleNotFoundError: No module named 'oracle_fbdi_integration'
```
**Fix**: Ensure you're in the project root directory

### Template Not Found
```
FileNotFoundError: Template file not found
```
**Fix**: Check that templates exist in `oracle_fbdi_integration/templates/`

### Upload Failed
```
{'success': False, 'error': 'Missing environment variable: FUSION_BASE_URL'}
```
**Fix**: Verify `.env` file has all required Oracle credentials

## 📚 Full Documentation

See `oracle_fbdi_integration/README.md` for complete documentation including:
- Custom journal entries
- Advanced segment mapping
- Balanced journal pairs
- Migration guide

## ✅ Testing Checklist

- [ ] Journal upload works from transaction view
- [ ] Budget upload works from budget management
- [ ] Files appear in correct `generated_files/` subdirectories
- [ ] Oracle upload succeeds (check Request ID)
- [ ] No import errors in logs

---

**Quick Start**: Just use the `utilities/` modules - they handle everything! 🚀
