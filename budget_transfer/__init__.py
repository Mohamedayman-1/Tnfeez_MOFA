# This will make sure the Celery app is always imported when Django starts
from config.celery import app as celery_app
#import sqlite_fix
__all__ = ('celery_app',)
