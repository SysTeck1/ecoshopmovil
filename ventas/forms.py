from decimal import Decimal

from django import forms

from .models import (
    Categoria,
    Cliente,
    Impuesto,
    Marca,
    Modelo,
    ProductCondition,
    ProductImage,
    Producto,
    Proveedor,
    FiscalVoucherConfig,
    FiscalVoucherXML,
    TradeInCredit,
    TIPO_PRODUCTO_CHOICES,
)


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "nombre",
            "tipo_documento",
            "documento",
            "correo",
            "direccion",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej. Juan Pérez",
                "required": True,
                "data-initial-focus": "true",
            }),
            "tipo_documento": forms.Select(attrs={
                "class": "select-control",
            }),
            "documento": forms.TextInput(attrs={
                "placeholder": "Ingrese el documento",
            }),
            "correo": forms.EmailInput(attrs={
                "placeholder": "correo@ejemplo.com",
            }),
            "direccion": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Calle, número, sector",
            }),
            "observaciones": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Notas internas, consideraciones especiales…",
            }),
        }

    def clean_documento(self):
        documento = self.cleaned_data.get("documento", "").strip()
        return documento

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()
        return nombre


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "nombre",
            "tipo_documento",
            "documento",
            "telefono",
            "correo",
            "direccion",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej. Proveedor XYZ",
                "required": True,
                "data-initial-focus": "true",
            }),
            "tipo_documento": forms.Select(attrs={
                "class": "select-control",
            }),
            "documento": forms.TextInput(attrs={
                "placeholder": "Ingrese el documento",
            }),
            "telefono": forms.TextInput(attrs={
                "placeholder": "+1 809-000-0000",
            }),
            "correo": forms.EmailInput(attrs={
                "placeholder": "contacto@proveedor.com",
            }),
            "direccion": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Calle, número, sector",
            }),
        }

    def clean_nombre(self):
        return self.cleaned_data.get("nombre", "").strip()


class FiscalVoucherXMLForm(forms.ModelForm):
    class Meta:
        model = FiscalVoucherXML
        fields = ["nombre", "archivo"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Identificador del XML (opcional)",
                "maxlength": 160,
            }),
            "archivo": forms.ClearableFileInput(attrs={
                "accept": ".xml",
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()
        if not nombre:
            archivo = self.cleaned_data.get("archivo")
            if archivo:
                return archivo.name
        return nombre


class ImpuestoForm(forms.ModelForm):
    class Meta:
        model = Impuesto
        fields = ["nombre", "porcentaje"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej. ITBIS",
                "required": True,
                "data-initial-focus": "true",
                "autocomplete": "off",
                "maxlength": 120,
            }),
            "porcentaje": forms.NumberInput(attrs={
                "placeholder": "Ej. 18",
                "step": "0.01",
                "min": "0",
                "max": "100",
            }),
        }

    def clean_nombre(self):
        return self.cleaned_data.get("nombre", "").strip()

    def clean_porcentaje(self):
        porcentaje = self.cleaned_data.get("porcentaje")
        if porcentaje is None:
            return porcentaje
        return porcentaje


class ProductoForm(forms.ModelForm):
    usar_impuesto_global = forms.BooleanField(
        required=False,
        initial=True,
        label="Usar impuesto global",
        help_text="Si se activa, este producto aplicará la tasa global configurada",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Establecer valor por defecto de stock_minimo desde la configuración del sitio
        if not self.instance.pk and not self.initial.get('stock_minimo'):
            from dashboard.models import SiteConfiguration
            site_config = SiteConfiguration.get_solo()
            self.initial['stock_minimo'] = site_config.stock_minimo_default
        
        for campo in ["precio_compra", "precio_venta", "stock", "stock_minimo"]:
            if campo in self.fields:
                self.fields[campo].required = False
        if "categoria" in self.fields:
            self.fields["categoria"].queryset = Categoria.objects.all()
            self.fields["categoria"].empty_label = "Sin categoría"
        if "marca" in self.fields:
            self.fields["marca"].queryset = Marca.objects.filter(activo=True)
            self.fields["marca"].required = False
            self.fields["marca"].empty_label = "Sin marca"
        if "modelo" in self.fields:
            self.fields["modelo"].queryset = Modelo.objects.filter(activo=True)
            self.fields["modelo"].required = False
            self.fields["modelo"].empty_label = "Sin modelo"
        if "proveedor" in self.fields:
            self.fields["proveedor"].queryset = Proveedor.objects.all()
            self.fields["proveedor"].empty_label = "Sin proveedor"
            self.fields["proveedor"].required = False
        for campo in ["almacenamiento", "memoria_ram"]:
            if campo in self.fields:
                self.fields[campo].required = False
        if "impuesto" in self.fields:
            self.fields["impuesto"].required = False
            self.fields["impuesto"].queryset = Impuesto.objects.all()
            self.fields["impuesto"].empty_label = "Sin impuesto"

    def clean(self):
        cleaned_data = super().clean()
        usar_impuesto_global = cleaned_data.get("usar_impuesto_global")
        impuesto = cleaned_data.get("impuesto")
        if usar_impuesto_global:
            cleaned_data["impuesto"] = None
        else:
            if impuesto is None:
                raise forms.ValidationError("Selecciona un impuesto o activa la opción de impuesto global.")
        return cleaned_data

    class Meta:
        model = Producto
        fields = [
            "nombre",
            "marca",
            "modelo",
            "categoria",
            "proveedor",
            "almacenamiento",
            "memoria_ram",
            "imei",
            "descripcion",
            "colores_disponibles",
            "imagen",
            "precio_compra",
            "precio_venta",
            "stock",
            "stock_minimo",
            "impuesto",
            "usar_impuesto_global",
            "activo",
        ]
        exclude = []
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej. iPhone 14 Pro",
                "required": True,
                "data-initial-focus": "true",
            }),
            "marca": forms.Select(attrs={
                "class": "select-control",
            }),
            "modelo": forms.Select(attrs={
                "class": "select-control",
            }),
            "categoria": forms.Select(attrs={
                "class": "select-control",
            }),
            "almacenamiento": forms.Select(attrs={
                "class": "select-control",
            }),
            "memoria_ram": forms.Select(attrs={
                "class": "select-control",
            }),
            "imei": forms.TextInput(attrs={
                "placeholder": "000000000000000",
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Describe brevemente el estado y características del teléfono",
            }),
            "colores_disponibles": forms.TextInput(attrs={
                "placeholder": "Negro, Azul, Dorado",
            }),
            "imagen": forms.ClearableFileInput(attrs={
                "accept": "image/*",
            }),
            "proveedor": forms.Select(attrs={
                "class": "select-control",
            }),
            "precio_compra": forms.NumberInput(attrs={
                "min": 0,
                "step": "0.01",
            }),
            "precio_venta": forms.NumberInput(attrs={
                "min": 0,
                "step": "0.01",
            }),
            "stock": forms.NumberInput(attrs={
                "min": 0,
            }),
            "stock_minimo": forms.NumberInput(attrs={
                "min": 0,
            }),
        }

    def clean_nombre(self):
        return self.cleaned_data.get("nombre", "").strip()

    def clean_colores_disponibles(self):
        return self.cleaned_data.get("colores_disponibles", "").strip()

    def _clean_decimal_default_zero(self, field_name):
        valor = self.cleaned_data.get(field_name)
        if valor in (None, ""):
            return Decimal("0")
        return valor

    def _clean_int_default_zero(self, field_name):
        valor = self.cleaned_data.get(field_name)
        if valor in (None, ""):
            return 0
        return valor

    def clean_precio_compra(self):
        return self._clean_decimal_default_zero("precio_compra")

    def clean_precio_venta(self):
        return self._clean_decimal_default_zero("precio_venta")

    def clean_stock(self):
        return self._clean_int_default_zero("stock")

    def clean_stock_minimo(self):
        return self._clean_int_default_zero("stock_minimo")


class CategoriaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import TipoProducto
        
        # Obtener tipos de producto dinámicamente
        tipos_producto = TipoProducto.objects.filter(activo=True).order_by('nombre')
        choices = [("", "🔧 General (todos los tipos)")]
        
        for tipo in tipos_producto:
            choices.append((tipo.id, f"{tipo.get_icono_display()} {tipo.nombre}"))
        
        self.fields['tipo_producto'] = forms.ModelChoiceField(
            queryset=TipoProducto.objects.filter(activo=True).order_by('nombre'),
            choices=choices,
            required=False,
            label="Tipo de producto",
            help_text="Selecciona el tipo de producto para esta categoría",
            empty_label="🔧 General (todos los tipos)",
        )

    class Meta:
        model = Categoria
        fields = ["nombre", "tipo_producto"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej. Accesorios",
                "required": True,
                "data-initial-focus": "true",
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nombre"].widget.attrs.setdefault("placeholder", "Ej. Accesorios")
        self.fields["nombre"].widget.attrs.setdefault("required", True)
        self.fields["nombre"].widget.attrs.setdefault("data-initial-focus", "true")
        self.fields["tipo_producto"].widget.attrs.update({
            "id": self.fields["tipo_producto"].widget.attrs.get("id", "category-register-type-input"),
            "class": "modal-field__input",
        })

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre de la categoría es requerido.")
        
        # Verificar unicidad excluyendo la instancia actual (edición)
        queryset = Categoria.objects.filter(nombre__iexact=nombre)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Ya existe una categoría con este nombre.")
        
        return nombre

    def save(self, commit=True):
        instance = super().save(commit=False)
        tipo_producto = self.cleaned_data.get("tipo_producto") or None
        instance.tipo_producto = tipo_producto
        if commit:
            instance.save()
        return instance


class FiscalVoucherConfigForm(forms.ModelForm):
    class Meta:
        model = FiscalVoucherConfig
        fields = [
            "nombre_contribuyente",
            "rnc",
            "correo_contacto",
            "telefono_contacto",
            "tipo_por_defecto",
            "serie_por_defecto",
            "secuencia_siguiente",
            "dias_vencimiento",
            "emitir_automatico",
            "modo_pruebas",
            "api_environment",
            "api_base_url",
            "api_auth_url",
            "api_submission_url",
            "api_status_url",
            "api_directory_url",
            "api_void_url",
            "api_commercial_approval_url",
            "api_client_id",
            "api_client_secret",
            "certificado_alias",
            "certificado_path",
            "certificado_password",
            "observaciones",
        ]
        widgets = {
            "nombre_contribuyente": forms.TextInput(attrs={
                "placeholder": "Nombre registrado ante la DGII",
                "maxlength": 160,
            }),
            "rnc": forms.TextInput(attrs={
                "placeholder": "RNC",
                "maxlength": 20,
                "autocomplete": "off",
            }),
            "correo_contacto": forms.EmailInput(attrs={
                "placeholder": "correo@empresa.com",
            }),
            "telefono_contacto": forms.TextInput(attrs={
                "placeholder": "+1 809-000-0000",
                "maxlength": 30,
            }),
            "tipo_por_defecto": forms.Select(attrs={
                "class": "select-control",
            }),
            "serie_por_defecto": forms.TextInput(attrs={
                "placeholder": "Ej. B01",
                "maxlength": 10,
                "autocomplete": "off",
            }),
            "secuencia_siguiente": forms.NumberInput(attrs={
                "min": 1,
                "step": 1,
            }),
            "dias_vencimiento": forms.NumberInput(attrs={
                "min": 0,
                "step": 1,
            }),
            "api_base_url": forms.URLInput(attrs={
                "placeholder": "https://",
            }),
            "api_auth_url": forms.URLInput(attrs={
                "placeholder": "https://",
            }),
            "api_submission_url": forms.URLInput(attrs={
                "placeholder": "https://",
            }),
            "api_status_url": forms.URLInput(attrs={
                "placeholder": "https://",
            }),
            "api_directory_url": forms.URLInput(attrs={
                "placeholder": "https://",
            }),
            "api_void_url": forms.URLInput(attrs={
                "placeholder": "https://",
            }),
            "api_commercial_approval_url": forms.URLInput(attrs={
                "placeholder": "https://",
            }),
            "api_client_secret": forms.PasswordInput(render_value=True, attrs={
                "autocomplete": "off",
            }),
            "certificado_password": forms.PasswordInput(render_value=True, attrs={
                "autocomplete": "off",
            }),
            "observaciones": forms.Textarea(attrs={
                "rows": 3,
            }),
        }

    def clean_nombre_contribuyente(self):
        return self.cleaned_data.get("nombre_contribuyente", "").strip()

    def clean_rnc(self):
        return self.cleaned_data.get("rnc", "").strip().upper()

    def clean_serie_por_defecto(self):
        serie = self.cleaned_data.get("serie_por_defecto", "").strip().upper()
        return serie


class TradeInCreditForm(forms.ModelForm):
    class Meta:
        model = TradeInCredit
        fields = [
            "nombre_cliente",
            "producto_nombre",
            "descripcion",
            "monto_credito",
            "cliente",
            "condiciones",
        ]
        widgets = {
            "nombre_cliente": forms.TextInput(attrs={
                "placeholder": "Nombre del cliente",
                "required": True,
            }),
            "producto_nombre": forms.TextInput(attrs={
                "placeholder": "Producto recibido",
                "required": True,
            }),
            "descripcion": forms.Textarea(attrs={
                "placeholder": "Estado, detalles o notas del producto",
                "rows": 3,
            }),
            "monto_credito": forms.NumberInput(attrs={
                "min": "0",
                "step": "0.01",
                "required": True,
            }),
            "cliente": forms.Select(attrs={
                "class": "select-control",
            }),
            "condiciones": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "cliente" in self.fields:
            self.fields["cliente"].required = False
            self.fields["cliente"].queryset = Cliente.objects.order_by("nombre")
            self.fields["cliente"].empty_label = "Sin cliente asignado"
        if "condiciones" in self.fields:
            self.fields["condiciones"].required = False
            self.fields["condiciones"].queryset = ProductCondition.objects.filter(activo=True).order_by("nombre")

    def clean_monto_credito(self):
        monto = self.cleaned_data.get("monto_credito") or Decimal("0")
        if monto <= Decimal("0"):
            raise forms.ValidationError("El monto debe ser mayor a cero.")
        return monto.quantize(Decimal("0.01"))
