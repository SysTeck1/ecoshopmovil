from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from ventas.models import Cliente, Producto


class TimeStampedModel(models.Model):
    """Modelo base con marcas de tiempo."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-created_at",)


class ServicioReparacion(TimeStampedModel):
    """Catálogo de servicios de reparación."""

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    costo_base = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Servicio de reparación"
        verbose_name_plural = "Servicios de reparación"
        ordering = ("nombre",)

    def __str__(self) -> str:
        return self.nombre


class Reparacion(TimeStampedModel):
    """Orden de reparación de equipos."""

    class Estado(models.TextChoices):
        RECIBIDA = "recibida", "Recibida"
        DIAGNOSTICADA = "diagnosticada", "Diagnosticada"
        EN_REPARACION = "en_reparacion", "En reparación"
        LISTA = "lista", "Lista para entrega"
        ENTREGADA = "entregada", "Entregada"
        CANCELADA = "cancelada", "Cancelada"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="reparaciones")
    dispositivo = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        related_name="reparaciones",
        null=True,
        blank=True,
        help_text="Seleccione un producto si forma parte del inventario.",
    )
    marca = models.CharField(max_length=80)
    modelo = models.CharField(max_length=120)
    imei = models.CharField("IMEI", max_length=20, blank=True)
    problema_reportado = models.TextField()
    diagnostico_preliminar = models.TextField(blank=True)
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    anticipo = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.RECIBIDA)
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reparaciones_asignadas",
        null=True,
        blank=True,
    )
    fecha_prometida = models.DateField(null=True, blank=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "Reparación"
        verbose_name_plural = "Reparaciones"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Reparación #{self.pk} - {self.cliente.nombre}"

    @property
    def saldo_pendiente(self):
        return max(self.costo_estimado - self.anticipo - self.pagos.aggregate(total=models.Sum("monto"))["total" or 0], 0)


class ReparacionServicio(TimeStampedModel):
    """Servicios aplicados en una reparación."""

    reparacion = models.ForeignKey(Reparacion, on_delete=models.CASCADE, related_name="servicios")
    servicio = models.ForeignKey(ServicioReparacion, on_delete=models.PROTECT, related_name="aplicaciones")
    costo = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "Servicio aplicado"
        verbose_name_plural = "Servicios aplicados"
        ordering = ("reparacion", "servicio")

    def __str__(self) -> str:
        return f"{self.servicio.nombre} ({self.reparacion})"


class ReparacionPago(TimeStampedModel):
    """Pagos registrados para una reparación."""

    reparacion = models.ForeignKey(Reparacion, on_delete=models.CASCADE, related_name="pagos")
    monto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    metodo_pago = models.CharField(max_length=50)
    referencia = models.CharField(max_length=100, blank=True)
    comentarios = models.TextField(blank=True)

    class Meta:
        verbose_name = "Pago de reparación"
        verbose_name_plural = "Pagos de reparación"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Pago {self.monto} - {self.reparacion}"


class BitacoraReparacion(TimeStampedModel):
    """Seguimiento de eventos relevantes en la reparación."""

    reparacion = models.ForeignKey(Reparacion, on_delete=models.CASCADE, related_name="bitacora")
    estado = models.CharField(max_length=20, choices=Reparacion.Estado.choices)
    comentario = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="bitacoras_reparacion",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Evento de reparación"
        verbose_name_plural = "Eventos de reparación"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.get_estado_display()} - {self.reparacion}"
