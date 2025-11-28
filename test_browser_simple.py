#!/usr/bin/env python
"""
Prueba simple para verificar que los endpoints funcionen en el navegador
"""

import requests
import time

def test_endpoints():
    """Probar endpoints directamente con requests"""
    
    base_url = "http://127.0.0.1:8000"
    session = requests.Session()
    
    print("🚀 INICIANDO PRUEBAS DIRECTAS AL SERVIDOR")
    print("=" * 50)
    
    # 1. Probar página de login
    print("🔍 Probando página de login...")
    try:
        response = session.get(f"{base_url}/admin/")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Página de login accesible")
        else:
            print(f"   ❌ Error: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return
    
    # 2. Iniciar sesión
    print("\n🔐 Iniciando sesión...")
    try:
        # Obtener token CSRF
        csrf_token = None
        if 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
        
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(f"{base_url}/admin/", data=login_data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 302 or 'dashboard' in response.text:
            print("   ✅ Sesión iniciada correctamente")
        else:
            print("   ❌ Error en login")
            print(f"   Contenido: {response.text[:200]}...")
            return
            
    except Exception as e:
        print(f"   ❌ Error en login: {e}")
        return
    
    # 3. Probar página de reportes
    print("\n📊 Probando página de reportes...")
    try:
        response = session.get(f"{base_url}/app/otros/reportes/")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Página de reportes funciona")
            if 'reportes-dashboard.js' in response.text:
                print("   ✅ JavaScript de reportes incluido")
            else:
                print("   ⚠️  JavaScript no encontrado")
        else:
            print(f"   ❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 4. Probar endpoint de API
    print("\n🔌 Probando endpoint de API...")
    try:
        start_time = time.time()
        response = session.get(f"{base_url}/app/reportes/ventas-totales/")
        api_time = time.time() - start_time
        
        print(f"   Status: {response.status_code}")
        print(f"   Time: {api_time:.3f}s")
        
        if response.status_code == 200:
            print("   ✅ API funciona")
            print(f"   Size: {len(response.content)} bytes")
            
            # Probar cache
            start_time = time.time()
            response2 = session.get(f"{base_url}/app/reportes/ventas-totales/")
            cached_time = time.time() - start_time
            
            print(f"   ⚡ Cache time: {cached_time:.3f}s")
            print(f"   🚀 Speed improvement: {api_time/cached_time:.1f}x")
            
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Content: {response.text[:300]}...")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n🎉 PRUEBAS COMPLETADAS!")
    print(f"📝 Para probar manualmente:")
    print(f"   1. Visita: {base_url}/admin/")
    print(f"   2. Usuario: admin, Contraseña: admin123")
    print(f"   3. Visita: {base_url}/app/otros/reportes/")

if __name__ == "__main__":
    test_endpoints()
