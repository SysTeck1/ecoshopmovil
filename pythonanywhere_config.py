# PythonAnywhere configuration for SistemaPOS
# This file contains the path configuration needed for PythonAnywhere deployment

import os
import sys

# Add your project directory to Python path
# Replace 'yourusername' with your actual PythonAnywhere username
PROJECT_DIR = '/home/yourusername/SistemaPOS'

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')

# Static files configuration for PythonAnywhere
STATIC_ROOT = os.path.join(PROJECT_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')

# Database configuration for PythonAnywhere
# You'll need to set up a MySQL database on PythonAnywhere
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'yourusername$sistemapos',  # Replace with your database name
        'USER': 'yourusername',             # Replace with your username
        'PASSWORD': 'your_database_password',  # Replace with your database password
        'HOST': 'yourusername.mysql.pythonanywhere-services.com',  # Replace with your username
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Security settings for production
DEBUG = False
ALLOWED_HOSTS = ['yourusername.pythonanywhere.com']  # Replace with your domain

# Email configuration (optional)
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@gmail.com'
EMAIL_HOST_PASSWORD = 'your_email_password'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(PROJECT_DIR, 'django.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
