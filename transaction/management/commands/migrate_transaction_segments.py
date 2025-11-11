"""
Management command to migrate legacy transaction data to dynamic segment structure.

This command syncs the legacy segment fields (cost_center_code, account_code, project_code)
to the new XX_TransactionSegment table.

Usage:
    python manage.py migrate_transaction_segments
    python manage.py migrate_transaction_segments --dry-run
    python manage.py migrate_transaction_segments --batch-size 1000
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction
from transaction.models import xx_TransactionTransfer
from transaction.managers import TransactionSegmentManager


class Command(BaseCommand):
    help = 'Migrate legacy transaction segment data to dynamic segment structure'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
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
            '--force',
            action='store_true',
            help='Force migration even if segments already exist',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Transaction Segment Migration ===\n'))

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
            
            self.migrate_transactions(options)
            
            # Display results
            self.display_migration_results(options['dry_run'])

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Migration failed: {str(e)}'))
            raise

    def display_migration_plan(self, options):
        """Display what will be migrated."""
        self.stdout.write(self.style.NOTICE('\n📊 Migration Plan:\n'))

        # Count transactions
        from account_and_entitys.models import XX_TransactionSegment
        
        total_transactions = xx_TransactionTransfer.objects.count()
        
        # Count transactions that already have dynamic segments
        transactions_with_segments = XX_TransactionSegment.objects.values_list(
            'transaction_transfer_id', flat=True
        ).distinct().count()
        
        transactions_to_migrate = total_transactions - transactions_with_segments

        self.stdout.write(f'  Total transactions: {total_transactions}')
        self.stdout.write(f'  Already migrated: {transactions_with_segments}')
        self.stdout.write(f'  To be migrated: {transactions_to_migrate}')
        self.stdout.write(f'\n  Batch size: {options["batch_size"]}')

    def migrate_transactions(self, options):
        """Perform the actual migration."""
        batch_size = options['batch_size']
        force = options['force']
        dry_run = options['dry_run']
        
        self.stdout.write('\n🔄 Migrating transaction segments...')
        
        if not dry_run:
            result = TransactionSegmentManager.bulk_migrate_legacy_transactions(
                batch_size=batch_size
            )
            
            self.stats['total_processed'] = result['total_processed']
            self.stats['successful'] = result['successful']
            self.stats['failed'] = result['failed']
            self.stats['errors'] = result['errors']
        else:
            # Dry run - just count
            from account_and_entitys.models import XX_TransactionSegment
            
            transactions_to_migrate = xx_TransactionTransfer.objects.exclude(
                transfer_id__in=XX_TransactionSegment.objects.values_list(
                    'transaction_transfer_id', flat=True
                ).distinct()
            )
            
            self.stats['total_processed'] = transactions_to_migrate.count()
            self.stats['successful'] = transactions_to_migrate.count()

    def display_migration_results(self, dry_run):
        """Display migration statistics."""
        self.stdout.write(self.style.SUCCESS('\n\n✅ Migration Complete!\n'))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('  (Dry run - no actual changes made)\n'))
        
        self.stdout.write('📊 Migration Statistics:\n')
        self.stdout.write(f'  Total Processed: {self.stats["total_processed"]}')
        self.stdout.write(f'  Successful:      {self.stats["successful"]}')
        self.stdout.write(f'  Failed:          {self.stats["failed"]}')
        self.stdout.write(f'  Skipped:         {self.stats["skipped"]}')
        
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
            self.stdout.write('  2. Test transaction creation with new segment structure')
            self.stdout.write('  3. Update API endpoints to use new serializers')
            self.stdout.write('  4. Test Oracle journal entry generation')
            self.stdout.write('  5. Update frontend to use dynamic segment fields\n')
