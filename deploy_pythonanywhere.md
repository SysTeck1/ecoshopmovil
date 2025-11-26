# 🚀 Deploy SistemaPOS on PythonAnywhere

## 📋 Prerequisites

1. **PythonAnywhere Account** (Free or Paid)
2. **GitHub Repository** with your SistemaPOS code
3. **MySQL Database** (setup on PythonAnywhere)

## 🔧 Step-by-Step Configuration

### 1. **Clone Your Repository**

```bash
# In PythonAnywhere Bash console
git clone https://github.com/yourusername/SistemaPOS.git
cd SistemaPOS
```

### 2. **Set Up Virtual Environment**

```bash
# Create virtual environment
mkvirtualenv --python=/usr/bin/python3.10 sistemapos-env

# Activate virtual environment
workon sistemapos-env

# Install dependencies
pip install -r requirements.txt
pip install mysqlclient
```

### 3. **Configure Database**

1. Go to **Databases** tab in PythonAnywhere
2. Create a MySQL database
3. Note your database credentials
4. Update `pythonanywhere_config.py` with your credentials

### 4. **Update Settings**

Create a production settings file:

```python
# SistemaPOS/production_settings.py
from .settings import *
from pythonanywhere_config import *

# Override production settings
DEBUG = False
ALLOWED_HOSTS = ['yourusername.pythonanywhere.com']

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = '/home/yourusername/SistemaPOS/staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = '/home/yourusername/SistemaPOS/media'
```

### 5. **Configure WSGI**

1. Go to **Web** tab in PythonAnywhere
2. Click **Add a new web app**
3. Choose **Manual Configuration** (Python 3.10)
4. In the **WSGI configuration file**, replace the content with:

```python
import os
import sys

# Add your project path
project_home = '/home/yourusername/SistemaPOS'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.production_settings')

# Import Django
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 6. **Collect Static Files**

```bash
# In PythonAnywhere Bash console
workon sistemapos-env
cd /home/yourusername/SistemaPOS

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 7. **Configure Static Files**

In the **Web** tab, set:
- **Static files URL**: `/static/`
- **Static files directory**: `/home/yourusername/SistemaPOS/staticfiles`

### 8. **Set Up Worker**

For background tasks (optional):

```bash
# In PythonAnywhere Tasks tab
# Add a scheduled task to run:
cd /home/yourusername/SistemaPOS && workon sistemapos-env && python manage.py runworker
```

## 🔧 Important Files to Update

### 1. **wsgi.py** (Already configured)
```python
# The file is already configured for PythonAnywhere
# Just update the project_path with your username
project_path = '/home/yourusername/SistemaPOS'
```

### 2. **pythonanywhere_config.py** (Created)
Update with your actual credentials:
- `yourusername` → Your PythonAnywhere username
- Database credentials
- Email settings

### 3. **production_settings.py** (Create)
```python
from .settings import *
from pythonanywhere_config import *

DEBUG = False
ALLOWED_HOSTS = ['yourusername.pythonanywhere.com']
```

## 🚀 Deployment Commands

```bash
# Pull latest changes
git pull origin main

# Install new dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Restart web app (in PythonAnywhere Web tab)
```

## 🔍 Troubleshooting

### Common Issues:

1. **500 Error**: Check logs in PythonAnywhere Web tab
2. **Static Files 404**: Ensure STATIC_ROOT is correctly set
3. **Database Connection**: Verify MySQL credentials
4. **Module Not Found**: Check virtual environment activation

### Log Files Location:
- **Web App Logs**: `/var/log/www.yourusername.pythonanywhere.com.error.log`
- **Django Logs**: `/home/yourusername/SistemaPOS/django.log`

## 🎯 Final Steps

1. **Test your site**: Visit `https://yourusername.pythonanywhere.com`
2. **Create admin user**: `python manage.py createsuperuser`
3. **Test all functionality**: Sales, products, reports
4. **Set up backup**: Regular database backups

## 📞 Support

- **PythonAnywhere Forums**: For deployment issues
- **Django Documentation**: For configuration help
- **GitHub Issues**: For application bugs

---

**🎉 Your SistemaPOS should now be live on PythonAnywhere!**
