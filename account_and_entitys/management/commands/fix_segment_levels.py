"""
Django management command to fix the level column in XX_Segment table.

Calculates the correct hierarchy level for each segment based on parent_code relationships:
- Level 0: Root segments (parent_code is NULL or empty)
- Level N: Segments whose parent is at level N-1

Usage:
    python manage.py fix_segment_levels
    
    Options:
    --dry-run: Show what would be updated without making changes
    --segment-type: Only fix specific segment type (1=Entity, 2=Account, 3=Project)
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from account_and_entitys.models import XX_Segment, XX_SegmentType


class Command(BaseCommand):
    help = 'Fix hierarchy levels in XX_Segment table based on parent_code relationships'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--segment-type',
            type=int,
            choices=[1, 2, 3],
            help='Only process specific segment type (1=Entity, 2=Account, 3=Project)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        segment_type_filter = options.get('segment_type')
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Starting Segment Level Correction'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        # Get segment types to process
        if segment_type_filter:
            segment_types = XX_SegmentType.objects.filter(segment_id=segment_type_filter)
        else:
            segment_types = XX_SegmentType.objects.all().order_by('segment_id')
        
        if not segment_types.exists():
            self.stdout.write(self.style.ERROR('❌ No segment types found!'))
            return
        
        total_updated = 0
        total_segments = 0
        level_distribution = {}
        
        # Process each segment type separately
        for segment_type in segment_types:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'Processing: {segment_type.segment_name} (ID: {segment_type.segment_id})'))
            self.stdout.write('-' * 70)
            
            # Get all segments for this type
            segments = XX_Segment.objects.filter(segment_type=segment_type).select_related('segment_type')
            segment_count = segments.count()
            total_segments += segment_count
            
            self.stdout.write(f'Total segments: {segment_count}')
            
            # Build a dictionary for quick lookup: code -> segment
            segments_dict = {seg.code: seg for seg in segments}
            
            # Track levels for this segment type
            type_level_dist = {}
            updated_count = 0
            
            # Build a level map: code -> calculated_level
            level_map = {}
            
            # Iteratively calculate levels
            current_level = 0
            max_iterations = 100  # Safety limit to prevent infinite loops
            processed_codes = set()
            
            for iteration in range(max_iterations):
                if current_level == 0:
                    # Level 0: Find root segments (no parent or parent not in system)
                    level_0_segments = [
                        seg for code, seg in segments_dict.items()
                        if (not seg.parent_code or seg.parent_code.strip() == '' or 
                            seg.parent_code not in segments_dict)
                        and code not in processed_codes
                    ]
                    
                    if not level_0_segments:
                        self.stdout.write(self.style.ERROR(f'  ⚠️  No root segments found (iteration {iteration})'))
                        break
                    
                    for seg in level_0_segments:
                        level_map[seg.code] = current_level
                        if seg.level != current_level:
                            if not dry_run:
                                seg.level = current_level
                                seg.save(update_fields=['level'])
                            updated_count += 1
                        processed_codes.add(seg.code)
                        type_level_dist[current_level] = type_level_dist.get(current_level, 0) + 1
                    
                    self.stdout.write(f'  ✓ Level {current_level}: {len(level_0_segments)} segments (root nodes)')
                    
                else:
                    # Level N: Find segments whose parent is at level N-1
                    parent_codes_at_prev_level = {
                        code for code in processed_codes
                        if level_map.get(code) == current_level - 1
                    }
                    
                    if not parent_codes_at_prev_level:
                        # No more parents at previous level, we're done
                        break
                    
                    level_n_segments = [
                        seg for code, seg in segments_dict.items()
                        if seg.parent_code in parent_codes_at_prev_level
                        and code not in processed_codes
                    ]
                    
                    if not level_n_segments:
                        # No children at this level, move to next
                        current_level += 1
                        continue
                    
                    for seg in level_n_segments:
                        level_map[seg.code] = current_level
                        if seg.level != current_level:
                            if not dry_run:
                                seg.level = current_level
                                seg.save(update_fields=['level'])
                            updated_count += 1
                        processed_codes.add(seg.code)
                        type_level_dist[current_level] = type_level_dist.get(current_level, 0) + 1
                    
                    self.stdout.write(f'  ✓ Level {current_level}: {len(level_n_segments)} segments')
                
                current_level += 1
                
                # Check if all segments processed
                if len(processed_codes) == segment_count:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ All segments processed in {iteration + 1} iterations'))
                    break
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Reached max iterations ({max_iterations})'))
            
            # Check for unprocessed segments (orphans)
            unprocessed = segment_count - len(processed_codes)
            if unprocessed > 0:
                self.stdout.write(self.style.WARNING(f'  ⚠️  {unprocessed} segments not processed (orphaned/circular references)'))
                
                # Show a few examples
                orphaned_segments = [
                    seg for code, seg in segments_dict.items()
                    if code not in processed_codes
                ][:5]  # Show first 5
                
                for seg in orphaned_segments:
                    self.stdout.write(f'     - Code: {seg.code}, Parent: {seg.parent_code or "NULL"}')
            
            self.stdout.write(f'Updated: {updated_count} segments')
            
            # Merge into total distribution
            for lvl, count in type_level_dist.items():
                level_distribution[lvl] = level_distribution.get(lvl, 0) + count
            
            total_updated += updated_count
        
        # Final summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Total segments processed: {total_segments}')
        self.stdout.write(f'Total segments updated: {total_updated}')
        
        if level_distribution:
            self.stdout.write('')
            self.stdout.write('Level Distribution:')
            for level in sorted(level_distribution.keys()):
                count = level_distribution[level]
                bar = '█' * min(50, count // 10)
                self.stdout.write(f'  Level {level}: {count:4d} segments {bar}')
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('🔍 DRY RUN - No changes were made to the database'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply changes'))
        else:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✅ Level correction complete!'))
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
