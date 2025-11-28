#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from dashboard.views import VentasView

def debug_ventas_view():
    print("🔍 Debugging VentasView...")
    
    # Crear un request factory
    factory = RequestFactory()
    
    # Crear un request GET simulado
    request = factory.get('/dashboard/ventas/')
    
    # Crear un usuario y asignarlo al request
    try:
        user = User.objects.first()
        if not user:
            print("❌ No hay usuarios en la base de datos")
            return
        request.user = user
        print(f"✅ Usuario encontrado: {user.username}")
    except Exception as e:
        print(f"❌ Error al obtener usuario: {e}")
        return
    
    # Intentar crear la vista y obtener el contexto
    try:
        view = VentasView()
        view.request = request
        context = view.get_context_data()
        print("✅ Contexto obtenido exitosamente")
        print(f"   - Clientes: {len(context.get('clientes', []))}")
        print(f"   - Productos: {len(context.get('productos', []))}")
        print(f"   - Invoices count: {context.get('invoices_count', 0)}")
        print(f"   - Global tax enabled: {context.get('global_tax_enabled', False)}")
        print(f"   - Global tax rate: {context.get('global_tax_rate', 0)}")
        
    except Exception as e:
        print(f"❌ Error en get_context_data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_ventas_view()
