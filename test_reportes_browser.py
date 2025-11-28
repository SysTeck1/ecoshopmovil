#!/usr/bin/env python
"""
Script para probar optimizaciones de reportes desde el navegador
"""

import os
import django
import time
import requests
from datetime import datetime, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

def test_reportes_optimization():
    """Probar optimizaciones de reportes con usuario autenticado"""
    
    print("🚀 INICIANDO PRUEBAS DE REPORTES CON AUTENTICACIÓN")
    print("=" * 60)
    
    # Crear cliente de pruebas
    client = Client()
    
    # Obtener o crear usuario de prueba
    User = get_user_model()
    user = User.objects.filter(is_staff=True).first()
    
    if not user:
        print("📝 Creando usuario de administrador...")
        user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
    
    # Iniciar sesión
    from django.contrib.auth import authenticate
    user = authenticate(username='admin', password='admin123')
    if not user:
        print("❌ Error de autenticación")
        return
    
    login_success = client.force_login(user)
    print(f"✅ Sesión iniciada como: {user.username}")
    
    # Endpoints a probar
    endpoints = [
        {
            'url': '/app/reportes/ventas-totales/',
            'name': 'Ventas Totales'
        },
        {
            'url': '/app/reportes/ganancias/',
            'name': 'Ganancias'
        },
        {
            'url': '/app/reportes/costo-ventas/',
            'name': 'Costo de Ventas'
        },
        {
            'url': '/app/reportes/costo-inventario/',
            'name': 'Costo de Inventario'
        },
        {
            'url': '/app/reportes/ventas-periodo/',
            'name': 'Ventas por Período'
        }
    ]
    
    results = []
    
    for endpoint in endpoints:
        print(f"\n🔍 Probando: {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        
        # Primera petición (sin cache)
        start_time = time.time()
        response1 = client.get(endpoint['url'])
        first_load_time = time.time() - start_time
        
        if response1.status_code == 200:
            size1 = len(response1.content)
            
            # Segunda petición (con cache)
            start_time = time.time()
            response2 = client.get(endpoint['url'])
            cached_load_time = time.time() - start_time
            
            if response2.status_code == 200:
                size2 = len(response2.content)
                
                # Analizar headers de compresión
                compression_ratio = size1 / size2 if size2 > 0 else 1
                speed_improvement = first_load_time / cached_load_time if cached_load_time > 0 else 0
                
                result = {
                    'name': endpoint['name'],
                    'first_load': first_load_time,
                    'cached_load': cached_load_time,
                    'speed_improvement': speed_improvement,
                    'size_original': size1,
                    'size_cached': size2,
                    'compression_ratio': compression_ratio,
                    'status': 'success'
                }
                
                results.append(result)
                
                print(f"   ✅ Primera carga: {first_load_time:.3f}s")
                print(f"   ✅ Carga cache: {cached_load_time:.3f}s")
                print(f"   🚀 Mejora velocidad: {speed_improvement:.1f}x")
                print(f"   📦 Tamaño: {size1} bytes")
                
                # Verificar headers de optimización
                if 'X-Response-Time' in response1:
                    print(f"   ⏱️  Response-Time: {response1['X-Response-Time']}")
                if 'Content-Encoding' in response1:
                    print(f"   🗜️  Compresión: {response1['Content-Encoding']}")
                if 'X-Compression-Ratio' in response1:
                    print(f"   📊 Ratio: {response1['X-Compression-Ratio']}")
            else:
                print(f"   ❌ Error en segunda petición: {response2.status_code}")
                results.append({'name': endpoint['name'], 'status': 'error', 'message': f'HTTP {response2.status_code}'})
        else:
            print(f"   ❌ Error en primera petición: {response1.status_code}")
            if response1.status_code == 500:
                print(f"   📄 Contenido de error: {response1.content[:200]}...")
            results.append({'name': endpoint['name'], 'status': 'error', 'message': f'HTTP {response1.status_code}'})
    
    # Resumen de resultados
    successful_results = [r for r in results if r.get('status') == 'success']
    
    print(f"\n📊 RESUMEN DE RESULTADOS")
    print("=" * 40)
    print(f"✅ Exitosos: {len(successful_results)}/{len(endpoints)}")
    
    if successful_results:
        avg_first_load = sum(r['first_load'] for r in successful_results) / len(successful_results)
        avg_cached_load = sum(r['cached_load'] for r in successful_results) / len(successful_results)
        avg_speed_improvement = sum(r['speed_improvement'] for r in successful_results) / len(successful_results)
        
        print(f"⚡ Tiempo promedio primera carga: {avg_first_load:.3f}s")
        print(f"🚀 Tiempo promedio con cache: {avg_cached_load:.3f}s")
        print(f"🎯 Mejora promedio de velocidad: {avg_speed_improvement:.1f}x")
        
        # Recomendaciones
        print(f"\n🎯 ANÁLISIS:")
        if avg_first_load < 1.0:
            print("   ✅ Excelente rendimiento de carga inicial")
        elif avg_first_load < 2.0:
            print("   ✅ Buen rendimiento de carga inicial")
        else:
            print("   ⚠️  Considerar optimizar consultas más pesadas")
        
        if avg_speed_improvement > 5.0:
            print("   ✅ Cache muy efectivo")
        elif avg_speed_improvement > 2.0:
            print("   ✅ Cache funcionando bien")
        else:
            print("   ⚠️  Considerar mejorar configuración de cache")
    
    # Probar página de reportes completa
    print(f"\n🌐 Probando página completa de reportes...")
    start_time = time.time()
    page_response = client.get('/app/otros/reportes/')
    page_load_time = time.time() - start_time
    
    if page_response.status_code == 200:
        print(f"   ✅ Página cargada en: {page_load_time:.3f}s")
        print(f"   📦 Tamaño: {len(page_response.content) / 1024:.1f} KB")
        
        # Verificar que el JavaScript esté incluido
        if 'reportes-dashboard.js' in page_response.content.decode():
            print("   ✅ JavaScript de reportes incluido")
        else:
            print("   ⚠️  JavaScript de reportes no encontrado")
    else:
        print(f"   ❌ Error cargando página: {page_response.status_code}")
    
    print(f"\n🎉 PRUEBAS COMPLETADAS!")
    print(f"📝 Para probar en el navegador:")
    print(f"   1. Inicia sesión en: http://127.0.0.1:8000/admin/")
    print(f"   2. Visita: http://127.0.0.1:8000/app/otros/reportes/")
    print(f"   3. Observa la carga diferida de las tarjetas")
    
    return results

if __name__ == "__main__":
    test_reportes_optimization()
