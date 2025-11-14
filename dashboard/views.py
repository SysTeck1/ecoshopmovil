import json
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from decimal import Decimal, InvalidOperation

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, IntegrityError
from django.db.models import F, Q, Sum, ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils import dateparse
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.generic import TemplateView
from django.urls import reverse, reverse_lazy

from django.templatetags.static import static

from ventas.forms import (
    CategoriaForm,
    ClienteForm,
    ImpuestoForm,
    ProductoForm,
    ProveedorForm,
    FiscalVoucherConfigForm,
    FiscalVoucherXMLForm,
)
from ventas.dgii import (
    DGIIVoucherService,
    DGIIVoucherServiceError,
    DGIIHttpClient,
    RequestsNotAvailable,
    build_fiscal_voucher_xml,
    build_requests_http_request,
)
from ventas.models import (
    Categoria,
    Cliente,
    Impuesto,
    Marca,
    Modelo,
    ProductImage,
    Producto,
    Proveedor,
    Venta,
    DetalleVenta,
    CuentaCredito,
    PagoCredito,
    CashSession,
    FiscalVoucherConfig,
    FiscalVoucher,
    FiscalVoucherLine,
    FiscalVoucherXML,
    Compra,
)

from .forms import SiteConfigurationLogoForm
from .models import SiteConfiguration


logger = logging.getLogger(__name__)


TAX_RATE = Decimal("0.18")
TWO_PLACES = Decimal("0.01")
PAYMENT_CYCLE_DAYS = 30
COUNTDOWN_WARNING_DAYS = 10
WHATSAPP_ALERT_DAYS = 5


def format_currency(value) -> str:
    try:
        decimal_value = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        decimal_value = Decimal("0")

    decimal_value = decimal_value.quantize(TWO_PLACES)
    return f"RD$ {decimal_value:,.2f}"


def compute_sale_totals(venta: Venta) -> dict[str, Decimal]:
    subtotal = Decimal("0")
    impuestos = Decimal("0")
    discount_total = Decimal("0")

    for detalle in venta.detalles.all():
        precio_unitario = detalle.precio_unitario or Decimal("0")
        cantidad = Decimal(detalle.cantidad or 0)
        descuento = detalle.descuento or Decimal("0")

        base_amount = (precio_unitario * cantidad).quantize(TWO_PLACES)
        line_discount = descuento.quantize(TWO_PLACES)
        line_subtotal = (base_amount - line_discount).quantize(TWO_PLACES)
        if line_subtotal < Decimal("0"):
            line_subtotal = Decimal("0.00")
        line_tax = (line_subtotal * TAX_RATE).quantize(TWO_PLACES)

        subtotal += line_subtotal
        impuestos += line_tax
        discount_total += line_discount

    subtotal = subtotal.quantize(TWO_PLACES)
    impuestos = impuestos.quantize(TWO_PLACES)
    discount_total = discount_total.quantize(TWO_PLACES)
    total = (subtotal + impuestos).quantize(TWO_PLACES)
    return {
        "subtotal": subtotal,
        "impuestos": impuestos,
        "descuento": discount_total,
        "total": total,
    }


def build_pagination(request, iterable, per_page: int = 10):
    paginator = Paginator(iterable, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    if "page" in query_params:
        query_params.pop("page")

    querystring = query_params.urlencode()
    return paginator, page_obj, querystring


def aggregate_cash_session(session: CashSession) -> dict[str, Decimal | int]:
    ventas_cache = None
    if hasattr(session, "_prefetched_objects_cache"):
        ventas_cache = session._prefetched_objects_cache.get("ventas")

    if ventas_cache is not None:
        ventas_iterable = ventas_cache
    else:
        ventas_iterable = list(session.ventas.prefetch_related("detalles__producto"))

    subtotal_sum = Decimal("0")
    impuestos_sum = Decimal("0")
    descuento_sum = Decimal("0")
    total_sum = Decimal("0")
    total_credito = Decimal("0")
    total_cost = Decimal("0")

    for venta in ventas_iterable:
        totales = compute_sale_totals(venta)
        subtotal_sum += totales["subtotal"]
        impuestos_sum += totales["impuestos"]
        descuento_sum += totales["descuento"]
        total_sum += totales["total"]
        if venta.metodo_pago == Venta.MetodoPago.CREDITO:
            total_credito += totales["total"]

        sale_cost = Decimal("0")
        for detalle in venta.detalles.all():
            cantidad_decimal = Decimal(detalle.cantidad or 0)
            try:
                costo_unitario = detalle.producto.precio_compra if detalle.producto else Decimal("0")
                costo_unitario = Decimal(str(costo_unitario))
            except (InvalidOperation, AttributeError, TypeError, ValueError):
                costo_unitario = Decimal("0")

            line_cost = (costo_unitario * cantidad_decimal).quantize(TWO_PLACES)
            sale_cost += line_cost

        total_cost += sale_cost.quantize(TWO_PLACES)

    # Calcular cobros de crédito del día de la sesión
    session_date = timezone.localtime(session.apertura_at).date()
    credit_payments_today = PagoCredito.objects.filter(
        created_at__date=session_date
    ).aggregate(total=Sum("monto"))
    total_credit_payments = (credit_payments_today.get("total") or Decimal("0")).quantize(TWO_PLACES)

    subtotal_sum = subtotal_sum.quantize(TWO_PLACES)
    impuestos_sum = impuestos_sum.quantize(TWO_PLACES)
    descuento_sum = descuento_sum.quantize(TWO_PLACES)
    total_sum = total_sum.quantize(TWO_PLACES)
    total_credito = total_credito.quantize(TWO_PLACES)
    total_cost = total_cost.quantize(TWO_PLACES)
    total_contado = (total_sum - total_credito).quantize(TWO_PLACES)
    total_profit = (total_sum - total_cost).quantize(TWO_PLACES)
    total_en_caja = (session.monto_inicial + total_contado + total_credit_payments).quantize(TWO_PLACES)

    ventas_count = len(ventas_iterable)

    return {
        "subtotal": subtotal_sum,
        "impuestos": impuestos_sum,
        "descuento": descuento_sum,
        "total": total_sum,
        "total_credito": total_credito,
        "total_contado": total_contado,
        "total_en_caja": total_en_caja,
        "total_cost": total_cost,
        "total_profit": total_profit,
        "total_credit_payments": total_credit_payments,
        "ventas_count": ventas_count,
    }


def serialize_cash_session(session: CashSession, include_totals: bool = False) -> dict[str, object]:
    apertura_local = timezone.localtime(session.apertura_at)
    cierre_local = timezone.localtime(session.cierre_at) if session.cierre_at else None

    data: dict[str, object] = {
        "id": session.pk,
        "estado": session.estado,
        "estado_display": session.get_estado_display(),
        "monto_inicial": float(session.monto_inicial),
        "monto_inicial_display": format_currency(session.monto_inicial),
        "total_en_caja_registrado": float(session.total_en_caja),
        "total_en_caja_registrado_display": format_currency(session.total_en_caja),
        "total_descuento_registrado": float(session.total_descuento),
        "total_descuento_registrado_display": format_currency(session.total_descuento),
        "apertura": apertura_local.isoformat(),
        "apertura_display": apertura_local.strftime("%d/%m/%Y %H:%M"),
    }

    if cierre_local:
        data.update(
            {
                "cierre": cierre_local.isoformat(),
                "cierre_display": cierre_local.strftime("%d/%m/%Y %H:%M"),
            }
        )
    else:
        data.update({"cierre": None, "cierre_display": "--"})

    if include_totals:
        totals = aggregate_cash_session(session)
        data.update(
            {
                "ventas_count": totals["ventas_count"],
                "totals": {
                    "subtotal": float(totals["subtotal"]),
                    "subtotal_display": format_currency(totals["subtotal"]),
                    "impuestos": float(totals["impuestos"]),
                    "impuestos_display": format_currency(totals["impuestos"]),
                    "descuento": float(totals["descuento"]),
                    "descuento_display": format_currency(totals["descuento"]),
                    "total": float(totals["total"]),
                    "total_display": format_currency(totals["total"]),
                    "total_credito": float(totals["total_credito"]),
                    "total_credito_display": format_currency(totals["total_credito"]),
                    "total_contado": float(totals["total_contado"]),
                    "total_contado_display": format_currency(totals["total_contado"]),
                    "total_en_caja": float(totals["total_en_caja"]),
                    "total_en_caja_display": format_currency(totals["total_en_caja"]),
                    "total_costo": float(totals["total_cost"]),
                    "total_costo_display": format_currency(totals["total_cost"]),
                    "total_ganancia": float(totals["total_profit"]),
                    "total_ganancia_display": format_currency(totals["total_profit"]),
                    "total_credit_payments": float(totals["total_credit_payments"]),
                    "total_credit_payments_display": format_currency(totals["total_credit_payments"]),
                },
            }
        )

    return data


def get_open_cash_session() -> CashSession | None:
    return (
        CashSession.objects.filter(estado=CashSession.Estado.ABIERTA)
        .order_by("-apertura_at")
        .first()
    )


@require_GET
def cash_session_status_api(request):
    include_totals = request.GET.get("include_totals") in {"1", "true", "True"}
    open_session = get_open_cash_session()
    last_closed = (
        CashSession.objects.filter(estado=CashSession.Estado.CERRADA)
        .order_by("-cierre_at")
        .first()
    )

    return JsonResponse(
        {
            "open_session": serialize_cash_session(open_session, include_totals=include_totals)
            if open_session
            else None,
            "last_closed": serialize_cash_session(last_closed, include_totals=True) if last_closed else None,
        }
    )


def build_inventory_cost_report():
    productos = (
        Producto.objects.select_related("proveedor", "categoria", "modelo")
        .filter(stock__gt=0)
        .order_by("nombre", "modelo__nombre")
    )

    total_cost = Decimal("0")
    total_stock = 0
    report_rows: list[dict[str, object]] = []

    for producto in productos:
        precio_compra = (producto.precio_compra or Decimal("0")).quantize(TWO_PLACES)
        stock = int(producto.stock or 0)
        costo_total = (precio_compra * Decimal(stock)).quantize(TWO_PLACES)

        total_cost += costo_total
        total_stock += stock

        report_rows.append(
            {
                "id": producto.pk,
                "producto": str(producto),
                "categoria": producto.categoria.nombre if producto.categoria else "—",
                "proveedor": producto.proveedor.nombre if producto.proveedor else "—",
                "precio_compra": float(precio_compra),
                "precio_compra_display": format_currency(precio_compra),
                "stock": stock,
                "costo_total": float(costo_total),
                "costo_total_display": format_currency(costo_total),
            }
        )

    total_cost = total_cost.quantize(TWO_PLACES)
    products_count = len(report_rows)

    return total_cost, total_stock, products_count, report_rows


def build_category_analysis_report(search_term: str | None = None):
    productos = (
        Producto.objects.select_related("categoria", "marca")
        .filter(stock__gt=0, activo=True)
        .order_by("categoria__nombre", "marca__nombre", "nombre")
    )

    if search_term:
        search_filters = (
            Q(categoria__nombre__icontains=search_term)
            | Q(marca__nombre__icontains=search_term)
            | Q(nombre__icontains=search_term)
        )
        productos = productos.filter(search_filters)

    groups: dict[tuple[int | None, int | None], dict[str, object]] = {}
    total_products = 0
    total_stock = 0
    total_value = Decimal("0")
    unique_categories: set[str] = set()

    for producto in productos:
        categoria = producto.categoria
        marca = producto.marca

        group_key = (categoria.pk if categoria else None, marca.pk if marca else None)

        if group_key not in groups:
            groups[group_key] = {
                "categoria": categoria.nombre if categoria else "Sin categoría",
                "marca": marca.nombre if marca else "Sin marca",
                "productos": 0,
                "stock": 0,
                "valor": Decimal("0"),
            }

        unique_categories.add(groups[group_key]["categoria"])

        try:
            stock = int(producto.stock or 0)
        except (TypeError, ValueError):
            stock = 0

        try:
            precio_compra = Decimal(producto.precio_compra or 0)
        except (InvalidOperation, TypeError, ValueError):
            precio_compra = Decimal("0")

        group = groups[group_key]
        group["productos"] += 1
        group["stock"] += stock
        group_value = (precio_compra * Decimal(stock)).quantize(TWO_PLACES)
        group["valor"] += group_value

        total_products += 1
        total_stock += stock
        total_value += group_value

    rows = []
    for data in sorted(groups.values(), key=lambda item: (item["categoria"], item["marca"])):
        valor = data["valor"].quantize(TWO_PLACES)
        rows.append(
            {
                "categoria": data["categoria"],
                "marca": data["marca"],
                "productos": data["productos"],
                "productos_display": data["productos"],
                "stock": data["stock"],
                "stock_display": data["stock"],
                "valor": float(valor),
                "valor_display": format_currency(valor),
            }
        )

    total_value = total_value.quantize(TWO_PLACES)
    group_count = len(rows)
    category_count = len(unique_categories)

    totals = {
        "productos": total_products,
        "productos_display": total_products,
        "stock": total_stock,
        "stock_display": total_stock,
        "valor": float(total_value),
        "valor_display": format_currency(total_value),
        "grupos": group_count,
        "grupos_display": group_count,
        "categorias": category_count,
        "categorias_display": category_count,
    }

    return rows, totals


@require_GET
def report_inventory_cost_api(request):
    total_cost, total_stock, products_count, report_rows = build_inventory_cost_report()

    return JsonResponse(
        {
            "total_cost": float(total_cost),
            "total_cost_display": format_currency(total_cost),
            "total_stock": total_stock,
            "products_count": products_count,
            "rows": report_rows,
        }
    )


def build_sales_cost_report(queryset):
    total_cost = Decimal("0")
    total_units = 0
    report_rows: list[dict[str, object]] = []

    for venta in queryset:
        sale_cost = Decimal("0")
        sale_units = 0

        for detalle in venta.detalles.all():
            try:
                cantidad_decimal = Decimal(detalle.cantidad or 0)
            except (InvalidOperation, TypeError, ValueError):
                cantidad_decimal = Decimal("0")
            try:
                cantidad_unidades = int(detalle.cantidad or 0)
            except (TypeError, ValueError):
                cantidad_unidades = 0

            producto = detalle.producto
            costo_unitario = Decimal("0")
            if producto and producto.precio_compra is not None:
                try:
                    costo_unitario = Decimal(producto.precio_compra)
                except (InvalidOperation, TypeError, ValueError):
                    costo_unitario = Decimal("0")

            line_cost = (costo_unitario * cantidad_decimal).quantize(TWO_PLACES)
            sale_cost += line_cost
            sale_units += cantidad_unidades

        sale_cost = sale_cost.quantize(TWO_PLACES)
        total_cost += sale_cost
        total_units += sale_units

        fecha_local = timezone.localtime(venta.fecha)

        report_rows.append(
            {
                "id": venta.pk,
                "factura": f"FAC-{venta.pk:06d}",
                "cliente": venta.cliente.nombre,
                "fecha": fecha_local.isoformat(),
                "fecha_display": fecha_local.strftime("%d/%m/%Y %H:%M"),
                "costo_total": float(sale_cost),
                "costo_total_display": format_currency(sale_cost),
                "unidades": sale_units,
                "unidades_display": str(sale_units),
            }
        )

    total_cost = total_cost.quantize(TWO_PLACES)

    return total_cost, total_units, len(report_rows), report_rows


@require_GET
def report_sales_cost_api(request):
    queryset, start_date, end_date = get_filtered_sales_queryset(request)
    total_cost, total_units, ventas_count, report_rows = build_sales_cost_report(queryset)

    return JsonResponse(
        {
            "total_cost": float(total_cost),
            "total_cost_display": format_currency(total_cost),
            "total_units": total_units,
            "total_units_display": total_units,
            "filters": {
                "fecha_inicio": start_date.isoformat() if start_date else "",
                "fecha_fin": end_date.isoformat() if end_date else "",
            },
            "ventas": ventas_count,
            "ventas_display": ventas_count,
            "rows": report_rows,
        }
    )


def build_sales_period_report(queryset, period: str):
    supported_periods = {"day", "month", "year"}
    if period not in supported_periods:
        period = "day"

    groups: dict[tuple, dict[str, object]] = {}
    total_amount = Decimal("0")
    total_sales = 0

    for venta in queryset:
        fecha_local = timezone.localtime(venta.fecha)

        if period == "year":
            group_key = (fecha_local.year,)
            group_label = f"{fecha_local.year}"
            sort_key = (fecha_local.year,)
            filter_value = f"{fecha_local.year}"
        elif period == "month":
            group_key = (fecha_local.year, fecha_local.month)
            group_label = fecha_local.strftime("%m/%Y")
            sort_key = (fecha_local.year, fecha_local.month)
            filter_value = f"{fecha_local.year}-{fecha_local.month:02d}"
        else:
            group_key = (fecha_local.year, fecha_local.month, fecha_local.day)
            group_label = fecha_local.strftime("%d/%m/%Y")
            sort_key = (fecha_local.year, fecha_local.month, fecha_local.day)
            filter_value = fecha_local.date().isoformat()

        totals = compute_sale_totals(venta)
        sale_total = totals.get("total", Decimal("0")).quantize(TWO_PLACES)

        if group_key not in groups:
            groups[group_key] = {
                "period_label": group_label,
                "period_value": filter_value,
                "sort_key": sort_key,
                "ventas": 0,
                "total": Decimal("0"),
            }

        groups[group_key]["ventas"] += 1
        groups[group_key]["total"] += sale_total

        total_amount += sale_total
        total_sales += 1

    rows = []
    for data in sorted(groups.values(), key=lambda item: item["sort_key"], reverse=True):
        total_value = data["total"].quantize(TWO_PLACES)
        rows.append(
            {
                "period": data["period_value"],
                "period_display": data["period_label"],
                "ventas": data["ventas"],
                "ventas_display": data["ventas"],
                "total": float(total_value),
                "total_display": format_currency(total_value),
            }
        )

    total_amount = total_amount.quantize(TWO_PLACES)

    return period, total_amount, total_sales, rows


def build_profit_period_report(queryset, period: str):
    supported_periods = {"day", "month", "year"}
    if period not in supported_periods:
        period = "day"

    groups: dict[tuple, dict[str, object]] = {}
    total_sales_amount = Decimal("0")
    total_cost_amount = Decimal("0")
    total_profit_amount = Decimal("0")
    total_sales_count = 0

    for venta in queryset:
        fecha_local = timezone.localtime(venta.fecha)

        if period == "year":
            group_key = (fecha_local.year,)
            group_label = f"{fecha_local.year}"
            sort_key = (fecha_local.year,)
            filter_value = f"{fecha_local.year}"
        elif period == "month":
            group_key = (fecha_local.year, fecha_local.month)
            group_label = fecha_local.strftime("%m/%Y")
            sort_key = (fecha_local.year, fecha_local.month)
            filter_value = f"{fecha_local.year}-{fecha_local.month:02d}"
        else:
            group_key = (fecha_local.year, fecha_local.month, fecha_local.day)
            group_label = fecha_local.strftime("%d/%m/%Y")
            sort_key = (fecha_local.year, fecha_local.month, fecha_local.day)
            filter_value = fecha_local.date().isoformat()

        sale_totals = compute_sale_totals(venta)
        sale_total = sale_totals.get("total", Decimal("0")).quantize(TWO_PLACES)

        sale_cost = Decimal("0")
        for detalle in venta.detalles.all():
            try:
                cantidad_decimal = Decimal(detalle.cantidad or 0)
            except (InvalidOperation, TypeError, ValueError):
                cantidad_decimal = Decimal("0")

            producto = detalle.producto
            costo_unitario = Decimal("0")
            if producto and producto.precio_compra is not None:
                try:
                    costo_unitario = Decimal(producto.precio_compra)
                except (InvalidOperation, TypeError, ValueError):
                    costo_unitario = Decimal("0")

            line_cost = (costo_unitario * cantidad_decimal).quantize(TWO_PLACES)
            sale_cost += line_cost

        sale_cost = sale_cost.quantize(TWO_PLACES)
        sale_profit = (sale_total - sale_cost).quantize(TWO_PLACES)

        if group_key not in groups:
            groups[group_key] = {
                "period_label": group_label,
                "period_value": filter_value,
                "sort_key": sort_key,
                "ventas": 0,
                "total_sales": Decimal("0"),
                "total_cost": Decimal("0"),
                "total_profit": Decimal("0"),
            }

        groups[group_key]["ventas"] += 1
        groups[group_key]["total_sales"] += sale_total
        groups[group_key]["total_cost"] += sale_cost
        groups[group_key]["total_profit"] += sale_profit

        total_sales_amount += sale_total
        total_cost_amount += sale_cost
        total_profit_amount += sale_profit
        total_sales_count += 1

    rows = []
    for data in sorted(groups.values(), key=lambda item: item["sort_key"], reverse=True):
        sales_value = data["total_sales"].quantize(TWO_PLACES)
        cost_value = data["total_cost"].quantize(TWO_PLACES)
        profit_value = data["total_profit"].quantize(TWO_PLACES)

        rows.append(
            {
                "period": data["period_value"],
                "period_display": data["period_label"],
                "ventas": data["ventas"],
                "ventas_display": data["ventas"],
                "total_sales": float(sales_value),
                "total_sales_display": format_currency(sales_value),
                "total_cost": float(cost_value),
                "total_cost_display": format_currency(cost_value),
                "total_profit": float(profit_value),
                "total_profit_display": format_currency(profit_value),
            }
        )

    total_sales_amount = total_sales_amount.quantize(TWO_PLACES)
    total_cost_amount = total_cost_amount.quantize(TWO_PLACES)
    total_profit_amount = total_profit_amount.quantize(TWO_PLACES)

    return period, total_sales_amount, total_cost_amount, total_profit_amount, total_sales_count, rows


def build_product_sales_report(queryset, search_term: str | None):
    detalle_qs = (
        DetalleVenta.objects.filter(venta__in=queryset)
        .select_related("producto__marca", "producto__modelo")
    )

    if search_term:
        search_value = search_term.strip()
        if search_value:
            detalle_qs = detalle_qs.filter(
                Q(producto__nombre__icontains=search_value)
                | Q(producto__marca__nombre__icontains=search_value)
                | Q(producto__modelo__nombre__icontains=search_value)
            )

    grouped: dict[tuple[str, str, str], dict[str, object]] = {}
    total_quantity = 0
    total_amount = Decimal("0")

    for detalle in detalle_qs:
        producto = detalle.producto
        if producto is None:
            continue

        producto_nombre = producto.nombre or "Sin nombre"
        marca_nombre = producto.marca.nombre if producto.marca else "Sin marca"
        modelo_nombre = producto.modelo.nombre if producto.modelo else "Sin modelo"
        key = (producto_nombre, marca_nombre, modelo_nombre)

        entry = grouped.setdefault(
            key,
            {
                "cantidad": 0,
                "subtotal": Decimal("0"),
                "total": Decimal("0"),
            },
        )

        cantidad = int(detalle.cantidad or 0)
        precio_unitario = detalle.precio_unitario or Decimal("0")
        descuento = detalle.descuento or Decimal("0")

        line_subtotal = (precio_unitario * cantidad) - descuento
        if line_subtotal < Decimal("0"):
            line_subtotal = Decimal("0")
        line_subtotal = line_subtotal.quantize(TWO_PLACES)
        line_tax = (line_subtotal * TAX_RATE).quantize(TWO_PLACES)
        line_total = (line_subtotal + line_tax).quantize(TWO_PLACES)

        entry["cantidad"] += cantidad
        entry["subtotal"] += line_subtotal
        entry["total"] += line_total

        total_quantity += cantidad
        total_amount += line_total

    sorted_entries = sorted(
        grouped.items(),
        key=lambda item: (item[1]["subtotal"], item[1]["cantidad"]),
        reverse=True,
    )

    rows: list[dict[str, object]] = []
    for (producto_nombre, marca_nombre, modelo_nombre), data in sorted_entries:
        subtotal_amount: Decimal = data["subtotal"].quantize(TWO_PLACES)
        total_amount_row: Decimal = data["total"].quantize(TWO_PLACES)
        cantidad_total = data["cantidad"]
        rows.append(
            {
                "producto": producto_nombre,
                "marca": marca_nombre,
                "modelo": modelo_nombre,
                "cantidad": cantidad_total,
                "cantidad_display": format(cantidad_total, ","),
                "subtotal": float(subtotal_amount),
                "subtotal_display": format_currency(subtotal_amount),
                "total": float(total_amount_row),
                "total_display": format_currency(total_amount_row),
            }
        )

    product_count = len(rows)
    total_amount = total_amount.quantize(TWO_PLACES)

    totals = {
        "productos": product_count,
        "productos_display": product_count,
        "cantidad": total_quantity,
        "cantidad_display": format(total_quantity, ","),
        "venta": float(total_amount),
        "venta_display": format_currency(total_amount),
    }

    return rows, totals


@require_GET
def report_sales_period_api(request):
    queryset, start_date, end_date = get_filtered_sales_queryset(request)
    period = (request.GET.get("period") or "day").strip().lower()

    period, total_amount, total_sales, rows = build_sales_period_report(queryset, period)

    return JsonResponse(
        {
            "total_sales": float(total_amount),
            "total_sales_display": format_currency(total_amount),
            "ventas": total_sales,
            "ventas_display": total_sales,
            "filters": {
                "fecha_inicio": start_date.isoformat() if start_date else "",
                "fecha_fin": end_date.isoformat() if end_date else "",
                "period": period,
            },
            "rows": rows,
        }
    )


@require_GET
def report_profit_period_api(request):
    queryset, start_date, end_date = get_filtered_sales_queryset(request)
    period = (request.GET.get("period") or "day").strip().lower()

    (
        period,
        total_sales_amount,
        total_cost_amount,
        total_profit_amount,
        total_sales_count,
        rows,
    ) = build_profit_period_report(queryset, period)

    return JsonResponse(
        {
            "total_sales": float(total_sales_amount),
            "total_sales_display": format_currency(total_sales_amount),
            "total_cost": float(total_cost_amount),
            "total_cost_display": format_currency(total_cost_amount),
            "total_profit": float(total_profit_amount),
            "total_profit_display": format_currency(total_profit_amount),
            "ventas": total_sales_count,
            "ventas_display": total_sales_count,
            "filters": {
                "fecha_inicio": start_date.isoformat() if start_date else "",
                "fecha_fin": end_date.isoformat() if end_date else "",
                "period": period,
            },
            "rows": rows,
        }
    )


@require_GET
def report_product_sales_api(request):
    queryset, start_date, end_date = get_filtered_sales_queryset(request)
    search_term = (request.GET.get("q") or "").strip()

    rows, totals = build_product_sales_report(queryset, search_term or None)

    return JsonResponse(
        {
            "filters": {
                "fecha_inicio": start_date.isoformat() if start_date else "",
                "fecha_fin": end_date.isoformat() if end_date else "",
                "q": search_term,
            },
            "rows": rows,
            "totals": totals,
        }
    )


@require_GET
def report_category_analysis_api(request):
    search_term = (request.GET.get("q") or "").strip()
    rows, totals = build_category_analysis_report(search_term or None)

    return JsonResponse(
        {
            "filters": {
                "q": search_term,
            },
            "rows": rows,
            "totals": totals,
        }
    )


@csrf_exempt
@require_POST
def cash_session_open_api(request):
    if get_open_cash_session() is not None:
        return JsonResponse({"error": "Ya existe una sesión de caja abierta."}, status=400)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Solicitud inválida"}, status=400)

    monto_inicial_raw = payload.get("monto_inicial", 0)
    try:
        monto_inicial = Decimal(str(monto_inicial_raw)).quantize(TWO_PLACES)
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({"error": "Monto inicial inválido"}, status=400)

    if monto_inicial < Decimal("0"):
        return JsonResponse({"error": "El monto inicial debe ser mayor o igual a cero"}, status=400)

    session = CashSession.objects.create(
        monto_inicial=monto_inicial,
        total_en_caja=monto_inicial,
        total_descuento=Decimal("0.00"),
    )

    last_closed = (
        CashSession.objects.filter(estado=CashSession.Estado.CERRADA)
        .exclude(pk=session.pk)
        .order_by("-cierre_at")
        .first()
    )

    return JsonResponse(
        {
            "open_session": serialize_cash_session(session),
            "last_closed": serialize_cash_session(last_closed, include_totals=True) if last_closed else None,
            "message": "Caja abierta correctamente.",
        },
        status=201,
    )


@csrf_exempt
@require_POST
def cash_session_close_api(request):
    with transaction.atomic():
        session = (
            CashSession.objects.select_for_update()
            .filter(estado=CashSession.Estado.ABIERTA)
            .order_by("-apertura_at")
            .first()
        )
        if session is None:
            return JsonResponse({"error": "No hay una sesión de caja abierta."}, status=400)

        totals = aggregate_cash_session(session)
        session.marcar_cerrada(
            total_en_caja=totals["total_en_caja"],
            total_ventas=totals["total"],
            total_impuesto=totals["impuestos"],
            total_descuento=totals["descuento"],
            total_ventas_credito=totals["total_credito"],
        )
        session.refresh_from_db()

    payload = {
        "open_session": None,
        "last_closed": serialize_cash_session(session, include_totals=True),
        "closed_session": serialize_cash_session(session, include_totals=True),
        "message": "Caja cerrada correctamente.",
    }
    return JsonResponse(payload)


@require_GET
def cash_session_report_api(request):
    start_date_str = (request.GET.get("fecha_inicio") or "").strip()
    end_date_str = (request.GET.get("fecha_fin") or "").strip()
    page_param = (request.GET.get("page") or "1").strip()
    page_size_param = (request.GET.get("page_size") or "10").strip()

    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    queryset = CashSession.objects.prefetch_related("ventas__detalles__producto").order_by("-apertura_at")

    if start_date:
        queryset = queryset.filter(apertura_at__date__gte=start_date)

    if end_date:
        queryset = queryset.filter(apertura_at__date__lte=end_date)

    try:
        page = int(page_param)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(page_size_param)
    except (TypeError, ValueError):
        page_size = 10

    if page < 1:
        page = 1
    page_size = max(1, min(page_size, 50))

    total_items = queryset.count()
    start_index = (page - 1) * page_size
    if start_index >= total_items and total_items:
        page = max(1, (total_items - 1) // page_size + 1)
        start_index = (page - 1) * page_size

    sessions = list(queryset[start_index : start_index + page_size])

    filters_payload = {
        "fecha_inicio": start_date.isoformat() if start_date else "",
        "fecha_fin": end_date.isoformat() if end_date else "",
    }

    pagination_payload = {
        "page": page,
        "page_size": page_size,
        "total": total_items,
        "page_count": (total_items + page_size - 1) // page_size if total_items else 0,
        "has_previous": page > 1,
        "has_next": start_index + page_size < total_items,
    }

    sessions_data = [serialize_cash_session(session, include_totals=True) for session in sessions]

    return JsonResponse({
        "sessions": sessions_data,
        "filters": filters_payload,
        "pagination": pagination_payload,
    })


def calculate_credit_totals(venta: Venta):
    subtotal = Decimal("0")
    impuestos = Decimal("0")

    subtotal_bruto = getattr(venta, "subtotal_bruto", None)
    descuento_total = getattr(venta, "descuento_total", None)

    if subtotal_bruto is not None and descuento_total is not None:
        try:
            subtotal = (Decimal(str(subtotal_bruto)) - Decimal(str(descuento_total))).quantize(TWO_PLACES)
            if subtotal < Decimal("0"):
                subtotal = Decimal("0")
            impuestos = (subtotal * TAX_RATE).quantize(TWO_PLACES)
        except (InvalidOperation, TypeError, ValueError):
            subtotal = Decimal("0")
            impuestos = Decimal("0")
    else:
        for detalle in venta.detalles.all():
            precio_unitario = detalle.precio_unitario or Decimal("0")
            cantidad = Decimal(detalle.cantidad or 0)
            descuento = detalle.descuento or Decimal("0")

            base_amount = (precio_unitario * cantidad).quantize(TWO_PLACES)
            line_tax = (base_amount * TAX_RATE).quantize(TWO_PLACES)
            line_subtotal = (base_amount - descuento).quantize(TWO_PLACES)
            if line_subtotal < Decimal("0"):
                line_subtotal = Decimal("0.00")

            subtotal += line_subtotal
            impuestos += line_tax

        subtotal = subtotal.quantize(TWO_PLACES)
        impuestos = impuestos.quantize(TWO_PLACES)

    total = (subtotal + impuestos).quantize(TWO_PLACES)

    return {
        "subtotal": subtotal,
        "impuestos": impuestos,
        "total": total,
    }


def serialize_credit_account(cuenta: CuentaCredito):
    venta = cuenta.venta
    fecha_local = timezone.localtime(venta.fecha)
    totals = calculate_credit_totals(venta)
    total_credito = totals["total"]
    total_abonado = Decimal("0")
    detalles = venta.detalles.select_related("producto").all()
    productos_resumen = []
    for detalle in detalles:
        producto = detalle.producto
        if producto:
            nombre_producto = str(producto)
        else:
            nombre_producto = "Producto eliminado"
        productos_resumen.append(f"{nombre_producto} x{detalle.cantidad}")
    productos_display = ", ".join(productos_resumen)
    pagos_queryset = cuenta.pagos.all().order_by("-created_at")
    last_payment = pagos_queryset.first()
    base_datetime = (
        timezone.localtime(last_payment.created_at)
        if last_payment
        else fecha_local
    )

    cycle_days = cuenta.frecuencia_dias or PAYMENT_CYCLE_DAYS
    if cycle_days <= 0:
        cycle_days = PAYMENT_CYCLE_DAYS

    last_payment_local = timezone.localtime(last_payment.created_at) if last_payment else None

    due_datetime = base_datetime + timedelta(days=cycle_days)
    now_local = timezone.localtime(timezone.now())
    remaining_seconds = int((due_datetime - now_local).total_seconds())

    is_overdue = remaining_seconds <= 0

    if is_overdue:
        countdown_display = "Vencido"
    else:
        days = remaining_seconds // 86400
        hours = (remaining_seconds % 86400) // 3600
        minutes = (remaining_seconds % 3600) // 60
        countdown_display = f"{days:02d}d {hours:02d}h {minutes:02d}m"

    pagos_data = []
    for pago in pagos_queryset:
        monto = pago.monto.quantize(TWO_PLACES)
        total_abonado += monto
        pago_fecha = timezone.localtime(pago.created_at)
        if pago.registrado_por and hasattr(pago.registrado_por, "get_full_name"):
            registrado_por = pago.registrado_por.get_full_name() or pago.registrado_por.get_username()
        elif pago.registrado_por:
            registrado_por = str(pago.registrado_por)
        else:
            registrado_por = ""
        pagos_data.append(
            {
                "id": pago.pk,
                "monto": float(monto),
                "monto_display": format_currency(monto),
                "fecha_iso": pago_fecha.isoformat(),
                "fecha_display": pago_fecha.strftime("%d/%m/%Y %I:%M %p"),
                "comentario": pago.comentario,
                "producto": productos_display,
                "registrado_por": registrado_por,
            }
        )

    total_abonado = total_abonado.quantize(TWO_PLACES)
    saldo_calculado = (total_credito - total_abonado).quantize(TWO_PLACES)
    if saldo_calculado < Decimal("0"):
        saldo_calculado = Decimal("0.00")

    fields_to_update = []
    if cuenta.total_credito != total_credito:
        cuenta.total_credito = total_credito
        fields_to_update.append("total_credito")

    if cuenta.saldo_pendiente != saldo_calculado:
        cuenta.saldo_pendiente = saldo_calculado
        fields_to_update.append("saldo_pendiente")

    is_fully_paid = saldo_calculado == Decimal("0.00")
    previous_estado = cuenta.estado

    if is_fully_paid:
        if previous_estado == "pagado_tarde":
            nuevo_estado = "pagado_tarde"
        else:
            nuevo_estado = "pagado"
    elif is_overdue:
        nuevo_estado = "atrasado"
    else:
        nuevo_estado = "pendiente"
    if previous_estado != nuevo_estado:
        cuenta.estado = nuevo_estado
        fields_to_update.append("estado")

    if fields_to_update:
        fields_to_update.append("updated_at")
        cuenta.save(update_fields=fields_to_update)

    phone_raw = cuenta.cliente.telefono or ""
    phone_digits = "".join(filter(str.isdigit, phone_raw))
    whatsapp_threshold_seconds = WHATSAPP_ALERT_DAYS * 86400
    whatsapp_enabled = (
        bool(phone_digits)
        and remaining_seconds <= whatsapp_threshold_seconds
        and cuenta.estado != "pagado"
    )

    # Datos de cuotas
    progreso_cuotas = cuenta.progreso_cuotas
    frecuencia_display = ""
    if cuenta.frecuencia_dias == 7:
        frecuencia_display = "Semanal"
    elif cuenta.frecuencia_dias == 15:
        frecuencia_display = "Quincenal"
    elif cuenta.frecuencia_dias == 30:
        frecuencia_display = "Mensual"
    else:
        frecuencia_display = f"Cada {cuenta.frecuencia_dias} días"

    return {
        "cuenta_id": cuenta.pk,
        "factura": f"FAC-{venta.pk:06d}",
        "cliente": cuenta.cliente.nombre,
        "cliente_documento": cuenta.cliente.documento,
        "total_credito": float(total_credito),
        "total_credito_display": format_currency(total_credito),
        "saldo_pendiente": float(cuenta.saldo_pendiente.quantize(TWO_PLACES)),
        "saldo_pendiente_display": format_currency(cuenta.saldo_pendiente.quantize(TWO_PLACES)),
        "total_abonado": float(total_abonado),
        "total_abonado_display": format_currency(total_abonado),
        "fecha_venta_iso": fecha_local.isoformat(),
        "fecha_venta_display": fecha_local.strftime("%d/%m/%Y %I:%M %p"),
        "estado": cuenta.estado,
        "estado_display": cuenta.estado.replace("_", " ").title(),
        "pagos": pagos_data,
        "productos_resumen": productos_resumen,
        "productos_display": productos_display,
        "due_date_iso": due_datetime.isoformat(),
        "due_date_display": due_datetime.strftime("%d/%m/%Y %I:%M %p"),
        "due_in_seconds": remaining_seconds,
        "countdown_display": countdown_display,
        "payment_cycle_days": cycle_days,
        "countdown_warning_days": COUNTDOWN_WARNING_DAYS,
        "whatsapp_alert_days": WHATSAPP_ALERT_DAYS,
        "cliente_telefono": phone_raw,
        "cliente_telefono_sanitized": phone_digits,
        "whatsapp_enabled": whatsapp_enabled,
        "is_overdue": is_overdue,
        "can_register_late_payment": bool(not is_fully_paid and is_overdue),
        "last_payment_iso": last_payment_local.isoformat() if last_payment_local else None,
        "last_payment_display": last_payment_local.strftime("%d/%m/%Y %I:%M %p") if last_payment_local else "",
        # Datos de cuotas
        "progreso_cuotas": progreso_cuotas,
        "numero_cuotas": cuenta.numero_cuotas,
        "cuotas_pagadas": cuenta.cuotas_pagadas,
        "frecuencia_dias": cuenta.frecuencia_dias,
        "frecuencia_display": frecuencia_display,
        "monto_cuota": float(cuenta.monto_cuota),
        "monto_cuota_display": format_currency(cuenta.monto_cuota),
        "abono_inicial": float(cuenta.abono_inicial),
        "abono_inicial_display": format_currency(cuenta.abono_inicial),
    }


class DashboardTemplateView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy("public:login")
    redirect_field_name = "next"


class DashboardHomeView(DashboardTemplateView):
    template_name = "dashboard/inicio.html"


class VentasView(DashboardTemplateView):
    template_name = "dashboard/ventas.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["clientes"] = Cliente.objects.all()
        context["productos"] = Producto.objects.all()
        context["invoices_count"] = Venta.objects.count()

        today = timezone.localdate()
        now = timezone.now()
        upcoming_limit = today + timedelta(days=7)

        active_credits = (
            CuentaCredito.objects.select_related("venta", "cliente")
            .prefetch_related("pagos")
            .exclude(estado__in=["pagado", "pagado_tarde"])
        )

        rows_buffer = []
        due_today_count = 0
        due_today_amount = Decimal("0.00")
        overdue_count = 0
        upcoming_count = 0
        total_pending_amount = Decimal("0.00")

        for cuenta in active_credits:
            serialized = serialize_credit_account(cuenta)

            due_iso = serialized.get("due_date_iso")
            due_dt = dateparse.parse_datetime(due_iso) if due_iso else None
            if due_dt is not None:
                due_dt = timezone.localtime(due_dt)
                due_date = due_dt.date()
            else:
                due_date = None

            estado_key = serialized.get("estado") or "pendiente"
            estado_display = serialized.get("estado_display") or estado_key.replace("_", " ").title()
            monto_cuota = Decimal(str(serialized.get("monto_cuota") or "0")).quantize(TWO_PLACES)
            total_pending_amount += max(cuenta.saldo_pendiente, Decimal("0"))

            is_due_today = bool(due_date and due_date == today)
            is_overdue = bool(serialized.get("is_overdue"))
            is_upcoming = bool(due_date and today < due_date <= upcoming_limit)

            if is_due_today:
                due_today_count += 1
                due_today_amount += monto_cuota

            if is_overdue:
                overdue_count += 1
            elif is_upcoming:
                upcoming_count += 1

            include_row = is_due_today or is_overdue or is_upcoming

            if include_row:
                status_class = f"credit-status credit-status--{estado_key}"
                chip_class = ["credit-collections__chip"]
                if is_due_today:
                    chip_class.append("credit-collections__chip--today")
                    due_badge = "Hoy"
                elif is_overdue:
                    chip_class.append("credit-collections__chip--overdue")
                    due_badge = "Atrasado"
                else:
                    chip_class.append("credit-collections__chip--upcoming")
                    due_badge = "Próximo"

                rows_buffer.append(
                    (
                        due_dt or now + timedelta(days=90),
                        {
                            "cuenta_id": serialized["cuenta_id"],
                            "cliente": serialized["cliente"],
                            "factura": serialized["factura"],
                            "estado": estado_display,
                            "estado_key": estado_key,
                            "status_class": status_class,
                            "monto_cuota_display": serialized.get("monto_cuota_display", format_currency(monto_cuota)),
                            "monto_cuota_raw": float(serialized.get("monto_cuota", monto_cuota)),
                            "saldo_pendiente": serialized.get("saldo_pendiente", 0),
                            "saldo_pendiente_display": serialized.get("saldo_pendiente_display", format_currency(cuenta.saldo_pendiente)),
                            "saldo_pendiente_raw": float(serialized.get("saldo_pendiente", cuenta.saldo_pendiente)),
                            "progreso": serialized.get("progreso_cuotas") or "",
                            "due_date_display": due_dt.strftime("%d/%m/%Y") if due_dt else "Sin fecha",
                            "due_badge": due_badge,
                            "chip_class": " ".join(chip_class),
                        },
                    )
                )

        collection_rows = [row for _, row in sorted(rows_buffer, key=lambda item: item[0])]

        payments_today_total = (
            PagoCredito.objects.filter(created_at__date=today).aggregate(total=Sum("monto"))
        )
        collected_today_amount = (payments_today_total.get("total") or Decimal("0")).quantize(TWO_PLACES)
        due_today_amount = due_today_amount.quantize(TWO_PLACES)
        total_pending_amount = total_pending_amount.quantize(TWO_PLACES)

        context["credit_collection_summary"] = {
            "due_today_count": due_today_count,
            "due_today_amount_display": format_currency(due_today_amount),
            "overdue_count": overdue_count,
            "upcoming_count": upcoming_count,
            "collected_today_display": format_currency(collected_today_amount),
            "total_pending_display": format_currency(total_pending_amount),
        }
        context["credit_collection_rows"] = collection_rows

        return context


class CotizacionesView(DashboardTemplateView):
    template_name = "dashboard/cotizaciones.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quotes_session = self.request.session.get("cotizaciones", [])
        context["clientes"] = Cliente.objects.all()
        context["productos"] = Producto.objects.all()
        context["quotes_count"] = len(quotes_session)
        paginator, page_obj, querystring = build_pagination(self.request, quotes_session)
        context["quotes_page"] = page_obj
        context["quotes_pagination_querystring"] = querystring
        context["quotes_session"] = quotes_session
        return context


class InventarioView(DashboardTemplateView):
    template_name = "dashboard/inventario.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_get = self.request.GET
        productos_qs = (
            Producto.objects.select_related("impuesto", "marca", "modelo", "categoria", "proveedor")
            .prefetch_related("imagenes")
            .order_by("nombre")
        )

        search_term = (request_get.get("search", "") or "").strip()
        categoria_id = (request_get.get("categoria", "") or "").strip()
        marca_id = (request_get.get("marca", "") or "").strip()
        status_value = (request_get.get("activo", "") or "").strip().lower()
        stock_filter = (request_get.get("stock", "") or "").strip().lower()

        if search_term:
            search_filters = (
                Q(nombre__icontains=search_term)
                | Q(imei__icontains=search_term)
                | Q(descripcion__icontains=search_term)
                | Q(modelo__nombre__icontains=search_term)
                | Q(marca__nombre__icontains=search_term)
                | Q(proveedor__nombre__icontains=search_term)
            )
            productos_qs = productos_qs.filter(search_filters).distinct()

        if categoria_id.isdigit():
            productos_qs = productos_qs.filter(categoria_id=int(categoria_id))

        if marca_id.isdigit():
            productos_qs = productos_qs.filter(marca_id=int(marca_id))

        if status_value in {"true", "false"}:
            productos_qs = productos_qs.filter(activo=(status_value == "true"))

        if stock_filter == "available":
            productos_qs = productos_qs.filter(stock__gt=0)
        elif stock_filter == "low":
            productos_qs = productos_qs.filter(stock__gt=0).filter(stock__lte=F("stock_minimo"))
        elif stock_filter == "out":
            productos_qs = productos_qs.filter(stock__lte=0)

        paginator, productos_page, querystring = build_pagination(self.request, productos_qs)
        context["productos_page"] = productos_page
        context["productos"] = productos_qs
        context["productos_list"] = list(productos_page.object_list)
        context["productos_pagination_querystring"] = querystring
        form = kwargs.get("producto_form") or ProductoForm()
        context["producto_form"] = form
        context.setdefault("categorias_catalogo", Categoria.objects.only("id", "nombre"))
        context.setdefault("marcas_catalogo", Marca.objects.filter(activo=True).only("id", "nombre"))
        context.setdefault(
            "marcas_admin_catalogo",
            Marca.objects.all().only("id", "nombre", "activo"),
        )
        context.setdefault(
            "modelos_catalogo",
            Modelo.objects.filter(activo=True).select_related("marca").order_by("nombre"),
        )
        context.setdefault(
            "modelos_admin_catalogo",
            Modelo.objects.select_related("marca").order_by("nombre"),
        )
        context.setdefault("impuestos_catalogo", Impuesto.objects.only("id", "nombre", "porcentaje"))
        context.setdefault("proveedores_catalogo", Proveedor.objects.only("id", "nombre"))
        force_modal = kwargs.get("force_product_modal", False) or bool(form.errors)
        context["force_product_modal"] = force_modal
        context["filter_values"] = {
            "search": search_term,
            "categoria": categoria_id,
            "marca": marca_id,
            "activo": status_value,
            "stock": stock_filter,
        }
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "create")
        producto_id = request.POST.get("producto_id")

        if action == "update":
            producto = get_object_or_404(Producto, pk=producto_id)
            form = ProductoForm(request.POST, request.FILES, instance=producto)
            if form.is_valid():
                producto = form.save()
                for archivo in request.FILES.getlist("imagenes_adicionales"):
                    if archivo:
                        ProductImage.objects.create(producto=producto, imagen=archivo)
                messages.success(request, f"Producto {producto} actualizado correctamente.")
                return redirect(request.path)
            context = self.get_context_data(
                producto_form=form,
                force_product_modal=True,
            )
            return self.render_to_response(context)

        if action == "delete":
            producto = get_object_or_404(Producto, pk=producto_id)
            nombre = producto.nombre
            try:
                producto.delete()
            except ProtectedError:
                messages.error(
                    request,
                    f"No se puede eliminar {nombre} porque está asociado a otras operaciones (ventas, reparaciones u otras referencias).",
                )
            else:
                messages.success(request, f"Producto {nombre} eliminado correctamente.")
            return redirect(request.path)

        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            for archivo in request.FILES.getlist("imagenes_adicionales"):
                if archivo:
                    ProductImage.objects.create(producto=producto, imagen=archivo)
            messages.success(request, f"Producto {producto} creado correctamente.")
            return redirect(request.path)
        context = self.get_context_data(
            producto_form=form,
            force_product_modal=True,
        )
        return self.render_to_response(context)


class ProductoDetailView(DashboardTemplateView):
    template_name = "dashboard/producto_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        producto_id = kwargs.get('producto_id')
        
        producto = get_object_or_404(
            Producto.objects.select_related('marca', 'modelo', 'categoria', 'proveedor', 'impuesto')
            .prefetch_related('imagenes'),
            pk=producto_id
        )
        
        context['producto'] = producto
        
        # Productos relacionados (misma marca o categoría)
        productos_relacionados = Producto.objects.filter(
            Q(marca=producto.marca) | Q(categoria=producto.categoria)
        ).exclude(pk=producto.pk).filter(activo=True)[:6]
        
        context['productos_relacionados'] = productos_relacionados
        
        return context


class ClientesView(DashboardTemplateView):
    template_name = "dashboard/clientes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_get = self.request.GET
        search_term = (request_get.get("search", "") or "").strip()
        tipo_documento = (request_get.get("tipo_documento", "") or "").strip()

        clientes_qs = Cliente.objects.all()

        if search_term:
            search_filters = (
                Q(nombre__icontains=search_term)
                | Q(documento__icontains=search_term)
                | Q(correo__icontains=search_term)
                | Q(telefono__icontains=search_term)
            )
            clientes_qs = clientes_qs.filter(search_filters)

        if tipo_documento:
            clientes_qs = clientes_qs.filter(tipo_documento=tipo_documento)

        clientes_qs = clientes_qs.order_by("codigo")

        _, clientes_page, querystring = build_pagination(self.request, clientes_qs)
        context["clientes_page"] = clientes_page
        context["clientes"] = clientes_page.object_list
        context["clientes_list"] = list(clientes_page.object_list)
        context["pagination_querystring"] = querystring
        form = kwargs.get("form") or ClienteForm()
        context["form"] = form
        context["next_codigo"] = Cliente.next_codigo()
        context["modal_mode"] = kwargs.get("modal_mode", "create")
        context["modal_codigo"] = kwargs.get("modal_codigo", context["next_codigo"])
        context["editing_cliente_id"] = kwargs.get("editing_cliente_id")
        force_modal_open = kwargs.get("force_modal_open", False) or bool(form.errors)
        context["force_modal_open"] = force_modal_open
        context["filter_values"] = {
            "search": search_term,
            "tipo_documento": tipo_documento,
        }
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "create")
        cliente_id = request.POST.get("cliente_id")

        if action == "delete":
            cliente = get_object_or_404(Cliente, pk=cliente_id)
            nombre = cliente.nombre
            cliente.delete()
            messages.success(request, f"Cliente {nombre} eliminado correctamente.")
            return redirect(request.path)

        if action == "edit_modal":
            cliente = get_object_or_404(Cliente, pk=cliente_id)
            form = ClienteForm(instance=cliente)
            context = self.get_context_data(
                form=form,
                modal_mode="edit",
                modal_codigo=cliente.codigo,
                editing_cliente_id=cliente.pk,
                force_modal_open=True,
            )
            return self.render_to_response(context)

        if action == "update":
            cliente = get_object_or_404(Cliente, pk=cliente_id)
            form = ClienteForm(request.POST, instance=cliente)
            if form.is_valid():
                cliente = form.save()
                messages.success(request, f"Cliente {cliente.nombre} actualizado correctamente.")
                return redirect(request.path)
            context = self.get_context_data(
                form=form,
                modal_mode="edit",
                modal_codigo=cliente.codigo,
                editing_cliente_id=cliente.pk,
                force_modal_open=True,
            )
            return self.render_to_response(context)

        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, f"Cliente {cliente.nombre} creado correctamente.")
            return redirect(request.path)
        context = self.get_context_data(
            form=form,
            modal_mode="create",
            modal_codigo=request.POST.get("codigo") or Cliente.next_codigo(),
            force_modal_open=True,
        )
        return self.render_to_response(context)


class ProveedorView(DashboardTemplateView):
    template_name = "dashboard/proveedor.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_get = self.request.GET
        search_term = (request_get.get("search", "") or "").strip()
        tipo_documento = (request_get.get("tipo_documento", "") or "").strip()

        proveedores_qs = Proveedor.objects.all()

        if search_term:
            search_filters = (
                Q(nombre__icontains=search_term)
                | Q(documento__icontains=search_term)
                | Q(correo__icontains=search_term)
                | Q(telefono__icontains=search_term)
            )
            proveedores_qs = proveedores_qs.filter(search_filters)

        if tipo_documento:
            proveedores_qs = proveedores_qs.filter(tipo_documento=tipo_documento)

        proveedores_qs = proveedores_qs.order_by("codigo")

        _, proveedores_page, querystring = build_pagination(self.request, proveedores_qs)
        context["proveedores_page"] = proveedores_page
        context["proveedores"] = proveedores_qs
        context["proveedores_list"] = list(proveedores_page.object_list)
        context["pagination_querystring"] = querystring
        form = kwargs.get("form") or ProveedorForm()
        context["form"] = form
        context["next_codigo"] = Proveedor.next_codigo()
        context["modal_mode"] = kwargs.get("modal_mode", "create")
        context["modal_codigo"] = kwargs.get("modal_codigo", context["next_codigo"])
        context["editing_proveedor_id"] = kwargs.get("editing_proveedor_id")
        force_modal_open = kwargs.get("force_modal_open", False) or bool(form.errors)
        context["force_modal_open"] = force_modal_open
        context["filter_values"] = {
            "search": search_term,
            "tipo_documento": tipo_documento,
        }
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "create")
        proveedor_id = request.POST.get("proveedor_id")

        if action == "delete":
            proveedor = get_object_or_404(Proveedor, pk=proveedor_id)
            nombre = proveedor.nombre
            proveedor.delete()
            messages.success(request, f"Proveedor {nombre} eliminado correctamente.")
            return redirect(request.path)

        if action == "edit_modal":
            proveedor = get_object_or_404(Proveedor, pk=proveedor_id)
            form = ProveedorForm(instance=proveedor)
            context = self.get_context_data(
                form=form,
                modal_mode="edit",
                modal_codigo=proveedor.codigo,
                editing_proveedor_id=proveedor.pk,
                force_modal_open=True,
            )
            return self.render_to_response(context)

        if action == "update":
            proveedor = get_object_or_404(Proveedor, pk=proveedor_id)
            form = ProveedorForm(request.POST, instance=proveedor)
            if form.is_valid():
                proveedor = form.save()
                messages.success(request, f"Proveedor {proveedor.nombre} actualizado correctamente.")
                return redirect(request.path)
            context = self.get_context_data(
                form=form,
                modal_mode="edit",
                modal_codigo=proveedor.codigo,
                editing_proveedor_id=proveedor.pk,
                force_modal_open=True,
            )
            return self.render_to_response(context)

        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save()
            messages.success(request, f"Proveedor {proveedor.nombre} creado correctamente.")
            return redirect(request.path)
        context = self.get_context_data(
            form=form,
            modal_mode="create",
            modal_codigo=request.POST.get("codigo") or Proveedor.next_codigo(),
            force_modal_open=True,
        )
        return self.render_to_response(context)


class ComprasView(DashboardTemplateView):
    template_name = "dashboard/compras.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_get = self.request.GET
        search_term = (request_get.get("search", "") or "").strip()
        proveedor_id = (request_get.get("proveedor", "") or "").strip()
        fecha_desde_raw = (request_get.get("fecha_desde", "") or "").strip()
        fecha_hasta_raw = (request_get.get("fecha_hasta", "") or "").strip()

        compras_qs = Compra.objects.select_related("proveedor", "producto")

        if search_term:
            search_filters = (
                Q(numero_pedido__icontains=search_term)
                | Q(proveedor__nombre__icontains=search_term)
                | Q(producto__nombre__icontains=search_term)
            )
            compras_qs = compras_qs.filter(search_filters).distinct()

        if proveedor_id.isdigit():
            compras_qs = compras_qs.filter(proveedor_id=int(proveedor_id))

        fecha_desde = parse_date(fecha_desde_raw) if fecha_desde_raw else None
        fecha_hasta = parse_date(fecha_hasta_raw) if fecha_hasta_raw else None

        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
            fecha_desde_raw, fecha_hasta_raw = fecha_desde_raw, fecha_hasta_raw

        if fecha_desde:
            compras_qs = compras_qs.filter(created_at__date__gte=fecha_desde)

        if fecha_hasta:
            compras_qs = compras_qs.filter(created_at__date__lte=fecha_hasta)

        compras_qs = compras_qs.order_by("-created_at", "-pk")

        _, compras_page, querystring = build_pagination(self.request, compras_qs)
        context["compras_page"] = compras_page
        context["compras"] = compras_page.object_list
        context["compras_all"] = list(compras_qs)
        context["pagination_querystring"] = querystring
        context["proveedores"] = Proveedor.objects.all()
        context["productos"] = Producto.objects.all()
        context["force_purchase_modal"] = self.request.session.pop("force_purchase_modal", False)
        context["purchase_form_errors"] = self.request.session.pop("purchase_form_errors", [])
        context["purchase_form_values"] = self.request.session.pop("purchase_form_values", {})
        context.setdefault("next_purchase_code", self._generate_order_number())
        context["filter_values"] = {
            "search": search_term,
            "proveedor": proveedor_id,
            "fecha_desde": fecha_desde_raw,
            "fecha_hasta": fecha_hasta_raw,
        }
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "add_purchase":
            return self._handle_add_purchase(request)
        return redirect(request.path)

    def _generate_order_number(self) -> str:
        ahora = timezone.localtime()
        base = ahora.strftime('%Y%m%d%H%M%S')
        numero = f"CMP-{base}"
        suffix = 0
        while Compra.objects.filter(numero_pedido=numero).exists():
            suffix += 1
            numero = f"CMP-{base}-{suffix:02d}"
        return numero

    def _handle_add_purchase(self, request):
        numero_pedido = request.POST.get("numero_pedido", "").strip()
        proveedor_id = request.POST.get("proveedor_id", "").strip()
        producto_id = request.POST.get("producto_id", "").strip()
        cantidad_raw = request.POST.get("cantidad", "").strip()

        form_values = {
            "numero_pedido": numero_pedido,
            "proveedor_id": proveedor_id,
            "producto_id": producto_id,
            "cantidad": cantidad_raw,
        }

        errors = []
        if not numero_pedido:
            numero_pedido = self._generate_order_number()
            form_values["numero_pedido"] = numero_pedido

        proveedor = None
        if not proveedor_id:
            errors.append("Debes seleccionar un proveedor.")
        else:
            proveedor = Proveedor.objects.filter(pk=proveedor_id).first()
            if not proveedor:
                errors.append("El proveedor seleccionado no existe.")

        producto = None
        if not producto_id:
            errors.append("Debes seleccionar un producto.")
        else:
            producto = Producto.objects.filter(pk=producto_id).first()
            if not producto:
                errors.append("El producto seleccionado no existe.")

        try:
            cantidad = int(cantidad_raw)
            if cantidad <= 0:
                raise ValueError
        except (ArithmeticError, ValueError):
            errors.append("La nueva cantidad debe ser un número positivo.")
            cantidad = None

        if errors:
            request.session["force_purchase_modal"] = True
            request.session["purchase_form_errors"] = errors
            request.session["purchase_form_values"] = form_values
            return redirect(request.path)

        if Compra.objects.filter(numero_pedido=numero_pedido).exists():
            numero_pedido = self._generate_order_number()
            form_values["numero_pedido"] = numero_pedido

        with transaction.atomic():
            producto = Producto.objects.select_for_update().get(pk=producto.pk)
            stock_anterior = producto.stock
            producto.stock = producto.stock + cantidad
            producto.save(update_fields=["stock", "updated_at"])

            Compra.objects.create(
                numero_pedido=numero_pedido,
                proveedor=proveedor,
                producto=producto,
                cantidad=cantidad,
                precio_compra=producto.precio_compra,
                precio_venta=producto.precio_venta,
                stock_anterior=stock_anterior,
                stock_actual=producto.stock,
                registrado_por=request.user if request.user.is_authenticated else None,
            )

        request.session.pop("purchase_form_values", None)
        messages.success(
            request,
            f"Compra registrada. Stock de {producto.nombre} actualizado de {stock_anterior} a {producto.stock}.",
        )
        return redirect(request.path)


class CobrosView(DashboardTemplateView):
    template_name = "dashboard/cobros.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        creditos_qs = CuentaCredito.objects.select_related("venta", "cliente").prefetch_related("pagos")

        search_term = self.request.GET.get("q", "").strip().lower()
        estado_filter = self.request.GET.get("estado", "").strip().lower()

        activos_data = []
        pagados_data = []

        for cuenta in creditos_qs:
            data = serialize_credit_account(cuenta)

            matches_search = True
            if search_term:
                matches_search = (
                    search_term in data["factura"].lower()
                    or search_term in data["cliente"].lower()
                    or search_term in data["estado_display"].lower()
                )

            matches_estado = True
            if estado_filter:
                matches_estado = data["estado"].lower() == estado_filter

            if not (matches_search and matches_estado):
                continue

            if data["estado"] in {"pagado", "pagado_tarde"}:
                pagados_data.append(data)
            else:
                activos_data.append(data)

        activos_sorted = sorted(activos_data, key=lambda credito: credito.get("factura", ""))
        pagados_sorted = sorted(pagados_data, key=lambda credito: credito.get("factura", ""))

        _, creditos_page, querystring = build_pagination(self.request, activos_sorted)

        context["creditos"] = creditos_page.object_list
        context["creditos_all"] = activos_sorted
        context["creditos_page"] = creditos_page
        context["creditos_pagados"] = pagados_sorted
        context["search_term"] = self.request.GET.get("q", "")
        context["estado_filter"] = self.request.GET.get("estado", "")
        context["pagination_querystring"] = querystring
        return context


@require_POST
def registrar_abono_credito_api(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Solicitud inválida"}, status=400)

    cuenta_id = payload.get("cuenta_id")
    monto = payload.get("monto")
    comentario = payload.get("comentario", "").strip()

    if not cuenta_id or monto in (None, ""):
        return JsonResponse({"error": "Datos incompletos"}, status=400)

    cuenta = get_object_or_404(
        CuentaCredito.objects.select_related("venta", "cliente").prefetch_related("pagos"),
        pk=cuenta_id,
    )

    try:
        monto_decimal = Decimal(str(monto)).quantize(TWO_PLACES)
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({"error": "Monto inválido"}, status=400)

    with transaction.atomic():
        try:
            cuenta.registrar_pago(monto_decimal)
        except ValueError as exc:
            transaction.set_rollback(True)
            return JsonResponse({"error": str(exc)}, status=400)

        PagoCredito.objects.create(
            cuenta=cuenta,
            monto=monto_decimal,
            registrado_por=request.user if request.user.is_authenticated else None,
            comentario=comentario,
        )

    cuenta.refresh_from_db()
    cuenta = CuentaCredito.objects.select_related("venta", "cliente").prefetch_related("pagos").get(pk=cuenta.pk)
    data = serialize_credit_account(cuenta)
    return JsonResponse({"credito": data})


@require_POST
def registrar_pago_tardio_credito_api(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Solicitud inválida"}, status=400)

    cuenta_id = payload.get("cuenta_id")
    monto = payload.get("monto")
    comentario = (payload.get("comentario") or "").strip()

    if not cuenta_id:
        return JsonResponse({"error": "Debes indicar la cuenta de crédito."}, status=400)

    cuenta = get_object_or_404(
        CuentaCredito.objects.select_related("venta", "cliente").prefetch_related("pagos"),
        pk=cuenta_id,
    )

    if cuenta.estado not in {"atrasado", "pendiente"} and cuenta.saldo_pendiente > 0:
        return JsonResponse({"error": "Solo puedes registrar pagos tardíos para créditos pendientes o atrasados."}, status=400)

    saldo_actual = cuenta.saldo_pendiente.quantize(TWO_PLACES)

    if monto in (None, ""):
        monto_decimal = saldo_actual
    else:
        try:
            monto_decimal = Decimal(str(monto)).quantize(TWO_PLACES)
        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse({"error": "Monto inválido"}, status=400)

    if monto_decimal <= 0:
        return JsonResponse({"error": "El monto debe ser mayor a cero."}, status=400)

    with transaction.atomic():
        try:
            cuenta.registrar_pago(monto_decimal)
        except ValueError as exc:
            transaction.set_rollback(True)
            return JsonResponse({"error": str(exc)}, status=400)

        PagoCredito.objects.create(
            cuenta=cuenta,
            monto=monto_decimal,
            registrado_por=request.user if request.user.is_authenticated else None,
            comentario=comentario or "Pago tardío",
        )

        cuenta.refresh_from_db()

        if cuenta.saldo_pendiente == Decimal("0.00"):
            cuenta.estado = "pagado_tarde"
            cuenta.save(update_fields=["estado", "updated_at"])

    cuenta = CuentaCredito.objects.select_related("venta", "cliente").prefetch_related("pagos").get(pk=cuenta.pk)
    data = serialize_credit_account(cuenta)
    return JsonResponse({"credito": data})


def _parse_json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


@require_POST
def toggle_brand_status_api(request, brand_id: int):
    brand = get_object_or_404(Marca, pk=brand_id)
    brand.activo = not brand.activo
    brand.save(update_fields=["activo", "updated_at"])
    return JsonResponse(
        {
            "id": brand.pk,
            "nombre": brand.nombre,
            "activo": brand.activo,
            "estado_display": "Activo" if brand.activo else "Inactivo",
        }
    )


@require_POST
def toggle_model_status_api(request, model_id: int):
    modelo = get_object_or_404(Modelo, pk=model_id)
    modelo.activo = not modelo.activo
    modelo.save(update_fields=["activo", "updated_at"])
    return JsonResponse(
        {
            "id": modelo.pk,
            "nombre": modelo.nombre,
            "marca": modelo.marca.nombre if modelo.marca else None,
            "activo": modelo.activo,
            "estado_display": "Activo" if modelo.activo else "Inactivo",
        }
    )


@require_POST
def create_brand_api(request):
    payload = _parse_json_body(request)
    if payload is None:
        return JsonResponse({"error": "Datos inválidos."}, status=400)

    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        return JsonResponse({"error": "Debes indicar el nombre de la marca."}, status=400)

    activo = bool(payload.get("activo", True))

    brand = Marca(nombre=nombre, activo=activo)
    try:
        brand.save()
    except IntegrityError:
        return JsonResponse({"error": "Ya existe una marca con ese nombre."}, status=409)

    return JsonResponse(
        {
            "id": brand.pk,
            "nombre": brand.nombre,
            "activo": brand.activo,
            "estado_display": "Activo" if brand.activo else "Inactivo",
        },
        status=201,
    )


@require_POST
def create_model_api(request):
    payload = _parse_json_body(request)
    if payload is None:
        return JsonResponse({"error": "Datos inválidos."}, status=400)

    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        return JsonResponse({"error": "Debes indicar el nombre del modelo."}, status=400)

    marca_id = payload.get("marca")
    marca = None
    if marca_id:
        marca = Marca.objects.filter(pk=marca_id).first()
        if not marca:
            return JsonResponse({"error": "La marca seleccionada no existe."}, status=400)

    activo = bool(payload.get("activo", True))

    modelo = Modelo(nombre=nombre, marca=marca, activo=activo)
    try:
        modelo.save()
    except IntegrityError:
        return JsonResponse({"error": "Ya existe un modelo con ese nombre para la marca seleccionada."}, status=409)

    return JsonResponse(
        {
            "id": modelo.pk,
            "nombre": modelo.nombre,
            "marca_id": modelo.marca.pk if modelo.marca else None,
            "marca_nombre": modelo.marca.nombre if modelo.marca else None,
            "activo": modelo.activo,
            "estado_display": "Activo" if modelo.activo else "Inactivo",
        },
        status=201,
    )


class OtrosView(DashboardTemplateView):
    template_name = "dashboard/otros.html"


class ReportesView(DashboardTemplateView):
    template_name = "dashboard/reportes.html"


class GastosView(DashboardTemplateView):
    template_name = "dashboard/gastos.html"


class UsuariosView(DashboardTemplateView):
    template_name = "dashboard/usuarios.html"


class ConfiguracionView(DashboardTemplateView):
    template_name = "dashboard/configuracion.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site_config = SiteConfiguration.get_solo()
        context.setdefault(
            "site_logo_form",
            getattr(self, "site_logo_form", SiteConfigurationLogoForm(instance=site_config)),
        )
        context["site_logo_url"] = site_config.logo.url if site_config.logo else static("img/logo/logo.png")
        context["site_logo_panel_open"] = getattr(self, "force_open_general_settings", False)
        context["site_configuration"] = site_config

        fiscal_config = FiscalVoucherConfig.objects.first()
        context["fiscal_config"] = fiscal_config
        context["fiscal_config_form"] = FiscalVoucherConfigForm(instance=fiscal_config)
        context["fiscal_xml_form"] = FiscalVoucherXMLForm()
        context["fiscal_xml_templates"] = (
            FiscalVoucherXML.objects.filter(configuracion=fiscal_config)
            if fiscal_config
            else FiscalVoucherXML.objects.none()
        )
        context["categorias"] = Categoria.objects.all()
        context["categoria_form"] = getattr(self, "categoria_form", CategoriaForm())
        context["next_categoria_codigo"] = Categoria.next_codigo()
        if not hasattr(self, "force_open_category"):
            self.force_open_category = self.request.GET.get("open") == "categories"
        context["force_open_category"] = getattr(self, "force_open_category", False)
        context["force_open_category_register"] = getattr(self, "force_open_category_register", False)

        context["impuestos"] = Impuesto.objects.all()
        context["impuesto_form"] = getattr(self, "impuesto_form", ImpuestoForm())
        context["next_impuesto_codigo"] = Impuesto.next_codigo()
        if not hasattr(self, "force_open_tax"):
            self.force_open_tax = self.request.GET.get("open") == "taxes"
        context["force_open_tax"] = getattr(self, "force_open_tax", False)
        context["force_open_tax_register"] = getattr(self, "force_open_tax_register", False)
        return context

    def post(self, request, *args, **kwargs):
        resource = request.POST.get("resource")
        action = request.POST.get("action")

        if resource == "site_config" and action == "update":
            site_config = SiteConfiguration.get_solo()
            form = SiteConfigurationLogoForm(request.POST, request.FILES, instance=site_config)
            if form.is_valid():
                form.save()
                messages.success(request, "Logo actualizado correctamente.")
                return redirect("dashboard:configuracion")

            self.site_logo_form = form
            self.force_open_general_settings = True
            return self.get(request, *args, **kwargs)

        if resource == "categoria" and action == "create":
            form = CategoriaForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Categoría registrada correctamente.")
                url = f"{reverse('dashboard:configuracion')}?open=categories"
                return redirect(url)

            self.categoria_form = form
            self.force_open_category = True
            self.force_open_category_register = True
            return self.get(request, *args, **kwargs)

        if resource == "impuesto" and action == "create":
            form = ImpuestoForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Impuesto registrado correctamente.")
                url = f"{reverse('dashboard:configuracion')}?open=taxes"
                return redirect(url)

            self.impuesto_form = form
            self.force_open_tax = True
            self.force_open_tax_register = True
            return self.get(request, *args, **kwargs)

        return self.get(request, *args, **kwargs)


def _serialize_fiscal_config(config: FiscalVoucherConfig | None) -> dict[str, object]:
    if config is None:
        return {
            "id": None,
            "nombre_contribuyente": "",
            "rnc": "",
            "correo_contacto": "",
            "telefono_contacto": "",
            "tipo_por_defecto": "",
            "serie_por_defecto": "",
            "secuencia_siguiente": 1,
            "dias_vencimiento": 30,
            "emitir_automatico": False,
            "modo_pruebas": True,
            "api_environment": FiscalVoucherConfig.Environment.SANDBOX,
            "api_base_url": "",
            "api_auth_url": "",
            "api_submission_url": "",
            "api_status_url": "",
            "api_directory_url": "",
            "api_void_url": "",
            "api_commercial_approval_url": "",
            "api_client_id": "",
            "api_client_secret": "",
            "certificado_alias": "",
            "certificado_path": "",
            "certificado_password": "",
            "observaciones": "",
        }

    return {
        "id": config.pk,
        "nombre_contribuyente": config.nombre_contribuyente,
        "rnc": config.rnc,
        "correo_contacto": config.correo_contacto,
        "telefono_contacto": config.telefono_contacto,
        "tipo_por_defecto": config.tipo_por_defecto,
        "serie_por_defecto": config.serie_por_defecto,
        "secuencia_siguiente": config.secuencia_siguiente,
        "dias_vencimiento": config.dias_vencimiento,
        "emitir_automatico": config.emitir_automatico,
        "modo_pruebas": config.modo_pruebas,
        "api_environment": config.api_environment,
        "api_base_url": config.api_base_url,
        "api_auth_url": config.api_auth_url,
        "api_submission_url": config.api_submission_url,
        "api_status_url": config.api_status_url,
        "api_directory_url": config.api_directory_url,
        "api_void_url": config.api_void_url,
        "api_commercial_approval_url": config.api_commercial_approval_url,
        "api_client_id": config.api_client_id,
        "api_client_secret": config.api_client_secret,
        "certificado_alias": config.certificado_alias,
        "certificado_path": config.certificado_path,
        "certificado_password": config.certificado_password,
        "observaciones": config.observaciones,
    }


def _serialize_xml_template(template: FiscalVoucherXML) -> dict[str, object]:
    return {
        "id": template.pk,
        "nombre": template.nombre,
        "estado": template.estado_conexion,
        "mensaje": template.mensaje,
        "ultimo_intento": template.ultimo_intento.isoformat() if template.ultimo_intento else "",
        "archivo_url": template.archivo.url if template.archivo else "",
        "creado": template.created_at.isoformat(),
        "actualizado": template.updated_at.isoformat(),
    }


@require_http_methods(["GET", "POST"])
def fiscal_voucher_config_api(request):
    config = FiscalVoucherConfig.objects.first()

    if request.method == "GET":
        return JsonResponse({
            "config": _serialize_fiscal_config(config),
        })

    if request.content_type == "application/json":
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON inválido"}, status=400)
        form_data = payload
    else:
        form_data = request.POST

    form = FiscalVoucherConfigForm(form_data, instance=config)
    if form.is_valid():
        config = form.save()
        return JsonResponse({
            "success": True,
            "config": _serialize_fiscal_config(config),
        })

    return JsonResponse({"success": False, "errors": form.errors}, status=400)


@require_http_methods(["GET", "POST"])
def fiscal_voucher_xml_api(request):
    config = FiscalVoucherConfig.objects.first()

    if request.method == "GET":
        queryset = FiscalVoucherXML.objects.filter(configuracion=config) if config else FiscalVoucherXML.objects.none()
        data = [_serialize_xml_template(xml) for xml in queryset.order_by("-created_at")]
        return JsonResponse({"templates": data})

    form = FiscalVoucherXMLForm(request.POST, request.FILES)
    if form.is_valid():
        xml_template = form.save(commit=False)
        if config:
            xml_template.configuracion = config
        xml_template.save()
        return JsonResponse({"success": True, "template": _serialize_xml_template(xml_template)})

    return JsonResponse({"success": False, "errors": form.errors}, status=400)


@require_POST
def fiscal_voucher_xml_check_api(request, xml_id: int):
    xml_template = get_object_or_404(FiscalVoucherXML, pk=xml_id)
    config = xml_template.configuracion or FiscalVoucherConfig.objects.first()

    xml_template.configuracion = config or xml_template.configuracion
    xml_template.estado_conexion = FiscalVoucherXML.ConexionEstado.BUSCANDO
    xml_template.ultimo_intento = timezone.now()
    xml_template.mensaje = "Verificando conexión..."
    xml_template.save(update_fields=["configuracion", "estado_conexion", "ultimo_intento", "mensaje", "updated_at"])

    if config is None:
        xml_template.estado_conexion = FiscalVoucherXML.ConexionEstado.SIN_CONEXION
        xml_template.mensaje = "No existe configuración fiscal activa."
    else:
        missing_fields: list[str] = []
        required_fields = [
            "api_base_url",
            "api_auth_url",
            "api_submission_url",
            "api_status_url",
            "api_directory_url",
            "api_void_url",
            "api_client_id",
            "api_client_secret",
            "certificado_path",
            "certificado_password",
        ]
        for field in required_fields:
            value = getattr(config, field, "")
            if not value:
                missing_fields.append(field)

        try:
            xml_template.archivo.open()
            xml_template.archivo.close()
        except Exception:
            missing_fields.append("archivo XML no válido")

        if missing_fields:
            xml_template.estado_conexion = FiscalVoucherXML.ConexionEstado.SIN_CONEXION
            xml_template.mensaje = "Faltan datos: " + ", ".join(missing_fields)
        else:
            try:
                build_requests_http_request()
            except RequestsNotAvailable:
                xml_template.estado_conexion = FiscalVoucherXML.ConexionEstado.SIN_CONEXION
                xml_template.mensaje = "La librería requests no está disponible para verificar la conexión."
            else:
                xml_template.estado_conexion = FiscalVoucherXML.ConexionEstado.CONECTADO
                xml_template.mensaje = "Validaciones básicas completadas."

    xml_template.ultimo_intento = timezone.now()
    xml_template.save(update_fields=["estado_conexion", "mensaje", "ultimo_intento", "updated_at"])

    return JsonResponse({"success": True, "template": _serialize_xml_template(xml_template)})


def _select_fiscal_config_for_update(config_id: int | None) -> FiscalVoucherConfig | None:
    queryset = FiscalVoucherConfig.objects.select_for_update()
    if config_id:
        return queryset.filter(pk=config_id).first()
    return queryset.first()


def _create_fiscal_voucher(
    *,
    venta: Venta,
    fiscal_data: dict[str, object] | None,
    subtotal: Decimal,
    impuestos: Decimal,
    total: Decimal,
    monto_pagado: Decimal,
    metodo_pago: str,
    line_items: list[dict[str, object]],
) -> FiscalVoucher | None:
    if not fiscal_data:
        return None

    config_id = fiscal_data.get("config_id") if isinstance(fiscal_data, dict) else None
    config = _select_fiscal_config_for_update(config_id if isinstance(config_id, int) else None)
    if config is None:
        raise ValueError("No existe una configuración fiscal activa. Configúrala antes de emitir comprobantes.")

    serie = (fiscal_data.get("serie") or config.serie_por_defecto or "").strip()
    tipo = (fiscal_data.get("tipo") or config.tipo_por_defecto or "").strip()
    if not serie or not tipo:
        raise ValueError("La configuración fiscal debe incluir una serie y un tipo de comprobante válidos.")

    secuencia = config.secuencia_siguiente or 1
    fecha_emision = timezone.localdate()
    dias_vencimiento = config.dias_vencimiento or 0
    fecha_vencimiento = fecha_emision + timedelta(days=dias_vencimiento) if dias_vencimiento else None

    voucher = FiscalVoucher.objects.create(
        config=config,
        venta=venta,
        tipo=tipo,
        serie=serie,
        secuencia=secuencia,
        fecha_emision=fecha_emision,
        fecha_vencimiento=fecha_vencimiento,
        subtotal=subtotal.quantize(TWO_PLACES),
        itbis=impuestos.quantize(TWO_PLACES),
        total=total.quantize(TWO_PLACES),
        monto_pagado=monto_pagado.quantize(TWO_PLACES),
        metodo_pago=metodo_pago,
        cliente_nombre=fiscal_data.get("cliente_nombre", ""),
        cliente_documento=fiscal_data.get("cliente_documento", ""),
        correo_envio=fiscal_data.get("correo_envio", ""),
        telefono_contacto=fiscal_data.get("telefono_contacto", ""),
        notas=fiscal_data.get("notas", ""),
        otros_impuestos=Decimal("0.00"),
        dgii_estado="pendiente_envio",
    )

    config.secuencia_siguiente = secuencia + 1
    config.save(update_fields=["secuencia_siguiente", "updated_at"])

    for item in line_items:
        detalle = item.get("detalle")
        if detalle is None:
            continue
        base = Decimal(item.get("base", Decimal("0.00")))
        descuento = Decimal(item.get("descuento", Decimal("0.00")))
        line_subtotal = (base - descuento).quantize(TWO_PLACES)
        if line_subtotal < Decimal("0"):
            line_subtotal = Decimal("0.00")
        line_tax = (line_subtotal * TAX_RATE).quantize(TWO_PLACES)
        line_total = (line_subtotal + line_tax).quantize(TWO_PLACES)

        cantidad = Decimal(detalle.cantidad).quantize(TWO_PLACES)
        precio_unitario = detalle.precio_unitario.quantize(TWO_PLACES)

        FiscalVoucherLine.objects.create(
            voucher=voucher,
            producto=detalle.producto,
            descripcion=str(detalle.producto),
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            subtotal=line_subtotal,
            impuesto=line_tax,
            total=line_total,
        )

    return voucher


def _send_fiscal_voucher_to_dgii(voucher_id: int) -> dict[str, object]:
    """Enviar el comprobante fiscal a la DGII si hay configuración disponible."""

    result: dict[str, object] = {}

    try:
        voucher = (
            FiscalVoucher.objects.select_related("config", "venta__cliente")
            .prefetch_related("lineas")
            .get(pk=voucher_id)
        )
    except FiscalVoucher.DoesNotExist:
        logger.error("DGII: comprobante fiscal %s no encontrado", voucher_id)
        return {"estado": "error", "error": "Comprobante fiscal no encontrado."}

    config = voucher.config
    if config is None:
        message = "No hay configuración DGII asociada al comprobante."
        voucher.dgii_estado = "pendiente_config"
        voucher.dgii_respuesta = {"error": message}
        voucher.save(update_fields=["dgii_estado", "dgii_respuesta", "updated_at"])
        return {"estado": voucher.dgii_estado, "error": message}

    if not config.api_submission_url:
        message = "Configura la URL de recepción e-CF (api_submission_url) antes de enviar."
        voucher.dgii_estado = "pendiente_config"
        voucher.dgii_respuesta = {"error": message}
        voucher.save(update_fields=["dgii_estado", "dgii_respuesta", "updated_at"])
        return {"estado": voucher.dgii_estado, "error": message}

    try:
        http_request = build_requests_http_request()
    except RequestsNotAvailable:
        message = "La librería 'requests' no está instalada; no se envió el comprobante a la DGII."
        logger.warning("DGII: %s", message)
        voucher.dgii_respuesta = {"warning": message}
        voucher.save(update_fields=["dgii_respuesta", "updated_at"])
        return {"estado": voucher.dgii_estado, "error": message}

    http_client = DGIIHttpClient(http_request=http_request)
    service_client = DGIIVoucherService(http_client=http_client)

    try:
        line_items = list(voucher.lineas.all())
        xml_payload = build_fiscal_voucher_xml(voucher, line_items=line_items)
    except Exception as exc:
        message = f"Error construyendo XML DGII: {exc}"
        logger.exception("DGII: %s", message)
        voucher.dgii_estado = "error_xml"
        voucher.dgii_respuesta = {"error": str(exc)}
        voucher.save(update_fields=["dgii_estado", "dgii_respuesta", "updated_at"])
        return {"estado": voucher.dgii_estado, "error": str(exc)}

    try:
        response = service_client.send_xml(config=config, xml_payload=xml_payload)
    except DGIIVoucherServiceError as exc:
        message = str(exc)
        logger.exception("DGII: error enviando comprobante %s", voucher.pk)
        voucher.dgii_estado = "error_envio"
        voucher.dgii_respuesta = {"error": message}
        voucher.save(update_fields=["dgii_estado", "dgii_respuesta", "updated_at"])
        return {"estado": voucher.dgii_estado, "error": message}
    except Exception as exc:  # pragma: no cover - guard ante excepciones inesperadas
        message = f"Error inesperado al enviar comprobante a DGII: {exc}"
        logger.exception("DGII: %s", message)
        voucher.dgii_estado = "error_envio"
        voucher.dgii_respuesta = {"error": str(exc)}
        voucher.save(update_fields=["dgii_estado", "dgii_respuesta", "updated_at"])
        return {"estado": voucher.dgii_estado, "error": str(exc)}

    data = dict(response.data)
    track_id = data.get("trackId") or data.get("track_id") or ""
    estado = data.get("estado") or "enviado"

    voucher.dgii_track_id = track_id
    voucher.dgii_estado = estado
    voucher.dgii_respuesta = data
    voucher.dgii_enviado_at = timezone.now()
    voucher.save(update_fields=[
        "dgii_track_id",
        "dgii_estado",
        "dgii_respuesta",
        "dgii_enviado_at",
        "updated_at",
    ])

    result.update({
        "estado": estado,
        "track_id": track_id,
        "respuesta": data,
    })
    return result


@require_GET
def ventas_historial_api(request):
    queryset = (
        Venta.objects.select_related("cliente", "cuenta_credito")
        .prefetch_related("detalles__producto", "cuenta_credito__pagos")
        .order_by("-fecha")
    )

    search_term = (request.GET.get("query", "") or "").strip()
    start_date_str = request.GET.get("fecha_inicio", "").strip()
    end_date_str = request.GET.get("fecha_fin", "").strip()

    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    if start_date:
        queryset = queryset.filter(fecha__date__gte=start_date)

    if end_date:
        queryset = queryset.filter(fecha__date__lte=end_date)

    if search_term:
        search_filters = Q(cliente__nombre__icontains=search_term) | Q(
            cliente__documento__icontains=search_term
        ) | Q(detalles__producto__nombre__icontains=search_term)

        normalized = search_term.replace("fac-", "").replace("FAC-", "")
        if normalized.isdigit():
            search_filters |= Q(pk=int(normalized))

        queryset = queryset.filter(search_filters).distinct()

    results = []
    for venta in queryset:
        fecha_local = timezone.localtime(venta.fecha)
        detalles = []
        subtotal = Decimal("0")
        impuestos = Decimal("0")
        total_detalle = Decimal("0")

        for detalle in venta.detalles.all():
            precio_unitario = detalle.precio_unitario or Decimal("0")
            cantidad = Decimal(detalle.cantidad or 0)
            descuento = detalle.descuento or Decimal("0")

            base_amount = (precio_unitario * cantidad).quantize(TWO_PLACES)
            line_tax = (base_amount * TAX_RATE).quantize(TWO_PLACES)
            line_subtotal = (base_amount - descuento).quantize(TWO_PLACES)
            if line_subtotal < Decimal("0"):
                line_subtotal = Decimal("0")
            line_total = (line_subtotal + line_tax).quantize(TWO_PLACES)

            subtotal += line_subtotal
            impuestos += line_tax
            total_detalle += line_total

            detalles.append(
                {
                    "producto": str(detalle.producto) if detalle.producto else detalle.descripcion,
                    "cantidad": detalle.cantidad,
                    "precio": float(precio_unitario),
                    "subtotal": float(line_subtotal),
                    "subtotal_formatted": format_currency(line_subtotal),
                    "impuesto": float(line_tax),
                    "impuesto_formatted": format_currency(line_tax),
                    "total": float(line_total),
                    "total_formatted": format_currency(line_total),
                }
            )

        subtotal = subtotal.quantize(TWO_PLACES)
        impuestos = impuestos.quantize(TWO_PLACES)
        total_venta = subtotal + impuestos

        try:
            cuenta_credito = venta.cuenta_credito
        except CuentaCredito.DoesNotExist:
            cuenta_credito = None

        total_abonado = Decimal("0")
        saldo_pendiente = Decimal("0")
        progreso_cuotas = ""
        frecuencia_display = ""
        es_credito = cuenta_credito is not None
        
        if cuenta_credito:
            aggregated = cuenta_credito.pagos.aggregate(total=Sum("monto"))
            total_abonado = (aggregated.get("total") or Decimal("0")).quantize(TWO_PLACES)
            saldo_pendiente = cuenta_credito.saldo_pendiente.quantize(TWO_PLACES)
            progreso_cuotas = cuenta_credito.progreso_cuotas
            
            # Formatear frecuencia
            if cuenta_credito.frecuencia_dias == 7:
                frecuencia_display = "Semanal"
            elif cuenta_credito.frecuencia_dias == 15:
                frecuencia_display = "Quincenal"
            elif cuenta_credito.frecuencia_dias == 30:
                frecuencia_display = "Mensual"
            else:
                frecuencia_display = f"Cada {cuenta_credito.frecuencia_dias} días"

        total_abonado = total_abonado.quantize(TWO_PLACES)
        saldo_pendiente = saldo_pendiente.quantize(TWO_PLACES)

        results.append(
            {
                "id": venta.pk,
                "factura": f"FAC-{venta.pk:06d}",
                "cliente_nombre": venta.cliente.nombre,
                "cliente_documento": venta.cliente.documento,
                "proveedor_nombre": "",
                "fecha": fecha_local.date().isoformat(),
                "hora": fecha_local.strftime("%H:%M"),
                "fecha_formateada": fecha_local.strftime("%d/%m/%Y %I:%M %p"),
                "subtotal": format_currency(subtotal),
                "subtotal_num": float(subtotal),
                "impuestos": format_currency(impuestos),
                "impuestos_num": float(impuestos),
                "total": format_currency(total_venta),
                "total_num": float(total_venta),
                "total_abonado": format_currency(total_abonado) if total_abonado else format_currency(Decimal("0")),
                "total_abonado_num": float(total_abonado),
                "saldo_pendiente": format_currency(saldo_pendiente) if cuenta_credito else format_currency(Decimal("0")),
                "saldo_pendiente_num": float(saldo_pendiente),
                "cajero": venta.vendedor.get_full_name() if venta.vendedor else "-",
                "metodo_pago": venta.get_metodo_pago_display(),
                "es_credito": es_credito,
                "progreso_cuotas": progreso_cuotas,
                "frecuencia_display": frecuencia_display,
                "estado": cuenta_credito.estado if cuenta_credito else "completado",
                "vendedor": venta.vendedor.get_full_name() if venta.vendedor else "",
                "detalles": detalles,
            }
        )
    total_results = len(results)
    pagination = {
        "total": total_results,
        "page": 1,
        "page_count": 1,
        "start_index": 1 if total_results else 0,
        "end_index": total_results,
        "has_previous": False,
        "has_next": False,
    }
    return JsonResponse({"results": results, "pagination": pagination})


@require_GET
def report_credit_installments_api(request):
    """API para reporte de cuotas de crédito"""
    from datetime import datetime, timedelta
    from django.utils.dateparse import parse_date
    
    # Filtros
    start_date_str = request.GET.get("fecha_inicio", "").strip()
    end_date_str = request.GET.get("fecha_fin", "").strip()
    estado_filter = request.GET.get("estado", "").strip()
    
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None
    
    # Query base
    queryset = CuentaCredito.objects.select_related("venta", "cliente").prefetch_related("pagos")
    
    # Aplicar filtros de fecha
    if start_date:
        queryset = queryset.filter(venta__fecha__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(venta__fecha__date__lte=end_date)
    
    # Aplicar filtro de estado
    if estado_filter:
        queryset = queryset.filter(estado=estado_filter)
    
    # Obtener datos
    creditos_data = []
    total_creditos = 0
    total_pendiente = Decimal("0")
    cuotas_vencidas = 0
    proximos_vencimientos = 0
    
    now = timezone.now()
    
    for cuenta in queryset:
        data = serialize_credit_account(cuenta)
        creditos_data.append(data)
        
        total_creditos += 1
        total_pendiente += cuenta.saldo_pendiente
        
        # Calcular vencimientos (simplificado - basado en fecha de última cuota)
        if cuenta.estado == "pendiente":
            # Estimar próximo vencimiento basado en frecuencia
            dias_desde_venta = (now.date() - cuenta.venta.fecha.date()).days
            cuotas_esperadas = max(1, dias_desde_venta // cuenta.frecuencia_dias)
            
            if cuenta.cuotas_pagadas < cuotas_esperadas:
                cuotas_vencidas += 1
            elif cuenta.cuotas_pagadas == cuotas_esperadas and cuenta.numero_cuotas > cuenta.cuotas_pagadas:
                # Próximo vencimiento en los próximos 7 días
                dias_hasta_vencimiento = cuenta.frecuencia_dias - (dias_desde_venta % cuenta.frecuencia_dias)
                if dias_hasta_vencimiento <= 7:
                    proximos_vencimientos += 1
    
    # Resumen
    summary = {
        "total_creditos": total_creditos,
        "total_pendiente": float(total_pendiente),
        "total_pendiente_display": format_currency(total_pendiente),
        "cuotas_vencidas": cuotas_vencidas,
        "proximos_vencimientos": proximos_vencimientos,
    }
    
    return JsonResponse({
        "creditos": creditos_data,
        "summary": summary,
        "filters": {
            "fecha_inicio": start_date.isoformat() if start_date else "",
            "fecha_fin": end_date.isoformat() if end_date else "",
            "estado": estado_filter,
        }
    })


def get_filtered_sales_queryset(request):
    queryset = Venta.objects.prefetch_related("detalles__producto").order_by("-fecha")

    start_date_str = (request.GET.get("fecha_inicio") or "").strip()
    end_date_str = (request.GET.get("fecha_fin") or "").strip()

    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    if start_date and not end_date:
        end_date = start_date
    elif end_date and not start_date:
        start_date = end_date

    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    if start_date:
        queryset = queryset.filter(fecha__date__gte=start_date)

    if end_date:
        queryset = queryset.filter(fecha__date__lte=end_date)

    return queryset, start_date, end_date


def build_sales_report(queryset):
    total_sales = Decimal("0")
    total_cost = Decimal("0")
    report_rows: list[dict[str, object]] = []

    for venta in queryset:
        sale_subtotal = Decimal("0")
        sale_tax = Decimal("0")
        sale_total = Decimal("0")
        sale_cost = Decimal("0")

        for detalle in venta.detalles.all():
            precio_unitario = detalle.precio_unitario or Decimal("0")
            cantidad = Decimal(detalle.cantidad or 0)
            descuento = detalle.descuento or Decimal("0")

            base_amount = (precio_unitario * cantidad).quantize(TWO_PLACES)
            line_discount = descuento.quantize(TWO_PLACES)
            line_subtotal = (base_amount - line_discount).quantize(TWO_PLACES)
            if line_subtotal < Decimal("0"):
                line_subtotal = Decimal("0.00")
            line_tax = (line_subtotal * TAX_RATE).quantize(TWO_PLACES)
            line_total = (line_subtotal + line_tax).quantize(TWO_PLACES)
            total_sales += line_total

            costo_unitario = getattr(detalle.producto, "precio_compra", None)
            if costo_unitario is None:
                costo_unitario = Decimal("0")
            line_cost = (Decimal(costo_unitario) * cantidad).quantize(TWO_PLACES)
            total_cost += line_cost

            sale_subtotal += line_subtotal
            sale_tax += line_tax
            sale_total += line_total
            sale_cost += line_cost

        fecha_local = timezone.localtime(venta.fecha)
        sale_subtotal = sale_subtotal.quantize(TWO_PLACES)
        sale_tax = sale_tax.quantize(TWO_PLACES)
        sale_total = sale_total.quantize(TWO_PLACES)
        sale_cost = sale_cost.quantize(TWO_PLACES)
        sale_profit = (sale_total - sale_cost).quantize(TWO_PLACES)

        factura_codigo = getattr(venta, "get_codigo_factura", None)
        if callable(factura_codigo):
            factura_display = factura_codigo()
        else:
            factura_display = f"FAC-{venta.pk:06d}"

        report_rows.append(
            {
                "id": venta.pk,
                "factura": factura_display,
                "cliente": venta.cliente.nombre,
                "fecha": fecha_local.isoformat(),
                "fecha_display": fecha_local.strftime("%d/%m/%Y %H:%M"),
                "subtotal": float(sale_subtotal),
                "subtotal_display": format_currency(sale_subtotal),
                "itbis": float(sale_tax),
                "itbis_display": format_currency(sale_tax),
                "total": float(sale_total),
                "total_display": format_currency(sale_total),
                "costo": float(sale_cost),
                "costo_display": format_currency(sale_cost),
                "ganancia": float(sale_profit),
                "ganancia_display": format_currency(sale_profit),
                "metodo_pago": venta.get_metodo_pago_display(),
            }
        )

    total_sales = total_sales.quantize(TWO_PLACES)
    total_cost = total_cost.quantize(TWO_PLACES)
    ventas_count = len(report_rows)

    return total_sales, total_cost, report_rows, ventas_count


@require_GET
def report_total_sales_api(request):
    queryset, start_date, end_date = get_filtered_sales_queryset(request)
    total_sales, total_cost, report_rows, ventas_count = build_sales_report(queryset)
    total_profit = (total_sales - total_cost).quantize(TWO_PLACES)

    return JsonResponse(
        {
            "total_sales": float(total_sales),
            "total_sales_display": format_currency(total_sales),
            "total_cost": float(total_cost),
            "total_cost_display": format_currency(total_cost),
            "total_profit": float(total_profit),
            "total_profit_display": format_currency(total_profit),
            "filters": {
                "fecha_inicio": start_date.isoformat() if start_date else "",
                "fecha_fin": end_date.isoformat() if end_date else "",
            },
            "ventas": ventas_count,
            "ventas_display": ventas_count,
            "rows": report_rows,
        }
    )


@require_GET
def report_profit_api(request):
    queryset, start_date, end_date = get_filtered_sales_queryset(request)
    total_sales, total_cost, report_rows, ventas_count = build_sales_report(queryset)
    total_profit = (total_sales - total_cost).quantize(TWO_PLACES)

    profit_rows = []
    for row in report_rows:
        profit_rows.append(
            {
                "factura": row["factura"],
                "fecha_display": row["fecha_display"],
                "total_display": row["total_display"],
                "costo_display": row["costo_display"],
                "ganancia_display": row["ganancia_display"],
            }
        )

    return JsonResponse(
        {
            "total_sales": float(total_sales),
            "total_sales_display": format_currency(total_sales),
            "total_cost": float(total_cost),
            "total_cost_display": format_currency(total_cost),
            "total_profit": float(total_profit),
            "total_profit_display": format_currency(total_profit),
            "filters": {
                "fecha_inicio": start_date.isoformat() if start_date else "",
                "fecha_fin": end_date.isoformat() if end_date else "",
            },
            "ventas": ventas_count,
            "ventas_display": ventas_count,
            "rows": profit_rows,
        }
    )


@require_POST
@csrf_exempt
def registrar_venta_api(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Solicitud inválida"}, status=400)

    cliente_id = payload.get("cliente_id")
    productos = payload.get("productos", [])
    if not cliente_id or not productos:
        return JsonResponse({"error": "Datos incompletos para registrar la venta"}, status=400)

    cliente = get_object_or_404(Cliente, pk=cliente_id)
    vendedor = None
    vendedor_id = payload.get("vendedor_id")
    if vendedor_id:
        vendedor = get_object_or_404(settings.AUTH_USER_MODEL, pk=vendedor_id)

    metodo_pago = payload.get("metodo_pago") or Venta.MetodoPago.EFECTIVO
    notas = payload.get("notas", "").strip()

    fiscal_voucher = None
    fiscal_voucher_id = None

    with transaction.atomic():
        cash_session = (
            CashSession.objects.select_for_update()
            .filter(estado=CashSession.Estado.ABIERTA)
            .order_by("-apertura_at")
            .first()
        )
        if cash_session is None:
            transaction.set_rollback(True)
            return JsonResponse({"error": "No hay una sesión de caja abierta."}, status=400)

        venta = Venta.objects.create(
            cliente=cliente,
            vendedor=vendedor,
            metodo_pago=metodo_pago,
            notas=notas,
            sesion_caja=cash_session,
        )

        subtotal_bruto = Decimal("0")
        line_items = []

        for item in productos:
            producto_id = item.get("producto_id")
            try:
                cantidad = int(item.get("cantidad", 0))
            except (TypeError, ValueError):
                cantidad = 0

            if not producto_id or cantidad <= 0:
                transaction.set_rollback(True)
                return JsonResponse({"error": "Información de producto incompleta"}, status=400)

            producto = get_object_or_404(Producto, pk=producto_id)

            updated = Producto.objects.filter(pk=producto.pk, stock__gte=cantidad).update(
                stock=F("stock") - cantidad
            )
            if updated == 0:
                transaction.set_rollback(True)
                return JsonResponse(
                    {"error": f"El producto {producto} no tiene stock suficiente."},
                    status=400,
                )
            producto.refresh_from_db(fields=["stock"])

            precio = item.get("precio")
            try:
                precio_decimal = Decimal(str(precio)) if precio is not None else producto.precio_venta
            except (InvalidOperation, TypeError, ValueError):
                precio_decimal = producto.precio_venta

            descuento = item.get("descuento", 0)
            try:
                descuento_decimal = Decimal(str(descuento)) if descuento is not None else Decimal("0")
            except (InvalidOperation, TypeError, ValueError):
                descuento_decimal = Decimal("0")

            if descuento_decimal < Decimal("0"):
                descuento_decimal = Decimal("0")

            line_base = (precio_decimal * cantidad).quantize(TWO_PLACES)
            max_line_discount = line_base
            if descuento_decimal > max_line_discount:
                descuento_decimal = max_line_discount

            subtotal_bruto += line_base

            detalle = DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio_decimal,
                descuento=descuento_decimal,
            )

            line_items.append(
                {
                    "detalle": detalle,
                    "base": line_base,
                    "descuento": descuento_decimal,
                }
            )

        subtotal_bruto = subtotal_bruto.quantize(TWO_PLACES)

        descuento_global = payload.get("descuento", 0)
        try:
            descuento_global = Decimal(str(descuento_global)).quantize(TWO_PLACES)
        except (InvalidOperation, TypeError, ValueError):
            descuento_global = Decimal("0")

        if descuento_global < Decimal("0"):
            descuento_global = Decimal("0")

        descuento_existente = sum((item["descuento"] for item in line_items), Decimal("0")).quantize(TWO_PLACES)
        descuento_disponible = max(subtotal_bruto - descuento_existente, Decimal("0"))
        descuento_a_aplicar = min(descuento_global, descuento_disponible)

        if descuento_a_aplicar > Decimal("0") and line_items:
            total_base_distribuible = sum((item["base"] for item in line_items if item["base"] > 0), Decimal("0"))
            if total_base_distribuible > Decimal("0"):
                restante = descuento_a_aplicar
                distribuibles = [item for item in line_items if item["base"] > 0]
                last_index = len(distribuibles) - 1

                for index, item in enumerate(distribuibles):
                    if index == last_index:
                        cuota = restante
                    else:
                        cuota = (descuento_a_aplicar * item["base"] / total_base_distribuible).quantize(TWO_PLACES)
                        if cuota > restante:
                            cuota = restante
                    if cuota <= Decimal("0"):
                        continue
                    item["descuento"] = (item["descuento"] + cuota).quantize(TWO_PLACES)
                    restante -= cuota
                    DetalleVenta.objects.filter(pk=item["detalle"].pk).update(descuento=item["descuento"])
                if restante > Decimal("0") and distribuibles:
                    item = distribuibles[-1]
                    item["descuento"] = (item["descuento"] + restante).quantize(TWO_PLACES)
                    DetalleVenta.objects.filter(pk=item["detalle"].pk).update(descuento=item["descuento"])

        total_descuento = sum((item["descuento"] for item in line_items), Decimal("0")).quantize(TWO_PLACES)

    subtotal_neto = (subtotal_bruto - total_descuento).quantize(TWO_PLACES)
    if subtotal_neto < Decimal("0"):
        subtotal_neto = Decimal("0")

    impuestos = (subtotal_neto * TAX_RATE).quantize(TWO_PLACES)

    total_venta = (subtotal_neto + impuestos).quantize(TWO_PLACES)

    total_pagado = payload.get("total_pagado", 0)
    try:
        total_pagado_decimal = Decimal(str(total_pagado)).quantize(TWO_PLACES)
    except (InvalidOperation, TypeError, ValueError):
        total_pagado_decimal = Decimal("0")
    if total_pagado_decimal < Decimal("0"):
        total_pagado_decimal = Decimal("0")

    cash_session.total_ventas = (cash_session.total_ventas + total_venta).quantize(TWO_PLACES)
    cash_session.total_impuesto = (cash_session.total_impuesto + impuestos).quantize(TWO_PLACES)
    cash_session.total_descuento = (cash_session.total_descuento + total_descuento).quantize(TWO_PLACES)
    if metodo_pago == Venta.MetodoPago.CREDITO:
        cash_session.total_ventas_credito = (cash_session.total_ventas_credito + total_venta).quantize(TWO_PLACES)
    else:
        efectivo_incremento = total_pagado_decimal if metodo_pago == Venta.MetodoPago.EFECTIVO else Decimal("0")
        cash_session.total_en_caja = (cash_session.total_en_caja + efectivo_incremento).quantize(TWO_PLACES)

    cash_session.save(update_fields=[
        "total_ventas",
        "total_impuesto",
        "total_descuento",
        "total_ventas_credito",
        "total_en_caja",
        "updated_at",
    ])

    venta.refresh_from_db()

    cuenta = None
    totals_credit = calculate_credit_totals(venta)

    if metodo_pago == Venta.MetodoPago.CREDITO:
        total_credito = totals_credit["total"]
        
        # Obtener configuración de cuotas del payload
        credito_config = payload.get("credito_config", {})
        numero_cuotas = credito_config.get("numero_cuotas", 1)
        frecuencia_dias = credito_config.get("frecuencia_dias", 30)
        abono_inicial = Decimal(str(credito_config.get("abono_inicial", 0))).quantize(TWO_PLACES)
        monto_cuota = Decimal(str(credito_config.get("monto_cuota", 0))).quantize(TWO_PLACES)
        
        cuenta, _ = CuentaCredito.objects.get_or_create(
            venta=venta,
            defaults={
                "cliente": cliente,
                "total_credito": total_credito,
                "saldo_pendiente": total_credito,
                "estado": "pendiente",
                "numero_cuotas": numero_cuotas,
                "frecuencia_dias": frecuencia_dias,
                "abono_inicial": abono_inicial,
                "monto_cuota": monto_cuota,
            },
        )
        if cuenta.total_credito != total_credito:
            total_abonado = sum(
                pago.monto.quantize(TWO_PLACES) for pago in cuenta.pagos.all()
            )
            saldo_recalculado = (total_credito - total_abonado).quantize(TWO_PLACES)
            if saldo_recalculado < Decimal("0"):
                saldo_recalculado = Decimal("0.00")
            nuevos_campos = {
                "total_credito": total_credito,
                "saldo_pendiente": saldo_recalculado,
                "estado": "pagado" if saldo_recalculado == Decimal("0.00") else "pendiente",
            }
            for field, value in nuevos_campos.items():
                setattr(cuenta, field, value)
            cuenta.save(update_fields=["total_credito", "saldo_pendiente", "estado", "updated_at"])

        if total_pagado_decimal > Decimal("0"):
            abono = min(total_pagado_decimal, cuenta.saldo_pendiente)
            if abono > Decimal("0"):
                cuenta.registrar_pago(abono)
                PagoCredito.objects.create(
                    cuenta=cuenta,
                    monto=abono,
                    registrado_por=request.user if request.user.is_authenticated else None,
                    comentario="Abono inicial al registrar la venta",
                )
                cuenta.refresh_from_db()

    try:
        fiscal_voucher = _create_fiscal_voucher(
            venta=venta,
            fiscal_data=payload.get("fiscal"),
            subtotal=subtotal_neto,
            impuestos=impuestos,
            total=total_venta,
            monto_pagado=total_pagado_decimal,
            metodo_pago=metodo_pago,
            line_items=line_items,
        )
        if fiscal_voucher:
            fiscal_voucher_id = fiscal_voucher.pk
    except ValueError as exc:
        transaction.set_rollback(True)
        return JsonResponse({"error": str(exc)}, status=400)

    fecha_local = timezone.localtime(venta.fecha)

    dgii_result: dict[str, object] = {}
    if fiscal_voucher and fiscal_voucher_id:
        dgii_result = _send_fiscal_voucher_to_dgii(fiscal_voucher_id)
        fiscal_voucher.refresh_from_db()

    data = {
        "id": venta.pk,
        "factura": f"FAC-{venta.pk:06d}",
        "cliente": venta.cliente.nombre,
        "total": float(venta.total),
        "subtotal_bruto": float(subtotal_bruto),
        "descuento_total": float(total_descuento),
        "impuestos": float(impuestos),
        "total_pagado": float(total_pagado_decimal),
        "fecha": fecha_local.strftime("%Y-%m-%d"),
        "hora": fecha_local.strftime("%H:%M"),
        "cajero": venta.vendedor.get_full_name() if venta.vendedor else "-",
        "metodo_pago": venta.get_metodo_pago_display(),
    }

    if cuenta:
        data["credito"] = {
            "cuenta_id": cuenta.pk,
            "total_credito": float(cuenta.total_credito),
            "saldo_pendiente": float(cuenta.saldo_pendiente),
            "estado": cuenta.estado,
        }

    if total_pagado_decimal > Decimal("0"):
        data["total_pagado_registrado"] = float(total_pagado_decimal)

    if fiscal_voucher:
        data["comprobante_fiscal"] = {
            "numero": fiscal_voucher.numero_completo,
            "tipo": fiscal_voucher.tipo,
            "serie": fiscal_voucher.serie,
            "secuencia": fiscal_voucher.secuencia,
            "total": float(fiscal_voucher.total.quantize(TWO_PLACES)),
            "subtotal": float(fiscal_voucher.subtotal.quantize(TWO_PLACES)),
            "itbis": float(fiscal_voucher.itbis.quantize(TWO_PLACES)),
            "dgii": {
                "estado": fiscal_voucher.dgii_estado,
                "track_id": fiscal_voucher.dgii_track_id or None,
                "enviado_at": fiscal_voucher.dgii_enviado_at.isoformat() if fiscal_voucher.dgii_enviado_at else None,
                "respuesta": fiscal_voucher.dgii_respuesta,
            },
        }
        if dgii_result.get("error"):
            data["comprobante_fiscal"]["dgii"]["error"] = dgii_result["error"]

    return JsonResponse(data)
