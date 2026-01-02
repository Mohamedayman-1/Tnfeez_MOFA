from django.apps import AppConfig

class UserManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_management'
    verbose_name = 'User Management'
    
    def ready(self):
        """Import signals when app is ready."""
        import user_management.signals  # noqa
        import user_management.audit_signals  # noqa - Import audit signals
