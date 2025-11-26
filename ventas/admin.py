from django.contrib import admin

from .models import (
    Categoria,
    Cliente,
    DetalleVenta,
    Marca,
    Modelo,
    Producto,
    ProductCondition,
    Venta,
    CashSession,
    FiscalVoucherConfig,
    FiscalVoucher,
    FiscalVoucherLine,
    TipoProducto,
)

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo_producto", "activo", "created_at")
    list_filter = ("activo", "tipo_producto")
    search_fields = ("codigo", "nombre")
    list_editable = ("activo",)
    readonly_fields = ("codigo", "created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("nombre", "tipo_producto", "activo")
        }),
        ("Información del Sistema", {
            "fields": ("codigo", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "created_at")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):
    list_display = ("nombre", "marca", "activo", "created_at")
    list_filter = ("activo", "marca")
    search_fields = ("nombre", "marca__nombre")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "correo")
    search_fields = ("nombre", "telefono", "documento_identidad")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "almacenamiento", "memoria_ram", "precio_venta", "stock", "activo")
    list_filter = ("categoria", "almacenamiento", "memoria_ram", "activo")
    search_fields = ("nombre", "modelo", "imei")


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "fecha", "metodo_pago", "total")
    list_filter = ("metodo_pago", "fecha")
    search_fields = ("cliente__nombre", "id")
    date_hierarchy = "fecha"
    inlines = [DetalleVentaInline]


@admin.register(CashSession)
class CashSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "apertura_at",
        "cierre_at",
        "monto_inicial",
        "total_en_caja",
        "total_ventas",
        "total_impuesto",
        "total_descuento",
        "total_ventas_credito",
        "estado",
    )
    list_filter = ("estado", "apertura_at", "cierre_at")
    search_fields = ("id",)
    date_hierarchy = "apertura_at"


@admin.register(FiscalVoucherConfig)
class FiscalVoucherConfigAdmin(admin.ModelAdmin):
    list_display = (
        "nombre_contribuyente",
        "rnc",
        "serie_por_defecto",
        "secuencia_siguiente",
        "emitir_automatico",
        "modo_pruebas",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")


class FiscalVoucherLineInline(admin.TabularInline):
    model = FiscalVoucherLine
    extra = 0
    fields = (
        "producto",
        "descripcion",
        "cantidad",
        "precio_unitario",
        "subtotal",
        "impuesto",
        "total",
    )
    readonly_fields = ("subtotal", "impuesto", "total")


@admin.register(FiscalVoucher)
class FiscalVoucherAdmin(admin.ModelAdmin):
    list_display = (
        "numero_completo",
        "venta",
        "tipo",
        "serie",
        "secuencia",
        "total",
        "estado",
        "fecha_emision",
    )
    list_filter = ("estado", "tipo", "fecha_emision")
    search_fields = ("numero_completo", "venta__id", "serie")
    readonly_fields = (
        "numero_completo",
        "created_at",
        "updated_at",
    )
    inlines = [FiscalVoucherLineInline]


@admin.register(TipoProducto)
class TipoProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "icono", "activo", "created_at")
    list_filter = ("activo", "icono")
    search_fields = ("nombre", "slug")
    list_editable = ("activo",)
    readonly_fields = ("slug",)
    prepopulated_fields = {"slug": ("nombre",)}
    fieldsets = (
        (None, {
            "fields": ("nombre", "slug", "icono", "descripcion", "activo")
        }),
        ("Información del Sistema", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
