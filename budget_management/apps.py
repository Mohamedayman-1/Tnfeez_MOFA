from django.apps import AppConfig

class BudgetManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budget_management'
    verbose_name = 'Budget Management'

    def ready(self):
        """
        Initialize signals when the app is ready
        This ensures signals are registered when Django starts
        """
        try:
            import budget_management.signals
            print("[OK] Budget management signals registered")
        except Exception as e:
            print(f"[ERROR] Error registering budget management signals: {e}")
