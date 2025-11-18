# This will make sure the Celery app is always imported when Django starts
from config.celery import app as celery_app

__all__ = ('celery_app',)
