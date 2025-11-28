import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from dashboard.views import get_filtered_sales_queryset, build_sales_report
from ventas.models import Venta

User = get_user_model()
user = User.objects.filter(username='admin').first()
if not user:
    user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')

client = Client()
client.force_login(user)

# Probar endpoint simple
print("🔍 Probando endpoint de reportes...")
response = client.get('/app/reportes/ventas-totales/')
print(f'Status: {response.status_code}')

if response.status_code == 200:
    print('✅ Endpoint funciona correctamente')
    print(f'Size: {len(response.content)} bytes')
    
    # Probar cache
    import time
    start = time.time()
    response2 = client.get('/app/reportes/ventas-totales/')
    cached_time = time.time() - start
    
    print(f'⚡ Tiempo con cache: {cached_time:.3f}s')
    
else:
    print(f'❌ Error: {response.status_code}')
    print(f'Contenido: {response.content.decode()[:300]}...')
    
    # Probar las funciones directamente
    print("\n🔧 Probando funciones directamente...")
    
    # Crear request mock
    from django.test import RequestFactory
    factory = RequestFactory()
    request = factory.get('/app/reportes/ventas-totales/')
    request.user = user
    
    try:
        queryset, start_date, end_date = get_filtered_sales_queryset(request)
        print(f'✅ get_filtered_sales_queryset funciona')
        print(f'   Queryset: {queryset.count()} ventas')
        
        total_sales, total_cost, total_discount, total_trade_in, report_rows, ventas_count = build_sales_report(queryset)
        print(f'✅ build_sales_report funciona')
        print(f'   Total ventas: {total_sales}')
        print(f'   Total costos: {total_cost}')
        print(f'   Ventas count: {ventas_count}')
        
    except Exception as e:
        print(f'❌ Error en funciones: {e}')
        import traceback
        traceback.print_exc()
