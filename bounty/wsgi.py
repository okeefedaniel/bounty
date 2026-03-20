"""WSGI config for Bounty project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bounty.settings')
application = get_wsgi_application()
