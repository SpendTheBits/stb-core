from spend_the_bits.celery import celery_app
from .models import *

import datetime
from celery import shared_task
from celery import Celery, chain

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from django.conf import settings
from accounts.utils import send_mail
from datetime import timedelta
from django.utils import timezone


