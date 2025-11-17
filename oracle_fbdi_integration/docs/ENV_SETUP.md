# Environment Configuration

## Single .env File

All Oracle Fusion configuration is now consolidated into **one** `.env` file at the project root:

```
Tnfeez_MOFA/
└── .env  ← Single source of truth for all configuration
```

### Previous Structure (Removed)
- ~~`account_and_entitys/.env`~~ ❌ Deleted
- ~~`test_upload_fbdi/.env`~~ ❌ Deleted  
- ~~`test_upload_fbdi/load&import/.env`~~ ❌ Deleted

### How It Works

All Python modules use `load_dotenv()` which automatically searches up the directory tree for a `.env` file. Since there's now only one `.env` at the root, **all modules read from the same configuration**.

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Automatically finds root .env file

base_url = os.getenv("FUSION_BASE_URL")
user = os.getenv("FUSION_USER")
```

### Configuration Sections

The consolidated `.env` file contains:

1. **Oracle Fusion Connection** - Base URL, credentials
2. **REST API Settings** - For account_and_entitys module
3. **BI Publisher** - SOAP endpoint
4. **General Ledger** - Ledger ID, journal source, etc.
5. **Budget Control** - DAS ID, ledger settings
6. **Document Import** - GL and budget import paths
7. **Posting & Encumbrance** - Auto-post and encumbrance IDs
8. **FBDI File Paths** - Template and output directories

### Benefits

✅ **No Duplication** - One source of truth  
✅ **Easy Maintenance** - Update once, applies everywhere  
✅ **No Conflicts** - No risk of different modules using different values  
✅ **Version Control** - Single file to track in `.gitignore`  

### Security Note

Remember to add `.env` to `.gitignore`:

```gitignore
# Environment variables
.env
.env.*
!.env.example
```

Never commit the `.env` file with real credentials!
