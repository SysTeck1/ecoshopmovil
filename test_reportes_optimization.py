#!/usr/bin/env python
"""
Script para probar optimizaciones de reportes
Ejecutar: python test_reportes_optimization.py
"""

import os
import django
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')
django.setup()

class ReportesOptimizationTester:
    """Tester para optimizaciones de reportes"""
    
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {}
    
    def test_single_report(self, endpoint, description):
        """Probar un solo endpoint de reporte"""
        url = f"{self.base_url}{endpoint}"
        
        print(f"🔍 Probando: {description}")
        print(f"   URL: {url}")
        
        try:
            # Primera petición (sin cache)
            start_time = time.time()
            response1 = self.session.get(url, timeout=30)
            first_load_time = time.time() - start_time
            
            if response1.status_code == 200:
                data1 = response1.json()
                size1 = len(response1.content)
                
                # Segunda petición (con cache)
                start_time = time.time()
                response2 = self.session.get(url, timeout=30)
                cached_load_time = time.time() - start_time
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    size2 = len(response2.content)
                    
                    # Verificar compresión
                    compression_ratio = size1 / size2 if size2 > 0 else 1
                    
                    result = {
                        'endpoint': endpoint,
                        'description': description,
                        'first_load': first_load_time,
                        'cached_load': cached_load_time,
                        'speed_improvement': first_load_time / cached_load_time if cached_load_time > 0 else 0,
                        'size_original': size1,
                        'size_compressed': size2,
                        'compression_ratio': compression_ratio,
                        'status': 'success'
                    }
                    
                    print(f"   ✅ Primera carga: {first_load_time:.3f}s")
                    print(f"   ✅ Carga cache: {cached_load_time:.3f}s")
                    print(f"   🚀 Mejora velocidad: {result['speed_improvement']:.1f}x")
                    print(f"   📦 Compresión: {compression_ratio:.1f}x")
                    
                    return result
                else:
                    print(f"   ❌ Error en segunda petición: {response2.status_code}")
                    return {'status': 'error', 'message': f'HTTP {response2.status_code}'}
            else:
                print(f"   ❌ Error en primera petición: {response1.status_code}")
                return {'status': 'error', 'message': f'HTTP {response1.status_code}'}
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Timeout (30s)")
            return {'status': 'error', 'message': 'Timeout'}
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def test_concurrent_reports(self, endpoints, max_workers=5):
        """Probar múltiples endpoints concurrentemente"""
        print(f"\n🔄 Probando carga concurrente ({len(endpoints)} endpoints)")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Enviar todas las peticiones
            future_to_endpoint = {
                executor.submit(self.test_single_report, ep['url'], ep['desc']): ep 
                for ep in endpoints
            }
            
            # Recopilar resultados
            results = []
            for future in as_completed(future_to_endpoint):
                result = future.result()
                results.append(result)
        
        return results
    
    def test_page_load(self, page_url, description):
        """Probar tiempo de carga de página completa"""
        print(f"\n🌐 Probando carga de página: {description}")
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}{page_url}", timeout=30)
            load_time = time.time() - start_time
            
            if response.status_code == 200:
                print(f"   ✅ Página cargada en: {load_time:.3f}s")
                print(f"   📦 Tamaño: {len(response.content) / 1024:.1f} KB")
                
                return {
                    'page': page_url,
                    'description': description,
                    'load_time': load_time,
                    'size_kb': len(response.content) / 1024,
                    'status': 'success'
                }
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
                return {'status': 'error', 'message': f'HTTP {response.status_code}'}
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        print("🚀 INICIANDO PRUEBAS DE OPTIMIZACIÓN DE REPORTES")
        print("=" * 60)
        
        # Endpoints de reportes a probar
        report_endpoints = [
            {
                'url': '/app/reportes/ventas-totales/',
                'desc': 'Ventas Totales'
            },
            {
                'url': '/app/reportes/ganancias/',
                'desc': 'Ganancias'
            },
            {
                'url': '/app/reportes/costo-ventas/',
                'desc': 'Costo de Ventas'
            },
            {
                'url': '/app/reportes/costo-inventario/',
                'desc': 'Costo de Inventario'
            },
            {
                'url': '/app/reportes/ventas-periodo/',
                'desc': 'Ventas por Período'
            }
        ]
        
        # Prueba 1: Carga concurrente de reportes
        concurrent_results = self.test_concurrent_reports(report_endpoints)
        
        # Prueba 2: Carga de página de reportes
        page_result = self.test_page_load('/app/otros/reportes/', 'Página de Reportes')
        
        # Analizar resultados
        successful_reports = [r for r in concurrent_results if r.get('status') == 'success']
        
        if successful_reports:
            avg_first_load = statistics.mean([r['first_load'] for r in successful_reports])
            avg_cached_load = statistics.mean([r['cached_load'] for r in successful_reports])
            avg_speed_improvement = statistics.mean([r['speed_improvement'] for r in successful_reports])
            avg_compression = statistics.mean([r['compression_ratio'] for r in successful_reports])
            
            print(f"\n📊 RESULTADOS DE OPTIMIZACIÓN")
            print("=" * 40)
            print(f"📈 Reportes exitosos: {len(successful_reports)}/{len(report_endpoints)}")
            print(f"⚡ Tiempo promedio primera carga: {avg_first_load:.3f}s")
            print(f"🚀 Tiempo promedio con cache: {avg_cached_load:.3f}s")
            print(f"🎯 Mejora promedio de velocidad: {avg_speed_improvement:.1f}x")
            print(f"📦 Compresión promedio: {avg_compression:.1f}x")
            
            if page_result.get('status') == 'success':
                print(f"🌐 Carga página completa: {page_result['load_time']:.3f}s")
            
            # Recomendaciones
            print(f"\n🎯 RECOMENDACIONES:")
            if avg_first_load > 3.0:
                print("  ⚠️  Considerar optimizar consultas de base de datos")
            if avg_speed_improvement < 2.0:
                print("  ⚠️  Considerar mejorar configuración de cache")
            if avg_compression < 1.5:
                print("  ⚠️  Considerar habilitar compresión gzip")
            if page_result.get('load_time', 0) > 5.0:
                print("  ⚠️  Considerar lazy loading para componentes pesados")
            
            print(f"\n✅ Pruebas completadas exitosamente!")
        else:
            print(f"\n❌ No se pudieron completar las pruebas")
        
        return {
            'concurrent_results': concurrent_results,
            'page_result': page_result,
            'summary': {
                'successful_reports': len(successful_reports),
                'total_reports': len(report_endpoints)
            }
        }

if __name__ == "__main__":
    tester = ReportesOptimizationTester()
    results = tester.run_all_tests()
