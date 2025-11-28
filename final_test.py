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

# Probar endpoint de reportes
response = client.get('/app/reportes/ventas-totales/')
print(f'Status: {response.status_code}')

if response.status_code == 200:
    print('✅ Endpoint de reportes funciona correctamente')
    data = response.json()
    print(f'Ventas totales: {data.get("total_sales_display", "N/A")}')
    print(f'Número de ventas: {data.get("ventas", "N/A")}')
    print(f'Filas incluidas: {len(data.get("rows", []))}')
else:
    print(f'❌ Error: {response.status_code}')
    print(f'Contenido: {response.content.decode()[:300]}...')

# Probar página de reportes
response = client.get('/app/otros/reportes/')
print(f'Página reportes Status: {response.status_code}')

if response.status_code == 200:
    print('✅ Página de reportes funciona')
    if 'reportes-dashboard.js' in response.content.decode():
        print('✅ JavaScript incluido')
    else:
        print('⚠️ JavaScript no encontrado')
else:
    print(f'❌ Error página: {response.status_code}')
