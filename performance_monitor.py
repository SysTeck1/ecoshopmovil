#!/usr/bin/env python
"""
Monitor de rendimiento para SistemaPOS
Ejecutar: python performance_monitor.py
"""

import os
import django
import time
import sqlite3
import psutil
from django.db import connection, connections
from django.test import Client
from cache_config import cache_manager

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')
django.setup()

class PerformanceMonitor:
    """Monitor de rendimiento del sistema"""
    
    def __init__(self):
        self.client = Client()
        self.results = {}
    
    def test_database_performance(self):
        """Probar rendimiento de consultas a base de datos"""
        print("🔍 Probando rendimiento de base de datos...")
        
        queries = [
            "SELECT COUNT(*) FROM ventas_producto WHERE activo = 1",
            "SELECT COUNT(*) FROM ventas_productounitdetail WHERE vendido = 0",
            "SELECT COUNT(*) FROM ventas_venta",
            "SELECT COUNT(*) FROM ventas_cliente",
        ]
        
        for i, query in enumerate(queries, 1):
            start_time = time.time()
            
            with connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.results[f'db_query_{i}'] = {
                'time': execution_time,
                'result': result[0],
                'query': query
            }
            
            print(f"  ✅ Query {i}: {execution_time:.4f}s - {result[0]} registros")
    
    def test_api_endpoints(self):
        """Probar rendimiento de endpoints API"""
        print("\n🚀 Probando rendimiento de endpoints API...")
        
        endpoints = [
            '/app/ventas/',
            '/app/ventas/productos/pagina/?page=1&page_size=20',
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            
            try:
                response = self.client.get(endpoint)
                end_time = time.time()
                
                self.results[f'endpoint_{endpoint}'] = {
                    'time': end_time - start_time,
                    'status': response.status_code,
                    'size': len(response.content)
                }
                
                print(f"  ✅ {endpoint}: {end_time - start_time:.4f}s - {response.status_code}")
            except Exception as e:
                print(f"  ❌ {endpoint}: Error - {e}")
    
    def test_cache_performance(self):
        """Probar rendimiento de cache"""
        print("\n💾 Probando rendimiento de cache...")
        
        # Test Redis cache
        if cache_manager.enabled:
            test_data = {'test': 'data', 'numbers': list(range(1000))}
            
            # Test write
            start_time = time.time()
            cache_manager.set_product_options(1, 20, test_data)
            write_time = time.time() - start_time
            
            # Test read
            start_time = time.time()
            cached_data = cache_manager.get_product_options(1, 20)
            read_time = time.time() - start_time
            
            self.results['cache_performance'] = {
                'write_time': write_time,
                'read_time': read_time,
                'enabled': True
            }
            
            print(f"  ✅ Redis Write: {write_time:.4f}s")
            print(f"  ✅ Redis Read: {read_time:.4f}s")
        else:
            print("  ⚠️  Redis no disponible")
            self.results['cache_performance'] = {'enabled': False}
    
    def test_memory_usage(self):
        """Probar uso de memoria"""
        print("\n🧠 Analizando uso de memoria...")
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        self.results['memory_usage'] = {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent()
        }
        
        print(f"  📊 RAM: {memory_info.rss / 1024 / 1024:.1f} MB")
        print(f"  📊 Virtual: {memory_info.vms / 1024 / 1024:.1f} MB")
        print(f"  📊 Porcentaje: {process.memory_percent():.1f}%")
    
    def test_database_indexes(self):
        """Verificar índices de base de datos"""
        print("\n📊 Verificando índices de base de datos...")
        
        with connection.cursor() as cursor:
            tables = ['ventas_producto', 'ventas_productounitdetail', 'ventas_venta']
            
            for table in tables:
                cursor.execute(f"PRAGMA index_list({table});")
                indexes = cursor.fetchall()
                
                custom_indexes = [idx for idx in indexes if 'idx_' in idx[1]]
                
                self.results[f'indexes_{table}'] = {
                    'total': len(indexes),
                    'custom': len(custom_indexes),
                    'names': [idx[1] for idx in custom_indexes]
                }
                
                print(f"  📦 {table}: {len(custom_indexes)} índices personalizados")
    
    def generate_report(self):
        """Generar reporte de rendimiento"""
        print("\n📈 REPORTE DE RENDIMIENTO")
        print("=" * 50)
        
        # Rendimiento de base de datos
        db_times = [self.results[k]['time'] for k in self.results if k.startswith('db_query_')]
        if db_times:
            avg_db_time = sum(db_times) / len(db_times)
            print(f"🗄️  Tiempo promedio BD: {avg_db_time:.4f}s")
        
        # Rendimiento de endpoints
        avg_endpoint_time = 0
        endpoint_times = [self.results[k]['time'] for k in self.results if k.startswith('endpoint_')]
        if endpoint_times:
            avg_endpoint_time = sum(endpoint_times) / len(endpoint_times)
            print(f"🌐 Tiempo promedio API: {avg_endpoint_time:.4f}s")
        
        # Cache
        cache_perf = self.results.get('cache_performance', {})
        if cache_perf.get('enabled'):
            print(f"💾 Cache Redis: ✅ Disponible")
            print(f"   Write: {cache_perf['write_time']:.4f}s")
            print(f"   Read: {cache_perf['read_time']:.4f}s")
        else:
            print(f"💾 Cache Redis: ⚠️ No disponible")
        
        # Memoria
        memory = self.results.get('memory_usage', {})
        if memory:
            print(f"🧠 Memoria RAM: {memory['rss']:.1f} MB")
        else:
            memory = {'rss': 0}
        
        # Índices
        total_custom_indexes = 0
        for k in self.results:
            if k.startswith('indexes_'):
                total_custom_indexes += self.results[k]['custom']
        
        print(f"📊 Índices personalizados: {total_custom_indexes}")
        
        # Recomendaciones
        print("\n🎯 RECOMENDACIONES:")
        if avg_db_time > 0.1:
            print("  ⚠️  Considerar optimizar consultas de base de datos")
        
        if avg_endpoint_time > 2.0:
            print("  ⚠️  Considerar implementar cache en endpoints lentos")
        
        if memory['rss'] > 500:
            print("  ⚠️  Uso de memoria elevado, considerar optimización")
        
        if total_custom_indexes < 10:
            print("  ⚠️  Considerar agregar más índices para optimizar búsquedas")
        
        if not cache_perf.get('enabled'):
            print("  💡 Instalar Redis para mejor rendimiento de cache")
    
    def run_full_test(self):
        """Ejecutar todas las pruebas de rendimiento"""
        print("🚀 INICIANDO MONITOR DE RENDIMIENTO")
        print("=" * 50)
        
        self.test_database_performance()
        self.test_api_endpoints()
        self.test_cache_performance()
        self.test_memory_usage()
        self.test_database_indexes()
        self.generate_report()

if __name__ == "__main__":
    monitor = PerformanceMonitor()
    monitor.run_full_test()
