"""
WSGI config for SistemaPOS project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# PythonAnywhere specific configuration
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')

# Add the project path to sys.path for PythonAnywhere
import sys
project_path = '/home/yourusername/SistemaPOS'  # Replace with your actual PythonAnywhere username
if project_path not in sys.path:
    sys.path.append(project_path)

application = get_wsgi_application()
