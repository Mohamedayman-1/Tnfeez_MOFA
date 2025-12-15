"""
Django management command to sync datasources from registry to database.

This command reads all registered datasources from the datasource_registry
and creates/updates DataSource records in the database to match.

Datasources are now organized in folders:
- datasources/global/ - User information datasources
- datasources/transaction/ - Transaction-level datasources  
- datasources/transfer/ - Transfer line-level datasources

Usage:
    python manage.py sync_datasources
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django_dynamic_validation.datasource_registry import datasource_registry
from django_dynamic_validation.models import DataSource
import importlib
import os
from pathlib import Path

User = get_user_model()  # Get the custom user model


class Command(BaseCommand):
    help = 'Sync datasources from registry to database (auto-discovers from datasources/ folder)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--show-structure',
            action='store_true',
            help='Show the datasource folder structure',
        )

    def handle(self, *args, **options):
        """
        Main command handler.
        
        This command:
        1. Auto-discovers and imports all datasource modules from datasources/ folder
        2. Gets all registered datasources from the registry
        3. Creates or updates DataSource records in the database
        4. Removes datasources no longer in registry
        """
        self.stdout.write(self.style.SUCCESS('=== Datasource Sync Command ===\n'))
        
        # Show folder structure if requested
        if options['show_structure']:
            self._show_structure()
            return
        
        # Auto-discover and import datasource modules
        self._discover_datasources()
        
        self.stdout.write(self.style.SUCCESS('\nStarting datasource sync...'))
        
        # Get all registered datasources
        registered = datasource_registry.list_all()
        
        if not registered:
            self.stdout.write(self.style.WARNING('No datasources registered in the registry'))
            return
        
        self.stdout.write(f'Found {len(registered)} registered datasources')
        
        # Get or create a system user for created_by field
        system_user, _ = User.objects.get_or_create(
            username='system',
            defaults={'is_active': False}
        )
        
        created_count = 0
        updated_count = 0
        
        # Sync each registered datasource
        for name, metadata in registered.items():
            datasource, created = DataSource.objects.update_or_create(
                name=name,
                defaults={
                    'description': metadata['description'],
                    'function_name': metadata['function_name'],
                    'parameter_names': metadata['parameters'],
                    'return_type': metadata['return_type'],
                    'created_by': system_user
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created: {name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Updated: {name}')
                )
        
        # Delete datasources in DB but not in registry
        db_datasources = set(DataSource.objects.values_list('name', flat=True))
        registered_names = set(registered.keys())
        orphaned = db_datasources - registered_names
        
        deleted_count = 0
        if orphaned:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠ Found {len(orphaned)} datasource(s) in database but not in registry:'
                )
            )
            for name in orphaned:
                self.stdout.write(self.style.WARNING(f'  - {name}'))
            
            # Delete orphaned datasources
            self.stdout.write(
                self.style.NOTICE(
                    '\nDeleting orphaned datasources from database...'
                )
            )
            for name in orphaned:
                DataSource.objects.filter(name=name).delete()
                deleted_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Deleted: {name}')
                )
        
        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== Sync Complete ==='
                f'\n  Created: {created_count}'
                f'\n  Updated: {updated_count}'
                f'\n  Deleted: {deleted_count}'
                f'\n  Total:   {len(registered)} datasources in registry'
            )
        )

    def _discover_datasources(self):
        """
        Auto-discover and import all datasource modules from datasources/ folder.
        
        Scans the datasources/ directory and imports all Python files,
        which triggers datasource registration.
        """
        self.stdout.write(self.style.NOTICE('Discovering datasource modules...\n'))
        
        # Get the datasources directory
        import django_dynamic_validation
        app_path = Path(django_dynamic_validation.__file__).parent
        datasources_path = app_path / 'datasources'
        
        if not datasources_path.exists():
            self.stdout.write(self.style.ERROR('  ✗ datasources/ folder not found!'))
            return
        
        # Scan for datasource folders
        discovered = []
        for folder in datasources_path.iterdir():
            if folder.is_dir() and not folder.name.startswith('__'):
                folder_name = folder.name
                self.stdout.write(f'  📁 {folder_name}/')
                
                # Import the package (which imports all modules via __init__.py)
                try:
                    module_path = f'django_dynamic_validation.datasources.{folder_name}'
                    importlib.import_module(module_path)
                    discovered.append(folder_name)
                    self.stdout.write(self.style.SUCCESS(f'     ✓ Imported'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'     ✗ Failed: {e}'))
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Discovered {len(discovered)} datasource categories')
        )

    def _show_structure(self):
        """Show the current datasource folder structure."""
        self.stdout.write(self.style.SUCCESS('=== Datasource Folder Structure ===\n'))
        
        import django_dynamic_validation
        app_path = Path(django_dynamic_validation.__file__).parent
        datasources_path = app_path / 'datasources'
        
        if not datasources_path.exists():
            self.stdout.write(self.style.ERROR('datasources/ folder not found!'))
            return
        
        self.stdout.write('datasources/')
        for folder in sorted(datasources_path.iterdir()):
            if folder.is_dir() and not folder.name.startswith('__'):
                self.stdout.write(f'├── {folder.name}/')
                
                # List Python files in folder
                for file in sorted(folder.glob('*.py')):
                    if file.name != '__init__.py':
                        icon = '│   ├──' if file != list(folder.glob('*.py'))[-1] else '│   └──'
                        self.stdout.write(f'{icon} {file.name}')
                self.stdout.write('│')
        
        self.stdout.write(
            self.style.NOTICE(
                '\n💡 To add a new datasource level:'
                '\n   1. Create folder: datasources/new_level/'
                '\n   2. Add __init__.py and your_datasources.py'
                '\n   3. Import in datasources/__init__.py'
                '\n   4. Run: python manage.py sync_datasources'
            )
        )

