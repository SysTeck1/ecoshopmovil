#!/usr/bin/env python
"""
Script para poblar la base de datos de SistemaPOS con datos de prueba
Personaliza las cantidades según tus necesidades
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta
import random

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaPOS.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from ventas.models import (
    Cliente, Producto, Marca, Modelo, Categoria, Proveedor,
    Impuesto, ProductCondition, ProductoUnitDetail,
    Venta, DetalleVenta, CashSession, CuentaCredito, PagoCredito,
    TradeInCredit, FiscalVoucher, FiscalVoucherConfig
)
from dashboard.models import SiteConfiguration

# ========================================
# CONFIGURACIÓN DE CANTIDADES (AJUSTA AQUÍ)
# ========================================
CONFIG = {
    # Usuarios
    'usuarios': 5,
    
    # Clientes
    'clientes': 50,
    
    # Categorías
    'categorias': 8,
    
    # Marcas
    'marcas': 15,
    
    # Modelos por marca
    'modelos_por_marca': 3,
    
    # Proveedores
    'proveedores': 20,
    
    # Productos
    'productos': 100,              # Productos originales
    'productos_adicionales': 200,  # Productos adicionales
    'unidades_por_producto': 50,   # ⭐ CAMBIADO: 50 unidades para TODOS los productos
    'unidades_producto_adicional': 50,  # 50 unidades para productos adicionales
    
    # Condiciones de producto
    'condiciones': 5,
    
    # Impuestos
    'impuestos': 4,
    
    # Ventas
    'ventas': 200,
    
    # Sesiones de caja
    'sesiones_caja': 10,
    
    # Créditos
    'creditos': 30,
}

# Datos de ejemplo
NOMBRES_CLIENTES = [
    "Juan Pérez", "María García", "Carlos Rodríguez", "Ana López", "Luis Martínez",
    "Sofía Hernández", "Diego Sánchez", "Laura Ramírez", "Pedro Torres", "Lucía Díaz",
    "Miguel Ángel", "Carmen Ruiz", "José Carlos", "Isabel Moreno", "Antonio Guerrero",
    "Patricia Castro", "Francisco Javier", "Beatriz Ortega", "Manuel Vargas", "Elena Jiménez"
]

APELLIDOS = ["García", "Rodríguez", "López", "Martínez", "Sánchez", "Pérez", "Gómez", "Díaz", "Fernández", "Moreno"]

NOMBRES_EMPRESAS = [
    "TechStore SRL", "MobileZone", "DigitalHub", "GadgetWorld", "PhoneCentral",
    "ElectroMarket", "SmartDevices", "TechPoint", "DigitalStore", "MobileShop"
]

CATEGORIAS_NOMBRES = [
    "Smartphones", "Laptops", "Tablets", "Smartwatches", "Accesorios", 
    "Audio", "Gaming", "Cámaras", "Televisores", "Consolas", "Monitores",
    "Impresoras", "Routers", "Discos Duros", "Memorias USB", "Baterías",
    "Fundas", "Cargadores", "Auriculares", "Parlantes", "Teclados", "Mouse"
]

MARCAS_NOMBRES = [
    # Smartphones
    "Apple", "Samsung", "Xiaomi", "Huawei", "OPPO", "Vivo", "Realme",
    "OnePlus", "Motorola", "Nokia", "Sony", "LG", "HTC", "Alcatel", "ZTE",
    # Laptops/Computadoras
    "Dell", "HP", "Lenovo", "ASUS", "Acer", "MSI", "Microsoft", "Razer",
    "Apple MacBook", "Toshiba", "Samsung", "LG", "Huawei",
    # Gaming
    "Sony PlayStation", "Microsoft Xbox", "Nintendo", "Razer", "Logitech",
    "Corsair", "ASUS ROG", "MSI Gaming", "SteelSeries",
    # Audio
    "Sony", "Bose", "JBL", "Sennheiser", "Audio-Technica", "Beats", "Skullcandy",
    "Apple AirPods", "Samsung Galaxy Buds", "Anker", "Jabra",
    # Televisores
    "Samsung", "LG", "Sony", "TCL", "Vizio", "Philips", "Panasonic", "Sharp",
    # Accesorios/Periféricos
    "Logitech", "Razer", "Corsair", "HyperX", "SteelSeries", "ZOWIE", "BenQ",
    "ASUS", "TP-Link", "Netgear", "Linksys", "D-Link", "Western Digital", "Seagate",
    "Kingston", "SanDisk", "Crucial", "Intel", "AMD", "NVIDIA"
]

ALMACENAMIENTO_CHOICES = ['32GB', '64GB', '128GB', '256GB', '512GB', '1TB', '2TB', '4TB', '8TB', '16TB']
RAM_CHOICES = ['2GB', '3GB', '4GB', '6GB', '8GB', '12GB', '16GB', '24GB', '32GB', '64GB']
COLORES = ['Negro', 'Blanco', 'Azul', 'Rojo', 'Verde', 'Dorado', 'Plateado', 'Rosa', 'Gris', 'Morado', 'Naranja', 'Amarillo']

# Especificaciones adicionales para diferentes tipos de productos
PROCESADORES_CHOICES = ['Intel i3', 'Intel i5', 'Intel i7', 'Intel i9', 'AMD Ryzen 3', 'AMD Ryzen 5', 'AMD Ryzen 7', 'AMD Ryzen 9', 'Apple M1', 'Apple M2']
TAMAÑO_PANTALLA_CHOICES = ['13"', '14"', '15.6"', '17.3"', '21"', '24"', '27"', '32"', '43"', '55"', '65"', '75"', '85"']
TIPO_CONEXION_CHOICES = ['USB-A', 'USB-C', 'HDMI', 'DisplayPort', 'Thunderbolt', 'WiFi', 'Bluetooth', 'Ethernet']
RESOLUCION_CHOICES = ['720p', '1080p', '1440p', '4K', '8K']
TIPO_BATERIA_CHOICES = ['2000mAh', '3000mAh', '4000mAh', '5000mAh', '6000mAh', '8000mAh', '10000mAh']

CONDICIONES_NOMBRES = [
    "Nuevo", "Como Nuevo", "Bueno", "Regular", "Para Reparación"
]

def crear_usuarios():
    """Crear usuarios de prueba"""
    print("👥 Creando usuarios...")
    
    # Crear superusuario si no existe
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@sistema.com', 'admin123')
        print("✅ Superusuario 'admin' creado")
    
    # Crear usuarios regulares
    for i in range(CONFIG['usuarios']):
        username = f"usuario{i+1}"
        if not User.objects.filter(username=username).exists():
            User.objects.create_user(
                username=username,
                email=f"{username}@sistema.com",
                password=f"pass{i+1:03d}",
                first_name=f"Usuario{i+1}",
                last_name=f"Test{i+1}"
            )
    
    print(f"✅ {CONFIG['usuarios']} usuarios creados")

def crear_categorias():
    """Crear categorías de productos"""
    print("📂 Creando categorías...")
    
    for i, nombre in enumerate(CATEGORIAS_NOMBRES[:CONFIG['categorias']]):
        Categoria.objects.get_or_create(
            nombre=nombre,
            defaults={'activo': True}
        )
    
    print(f"✅ {CONFIG['categorias']} categorías creadas")

def crear_marcas():
    """Crear marcas de productos"""
    print("🏷️ Creando marcas...")
    
    for i, nombre in enumerate(MARCAS_NOMBRES[:CONFIG['marcas']]):
        Marca.objects.get_or_create(
            nombre=nombre,
            defaults={'activo': True}
        )
    
    print(f"✅ {CONFIG['marcas']} marcas creadas")

def crear_modelos():
    """Crear modelos por marca"""
    print("📱 Creando modelos...")
    
    marcas = Marca.objects.all()
    
    for marca in marcas:
        for i in range(CONFIG['modelos_por_marca']):
            nombre_modelo = f"Modelo-{marca.nombre[:3]}-{i+1:02d}"
            Modelo.objects.get_or_create(
                nombre=nombre_modelo,
                marca=marca,
                defaults={'activo': True}
            )
    
    total_modelos = CONFIG['marcas'] * CONFIG['modelos_por_marca']
    print(f"✅ {total_modelos} modelos creados")

def crear_proveedores():
    """Crear proveedores"""
    print("🏢 Creando proveedores...")
    
    for i in range(CONFIG['proveedores']):
        nombre = f"Proveedor {i+1}"
        if i < len(NOMBRES_EMPRESAS):
            nombre = NOMBRES_EMPRESAS[i]
        
        Proveedor.objects.get_or_create(
            nombre=nombre,
            defaults={
                'tipo_documento': random.choice(['rnc', 'cedula', 'otro']),
                'documento': f"{random.randint(10000000000, 99999999999)}",
                'telefono': f"809-555-{i:04d}",
                'correo': f"proveedor{i+1}@email.com",
                'direccion': f"Calle Principal #{i+1}, Ciudad",
            }
        )
    
    print(f"✅ {CONFIG['proveedores']} proveedores creados")

def crear_impuestos():
    """Crear impuestos"""
    print("💰 Creando impuestos...")
    
    impuestos_data = [
        ("ITBIS 18%", Decimal("18.00")),
        ("ITBIS 0%", Decimal("0.00")),
        ("Exento", Decimal("0.00")),
        ("Reducido 16%", Decimal("16.00")),
    ]
    
    for nombre, porcentaje in impuestos_data[:CONFIG['impuestos']]:
        Impuesto.objects.get_or_create(
            nombre=nombre,
            defaults={'porcentaje': porcentaje, 'activo': True}
        )
    
    print(f"✅ {CONFIG['impuestos']} impuestos creados")

def crear_condiciones():
    """Crear condiciones de producto"""
    print("📋 Creando condiciones...")
    
    for i, nombre in enumerate(CONDICIONES_NOMBRES[:CONFIG['condiciones']]):
        ProductCondition.objects.get_or_create(
            nombre=nombre,
            defaults={'activo': True}
        )
    
    print(f"✅ {CONFIG['condiciones']} condiciones creadas")

def crear_clientes():
    """Crear clientes"""
    print("👤 Creando clientes...")
    
    for i in range(CONFIG['clientes']):
        nombre = random.choice(NOMBRES_CLIENTES)
        apellido = random.choice(APELLIDOS)
        nombre_completo = f"{nombre} {apellido}"
        
        Cliente.objects.get_or_create(
            documento=f"{401000000 + i:09d}",
            defaults={
                'nombre': nombre_completo,
                'tipo_documento': random.choice(['cedula', 'rnc', 'pasaporte']),
                'correo': f"cliente{i+1}@email.com",
                'telefono': f"809-555-{i:04d}",
                'direccion': f"Calle {i+1}, Ciudad",
            }
        )
    
    print(f"✅ {CONFIG['clientes']} clientes creados")

def crear_productos():
    """Crear productos con unidades"""
    print("📦 Creando productos y unidades...")
    
    categorias = list(Categoria.objects.all())
    marcas = list(Marca.objects.all())
    modelos = list(Modelo.objects.all())
    proveedores = list(Proveedor.objects.all())
    condiciones = list(ProductCondition.objects.all())
    impuestos = list(Impuesto.objects.all())
    
    # Plantillas para diferentes tipos de productos (mismas que productos adicionales)
    templates_productos = {
        'Smartphones': {
            'prefijos': ['Galaxy', 'iPhone', 'Redmi', 'Poco', 'Find', 'Reno', 'Nord', 'Edge'],
            'sufijos': ['Pro', 'Max', 'Plus', 'Lite', 'Standard', 'Elite', 'Ultra', 'Mini'],
            'almacenamiento': ['64GB', '128GB', '256GB', '512GB'],
            'ram': ['4GB', '6GB', '8GB', '12GB'],
            'precio_base': (150, 1200),
            'specs': ['pantalla', 'camara', 'bateria']
        },
        'Laptops': {
            'prefijos': ['Inspiron', 'Pavilion', 'ThinkPad', 'ZenBook', 'MacBook', 'Predator', 'VivoBook'],
            'sufijos': ['Pro', 'Air', 'Gaming', 'Business', 'Student', 'Creator', 'Ultra'],
            'almacenamiento': ['256GB', '512GB', '1TB', '2TB'],
            'ram': ['8GB', '16GB', '24GB', '32GB'],
            'precio_base': (400, 2500),
            'specs': ['procesador', 'pantalla', 'bateria']
        },
        'Tablets': {
            'prefijos': ['iPad', 'Galaxy Tab', 'Surface', 'MediaPad', 'ThinkPad'],
            'sufijos': ['Pro', 'Air', 'Lite', 'Plus', 'Go', 'Studio'],
            'almacenamiento': ['64GB', '128GB', '256GB', '512GB'],
            'ram': ['4GB', '6GB', '8GB', '12GB'],
            'precio_base': (200, 1500),
            'specs': ['pantalla', 'bateria', 'conectividad']
        },
        'Smartwatches': {
            'prefijos': ['Apple Watch', 'Galaxy Watch', 'Fitbit', 'Garmin', 'Amazfit'],
            'sufijos': ['SE', 'Series', 'Pro', 'Active', 'Sport', 'Classic'],
            'almacenamiento': ['16GB', '32GB'],
            'ram': ['1GB', '2GB', '4GB'],
            'precio_base': (100, 800),
            'specs': ['pantalla', 'bateria', 'sensores']
        },
        'Accesorios': {
            'prefijos': ['Case', 'Cover', 'Screen Protector', 'Stand', 'Holder'],
            'sufijos': ['Premium', 'Pro', 'Ultra', 'Basic', 'Plus', 'Max'],
            'almacenamiento': ['N/A'],
            'ram': ['N/A'],
            'precio_base': (5, 100),
            'specs': ['material', 'compatibilidad']
        },
        'Audio': {
            'prefijos': ['AirPods', 'Galaxy Buds', 'Echo', 'Soundcore', 'JBL', 'Sony'],
            'sufijos': ['Pro', 'Max', 'Studio', 'Sport', 'Wireless', 'Noise Canceling'],
            'almacenamiento': ['N/A'],
            'ram': ['N/A'],
            'precio_base': (20, 400),
            'specs': ['bluetooth', 'bateria', 'calidad']
        },
        'Gaming': {
            'prefijos': ['PlayStation', 'Xbox', 'Nintendo', 'Steam Deck', 'ROG', 'Legion'],
            'sufijos': ['5', 'Series X', 'Switch', 'OLED', 'Pro', 'Max'],
            'almacenamiento': ['256GB', '512GB', '1TB', '2TB'],
            'ram': ['8GB', '16GB', '32GB'],
            'precio_base': (250, 2000),
            'specs': ['procesador', 'graficos', 'almacenamiento']
        },
        'Cámaras': {
            'prefijos': ['EOS', 'Alpha', 'D', 'Z', 'Lumix', 'FinePix'],
            'sufijos': ['Mark IV', 'A7', '850', 'Z9', 'GH5', 'X-T4'],
            'almacenamiento': ['64GB', '128GB', '256GB', '512GB'],
            'ram': ['4GB', '8GB', '16GB'],
            'precio_base': (300, 5000),
            'specs': ['sensor', 'lente', 'resolucion']
        },
        'Televisores': {
            'prefijos': ['Bravia', 'OLED', 'QLED', 'Neo QLED', 'Crystal', 'UHD'],
            'sufijos': ['Smart', '4K', '8K', 'HDR', 'Dolby', 'Gaming'],
            'almacenamiento': ['16GB', '32GB'],
            'ram': ['2GB', '4GB', '8GB'],
            'precio_base': (300, 3000),
            'specs': ['pantalla', 'resolucion', 'smart']
        },
        'Monitores': {
            'prefijos': ['UltraSharp', 'Predator', 'Swift', 'Optix', 'LG', 'Samsung'],
            'sufijos': ['Gaming', 'Professional', '4K', 'Curved', 'Ultrawide'],
            'almacenamiento': ['N/A'],
            'ram': ['N/A'],
            'precio_base': (150, 1500),
            'specs': ['pantalla', 'resolucion', 'refresh']
        }
    }
    
    for i in range(CONFIG['productos']):
        categoria = random.choice(categorias)
        marca = random.choice(marcas)
        # Filtrar modelos de esta marca
        modelos_de_marca = [m for m in modelos if m.marca_id == marca.id]
        modelo = random.choice(modelos_de_marca) if modelos_de_marca else modelos[0]
        proveedore = random.choice(proveedores)
        condicion = random.choice(condiciones)
        impuesto = random.choice(impuestos)
        
        # Obtener template según categoría
        template = templates_productos.get(categoria.nombre, templates_productos['Accesorios'])
        
        # Generar nombre de producto
        prefijo = random.choice(template['prefijos'])
        sufijo = random.choice(template['sufijos'])
        numero = random.randint(1, 99)
        nombre_producto = f"{prefijo} {sufijo} {numero}"
        
        # Generar specs según tipo
        specs_extra = ""
        if 'procesador' in template.get('specs', []):
            procesador = random.choice(PROCESADORES_CHOICES)
            specs_extra += f" | {procesador}"
        if 'pantalla' in template.get('specs', []):
            pantalla = random.choice(TAMAÑO_PANTALLA_CHOICES)
            specs_extra += f" | {pantalla}"
        if 'bateria' in template.get('specs', []):
            bateria = random.choice(TIPO_BATERIA_CHOICES)
            specs_extra += f" | {bateria}"
        if 'resolucion' in template.get('specs', []):
            resolucion = random.choice(RESOLUCION_CHOICES)
            specs_extra += f" | {resolucion}"
        if 'conectividad' in template.get('specs', []):
            conexion = random.choice(TIPO_CONEXION_CHOICES)
            specs_extra += f" | {conexion}"
        
        # Rango de precios
        precio_min, precio_max = template['precio_base']
        precio_compra = Decimal(str(random.uniform(precio_min * 0.6, precio_max * 0.8)))
        precio_venta = Decimal(str(random.uniform(precio_min, precio_max)))
        
        # Crear producto
        producto, created = Producto.objects.get_or_create(
            nombre=nombre_producto,
            defaults={
                'descripcion': f"Descripción del {nombre_producto}. Productos de alta calidad con las mejores especificaciones.{specs_extra}",
                'categoria': categoria,
                'marca': marca,
                'modelo': modelo,
                'proveedor': proveedore,
                'precio_compra': precio_compra,
                'precio_venta': precio_venta,
                'stock': CONFIG['unidades_por_producto'],  # ⭐ CAMBIADO: 50 unidades
                'stock_minimo': random.randint(5, 15),
                'almacenamiento': random.choice(template['almacenamiento']),
                'memoria_ram': random.choice(template['ram']),
                'colores_disponibles': ", ".join(random.sample(COLORES, random.randint(2, 5))),
                'activo': True,
                'impuesto': impuesto,
                'usar_impuesto_global': random.choice([True, False]),
            }
        )
        
        # Crear unidades detalladas (50 unidades por producto)
        for unidad_idx in range(1, CONFIG['unidades_por_producto'] + 1):
            # Generar IMEI si es smartphone, sino serial number
            if categoria.nombre == 'Smartphones':
                identificador = f"IMEI{random.randint(100000000000000, 999999999999999)}"
            else:
                identificador = f"SN{producto.id:04d}{unidad_idx:03d}{random.randint(100, 999)}"
            
            ProductoUnitDetail.objects.get_or_create(
                producto=producto,
                unidad_index=unidad_idx,
                defaults={
                    'imei': identificador,
                    'color': random.choice(COLORES),
                    'almacenamiento': random.choice(template['almacenamiento']),
                    'memoria_ram': random.choice(template['ram']),
                    'vida_bateria': random.randint(70, 100),
                    'codigo_barras': f"BAR{producto.id}{unidad_idx:03d}",
                    'condicion': condicion,
                    'precio_compra': precio_compra * Decimal(str(random.uniform(0.9, 1.1))),
                    'precio_venta': precio_venta * Decimal(str(random.uniform(0.9, 1.1))),
                    'vendido': False,  # Todas disponibles inicialmente
                    'usar_impuesto_global': random.choice([True, False]),
                    'impuesto': impuesto if random.choice([True, False]) else None,
                }
            )
    
    print(f"✅ {CONFIG['productos']} productos creados con {CONFIG['unidades_por_producto']} unidades cada uno")

def crear_productos_adicionales():
    """Crear 500 productos adicionales con 50 unidades cada uno"""
    print("📦 Creando productos adicionales y unidades...")
    
    categorias = list(Categoria.objects.all())
    marcas = list(Marca.objects.all())
    modelos = list(Modelo.objects.all())
    proveedores = list(Proveedor.objects.all())
    condiciones = list(ProductCondition.objects.all())
    impuestos = list(Impuesto.objects.all())
    
    # Plantillas para diferentes tipos de productos
    templates_productos = {
        'Smartphones': {
            'prefijos': ['Galaxy', 'iPhone', 'Redmi', 'Poco', 'Find', 'Reno', 'Nord', 'Edge'],
            'sufijos': ['Pro', 'Max', 'Plus', 'Lite', 'Standard', 'Elite', 'Ultra', 'Mini'],
            'almacenamiento': ['64GB', '128GB', '256GB', '512GB'],
            'ram': ['4GB', '6GB', '8GB', '12GB'],
            'precio_base': (150, 1200),
            'specs': ['pantalla', 'camara', 'bateria']
        },
        'Laptops': {
            'prefijos': ['Inspiron', 'Pavilion', 'ThinkPad', 'ZenBook', 'MacBook', 'Predator', 'VivoBook'],
            'sufijos': ['Pro', 'Air', 'Gaming', 'Business', 'Student', 'Creator', 'Ultra'],
            'almacenamiento': ['256GB', '512GB', '1TB', '2TB'],
            'ram': ['8GB', '16GB', '24GB', '32GB'],
            'precio_base': (400, 2500),
            'specs': ['procesador', 'pantalla', 'bateria']
        },
        'Tablets': {
            'prefijos': ['iPad', 'Galaxy Tab', 'Surface', 'MediaPad', 'ThinkPad'],
            'sufijos': ['Pro', 'Air', 'Lite', 'Plus', 'Go', 'Studio'],
            'almacenamiento': ['64GB', '128GB', '256GB', '512GB'],
            'ram': ['4GB', '6GB', '8GB', '12GB'],
            'precio_base': (200, 1500),
            'specs': ['pantalla', 'bateria', 'conectividad']
        },
        'Smartwatches': {
            'prefijos': ['Apple Watch', 'Galaxy Watch', 'Fitbit', 'Garmin', 'Amazfit'],
            'sufijos': ['SE', 'Series', 'Pro', 'Active', 'Sport', 'Classic'],
            'almacenamiento': ['16GB', '32GB'],
            'ram': ['1GB', '2GB', '4GB'],
            'precio_base': (100, 800),
            'specs': ['pantalla', 'bateria', 'sensores']
        },
        'Accesorios': {
            'prefijos': ['Case', 'Cover', 'Screen Protector', 'Stand', 'Holder'],
            'sufijos': ['Premium', 'Pro', 'Ultra', 'Basic', 'Plus', 'Max'],
            'almacenamiento': ['N/A'],
            'ram': ['N/A'],
            'precio_base': (5, 100),
            'specs': ['material', 'compatibilidad']
        },
        'Audio': {
            'prefijos': ['AirPods', 'Galaxy Buds', 'Echo', 'Soundcore', 'JBL', 'Sony'],
            'sufijos': ['Pro', 'Max', 'Studio', 'Sport', 'Wireless', 'Noise Canceling'],
            'almacenamiento': ['N/A'],
            'ram': ['N/A'],
            'precio_base': (20, 400),
            'specs': ['bluetooth', 'bateria', 'calidad']
        },
        'Gaming': {
            'prefijos': ['PlayStation', 'Xbox', 'Nintendo', 'Steam Deck', 'ROG', 'Legion'],
            'sufijos': ['5', 'Series X', 'Switch', 'OLED', 'Pro', 'Max'],
            'almacenamiento': ['256GB', '512GB', '1TB', '2TB'],
            'ram': ['8GB', '16GB', '32GB'],
            'precio_base': (250, 2000),
            'specs': ['procesador', 'graficos', 'almacenamiento']
        },
        'Cámaras': {
            'prefijos': ['EOS', 'Alpha', 'D', 'Z', 'Lumix', 'FinePix'],
            'sufijos': ['Mark IV', 'A7', '850', 'Z9', 'GH5', 'X-T4'],
            'almacenamiento': ['64GB', '128GB', '256GB', '512GB'],
            'ram': ['4GB', '8GB', '16GB'],
            'precio_base': (300, 5000),
            'specs': ['sensor', 'lente', 'resolucion']
        },
        'Televisores': {
            'prefijos': ['Bravia', 'OLED', 'QLED', 'Neo QLED', 'Crystal', 'UHD'],
            'sufijos': ['Smart', '4K', '8K', 'HDR', 'Dolby', 'Gaming'],
            'almacenamiento': ['16GB', '32GB'],
            'ram': ['2GB', '4GB', '8GB'],
            'precio_base': (300, 3000),
            'specs': ['pantalla', 'resolucion', 'smart']
        },
        'Monitores': {
            'prefijos': ['UltraSharp', 'Predator', 'Swift', 'Optix', 'LG', 'Samsung'],
            'sufijos': ['Gaming', 'Professional', '4K', 'Curved', 'Ultrawide'],
            'almacenamiento': ['N/A'],
            'ram': ['N/A'],
            'precio_base': (150, 1500),
            'specs': ['pantalla', 'resolucion', 'refresh']
        }
    }
    
    # Procesar en lotes para mejor rendimiento
    batch_size = 50
    for batch_start in range(0, CONFIG['productos_adicionales'], batch_size):
        batch_end = min(batch_start + batch_size, CONFIG['productos_adicionales'])
        print(f"   Procesando lote {batch_start//batch_size + 1}/{(CONFIG['productos_adicionales'] + batch_size - 1)//batch_size} (productos {batch_start+1}-{batch_end})")
        
        for i in range(batch_start, batch_end):
            categoria = random.choice(categorias)
            marca = random.choice(marcas)
            
            # Filtrar modelos de esta marca
            modelos_de_marca = [m for m in modelos if m.marca_id == marca.id]
            modelo = random.choice(modelos_de_marca) if modelos_de_marca else modelos[0]
            proveedore = random.choice(proveedores)
            condicion = random.choice(condiciones)
            impuesto = random.choice(impuestos)
            
            # Obtener template según categoría
            template = templates_productos.get(categoria.nombre, templates_productos['Accesorios'])
            
            # Generar nombre de producto
            prefijo = random.choice(template['prefijos'])
            sufijo = random.choice(template['sufijos'])
            numero = random.randint(1, 99)
            nombre_producto = f"{prefijo} {sufijo} {numero}"
            
            # Generar specs según tipo
            specs_extra = ""
            if 'procesador' in template.get('specs', []):
                procesador = random.choice(PROCESADORES_CHOICES)
                specs_extra += f" | {procesador}"
            if 'pantalla' in template.get('specs', []):
                pantalla = random.choice(TAMAÑO_PANTALLA_CHOICES)
                specs_extra += f" | {pantalla}"
            if 'bateria' in template.get('specs', []):
                bateria = random.choice(TIPO_BATERIA_CHOICES)
                specs_extra += f" | {bateria}"
            if 'resolucion' in template.get('specs', []):
                resolucion = random.choice(RESOLUCION_CHOICES)
                specs_extra += f" | {resolucion}"
            if 'conectividad' in template.get('specs', []):
                conexion = random.choice(TIPO_CONEXION_CHOICES)
                specs_extra += f" | {conexion}"
            
            # Rango de precios
            precio_min, precio_max = template['precio_base']
            precio_compra = Decimal(str(random.uniform(precio_min * 0.6, precio_max * 0.8)))
            precio_venta = Decimal(str(random.uniform(precio_min, precio_max)))
            
            # Crear producto
            producto, created = Producto.objects.get_or_create(
                nombre=nombre_producto,
                defaults={
                    'descripcion': f"Descripción del {nombre_producto}. Productos de alta calidad con las mejores especificaciones.{specs_extra}",
                    'categoria': categoria,
                    'marca': marca,
                    'modelo': modelo,
                    'proveedor': proveedore,
                    'precio_compra': precio_compra,
                    'precio_venta': precio_venta,
                    'stock': CONFIG['unidades_producto_adicional'],
                    'stock_minimo': random.randint(5, 15),
                    'almacenamiento': random.choice(template['almacenamiento']),
                    'memoria_ram': random.choice(template['ram']),
                    'colores_disponibles': ", ".join(random.sample(COLORES, random.randint(2, 5))),
                    'activo': True,
                    'impuesto': impuesto,
                    'usar_impuesto_global': random.choice([True, False]),
                }
            )
            
            # Crear unidades detalladas
            unidades_creadas = 0
            for unidad_idx in range(1, CONFIG['unidades_producto_adicional'] + 1):
                # Generar IMEI si es smartphone, sino serial number
                if categoria.nombre == 'Smartphones':
                    identificador = f"IMEI{random.randint(100000000000000, 999999999999999)}"
                else:
                    identificador = f"SN{producto.id:04d}{unidad_idx:03d}{random.randint(100, 999)}"
                
                unidad, created = ProductoUnitDetail.objects.get_or_create(
                    producto=producto,
                    unidad_index=unidad_idx,
                    defaults={
                        'imei': identificador,
                        'color': random.choice(COLORES),
                        'almacenamiento': random.choice(template['almacenamiento']),
                        'memoria_ram': random.choice(template['ram']),
                        'vida_bateria': random.randint(70, 100),
                        'codigo_barras': f"BAR{producto.id}{unidad_idx:03d}",
                        'condicion': condicion,
                        'precio_compra': precio_compra * Decimal(str(random.uniform(0.9, 1.1))),
                        'precio_venta': precio_venta * Decimal(str(random.uniform(0.9, 1.1))),
                        'vendido': False,  # Todas disponibles inicialmente
                        'usar_impuesto_global': random.choice([True, False]),
                        'impuesto': impuesto if random.choice([True, False]) else None,
                    }
                )
                if created:
                    unidades_creadas += 1
    
    print(f"✅ {CONFIG['productos_adicionales']} productos adicionales creados con {CONFIG['unidades_producto_adicional']} unidades cada uno")

def crear_sesiones_caja():
    """Crear sesiones de caja"""
    print("💵 Creando sesiones de caja...")
    
    for i in range(CONFIG['sesiones_caja']):
        fecha_apertura = timezone.now() - timedelta(days=random.randint(1, 30))
        
        CashSession.objects.get_or_create(
            apertura_at=fecha_apertura,
            defaults={
                'cierre_at': fecha_apertura + timedelta(hours=random.randint(6, 12)),
                'estado': random.choice(['CERRADA', 'CERRADA', 'CERRADA', 'ABIERTA']),  # Mayormente cerradas
                'monto_inicial': Decimal(str(random.uniform(1000, 5000))),
                'total_en_caja': Decimal(str(random.uniform(2000, 10000))),
                'total_ventas': Decimal(str(random.uniform(1000, 8000))),
                'total_impuesto': Decimal(str(random.uniform(100, 1000))),
                'total_descuento': Decimal(str(random.uniform(0, 500))),
                'total_ventas_credito': Decimal(str(random.uniform(0, 2000))),
            }
        )
    
    print(f"✅ {CONFIG['sesiones_caja']} sesiones de caja creadas")

def crear_ventas():
    """Crear ventas y detalles"""
    print("🛒 Creando ventas...")
    
    clientes = list(Cliente.objects.all())
    productos = list(Producto.objects.all())
    sesiones = list(CashSession.objects.filter(estado='CERRADA'))
    vendedores = list(User.objects.filter(is_staff=True))
    
    if not sesiones:
        print("⚠️ No hay sesiones de caja cerradas, creando una por defecto")
        sesion = CashSession.objects.create(
            estado='CERRADA',
            monto_inicial=Decimal('1000.00'),
            total_en_caja=Decimal('2000.00'),
            total_ventas=Decimal('1000.00'),
            total_impuesto=Decimal('180.00'),
            total_descuento=Decimal('0.00'),
            total_ventas_credito=Decimal('0.00'),
        )
        sesiones = [sesion]
    
    for i in range(CONFIG['ventas']):
        cliente = random.choice(clientes)
        sesion = random.choice(sesiones)
        vendedor = random.choice(vendedores) if vendedores else None
        
        # Crear venta
        venta = Venta.objects.create(
            cliente=cliente,
            vendedor=vendedor,
            metodo_pago=random.choice(['EFECTIVO', 'TARJETA', 'TRANSFERENCIA', 'CREDITO']),
            notas=f"Venta de prueba #{i+1}",
            sesion_caja=sesion,
        )
        
        # Agregar productos a la venta
        num_productos = random.randint(1, 3)
        total_venta = Decimal('0')
        
        for j in range(num_productos):
            producto = random.choice(productos)
            cantidad = random.randint(1, 2)
            
            # Verificar stock
            if producto.stock >= cantidad:
                precio_unitario = producto.precio_venta
                subtotal = precio_unitario * cantidad
                total_venta += subtotal
                
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    descuento=Decimal('0'),
                    unidad_index=random.randint(1, CONFIG['unidades_por_producto']),
                )
                
                # Reducir stock
                producto.stock -= cantidad
                producto.save()
        
        # El total se calcula automáticamente desde la propiedad total
    
    print(f"✅ {CONFIG['ventas']} ventas creadas")

def crear_creditos():
    """Crear cuentas de crédito"""
    print("💳 Creando créditos...")
    
    ventas_credito = Venta.objects.filter(metodo_pago='CREDITO')
    
    for i, venta in enumerate(ventas_credito[:CONFIG['creditos']]):
        # Crear cuenta de crédito
        credito = CuentaCredito.objects.create(
            venta=venta,
            cliente=venta.cliente,
            total_credito=venta.total,
            saldo_pendiente=venta.total * Decimal(str(random.uniform(0.3, 1.0))),
            numero_cuotas=random.randint(1, 12),
            cuotas_pagadas=random.randint(0, 3),
            monto_cuota=venta.total / random.randint(3, 12),
            abono_inicial=Decimal('0'),
            frecuencia_dias=30,
            estado=random.choice(['pendiente', 'pendiente', 'vencido', 'pagado']),
        )
        
        # Crear algunos pagos
        if credito.estado in ['pendiente', 'vencido'] and random.choice([True, False]):
            PagoCredito.objects.create(
                cuenta=credito,
                monto=credito.monto_cuota,
                registrado_por=User.objects.first(),
                comentario=f"Pago {i+1}",
            )
    
    print(f"✅ {min(CONFIG['creditos'], len(ventas_credito))} créditos creados")

def configurar_sitio():
    """Configurar parámetros del sitio"""
    print("⚙️ Configurando sitio...")
    
    config, created = SiteConfiguration.objects.get_or_create(
        id=1,
        defaults={
            'empresa_nombre': 'SistemaPOS Demo',
            'empresa_rnc': '131231231',
            'empresa_telefono': '809-555-0000',
            'empresa_direccion': 'Calle Principal #123, Santo Domingo',
            'global_tax_enabled': True,
            'global_tax_rate': Decimal('18.00'),
            'stock_minimo_default': 3,
            'bloquear_venta_sin_stock': False,
            'alerta_stock_bajo_porcentaje': 20,
        }
    )
    
    print("✅ Configuración del sitio completada")

def main():
    """Función principal"""
    print("🚀 Iniciando poblado de base de datos...")
    print(f"📊 Configuración: {CONFIG}")
    print("=" * 50)
    
    try:
        # Ejecutar en orden correcto
        crear_usuarios()
        crear_categorias()
        crear_marcas()
        crear_modelos()
        crear_proveedores()
        crear_impuestos()
        crear_condiciones()
        crear_clientes()
        crear_productos()
        crear_productos_adicionales()
        crear_sesiones_caja()
        crear_ventas()
        crear_creditos()
        configurar_sitio()
        
        print("=" * 50)
        print("✅ Poblado completado exitosamente!")
        print("🎉 Base de datos lista para usar")
        print("\n📋 Resumen:")
        print(f"   • Usuarios: {User.objects.count()}")
        print(f"   • Clientes: {Cliente.objects.count()}")
        print(f"   • Productos originales: {CONFIG['productos']}")
        print(f"   • Productos adicionales: {CONFIG['productos_adicionales']}")
        print(f"   • Total productos: {Producto.objects.count()}")
        print(f"   • Unidades totales: {ProductoUnitDetail.objects.count()}")
        print(f"   • Ventas: {Venta.objects.count()}")
        print(f"   • Créditos: {CuentaCredito.objects.count()}")
        
        print(f"\n📊 Distribución:")
        print(f"   • Productos originales: {CONFIG['productos']} x {CONFIG['unidades_por_producto']} = {CONFIG['productos'] * CONFIG['unidades_por_producto']}")
        print(f"   • Productos adicionales: {CONFIG['productos_adicionales']} x {CONFIG['unidades_producto_adicional']} = {CONFIG['productos_adicionales'] * CONFIG['unidades_producto_adicional']}")
        print(f"   • Total unidades esperadas: {(CONFIG['productos'] * CONFIG['unidades_por_producto']) + (CONFIG['productos_adicionales'] * CONFIG['unidades_producto_adicional'])}")
        print(f"   • Total unidades creadas: {ProductoUnitDetail.objects.count()}")
        print(f"\n🎯 TODOS los productos ahora tienen 50 unidades según su tipo")
        
        print("\n🔑 Acceso:")
        print("   • URL: http://127.0.0.1:8000/admin/")
        print("   • Usuario: admin")
        print("   • Contraseña: admin123")
        
    except Exception as e:
        print(f"❌ Error durante el poblado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
