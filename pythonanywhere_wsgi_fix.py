# PythonAnywhere WSGI configuration fix
# This is the correct content for your PythonAnywhere WSGI file

import os
import sys

# Add your project path
project_home = '/home/barkley5/SistemaPOS'  # Your username is barkley5
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Print debug information (optional)
print("PythonAnywhere WSGI configuration loaded successfully")
print(f"Project path: {project_home}")
print(f"Python path: {sys.path[:3]}...")  # First 3 entries
