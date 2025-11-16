"""
Oracle FBDI Integration Module

This module provides tools for generating and uploading FBDI (File-Based Data Import) 
files to Oracle Fusion Cloud ERP for:
- Journal Entries (GL_INTERFACE)
- Budget Data (XCC_BUDGET_INTERFACE)

Package Structure:
    - core/: Core business logic for journal and budget management
    - templates/: Excel template files (.xlsm)
    - generated_files/: Output files (journals/, budgets/, archives/)
    - utilities/: Helper functions and integration tools
"""

__version__ = "2.0.0"
__author__ = "Tnfeez MOFA Development Team"

from pathlib import Path

# Module paths
MODULE_DIR = Path(__file__).parent
TEMPLATES_DIR = MODULE_DIR / "templates"
GENERATED_FILES_DIR = MODULE_DIR / "generated_files"
JOURNALS_DIR = GENERATED_FILES_DIR / "journals"
BUDGETS_DIR = GENERATED_FILES_DIR / "budgets"
ARCHIVES_DIR = GENERATED_FILES_DIR / "archives"

# Ensure directories exist
for directory in [TEMPLATES_DIR, JOURNALS_DIR, BUDGETS_DIR, ARCHIVES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
