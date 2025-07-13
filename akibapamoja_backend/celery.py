import logging
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'akibapamoja_backend.settings')

if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    raise EnvironmentError("DJANGO_SETTINGS_MODULE environment variable is not set.")

app = Celery('akibapamoja_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Ensure broker and backend are explicitly set in Django settings.py:
# CELERY_BROKER_URL = 'redis://localhost:6379/0'
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

app.autodiscover_tasks(settings.INSTALLED_APPS)

logger = logging.getLogger(__name__)

@app.task(bind=True)
def debug_task(self):
    try:
        logger.debug(f'Request: {self.request!r}')
    except Exception as e:
        logger.error(f"Error in debug_task: {e}")

if __name__ == '__main__':
    # This allows the file to be run as a script.
    pass