from __future__ import annotations

from decimal import Decimal, InvalidOperation
import secrets

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F, Sum, Max
from django.utils import timezone
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    """Modelo base con marcas de tiempo."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-created_at",)


class Cliente(TimeStampedModel):
    """Clientes del punto de venta."""

    CODIGO_PREFIX = "CLI"
    CODIGO_PADDING = 5

    class TipoDocumento(models.TextChoices):
        CEDULA = "cedula", "Cédula"
        PASAPORTE = "pasaporte", "Pasaporte"
        RNC = "rnc", "RNC"
        OTRO = "otro", "Otro"

    codigo = models.CharField(max_length=12, unique=True, editable=False, blank=True, null=True)
    nombre = models.CharField(max_length=150)
    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices, blank=True)
    documento = models.CharField(max_length=50, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ("nombre",)

    def __str__(self) -> str:
        code = self.codigo or self.next_codigo()
        return f"{code} - {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._generate_codigo()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_codigo(cls) -> str:
        prefix = cls.CODIGO_PREFIX
        padding = cls.CODIGO_PADDING
        max_codigo = (
            cls.objects.filter(codigo__startswith=prefix)
            .aggregate(max_code=Max("codigo"))
            .get("max_code")
        )
        if max_codigo:
            try:
                sequence = int(max_codigo[len(prefix):]) + 1
            except ValueError:
                sequence = cls.objects.count() + 1
        else:
            sequence = 1
        return f"{prefix}{sequence:0{padding}d}"

    @classmethod
    def next_codigo(cls) -> str:
        return cls._generate_codigo()


class Proveedor(TimeStampedModel):
    """Proveedores del sistema POS."""

    CODIGO_PREFIX = "PRO"
    CODIGO_PADDING = 5

    class TipoDocumento(models.TextChoices):
        RNC = "rnc", "RNC"
        CEDULA = "cedula", "Cédula"
        PASAPORTE = "pasaporte", "Pasaporte"
        OTRO = "otro", "Otro"

    codigo = models.CharField(max_length=12, unique=True, editable=False, blank=True, null=True)
    nombre = models.CharField(max_length=180)
    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices, blank=True)
    documento = models.CharField(max_length=50, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    correo = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ("nombre",)

    def __str__(self) -> str:
        code = self.codigo or self.next_codigo()
        return f"{code} - {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._generate_codigo()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_codigo(cls) -> str:
        prefix = cls.CODIGO_PREFIX
        padding = cls.CODIGO_PADDING
        max_codigo = (
            cls.objects.filter(codigo__startswith=prefix)
            .aggregate(max_code=Max("codigo"))
            .get("max_code")
        )
        if max_codigo:
            try:
                sequence = int(max_codigo[len(prefix):]) + 1
            except ValueError:
                sequence = cls.objects.count() + 1
        else:
            sequence = 1
        return f"{prefix}{sequence:0{padding}d}"

    @classmethod
    def next_codigo(cls) -> str:
        return cls._generate_codigo()


class Categoria(TimeStampedModel):
    """Categorías de productos disponibles en el sistema POS."""

    CODIGO_PREFIX = "CAT"
    CODIGO_PADDING = 4

    codigo = models.CharField(
        max_length=15,
        unique=True,
        editable=False,
        blank=True,
    )
    nombre = models.CharField(max_length=120, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ("nombre",)

    def __str__(self) -> str:
        code = self.codigo or self.next_codigo()
        return f"{code} - {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._generate_codigo()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_codigo(cls) -> str:
        prefix = cls.CODIGO_PREFIX
        padding = cls.CODIGO_PADDING
        max_codigo = (
            cls.objects.filter(codigo__startswith=prefix)
            .aggregate(max_code=Max("codigo"))
            .get("max_code")
        )
        if max_codigo:
            try:
                sequence = int(max_codigo[len(prefix):]) + 1
            except ValueError:
                sequence = cls.objects.count() + 1
        else:
            sequence = 1
        return f"{prefix}{sequence:0{padding}d}"

    @classmethod
    def next_codigo(cls) -> str:
        return cls._generate_codigo()


class Marca(TimeStampedModel):
    """Marcas de productos disponibles en el sistema POS."""

    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ("nombre",)

    def __str__(self) -> str:
        return self.nombre


class Modelo(TimeStampedModel):
    """Modelos asociados a una marca específica."""

    nombre = models.CharField(max_length=150)
    marca = models.ForeignKey(
        Marca,
        on_delete=models.CASCADE,
        related_name="modelos",
        blank=True,
        null=True,
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Modelo"
        verbose_name_plural = "Modelos"
        ordering = ("nombre",)
        unique_together = ("marca", "nombre")

    def __str__(self) -> str:
        if self.marca:
            return f"{self.marca.nombre} {self.nombre}"
        return self.nombre


class Impuesto(TimeStampedModel):
    """Tabla de impuestos configurables para productos o transacciones."""

    CODIGO_PREFIX = "IMP"
    CODIGO_PADDING = 4

    codigo = models.CharField(
        max_length=15,
        unique=True,
        editable=False,
        blank=True,
    )
    nombre = models.CharField(max_length=120, unique=True)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Impuesto"
        verbose_name_plural = "Impuestos"
        ordering = ("nombre",)

    def __str__(self) -> str:
        code = self.codigo or self.next_codigo()
        status = "Activo" if self.activo else "Inactivo"
        return f"{code} - {self.nombre} ({self.porcentaje}%) [{status}]"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._generate_codigo()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_codigo(cls) -> str:
        prefix = cls.CODIGO_PREFIX
        padding = cls.CODIGO_PADDING
        max_codigo = (
            cls.objects.filter(codigo__startswith=prefix)
            .aggregate(max_code=Max("codigo"))
            .get("max_code")
        )
        if max_codigo:
            try:
                sequence = int(max_codigo[len(prefix):]) + 1
            except ValueError:
                sequence = cls.objects.count() + 1
        else:
            sequence = 1
        return f"{prefix}{sequence:0{padding}d}"

    @classmethod
    def next_codigo(cls) -> str:
        return cls._generate_codigo()


class Producto(TimeStampedModel):
    """Inventario principal de teléfonos y accesorios."""

    ALMACENAMIENTO_CHOICES = [
        ("8GB", "8 GB"),
        ("16GB", "16 GB"),
        ("32GB", "32 GB"),
        ("64GB", "64 GB"),
        ("128GB", "128 GB"),
        ("256GB", "256 GB"),
        ("512GB", "512 GB"),
        ("1TB", "1 TB"),
    ]

    RAM_CHOICES = [
        ("1GB", "1 GB"),
        ("2GB", "2 GB"),
        ("3GB", "3 GB"),
        ("4GB", "4 GB"),
        ("6GB", "6 GB"),
        ("8GB", "8 GB"),
        ("12GB", "12 GB"),
        ("16GB", "16 GB"),
    ]

    nombre = models.CharField(max_length=150)
    marca = models.ForeignKey(
        "Marca",
        on_delete=models.SET_NULL,
        related_name="productos",
        blank=True,
        null=True,
    )
    modelo = models.ForeignKey(
        "Modelo",
        on_delete=models.SET_NULL,
        related_name="productos",
        blank=True,
        null=True,
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        related_name="productos",
        blank=True,
        null=True,
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        related_name="productos",
        blank=True,
        null=True,
    )
    almacenamiento = models.CharField(
        max_length=10,
        choices=ALMACENAMIENTO_CHOICES,
        blank=True,
    )
    memoria_ram = models.CharField(
        max_length=10,
        choices=RAM_CHOICES,
        blank=True,
    )
    imei = models.CharField("IMEI", max_length=20, blank=True)
    descripcion = models.TextField(blank=True)
    colores_disponibles = models.CharField(max_length=150, blank=True)
    imagen = models.ImageField(upload_to="productos/", blank=True, null=True)
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    impuesto = models.ForeignKey(
        Impuesto,
        on_delete=models.SET_NULL,
        related_name="productos",
        blank=True,
        null=True,
    )
    usar_impuesto_global = models.BooleanField(
        default=True,
        help_text="Si está habilitado, este producto usará la tasa global configurada."
    )

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        unique_together = ("nombre", "modelo", "imei")
        ordering = ("nombre", "modelo")

    def __str__(self) -> str:
        base = f"{self.nombre}"
        if self.modelo:
            base = f"{base} {self.modelo}"
        return base

    @property
    def margen(self):
        return self.precio_venta - self.precio_compra

    @property
    def imagen_principal(self):
        urls = self.imagenes_urls
        return urls[0] if urls else ""

    @property
    def imagenes_urls(self):
        urls = []
        if self.imagen:
            try:
                urls.append(self.imagen.url)
            except ValueError:
                pass
        for imagen_rel in self.imagenes.all():
            try:
                url = imagen_rel.imagen.url
            except ValueError:
                continue
            if url not in urls:
                urls.append(url)
        return urls


class Compra(TimeStampedModel):
    numero_pedido = models.CharField(max_length=32, unique=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="compras")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="compras")
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    stock_anterior = models.PositiveIntegerField()
    stock_actual = models.PositiveIntegerField()
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="compras_registradas",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.numero_pedido} - {self.producto.nombre} ({self.cantidad})"


class ProductImage(TimeStampedModel):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="imagenes")
    imagen = models.ImageField(upload_to="productos/", blank=False)

    class Meta:
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de producto"

    def __str__(self) -> str:
        return f"Imagen de {self.producto}"


class TradeInCredit(TimeStampedModel):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        USADO = "usado", "Usado"
        CANCELADO = "cancelado", "Cancelado"

    CODIGO_PREFIX = "TRD"
    CODIGO_PADDING = 6

    codigo = models.CharField(max_length=20, unique=True, editable=False)
    nombre_cliente = models.CharField(max_length=150)
    producto_nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    monto_credito = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        related_name="trade_in_creditos",
        null=True,
        blank=True,
    )
    condiciones = models.ManyToManyField(
        "ProductCondition",
        blank=True,
        related_name="trade_in_creditos",
    )
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    venta_aplicada = models.ForeignKey(
        "Venta",
        on_delete=models.SET_NULL,
        related_name="trade_in_creditos",
        null=True,
        blank=True,
    )
    usado_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Crédito por intercambio"
        verbose_name_plural = "Créditos por intercambio"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.codigo} - {self.producto_nombre} ({self.monto_credito})"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._generate_codigo()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_codigo(cls) -> str:
        random_suffix = secrets.token_hex(3).upper()
        return f"{cls.CODIGO_PREFIX}-{random_suffix}"

    def marcar_como_usado(self, venta: "Venta" | None = None, cliente: Cliente | None = None):
        if self.estado == self.Estado.USADO:
            return
        self.estado = self.Estado.USADO
        if venta is not None:
            self.venta_aplicada = venta
        updated_fields = ["estado", "venta_aplicada", "usado_en", "updated_at"]
        if cliente is not None and self.cliente_id is None:
            self.cliente = cliente
            updated_fields.append("cliente")
        self.usado_en = timezone.now()
        self.save(update_fields=updated_fields)

    def cancelar(self):
        if self.estado == self.Estado.CANCELADO:
            return
        self.estado = self.Estado.CANCELADO
        self.save(update_fields=["estado", "updated_at"])

    @property
    def condiciones_ids_csv(self) -> str:
        return ",".join(str(pk) for pk in self.condiciones.values_list("id", flat=True))

    @property
    def condiciones_resumen(self) -> str:
        nombres = list(self.condiciones.values_list("nombre", flat=True))
        return ", ".join(nombres)


class ProductCondition(TimeStampedModel):
    codigo = models.CharField(max_length=30, unique=True, blank=True)
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Condición de producto"
        verbose_name_plural = "Condiciones de producto"
        ordering = ("nombre",)

    def __str__(self) -> str:
        estado = "Activo" if self.activo else "Inactivo"
        if self.codigo:
            return f"{self.codigo} - {self.nombre} ({estado})"
        return f"{self.nombre} ({estado})"

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.strip()
        if not self.codigo and self.nombre:
            base_code = slugify(self.nombre) or secrets.token_hex(2)
            base_code = base_code.replace('-', '').upper()
            base_code = base_code[:30]
            candidate = base_code
            counter = 1
            while ProductCondition.objects.filter(codigo=candidate).exclude(pk=self.pk).exists():
                counter += 1
                suffix = f"-{counter}"
                candidate = f"{base_code[: max(0, 30 - len(suffix))]}{suffix}".upper()
            self.codigo = candidate
        elif self.codigo:
            self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)


class CashSession(TimeStampedModel):
    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        CERRADA = "cerrada", "Cerrada"

    apertura_at = models.DateTimeField(default=timezone.now)
    cierre_at = models.DateTimeField(null=True, blank=True)
    monto_inicial = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    total_en_caja = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_ventas = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_trade_in = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_ventas_credito = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)

    class Meta:
        verbose_name = "Sesión de caja"
        verbose_name_plural = "Sesiones de caja"
        ordering = ("-apertura_at",)

    def __str__(self) -> str:
        cierre = self.cierre_at.strftime("%d/%m/%Y %H:%M") if self.cierre_at else "--"
        return f"Caja #{self.pk} - {self.apertura_at:%d/%m/%Y %H:%M} / {cierre}"

    def marcar_cerrada(
        self,
        total_en_caja: Decimal,
        total_ventas: Decimal,
        total_impuesto: Decimal,
        total_descuento: Decimal,
        total_ventas_credito: Decimal,
    ):
        if self.estado == self.Estado.CERRADA:
            return
        self.total_en_caja = Decimal(total_en_caja).quantize(Decimal("0.01"))
        self.total_ventas = Decimal(total_ventas).quantize(Decimal("0.01"))
        self.total_impuesto = Decimal(total_impuesto).quantize(Decimal("0.01"))
        self.total_descuento = Decimal(total_descuento).quantize(Decimal("0.01"))
        self.total_ventas_credito = Decimal(total_ventas_credito).quantize(Decimal("0.01"))
        self.cierre_at = timezone.now()
        self.estado = self.Estado.CERRADA
        self.save(update_fields=[
            "total_en_caja",
            "total_ventas",
            "total_impuesto",
            "total_descuento",
            "total_ventas_credito",
            "cierre_at",
            "estado",
            "updated_at",
        ])


class Venta(TimeStampedModel):
    """Encabezado de ventas."""

    class MetodoPago(models.TextChoices):
        EFECTIVO = "efectivo", "Efectivo"
        TARJETA = "tarjeta", "Tarjeta"
        TRANSFERENCIA = "transferencia", "Transferencia"
        MIXTO = "mixto", "Mixto"
        CREDITO = "credito", "Crédito"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ventas")
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ventas_registradas",
        null=True,
        blank=True,
    )
    fecha = models.DateTimeField(auto_now_add=True)
    metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices, default=MetodoPago.EFECTIVO)
    notas = models.TextField(blank=True)
    sesion_caja = models.ForeignKey(
        "CashSession",
        on_delete=models.SET_NULL,
        related_name="ventas",
        null=True,
        blank=True,
    )
    descuento_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    trade_in_monto = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ("-fecha",)

    def __str__(self) -> str:
        return f"Venta #{self.pk} - {self.cliente.nombre}"

    @property
    def total(self):
        return sum(detalle.subtotal for detalle in self.detalles.all())


class FiscalVoucherConfig(TimeStampedModel):
    """Configuración del contribuyente y parámetros para emitir comprobantes."""

    class VoucherType(models.TextChoices):
        B01 = "B01", "B01 - Crédito Fiscal"
        CF2 = "CF2", "CF2 - Consumidor final"
        CF3 = "CF3", "CF3 - Regímenes especiales"
        B14 = "B14", "B14 - Gastos menores"
        B15 = "B15", "B15 - Regímenes especiales"

    class Environment(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox / Pruebas"
        PRODUCTION = "production", "Producción"

    nombre_contribuyente = models.CharField(max_length=160, blank=True)
    rnc = models.CharField("RNC", max_length=20, blank=True)
    correo_contacto = models.EmailField(blank=True)
    telefono_contacto = models.CharField(max_length=30, blank=True)
    tipo_por_defecto = models.CharField(max_length=4, choices=VoucherType.choices, blank=True)
    serie_por_defecto = models.CharField(max_length=10, blank=True)
    secuencia_siguiente = models.PositiveIntegerField(default=1)
    dias_vencimiento = models.PositiveIntegerField(default=30)
    emitir_automatico = models.BooleanField(default=False)
    modo_pruebas = models.BooleanField(default=True)
    api_environment = models.CharField(
        max_length=20,
        choices=Environment.choices,
        default=Environment.SANDBOX,
    )
    api_base_url = models.URLField("URL base API", blank=True)
    api_auth_url = models.URLField("URL autenticación", blank=True)
    api_submission_url = models.URLField("URL recepción e-CF", blank=True)
    api_status_url = models.URLField("URL consulta estado", blank=True)
    api_directory_url = models.URLField("URL directorio clientes", blank=True)
    api_void_url = models.URLField("URL anulación e-CF", blank=True)
    api_commercial_approval_url = models.URLField("URL aprobación comercial", blank=True)
    api_client_id = models.CharField(max_length=120, blank=True)
    api_client_secret = models.CharField(max_length=255, blank=True)
    certificado_alias = models.CharField(max_length=160, blank=True)
    certificado_path = models.CharField(max_length=255, blank=True)
    certificado_password = models.CharField(max_length=255, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Configuración de comprobante fiscal"
        verbose_name_plural = "Configuración de comprobante fiscal"

    def __str__(self) -> str:
        nombre = self.nombre_contribuyente or "Sin definir"
        serie = self.serie_por_defecto or "—"
        return f"{nombre} / Serie {serie}"


class FiscalVoucherXML(TimeStampedModel):
    class ConexionEstado(models.TextChoices):
        SIN_CONEXION = "sin_conexion", "Sin conexión"
        BUSCANDO = "buscando", "Buscando conexión"
        CONECTADO = "conectado", "Conectado"

    configuracion = models.ForeignKey(
        FiscalVoucherConfig,
        on_delete=models.CASCADE,
        related_name="xml_templates",
        null=True,
        blank=True,
    )
    nombre = models.CharField(max_length=160)
    archivo = models.FileField(upload_to="dgii/xml/")
    estado_conexion = models.CharField(
        max_length=20,
        choices=ConexionEstado.choices,
        default=ConexionEstado.SIN_CONEXION,
    )
    ultimo_intento = models.DateTimeField(null=True, blank=True)
    mensaje = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "XML DGII"
        verbose_name_plural = "XML DGII"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.nombre


class FiscalVoucher(TimeStampedModel):
    """Comprobante fiscal asociado a una venta."""

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        EMITIDO = "emitido", "Emitido"
        ANULADO = "anulado", "Anulado"

    config = models.ForeignKey(
        FiscalVoucherConfig,
        on_delete=models.PROTECT,
        related_name="comprobantes",
        null=True,
        blank=True,
    )
    venta = models.OneToOneField(
        "Venta",
        on_delete=models.CASCADE,
        related_name="comprobante_fiscal",
    )
    tipo = models.CharField(max_length=4, choices=FiscalVoucherConfig.VoucherType.choices)
    serie = models.CharField(max_length=10)
    secuencia = models.PositiveIntegerField()
    numero_completo = models.CharField(max_length=32, unique=True, blank=True)
    fecha_emision = models.DateField(default=timezone.localdate)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    itbis = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=Decimal("0"),
    )
    otros_impuestos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=Decimal("0"),
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    monto_pagado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=Decimal("0"),
    )
    metodo_pago = models.CharField(max_length=20, choices=Venta.MetodoPago.choices, blank=True)
    cliente_nombre = models.CharField(max_length=160, blank=True)
    cliente_documento = models.CharField(max_length=30, blank=True)
    correo_envio = models.EmailField(blank=True)
    telefono_contacto = models.CharField(max_length=30, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.EMITIDO)
    notas = models.TextField(blank=True)
    dgii_track_id = models.CharField(max_length=64, blank=True)
    dgii_estado = models.CharField(max_length=30, blank=True)
    dgii_respuesta = models.JSONField(null=True, blank=True)
    dgii_enviado_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Comprobante fiscal"
        verbose_name_plural = "Comprobantes fiscales"
        ordering = ("-fecha_emision", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["serie", "secuencia"], name="unique_fiscal_voucher_sequence"
            )
        ]

    def __str__(self) -> str:
        return self.numero_completo or f"{self.serie}-{self.secuencia:08d}"

    def save(self, *args, **kwargs):
        if not self.numero_completo and self.serie and self.secuencia is not None:
            self.numero_completo = f"{self.serie}-{str(self.secuencia).zfill(8)}"
        super().save(*args, **kwargs)


class FiscalVoucherLine(TimeStampedModel):
    """Detalle de conceptos incluidos en un comprobante fiscal."""

    voucher = models.ForeignKey(
        FiscalVoucher,
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="lineas_fiscales",
        null=True,
        blank=True,
    )
    descripcion = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    impuesto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=Decimal("0"),
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = "Línea de comprobante fiscal"
        verbose_name_plural = "Líneas de comprobante fiscal"
        ordering = ("voucher", "id")

    def __str__(self) -> str:
        return f"{self.descripcion} ({self.cantidad})"


class CuentaCredito(TimeStampedModel):
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name="cuenta_credito")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="creditos")
    total_credito = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    saldo_pendiente = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=20, default="pendiente")
    # Campos para sistema de cuotas
    numero_cuotas = models.PositiveIntegerField(default=1)
    cuotas_pagadas = models.PositiveIntegerField(default=0)
    monto_cuota = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    abono_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    frecuencia_dias = models.PositiveIntegerField(default=30)  # Días entre cuotas

    class Meta:
        verbose_name = "Cuenta de crédito"
        verbose_name_plural = "Cuentas de crédito"

    def __str__(self) -> str:
        return f"Crédito #{self.venta_id} - {self.cliente.nombre}"

    def registrar_pago(self, monto):
        try:
            monto_decimal = Decimal(monto)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Monto inválido") from None

        monto_decimal = monto_decimal.quantize(Decimal("0.01"))

        if monto_decimal <= 0:
            raise ValueError("El monto de abono debe ser mayor a cero")
        if monto_decimal > self.saldo_pendiente:
            raise ValueError("El monto excede el saldo pendiente")

        nuevo_saldo = (self.saldo_pendiente - monto_decimal).quantize(Decimal("0.01"))
        self.saldo_pendiente = max(nuevo_saldo, Decimal("0.00"))
        
        # Actualizar cuotas pagadas si aplica
        if self.monto_cuota > 0:
            cuotas_completadas = int((self.total_credito - self.abono_inicial - self.saldo_pendiente) / self.monto_cuota)
            self.cuotas_pagadas = min(cuotas_completadas, self.numero_cuotas)
        
        if self.saldo_pendiente == 0:
            self.estado = "pagado"
            self.cuotas_pagadas = self.numero_cuotas
        else:
            if self.estado == "pagado":
                self.estado = "pendiente"
        self.save(update_fields=["saldo_pendiente", "estado", "cuotas_pagadas", "updated_at"])

    @property
    def progreso_cuotas(self):
        """Retorna el progreso de cuotas como string (ej: '3/10')"""
        if self.numero_cuotas <= 1:
            return ""
        return f"{self.cuotas_pagadas}/{self.numero_cuotas}"

    def calcular_cuotas(self, numero_cuotas, abono_inicial=None):
        """Calcula el monto de cada cuota basado en el total y abono inicial"""
        if abono_inicial is None:
            abono_inicial = Decimal("0")
        
        abono_inicial = Decimal(str(abono_inicial)).quantize(Decimal("0.01"))
        saldo_a_financiar = (self.total_credito - abono_inicial).quantize(Decimal("0.01"))
        
        if numero_cuotas <= 0 or saldo_a_financiar <= 0:
            return Decimal("0")
        
        return (saldo_a_financiar / numero_cuotas).quantize(Decimal("0.01"))


class PagoCredito(TimeStampedModel):
    cuenta = models.ForeignKey(CuentaCredito, on_delete=models.CASCADE, related_name="pagos")
    monto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="pagos_credito_registrados",
        null=True,
        blank=True,
    )
    comentario = models.TextField(blank=True)

    class Meta:
        verbose_name = "Pago de crédito"
        verbose_name_plural = "Pagos de crédito"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Abono {self.monto:.2f} a crédito #{self.cuenta.venta_id}"


class DetalleVenta(TimeStampedModel):
    """Detalle de productos vendidos."""

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="detalles_venta")
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"
        ordering = ("venta", "producto")

    def __str__(self) -> str:
        return f"{self.producto} x {self.cantidad}"

    @property
    def subtotal(self):
        return (self.precio_unitario * self.cantidad) - self.descuento
