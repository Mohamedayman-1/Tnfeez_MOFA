"""
Django Dynamic Validation App Configuration
"""

from django.apps import AppConfig


class DynamicValidationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_dynamic_validation'
    verbose_name = 'Dynamic Validation System'
    
    def ready(self):
        """
        Import datasource functions and execution points when app is ready.
        This ensures all datasources and execution points are registered at startup.
        """
        try:
            # Import example datasources
            from . import datasources  # noqa: F401
        except ImportError:
            pass
        
        try:
            # Import example execution points
            from . import execution_points  # noqa: F401
        except ImportError:
            pass
        
        # Try to import user-defined datasources from project
        try:
            import datasources  # noqa: F401
        except ImportError:
            pass
        
        # Try to import user-defined execution points from project
        try:
            import execution_points  # noqa: F401
        except ImportError:
            pass
