"""
Pytest configuration for Django tests.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')

# Setup Django
if not settings.configured:
    django.setup()


