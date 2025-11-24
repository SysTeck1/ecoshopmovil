"""
Sistema de tipos de productos para formularios dinámicos
"""
from django import forms
from django.core.exceptions import ValidationError


class ProductTypeRegistry:
    """Registro de tipos de productos con sus formularios específicos"""
    
    def __init__(self):
        self._types = {}
    
    def register(self, type_key, type_config):
        """Registra un tipo de producto"""
        self._types[type_key] = type_config
    
    def get_type(self, type_key):
        """Obtiene configuración de un tipo"""
        return self._types.get(type_key)
    
    def get_all_types(self):
        """Obtiene todos los tipos registrados"""
        return self._types
    
    def get_choices(self):
        """Obtiene choices para formularios"""
        return [(key, config['name']) for key, config in self._types.items()]


# Instancia global del registro
product_registry = ProductTypeRegistry()


# Configuraciones de tipos de productos
PHONE_CONFIG = {
    'name': 'Teléfonos',
    'icon': '📱',
    'fields': {
        'almacenamiento': {
            'type': 'choice',
            'label': 'Almacenamiento',
            'choices': [
                ('16GB', '16 GB'), ('32GB', '32 GB'), ('64GB', '64 GB'),
                ('128GB', '128 GB'), ('256GB', '256 GB'), ('512GB', '512 GB'), ('1TB', '1 TB')
            ],
            'required': False
        },
        'memoria_ram': {
            'type': 'choice',
            'label': 'RAM',
            'choices': [
                ('2GB', '2 GB'), ('3GB', '3 GB'), ('4GB', '4 GB'),
                ('6GB', '6 GB'), ('8GB', '8 GB'), ('12GB', '12 GB'), ('16GB', '16 GB')
            ],
            'required': False
        },
        'imei': {
            'type': 'text',
            'label': 'IMEI',
            'max_length': 50,
            'required': False
        },
        'color': {
            'type': 'text',
            'label': 'Color',
            'max_length': 50,
            'required': False
        },
        'vida_bateria': {
            'type': 'number',
            'label': 'Vida útil batería (%)',
            'min_value': 0,
            'max_value': 100,
            'required': False
        },
        'colores_disponibles': {
            'type': 'text',
            'label': 'Colores disponibles',
            'help_text': 'Separados por comas',
            'required': False
        }
    }
}

ACCESSORY_CONFIG = {
    'name': 'Accesorios',
    'icon': '🔌',
    'fields': {
        'tipo_accesorio': {
            'type': 'choice',
            'label': 'Tipo de accesorio',
            'choices': [
                ('cargador', 'Cargador'),
                ('cable', 'Cable'),
                ('auriculares', 'Auriculares'),
                ('funda', 'Funda/Case'),
                ('protector', 'Protector de pantalla'),
                ('soporte', 'Soporte'),
                ('bateria', 'Batería externa'),
                ('otro', 'Otro')
            ],
            'required': True
        },
        'compatibilidad': {
            'type': 'text',
            'label': 'Compatibilidad',
            'help_text': 'Dispositivos compatibles',
            'max_length': 200,
            'required': False
        },
        'color': {
            'type': 'text',
            'label': 'Color',
            'max_length': 50,
            'required': False
        },
        'material': {
            'type': 'choice',
            'label': 'Material',
            'choices': [
                ('plastico', 'Plástico'),
                ('silicona', 'Silicona'),
                ('cuero', 'Cuero'),
                ('metal', 'Metal'),
                ('vidrio', 'Vidrio templado'),
                ('tela', 'Tela'),
                ('otro', 'Otro')
            ],
            'required': False
        },
        'potencia': {
            'type': 'text',
            'label': 'Potencia/Capacidad',
            'help_text': 'Ej: 20W, 10000mAh, etc.',
            'max_length': 50,
            'required': False
        }
    }
}

LAPTOP_CONFIG = {
    'name': 'Laptops',
    'icon': '💻',
    'fields': {
        'procesador': {
            'type': 'text',
            'label': 'Procesador',
            'max_length': 100,
            'required': False
        },
        'memoria_ram': {
            'type': 'choice',
            'label': 'RAM',
            'choices': [
                ('4GB', '4 GB'), ('8GB', '8 GB'), ('16GB', '16 GB'),
                ('32GB', '32 GB'), ('64GB', '64 GB')
            ],
            'required': False
        },
        'almacenamiento': {
            'type': 'choice',
            'label': 'Almacenamiento',
            'choices': [
                ('128GB', '128 GB SSD'), ('256GB', '256 GB SSD'),
                ('512GB', '512 GB SSD'), ('1TB', '1 TB SSD'),
                ('2TB', '2 TB SSD'), ('1TB_HDD', '1 TB HDD')
            ],
            'required': False
        },
        'pantalla': {
            'type': 'text',
            'label': 'Pantalla',
            'help_text': 'Ej: 15.6" Full HD, 13.3" 4K',
            'max_length': 100,
            'required': False
        },
        'tarjeta_grafica': {
            'type': 'text',
            'label': 'Tarjeta gráfica',
            'max_length': 100,
            'required': False
        },
        'sistema_operativo': {
            'type': 'choice',
            'label': 'Sistema operativo',
            'choices': [
                ('windows11', 'Windows 11'),
                ('windows10', 'Windows 10'),
                ('macos', 'macOS'),
                ('linux', 'Linux'),
                ('sin_os', 'Sin OS'),
                ('otro', 'Otro')
            ],
            'required': False
        },
        'numero_serie': {
            'type': 'text',
            'label': 'Número de serie',
            'max_length': 100,
            'required': False
        }
    }
}

TABLET_CONFIG = {
    'name': 'Tablets',
    'icon': '📟',
    'fields': {
        'pantalla': {
            'type': 'text',
            'label': 'Pantalla',
            'help_text': 'Ej: 10.1", 12.9"',
            'max_length': 50,
            'required': False
        },
        'almacenamiento': {
            'type': 'choice',
            'label': 'Almacenamiento',
            'choices': [
                ('32GB', '32 GB'), ('64GB', '64 GB'), ('128GB', '128 GB'),
                ('256GB', '256 GB'), ('512GB', '512 GB'), ('1TB', '1 TB')
            ],
            'required': False
        },
        'memoria_ram': {
            'type': 'choice',
            'label': 'RAM',
            'choices': [
                ('2GB', '2 GB'), ('3GB', '3 GB'), ('4GB', '4 GB'),
                ('6GB', '6 GB'), ('8GB', '8 GB'), ('12GB', '12 GB')
            ],
            'required': False
        },
        'conectividad': {
            'type': 'choice',
            'label': 'Conectividad',
            'choices': [
                ('wifi', 'Solo WiFi'),
                ('wifi_cellular', 'WiFi + Cellular'),
                ('wifi_5g', 'WiFi + 5G')
            ],
            'required': False
        },
        'color': {
            'type': 'text',
            'label': 'Color',
            'max_length': 50,
            'required': False
        },
        'vida_bateria': {
            'type': 'number',
            'label': 'Vida útil batería (%)',
            'min_value': 0,
            'max_value': 100,
            'required': False
        }
    }
}

GAMING_CONFIG = {
    'name': 'Gaming',
    'icon': '🎮',
    'fields': {
        'tipo_gaming': {
            'type': 'choice',
            'label': 'Tipo de producto',
            'choices': [
                ('consola', 'Consola'),
                ('control', 'Control/Mando'),
                ('juego', 'Videojuego'),
                ('accesorio', 'Accesorio gaming')
            ],
            'required': True
        },
        'plataforma': {
            'type': 'choice',
            'label': 'Plataforma',
            'choices': [
                ('ps5', 'PlayStation 5'),
                ('ps4', 'PlayStation 4'),
                ('xbox_series', 'Xbox Series X/S'),
                ('xbox_one', 'Xbox One'),
                ('nintendo_switch', 'Nintendo Switch'),
                ('pc', 'PC'),
                ('universal', 'Universal')
            ],
            'required': False
        },
        'almacenamiento': {
            'type': 'choice',
            'label': 'Almacenamiento',
            'choices': [
                ('500GB', '500 GB'), ('1TB', '1 TB'), ('2TB', '2 TB')
            ],
            'required': False
        },
        'color': {
            'type': 'text',
            'label': 'Color',
            'max_length': 50,
            'required': False
        },
        'numero_serie': {
            'type': 'text',
            'label': 'Número de serie',
            'max_length': 100,
            'required': False
        }
    }
}

# Registrar todos los tipos
product_registry.register('phone', PHONE_CONFIG)
product_registry.register('accessory', ACCESSORY_CONFIG)
product_registry.register('laptop', LAPTOP_CONFIG)
product_registry.register('tablet', TABLET_CONFIG)
product_registry.register('gaming', GAMING_CONFIG)


def get_dynamic_form_class(product_type):
    """Genera una clase de formulario dinámico basado en el tipo de producto"""
    
    config = product_registry.get_type(product_type)
    if not config:
        return None
    
    form_fields = {}
    
    for field_name, field_config in config['fields'].items():
        field_type = field_config['type']
        field_kwargs = {
            'label': field_config['label'],
            'required': field_config.get('required', False),
        }
        
        if 'help_text' in field_config:
            field_kwargs['help_text'] = field_config['help_text']
        
        if field_type == 'text':
            if 'max_length' in field_config:
                field_kwargs['max_length'] = field_config['max_length']
            form_fields[field_name] = forms.CharField(**field_kwargs)
            
        elif field_type == 'choice':
            choices = [('', '-- Seleccionar --')] + field_config['choices']
            field_kwargs['choices'] = choices
            form_fields[field_name] = forms.ChoiceField(**field_kwargs)
            
        elif field_type == 'number':
            if 'min_value' in field_config:
                field_kwargs['min_value'] = field_config['min_value']
            if 'max_value' in field_config:
                field_kwargs['max_value'] = field_config['max_value']
            form_fields[field_name] = forms.IntegerField(**field_kwargs)
    
    # Crear clase de formulario dinámicamente
    DynamicForm = type(f'{product_type.title()}Form', (forms.Form,), form_fields)
    
    return DynamicForm
