"""
Management command to migrate legacy segment data (XX_Entity, XX_Account, XX_Project)
to the new dynamic segment structure (XX_SegmentType, XX_Segment).

This command provides a safe migration path from the hardcoded 3-segment system
to the new dynamic multi-segment system.

Usage:
    python manage.py migrate_legacy_segments
    python manage.py migrate_legacy_segments --dry-run
    python manage.py migrate_legacy_segments --batch-size 1000
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from account_and_entitys.models import (
    XX_Entity, XX_Account, XX_Project,
    XX_SegmentType, XX_Segment
)
from account_and_entitys.managers.segment_manager import SegmentManager


class Command(BaseCommand):
    help = 'Migrate legacy segment data to dynamic segment structure'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            'entities_migrated': 0,
            'accounts_migrated': 0,
            'projects_migrated': 0,
            'entities_skipped': 0,
            'accounts_skipped': 0,
            'projects_skipped': 0,
            'errors': []
        }

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without making any changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of records to process in each batch (default: 500)',
        )
        parser.add_argument(
            '--entity-only',
            action='store_true',
            help='Only migrate entity segments',
        )
        parser.add_argument(
            '--account-only',
            action='store_true',
            help='Only migrate account segments',
        )
        parser.add_argument(
            '--project-only',
            action='store_true',
            help='Only migrate project segments',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force migration even if target segments already exist',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Legacy Segment Migration ===\n'))

        # Validate segment types exist
        if not self.validate_segment_types():
            raise CommandError('Segment types not configured. Run "python manage.py setup_client" first.')

        # Display migration plan
        self.display_migration_plan(options)

        # Confirm if not dry-run
        if not options['dry_run']:
            confirm = input('\nDo you want to proceed with the migration? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Migration cancelled.'))
                return

        # Perform migration
        try:
            if options['dry_run']:
                self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be made\n'))
            
            self.migrate_segments(options)
            
            # Display results
            self.display_migration_results(options['dry_run'])

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Migration failed: {str(e)}'))
            raise

    def validate_segment_types(self):
        """Validate that segment types are configured."""
        self.stdout.write('📋 Validating segment type configuration...')
        
        required_types = ['Entity', 'Account', 'Project']
        existing_types = XX_SegmentType.objects.filter(
            segment_name__in=required_types
        ).values_list('segment_name', flat=True)
        
        missing_types = set(required_types) - set(existing_types)
        
        if missing_types:
            self.stdout.write(self.style.ERROR(f'  ❌ Missing segment types: {", ".join(missing_types)}'))
            return False
        
        self.stdout.write(self.style.SUCCESS('  ✓ All required segment types found'))
        return True

    def display_migration_plan(self, options):
        """Display what will be migrated."""
        self.stdout.write(self.style.NOTICE('\n📊 Migration Plan:\n'))

        # Count legacy records
        entity_count = XX_Entity.objects.count()
        account_count = XX_Account.objects.count()
        project_count = XX_Project.objects.count()

        if not options['account_only'] and not options['project_only']:
            self.stdout.write(f'  Entities to migrate: {entity_count}')
        if not options['entity_only'] and not options['project_only']:
            self.stdout.write(f'  Accounts to migrate: {account_count}')
        if not options['entity_only'] and not options['account_only']:
            self.stdout.write(f'  Projects to migrate: {project_count}')

        # Count existing dynamic segments
        existing_segments = XX_Segment.objects.values('segment_type__segment_name').annotate(
            count=Count('id')
        )
        if existing_segments:
            self.stdout.write('\n  Existing dynamic segments:')
            for seg in existing_segments:
                self.stdout.write(f'    {seg["segment_type__segment_name"]}: {seg["count"]}')

        self.stdout.write(f'\n  Batch size: {options["batch_size"]}')

    def migrate_segments(self, options):
        """Perform the actual migration."""
        batch_size = options['batch_size']
        
        # Migrate entities
        if not options['account_only'] and not options['project_only']:
            self.stdout.write('\n🔄 Migrating entities...')
            self.migrate_entity_segments(batch_size, options['dry_run'], options['force'])

        # Migrate accounts
        if not options['entity_only'] and not options['project_only']:
            self.stdout.write('\n🔄 Migrating accounts...')
            self.migrate_account_segments(batch_size, options['dry_run'], options['force'])

        # Migrate projects
        if not options['entity_only'] and not options['account_only']:
            self.stdout.write('\n🔄 Migrating projects...')
            self.migrate_project_segments(batch_size, options['dry_run'], options['force'])

    def migrate_entity_segments(self, batch_size, dry_run, force):
        """Migrate XX_Entity to XX_Segment."""
        try:
            segment_type = XX_SegmentType.objects.get(segment_name='Entity')
        except XX_SegmentType.DoesNotExist:
            self.stdout.write(self.style.ERROR('  ❌ Entity segment type not found'))
            return

        entities = XX_Entity.objects.all()
        total = entities.count()
        processed = 0

        for i in range(0, total, batch_size):
            batch = entities[i:i + batch_size]
            
            if not dry_run:
                with transaction.atomic():
                    for entity in batch:
                        result = SegmentManager.migrate_legacy_segment_to_dynamic(
                            legacy_model_name='XX_Entity',
                            legacy_code=entity.entity_code,
                            segment_type_name='Entity',
                            force=force
                        )
                        
                        if result['success']:
                            self.stats['entities_migrated'] += 1
                        else:
                            self.stats['entities_skipped'] += 1
                            if result['message']:
                                self.stats['errors'].append(f"Entity {entity.entity_code}: {result['message']}")
            else:
                self.stats['entities_migrated'] += len(batch)

            processed += len(batch)
            self.stdout.write(f'  Progress: {processed}/{total} entities', ending='\r')

        self.stdout.write(f'  ✓ Processed {total} entities' + ' ' * 20)

    def migrate_account_segments(self, batch_size, dry_run, force):
        """Migrate XX_Account to XX_Segment."""
        try:
            segment_type = XX_SegmentType.objects.get(segment_name='Account')
        except XX_SegmentType.DoesNotExist:
            self.stdout.write(self.style.ERROR('  ❌ Account segment type not found'))
            return

        accounts = XX_Account.objects.all()
        total = accounts.count()
        processed = 0

        for i in range(0, total, batch_size):
            batch = accounts[i:i + batch_size]
            
            if not dry_run:
                with transaction.atomic():
                    for account in batch:
                        result = SegmentManager.migrate_legacy_segment_to_dynamic(
                            legacy_model_name='XX_Account',
                            legacy_code=account.account_code,
                            segment_type_name='Account',
                            force=force
                        )
                        
                        if result['success']:
                            self.stats['accounts_migrated'] += 1
                        else:
                            self.stats['accounts_skipped'] += 1
                            if result['message']:
                                self.stats['errors'].append(f"Account {account.account_code}: {result['message']}")
            else:
                self.stats['accounts_migrated'] += len(batch)

            processed += len(batch)
            self.stdout.write(f'  Progress: {processed}/{total} accounts', ending='\r')

        self.stdout.write(f'  ✓ Processed {total} accounts' + ' ' * 20)

    def migrate_project_segments(self, batch_size, dry_run, force):
        """Migrate XX_Project to XX_Segment."""
        try:
            segment_type = XX_SegmentType.objects.get(segment_name='Project')
        except XX_SegmentType.DoesNotExist:
            self.stdout.write(self.style.ERROR('  ❌ Project segment type not found'))
            return

        projects = XX_Project.objects.all()
        total = projects.count()
        processed = 0

        for i in range(0, total, batch_size):
            batch = projects[i:i + batch_size]
            
            if not dry_run:
                with transaction.atomic():
                    for project in batch:
                        result = SegmentManager.migrate_legacy_segment_to_dynamic(
                            legacy_model_name='XX_Project',
                            legacy_code=project.project_code,
                            segment_type_name='Project',
                            force=force
                        )
                        
                        if result['success']:
                            self.stats['projects_migrated'] += 1
                        else:
                            self.stats['projects_skipped'] += 1
                            if result['message']:
                                self.stats['errors'].append(f"Project {project.project_code}: {result['message']}")
            else:
                self.stats['projects_migrated'] += len(batch)

            processed += len(batch)
            self.stdout.write(f'  Progress: {processed}/{total} projects', ending='\r')

        self.stdout.write(f'  ✓ Processed {total} projects' + ' ' * 20)

    def display_migration_results(self, dry_run):
        """Display migration statistics."""
        self.stdout.write(self.style.SUCCESS('\n\n✅ Migration Complete!\n'))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('  (Dry run - no actual changes made)\n'))
        
        self.stdout.write('📊 Migration Statistics:\n')
        self.stdout.write(f'  Entities:')
        self.stdout.write(f'    Migrated: {self.stats["entities_migrated"]}')
        self.stdout.write(f'    Skipped:  {self.stats["entities_skipped"]}')
        
        self.stdout.write(f'\n  Accounts:')
        self.stdout.write(f'    Migrated: {self.stats["accounts_migrated"]}')
        self.stdout.write(f'    Skipped:  {self.stats["accounts_skipped"]}')
        
        self.stdout.write(f'\n  Projects:')
        self.stdout.write(f'    Migrated: {self.stats["projects_migrated"]}')
        self.stdout.write(f'    Skipped:  {self.stats["projects_skipped"]}')
        
        total_migrated = (
            self.stats["entities_migrated"] + 
            self.stats["accounts_migrated"] + 
            self.stats["projects_migrated"]
        )
        total_skipped = (
            self.stats["entities_skipped"] + 
            self.stats["accounts_skipped"] + 
            self.stats["projects_skipped"]
        )
        
        self.stdout.write(f'\n  Total Migrated: {total_migrated}')
        self.stdout.write(f'  Total Skipped:  {total_skipped}')
        
        if self.stats['errors']:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Errors encountered: {len(self.stats["errors"])}'))
            self.stdout.write('\n  First 10 errors:')
            for error in self.stats['errors'][:10]:
                self.stdout.write(f'    - {error}')
            
            if len(self.stats['errors']) > 10:
                self.stdout.write(f'    ... and {len(self.stats["errors"]) - 10} more')
        
        if not dry_run:
            self.stdout.write(self.style.NOTICE('\n📝 Next Steps:\n'))
            self.stdout.write('  1. Verify migrated data in Django admin')
            self.stdout.write('  2. Update transaction records to use XX_TransactionSegment')
            self.stdout.write('  3. Test budget transfers with new segment structure')
            self.stdout.write('  4. Update Oracle integration to use dynamic segments')
            self.stdout.write('  5. After verification, consider archiving legacy tables\n')
