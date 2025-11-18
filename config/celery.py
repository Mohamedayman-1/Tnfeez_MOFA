"""
Celery configuration for Tnfeez_MOFA project
"""
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')

app = Celery('tnfeez_mofa')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure eager mode for testing (tasks run synchronously when True)
# Set to False in production
app.conf.task_always_eager = False
app.conf.task_eager_propagates = False


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
