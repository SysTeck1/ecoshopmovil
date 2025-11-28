"""
Formularios dinámicos para diferentes tipos de productos
"""
from django import forms
from django.forms import inlineformset_factory
from ventas.models import Producto, ProductoSpecificFields
from ventas.product_types import product_registry, get_dynamic_form_class


class ProductTypeSelectionForm(forms.Form):
    """Formulario para seleccionar el tipo de producto"""
    
    tipo_producto = forms.ChoiceField(
        label="Tipo de producto",
        choices=Producto.TIPO_PRODUCTO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'field__control',
            'data-product-type-selector': True
        }),
        help_text="Selecciona el tipo de producto para mostrar campos específicos"
    )


class BaseProductForm(forms.ModelForm):
    """Formulario base para productos"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Establecer valor por defecto de stock_minimo desde la configuración del sitio
        if not self.instance.pk and not self.initial.get('stock_minimo'):
            from .models import SiteConfiguration
            try:
                site_config = SiteConfiguration.get_solo()
                self.initial['stock_minimo'] = site_config.stock_minimo_default
            except Exception:
                # Si hay error, usar valor por defecto
                self.initial['stock_minimo'] = 5
    
    class Meta:
        model = Producto
        fields = [
            'tipo_producto', 'nombre', 'marca', 'modelo', 'categoria', 'proveedor',
            'descripcion', 'precio_compra', 'precio_venta', 'stock', 'stock_minimo',
            'almacenamiento', 'memoria_ram', 'imei', 'colores_disponibles',
            'usar_impuesto_global', 'impuesto', 'activo'
        ]
        widgets = {
            'tipo_producto': forms.Select(attrs={
                'class': 'field__control',
                'data-product-type-selector': True
            }),
            'nombre': forms.TextInput(attrs={'class': 'field__control'}),
            'descripcion': forms.Textarea(attrs={'class': 'field__control', 'rows': 3}),
            'precio_compra': forms.NumberInput(attrs={'class': 'field__control', 'step': '0.01'}),
            'precio_venta': forms.NumberInput(attrs={'class': 'field__control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'field__control'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'field__control'}),
            'almacenamiento': forms.Select(attrs={'class': 'field__control'}),
            'memoria_ram': forms.Select(attrs={'class': 'field__control'}),
            'imei': forms.Textarea(attrs={'class': 'field__control', 'rows': 3}),
            'colores_disponibles': forms.TextInput(attrs={'class': 'field__control'}),
            'marca': forms.Select(attrs={'class': 'field__control'}),
            'modelo': forms.Select(attrs={'class': 'field__control'}),
            'categoria': forms.Select(attrs={'class': 'field__control'}),
            'proveedor': forms.Select(attrs={'class': 'field__control'}),
            'impuesto': forms.Select(attrs={'class': 'field__control'}),
        }


class ProductoSpecificFieldsForm(forms.ModelForm):
    """Formulario para campos específicos del producto"""
    
    class Meta:
        model = ProductoSpecificFields
        exclude = ['producto', 'created_at', 'updated_at']
        widgets = {
            'procesador': forms.TextInput(attrs={'class': 'field__control'}),
            'pantalla': forms.TextInput(attrs={'class': 'field__control'}),
            'sistema_operativo': forms.TextInput(attrs={'class': 'field__control'}),
            'tipo_accesorio': forms.TextInput(attrs={'class': 'field__control'}),
            'compatibilidad': forms.TextInput(attrs={'class': 'field__control'}),
            'material': forms.TextInput(attrs={'class': 'field__control'}),
            'potencia': forms.TextInput(attrs={'class': 'field__control'}),
            'tarjeta_grafica': forms.TextInput(attrs={'class': 'field__control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'field__control'}),
            'tipo_gaming': forms.TextInput(attrs={'class': 'field__control'}),
            'plataforma': forms.TextInput(attrs={'class': 'field__control'}),
            'conectividad': forms.TextInput(attrs={'class': 'field__control'}),
        }


def get_product_form_fields(product_type):
    """Obtiene los campos que deben mostrarse para un tipo de producto específico"""
    
    config = product_registry.get_type(product_type)
    if not config:
        return []
    
    # Campos base que siempre se muestran (excepto precios en creación)
    base_fields = ['tipo_producto', 'nombre', 'marca', 'modelo', 'categoria', 'proveedor', 'descripcion', 'stock', 'stock_minimo', 'activo']
    
    # Agregar precios solo si no es modo creación (se determina en la vista)
    base_fields_with_prices = base_fields + ['precio_compra', 'precio_venta']
    
    # Campos específicos según el tipo (sin IMEI ni colores para creación)
    specific_fields = []
    
    if product_type == 'phone':
        specific_fields = ['almacenamiento', 'memoria_ram', 'usar_impuesto_global', 'impuesto']  # Sin imei ni colores
    elif product_type == 'accessory':
        specific_fields = ['usar_impuesto_global', 'impuesto']
    elif product_type == 'laptop':
        specific_fields = ['almacenamiento', 'memoria_ram', 'usar_impuesto_global', 'impuesto']
    elif product_type == 'tablet':
        specific_fields = ['almacenamiento', 'memoria_ram', 'usar_impuesto_global', 'impuesto']  # Sin colores
    elif product_type == 'gaming':
        specific_fields = ['almacenamiento', 'usar_impuesto_global', 'impuesto']
    
    return base_fields + specific_fields


def get_product_form_fields_with_prices(product_type):
    """Obtiene los campos que deben mostrarse para un tipo de producto específico (incluyendo precios)"""
    
    config = product_registry.get_type(product_type)
    if not config:
        return []
    
    # Campos base con precios para modo edición
    base_fields = ['tipo_producto', 'nombre', 'marca', 'modelo', 'categoria', 'proveedor', 'descripcion', 'precio_compra', 'precio_venta', 'stock', 'stock_minimo', 'activo']
    
    # Campos específicos según el tipo
    specific_fields = []
    
    if product_type == 'phone':
        specific_fields = ['almacenamiento', 'memoria_ram', 'imei', 'colores_disponibles', 'usar_impuesto_global', 'impuesto']
    elif product_type == 'accessory':
        specific_fields = ['usar_impuesto_global', 'impuesto']
    elif product_type == 'laptop':
        specific_fields = ['almacenamiento', 'memoria_ram', 'usar_impuesto_global', 'impuesto']
    elif product_type == 'tablet':
        specific_fields = ['almacenamiento', 'memoria_ram', 'colores_disponibles', 'usar_impuesto_global', 'impuesto']
    elif product_type == 'gaming':
        specific_fields = ['almacenamiento', 'usar_impuesto_global', 'impuesto']
    
    return base_fields + specific_fields


def get_specific_form_fields(product_type):
    """Obtiene los campos específicos que deben mostrarse para un tipo de producto"""
    
    field_mapping = {
        'phone': ['procesador', 'pantalla', 'sistema_operativo'],
        'accessory': ['tipo_accesorio', 'compatibilidad', 'material', 'potencia'],
        'laptop': ['procesador', 'pantalla', 'tarjeta_grafica', 'sistema_operativo', 'numero_serie'],
        'tablet': ['procesador', 'pantalla', 'sistema_operativo', 'conectividad'],
        'gaming': ['tipo_gaming', 'plataforma', 'numero_serie']
    }
    
    return field_mapping.get(product_type, [])


class DynamicProductForm(BaseProductForm):
    """Formulario dinámico que se adapta según el tipo de producto"""
    
    def __init__(self, *args, **kwargs):
        self.product_type = kwargs.pop('product_type', 'phone')
        self.is_creation_mode = kwargs.pop('is_creation_mode', True)
        super().__init__(*args, **kwargs)
        
        # Personalizar el campo de modelo para incluir data-brand-id ANTES de eliminar campos
        if 'modelo' in self.fields:
            self.fields['modelo'].widget.attrs['class'] = 'field__control'
            # Personalizar las opciones del campo modelo
            from ventas.models import Modelo
            modelos = Modelo.objects.select_related('marca').order_by('marca__nombre', 'nombre')
            
            # Crear opciones con data-brand-id
            choices = [('', '---------')]
            for modelo in modelos:
                choice_value = str(modelo.id)
                choice_label = f"{modelo.marca.nombre} - {modelo.nombre}" if modelo.marca else modelo.nombre
                choices.append((choice_value, choice_label))
            
            self.fields['modelo'].choices = choices
            
            # Agregar atributo data-brand-id a cada opción
            self.fields['modelo'].widget.attrs['data-brand-options'] = 'true'
            
            # Crear un diccionario de marca_id para cada modelo
            brand_mapping = {}
            for modelo in modelos:
                brand_mapping[str(modelo.id)] = str(modelo.marca.id) if modelo.marca else ''
            
            self.fields['modelo'].widget.attrs['data-brand-mapping'] = str(brand_mapping)
        
        # Obtener campos permitidos para este tipo de producto
        if self.is_creation_mode:
            allowed_fields = get_product_form_fields(self.product_type)  # Sin precios
        else:
            allowed_fields = get_product_form_fields_with_prices(self.product_type)  # Con precios
        
        # Remover campos no permitidos
        fields_to_remove = []
        for field_name in self.fields:
            if field_name not in allowed_fields:
                fields_to_remove.append(field_name)
        
        for field_name in fields_to_remove:
            del self.fields[field_name]
        
        # Configurar el campo tipo_producto
        if 'tipo_producto' in self.fields:
            self.fields['tipo_producto'].initial = self.product_type
            
        # Hacer campos condicionales opcionales según el tipo
        if self.product_type == 'accessory':
            # Para accesorios, algunos campos de teléfonos no son relevantes
            optional_fields = ['almacenamiento', 'memoria_ram', 'imei']
            for field in optional_fields:
                if field in self.fields:
                    self.fields[field].required = False
                    
        elif self.product_type == 'gaming':
            # Para gaming, algunos campos son opcionales
            optional_fields = ['memoria_ram', 'imei']
            for field in optional_fields:
                if field in self.fields:
                    self.fields[field].required = False
        
        # En modo creación, si los precios están presentes, hacerlos opcionales
        if self.is_creation_mode:
            price_fields = ['precio_compra', 'precio_venta']
            for field in price_fields:
                if field in self.fields:
                    self.fields[field].required = False


class DynamicSpecificFieldsForm(ProductoSpecificFieldsForm):
    """Formulario dinámico para campos específicos"""
    
    def __init__(self, *args, **kwargs):
        self.product_type = kwargs.pop('product_type', 'phone')
        super().__init__(*args, **kwargs)
        
        # Obtener campos permitidos para este tipo de producto
        allowed_fields = get_specific_form_fields(self.product_type)
        
        # Remover campos no permitidos
        fields_to_remove = []
        for field_name in self.fields:
            if field_name not in allowed_fields and field_name != 'extra_fields':
                fields_to_remove.append(field_name)
        
        for field_name in fields_to_remove:
            del self.fields[field_name]
