# Constants for SistemaPOS project
from decimal import Decimal


def get_demo_invoice_data():
    """
    Returns demo data for invoice preview.
    This can be replaced with real data from database.
    """
    return {
        'empresa': {
            'nombre': 'Sistema POS',
            'rnc': '123456789',
            'direccion': 'Calle Principal #123, Santo Domingo',
            'telefono': '809-555-1234',
            'email': 'info@sistemapos.com'
        },
        'posicion_logo': 'left',
        'numero_factura': 'DEMO-000001',
        'fecha': 'Demo Date',
        'cliente': {
            'nombre': 'CLIENTE DEMO',
            'rnc': '12345678901',
            'direccion': 'Calle Principal #123, Santo Domingo',
            'telefono': '809-555-1234'
        },
        'items': [
            {
                'descripcion': 'iPhone 13 Pro - 128GB - Azul',
                'cantidad': 1,
                'precio_unitario': Decimal('29999.00'),
                'itbis': Decimal('3900.00'),
                'total': Decimal('33899.00')
            },
            {
                'descripcion': 'Funda de Silicone - Rosa',
                'cantidad': 2,
                'precio_unitario': Decimal('500.00'),
                'itbis': Decimal('65.00'),
                'total': Decimal('1130.00')
            },
            {
                'descripcion': 'Protector de Pantalla - Templado',
                'cantidad': 1,
                'precio_unitario': Decimal('800.00'),
                'itbis': Decimal('104.00'),
                'total': Decimal('904.00')
            }
        ],
        'subtotal': Decimal('31300.00'),
        'total_itbis': Decimal('4069.00'),
        'total_general': Decimal('35369.00'),
        'forma_pago': 'Efectivo',
    }
