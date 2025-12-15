"""
Datasources Package

Organized datasource modules by scope/level:

- user_info/    - User information and system-wide datasources
- transaction/  - Transaction-level aggregated data
- transfer/     - Transfer line-level data

All datasources use StandardParams for consistent parameter naming
and support auto-population in views.

Usage:
    # Import all datasources (auto-registers them)
    from django_dynamic_validation import datasources
    
    # Or import specific levels
    from django_dynamic_validation.datasources.user_info import user_datasources
    from django_dynamic_validation.datasources.transaction import transaction_datasources
    from django_dynamic_validation.datasources.transfer import transfer_datasources

Adding New Datasource Levels:
    1. Create new folder: datasources/new_level/
    2. Create __init__.py and datasource files
    3. Import in this file
    4. Update sync_datasources command
"""

# Import all datasource modules to register them
from .user_info import user_datasources
from .transaction import transaction_datasources
from .transfer import transfer_datasources

__all__ = [
    'user_datasources',
    'transaction_datasources',
    'transfer_datasources',
]
