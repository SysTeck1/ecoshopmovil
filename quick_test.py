import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(username='admin').first()
if not user:
    user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')

client = Client()
client.force_login(user)

# Probar endpoint
response = client.get('/app/reportes/ventas-totales/')
print(f'Status: {response.status_code}')
if response.status_code == 200:
    print(f'Size: {len(response.content)} bytes')
    print(f'Content-Type: {response.get("Content-Type", "N/A")}')
    print(f'Compression: {response.get("Content-Encoding", "N/A")}')
    print(f'X-Compression-Ratio: {response.get("X-Compression-Ratio", "N/A")}')
else:
    print(f'Error: {response.content[:200]}')
