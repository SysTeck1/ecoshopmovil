#!/usr/bin/env python
"""
Script para crear índices de rendimiento para grandes volúmenes de datos
Ejecutar: python create_performance_indexes.py
"""

import os
import django
import sqlite3

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')
django.setup()

from django.db import connection
from SistemaPOS.settings import BASE_DIR

def create_indexes():
    """Crear índices para optimizar rendimiento"""
    
    indexes = [
        # Índices para productos
        "CREATE INDEX IF NOT EXISTS idx_producto_activo_nombre ON ventas_producto(activo, nombre);",
        "CREATE INDEX IF NOT EXISTS idx_producto_precio_venta ON ventas_producto(precio_venta) WHERE precio_venta IS NOT NULL;",
        "CREATE INDEX IF NOT EXISTS idx_producto_marca_modelo ON ventas_producto(marca_id, modelo_id);",
        "CREATE INDEX IF NOT EXISTS idx_producto_categoria ON ventas_producto(categoria_id);",
        "CREATE INDEX IF NOT EXISTS idx_producto_busqueda ON ventas_producto(activo, nombre, marca_id, categoria_id, precio_venta);",
        
        # Índices para unidades de producto
        "CREATE INDEX IF NOT EXISTS idx_unidad_producto_vendido ON ventas_productounitdetail(producto_id, vendido);",
        "CREATE INDEX IF NOT EXISTS idx_unidad_producto_index ON ventas_productounitdetail(producto_id, unidad_index);",
        "CREATE INDEX IF NOT EXISTS idx_unidad_vendida_fecha ON ventas_productounitdetail(vendido, fecha_venta);",
        "CREATE INDEX IF NOT EXISTS idx_unidad_codigo_barras ON ventas_productounitdetail(codigo_barras) WHERE codigo_barras IS NOT NULL;",
        
        # Índices para ventas
        "CREATE INDEX IF NOT EXISTS idx_venta_fecha_cliente ON ventas_venta(fecha, cliente_id);",
        "CREATE INDEX IF NOT EXISTS idx_venta_estado_fecha ON ventas_venta(estado, fecha);",
        "CREATE INDEX IF NOT EXISTS idx_venta_sesion_caja ON ventas_venta(sesion_caja_id);",
        
        # Índices para clientes y proveedores
        "CREATE INDEX IF NOT EXISTS idx_cliente_nombre ON ventas_cliente(nombre);",
        "CREATE INDEX IF NOT EXISTS idx_cliente_documento ON ventas_cliente(documento) WHERE documento IS NOT NULL;",
        "CREATE INDEX IF NOT EXISTS idx_proveedor_nombre ON ventas_proveedor(nombre);",
        
        # Índices para créditos y pagos
        "CREATE INDEX IF NOT EXISTS idx_credito_venta ON ventas_cuentacredito(venta_id);",
        "CREATE INDEX IF NOT EXISTS idx_credito_cliente ON ventas_cuentacredito(cliente_id);",
        "CREATE INDEX IF NOT EXISTS idx_pago_credito_fecha ON ventas_pagocredito(cuenta_credito_id, fecha_pago);",
        
        # Índices para sesiones de caja
        "CREATE INDEX IF NOT EXISTS idx_sesion_fecha ON ventas_cashsession(fecha_apertura);",
        "CREATE INDEX IF NOT EXISTS idx_sesion_estado ON ventas_cashsession(estado);",
    ]
    
    print("🚀 Creando índices de rendimiento...")
    
    with connection.cursor() as cursor:
        for i, sql in enumerate(indexes, 1):
            try:
                cursor.execute(sql)
                print(f"✅ Índice {i}/{len(indexes)} creado exitosamente")
            except Exception as e:
                print(f"❌ Error creando índice {i}: {e}")
    
    print("🎯 Índices de rendimiento creados exitosamente!")

def analyze_indexes():
    """Analizar los índices creados"""
    
    print("\n📊 Analizando índices creados...")
    
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA index_list(ventas_producto);")
        producto_indexes = cursor.fetchall()
        
        cursor.execute("PRAGMA index_list(ventas_productounitdetail);")
        unidad_indexes = cursor.fetchall()
        
        cursor.execute("PRAGMA index_list(ventas_venta);")
        venta_indexes = cursor.fetchall()
    
    print(f"📦 Índices en productos: {len(producto_indexes)}")
    for idx in producto_indexes:
        if 'idx_' in idx[1]:  # Solo mostrar nuestros índices
            print(f"   - {idx[1]}")
    
    print(f"🏷️  Índices en unidades: {len(unidad_indexes)}")
    for idx in unidad_indexes:
        if 'idx_' in idx[1]:
            print(f"   - {idx[1]}")
    
    print(f"💰 Índices en ventas: {len(venta_indexes)}")
    for idx in venta_indexes:
        if 'idx_' in idx[1]:
            print(f"   - {idx[1]}")

if __name__ == "__main__":
    create_indexes()
    analyze_indexes()
