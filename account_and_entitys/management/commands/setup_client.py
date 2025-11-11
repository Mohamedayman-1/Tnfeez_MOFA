"""
Management command to set up client-specific segment configuration.
This interactive command helps configure dynamic segments for a new client installation.

Usage:
    python manage.py setup_client
    python manage.py setup_client --config path/to/config.json
    python manage.py setup_client --interactive
"""
import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from account_and_entitys.models import XX_SegmentType, XX_Segment


class Command(BaseCommand):
    help = 'Set up client-specific segment configuration for dynamic segments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            help='Path to JSON configuration file',
        )
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Run in interactive mode to configure segments',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force overwrite of existing segment configuration',
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate the configuration without applying changes',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Tnfeez Dynamic Segment Setup ===\n'))

        # Determine configuration source
        if options['config']:
            config = self.load_config_from_file(options['config'])
        elif options['interactive']:
            config = self.interactive_configuration()
        else:
            # Use default config
            default_config_path = os.path.join('config', 'segments_config.json')
            if os.path.exists(default_config_path):
                config = self.load_config_from_file(default_config_path)
            else:
                raise CommandError('No configuration provided. Use --config, --interactive, or ensure config/segments_config.json exists.')

        # Validate configuration
        self.stdout.write('\n📋 Validating configuration...')
        validation_errors = self.validate_config(config)
        if validation_errors:
            self.stdout.write(self.style.ERROR('\n❌ Configuration validation failed:'))
            for error in validation_errors:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
            raise CommandError('Configuration validation failed. Please fix the errors and try again.')
        
        self.stdout.write(self.style.SUCCESS('✓ Configuration is valid'))

        # Display configuration summary
        self.display_configuration_summary(config)

        # Validate only mode
        if options['validate_only']:
            self.stdout.write(self.style.SUCCESS('\n✓ Validation complete (no changes applied)\n'))
            return

        # Check for existing configuration
        existing_segments = XX_SegmentType.objects.exists()
        if existing_segments and not options['force']:
            self.stdout.write(self.style.WARNING('\n⚠️  Existing segment configuration detected!'))
            confirm = input('Do you want to overwrite the existing configuration? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Setup cancelled.'))
                return

        # Apply configuration
        try:
            with transaction.atomic():
                self.apply_configuration(config, options['force'])
            self.stdout.write(self.style.SUCCESS('\n✅ Client configuration applied successfully!\n'))
            self.display_next_steps()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Failed to apply configuration: {str(e)}'))
            raise

    def load_config_from_file(self, file_path):
        """Load configuration from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.stdout.write(self.style.SUCCESS(f'✓ Loaded configuration from {file_path}'))
            return config
        except FileNotFoundError:
            raise CommandError(f'Configuration file not found: {file_path}')
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON in configuration file: {str(e)}')

    def interactive_configuration(self):
        """Interactive mode to configure segments."""
        self.stdout.write(self.style.NOTICE('\n🔧 Interactive Segment Configuration\n'))

        config = {
            'client_id': input('Client ID: ').strip(),
            'client_name': input('Client Name: ').strip(),
            'installation_date': datetime.now().strftime('%Y-%m-%d'),
            'segments': [],
            'oracle_config': {
                'max_segments_supported': 30,
                'ledger_id': input('Oracle Ledger ID: ').strip(),
                'balance_report_segment_mapping': {}
            },
            'validation_rules': {
                'allow_cross_segment_transfers': True,
                'require_envelope_check': True,
                'enforce_hierarchy_constraints': True
            }
        }

        # Number of segments
        while True:
            try:
                num_segments = int(input('\nHow many segments does this client need? (2-30): '))
                if 2 <= num_segments <= 30:
                    break
                else:
                    self.stdout.write(self.style.ERROR('Please enter a number between 2 and 30.'))
            except ValueError:
                self.stdout.write(self.style.ERROR('Please enter a valid number.'))

        # Configure each segment
        for i in range(num_segments):
            self.stdout.write(self.style.NOTICE(f'\n--- Segment {i + 1} Configuration ---'))
            segment = {
                'segment_id': i + 1,
                'segment_name': input(f'Segment {i + 1} Name: ').strip(),
                'segment_type': input(f'Segment {i + 1} Type (cost_center/account/project/custom): ').strip(),
                'oracle_segment_number': i + 1,
                'is_required': input(f'Is this segment required? (yes/no): ').lower() == 'yes',
                'has_hierarchy': input(f'Does this segment have hierarchy? (yes/no): ').lower() == 'yes',
                'max_length': 50,
                'display_order': i + 1,
                'description': input(f'Description: ').strip()
            }
            config['segments'].append(segment)
            config['oracle_config']['balance_report_segment_mapping'][f'segment{i + 1}'] = i + 1

        return config

    def validate_config(self, config):
        """Validate the configuration."""
        errors = []

        # Required top-level fields
        required_fields = ['client_id', 'segments', 'oracle_config']
        for field in required_fields:
            if field not in config:
                errors.append(f'Missing required field: {field}')

        if 'segments' in config:
            # Number of segments
            num_segments = len(config['segments'])
            if num_segments < 2 or num_segments > 30:
                errors.append(f'Invalid number of segments: {num_segments}. Must be between 2 and 30.')

            # Validate each segment
            segment_ids = set()
            oracle_numbers = set()
            for segment in config['segments']:
                # Required segment fields
                required_segment_fields = ['segment_id', 'segment_name', 'oracle_segment_number', 'is_required']
                for field in required_segment_fields:
                    if field not in segment:
                        errors.append(f'Segment missing required field: {field}')

                # Unique segment_id
                if 'segment_id' in segment:
                    if segment['segment_id'] in segment_ids:
                        errors.append(f'Duplicate segment_id: {segment["segment_id"]}')
                    segment_ids.add(segment['segment_id'])

                # Unique oracle_segment_number
                if 'oracle_segment_number' in segment:
                    if segment['oracle_segment_number'] in oracle_numbers:
                        errors.append(f'Duplicate oracle_segment_number: {segment["oracle_segment_number"]}')
                    oracle_numbers.add(segment['oracle_segment_number'])

                # Oracle segment number range
                if 'oracle_segment_number' in segment:
                    if not (1 <= segment['oracle_segment_number'] <= 30):
                        errors.append(f'Invalid oracle_segment_number {segment["oracle_segment_number"]}. Must be between 1 and 30.')

        return errors

    def display_configuration_summary(self, config):
        """Display a summary of the configuration."""
        self.stdout.write(self.style.NOTICE('\n📊 Configuration Summary:\n'))
        self.stdout.write(f'  Client ID: {config.get("client_id", "N/A")}')
        self.stdout.write(f'  Client Name: {config.get("client_name", "N/A")}')
        self.stdout.write(f'  Number of Segments: {len(config.get("segments", []))}')
        self.stdout.write(f'  Oracle Ledger ID: {config.get("oracle_config", {}).get("ledger_id", "N/A")}')
        
        self.stdout.write('\n  Segments:')
        for segment in config.get('segments', []):
            required_mark = '✓' if segment.get('is_required') else ' '
            hierarchy_mark = '🌳' if segment.get('has_hierarchy') else '  '
            self.stdout.write(f'    [{required_mark}] {hierarchy_mark} Segment {segment.get("segment_id")}: {segment.get("segment_name")} ({segment.get("segment_type")})')

    def apply_configuration(self, config, force=False):
        """Apply the configuration to the database."""
        self.stdout.write('\n🚀 Applying configuration...\n')

        # Clear existing configuration if force
        if force:
            self.stdout.write('  Clearing existing segment types...')
            XX_SegmentType.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('  ✓ Cleared'))

        # Create segment types
        self.stdout.write('  Creating segment types...')
        segment_types_created = 0
        for segment_config in config['segments']:
            segment_type, created = XX_SegmentType.objects.update_or_create(
                segment_id=segment_config['segment_id'],
                defaults={
                    'segment_name': segment_config['segment_name'],
                    'segment_type': segment_config.get('segment_type', 'custom'),
                    'oracle_segment_number': segment_config['oracle_segment_number'],
                    'is_required': segment_config['is_required'],
                    'has_hierarchy': segment_config.get('has_hierarchy', False),
                    'max_length': segment_config.get('max_length', 50),
                    'display_order': segment_config.get('display_order', segment_config['segment_id']),
                    'description': segment_config.get('description', ''),
                    'is_active': True
                }
            )
            if created:
                segment_types_created += 1
            self.stdout.write(f'  {"✓ Created" if created else "✓ Updated"}: {segment_type.segment_name}')

        self.stdout.write(self.style.SUCCESS(f'\n  ✓ {segment_types_created} segment types created'))

        # Save configuration metadata
        config_file_path = os.path.join('config', f'segments_config_{config["client_id"]}.json')
        os.makedirs('config', exist_ok=True)
        with open(config_file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Configuration saved to {config_file_path}'))

    def display_next_steps(self):
        """Display next steps after configuration."""
        self.stdout.write(self.style.NOTICE('\n📝 Next Steps:\n'))
        self.stdout.write('  1. Load segment values (entities, accounts, projects) into XX_Segment table')
        self.stdout.write('  2. If migrating from legacy system, run: python manage.py migrate_legacy_segments')
        self.stdout.write('  3. Configure envelopes and mappings in Django admin')
        self.stdout.write('  4. Update Oracle Fusion integration settings')
        self.stdout.write('  5. Test budget transfers with new segment configuration')
        self.stdout.write('\n  📚 Refer to documentation in __CLIENT_SETUP_DOCS__/ for detailed guides\n')
