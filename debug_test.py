import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

User = get_user_model()
user = User.objects.filter(username='admin').first()
if not user:
    user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')

client = Client()
client.force_login(user)

# Probar endpoint simple
print("🔍 Probando endpoint simple de prueba...")

# Probar página de login primero
response = client.get('/admin/')
print(f'Login page status: {response.status_code}')

# Probar dashboard
response = client.get('/app/ventas/')
print(f'Dashboard status: {response.status_code}')

# Probar página de reportes
response = client.get('/app/otros/reportes/')
print(f'Reportes page status: {response.status_code}')

# Probar endpoint con problema
print("\n🔍 Analizando endpoint problemático...")

# Verificar si el problema está en las importaciones
try:
    from dashboard.views import report_total_sales_api
    print("✅ Importación de report_total_sales_api exitosa")
    
    # Probar llamando directamente a la función
    from django.test import RequestFactory
    factory = RequestFactory()
    request = factory.get('/app/reportes/ventas-totales/')
    request.user = user
    
    response = report_total_sales_api(request)
    print(f"✅ Función directa funciona: {response.status_code}")
    
except Exception as e:
    print(f"❌ Error importando o ejecutando función: {e}")
    import traceback
    traceback.print_exc()

# Verificar URLs
print("\n🔍 Verificando configuración de URLs...")
try:
    from django.urls import reverse
    url = reverse('report_total_sales_api')
    print(f'✅ URL reverse funciona: {url}')
    
    # Probar con el cliente
    response = client.get(url)
    print(f'✅ Cliente con reverse: {response.status_code}')
    
except Exception as e:
    print(f"❌ Error con URLs: {e}")
    import traceback
    traceback.print_exc()
