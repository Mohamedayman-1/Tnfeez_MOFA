"""
Management command to sync and display registered execution points.
"""

from django.core.management.base import BaseCommand
from django_dynamic_validation.execution_point_registry import execution_point_registry
from django_dynamic_validation.models import ValidationWorkflow


class Command(BaseCommand):
    help = 'Sync and display registered execution points (with cleanup of orphaned workflows)'
    
    def handle(self, *args, **options):
        # Import example execution points to ensure they're registered
        try:
            import django_dynamic_validation.execution_points
        except ImportError:
            pass
        
        points = execution_point_registry.list_all()
        categories = execution_point_registry.get_categories()
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        self.stdout.write(self.style.SUCCESS(f'REGISTERED EXECUTION POINTS'))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))
        
        self.stdout.write(f"Total execution points: {len(points)}")
        self.stdout.write(f"Categories: {', '.join(categories)}\n")
        
        # Group by category
        for category in sorted(categories):
            category_points = execution_point_registry.list_by_category(category)
            
            self.stdout.write(self.style.WARNING(f'\n{category.upper()} ({len(category_points)} points)'))
            self.stdout.write('-' * 70)
            
            for point in sorted(category_points, key=lambda x: x['name']):
                self.stdout.write(
                    f"  • {self.style.SUCCESS(point['code']):<30} {point['name']}"
                )
                if point['description']:
                    self.stdout.write(f"    {point['description']}")
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        
        # Check for workflows with execution points not in registry
        registered_codes = {point['code'] for point in points}
        orphaned_workflows = ValidationWorkflow.objects.exclude(
            execution_point__in=registered_codes
        )
        
        if orphaned_workflows.exists():
            orphaned_count = orphaned_workflows.count()
            self.stdout.write(
                self.style.WARNING(
                    f'\nFound {orphaned_count} workflow(s) referencing non-existent execution points:'
                )
            )
            for workflow in orphaned_workflows:
                self.stdout.write(
                    self.style.WARNING(
                        f'  - Workflow "{workflow.name}" (ID: {workflow.id}) '
                        f'references "{workflow.execution_point}"'
                    )
                )
            
            # Delete orphaned workflows
            self.stdout.write(
                self.style.NOTICE(
                    '\nDeleting workflows with orphaned execution points...'
                )
            )
            deleted_count, _ = orphaned_workflows.delete()
            self.stdout.write(
                self.style.ERROR(
                    f'  Deleted {deleted_count} orphaned workflow(s)'
                )
            )
        
        self.stdout.write(self.style.SUCCESS('\nExecution points synced successfully!\n'))
