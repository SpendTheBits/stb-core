import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spend_the_bits.settings')

celery_app = Celery('spend_the_bits')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()