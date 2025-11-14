"""XML builder for DGII e-CF documents."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable
from xml.etree import ElementTree as ET

from django.utils import timezone

from ventas.models import FiscalVoucher, FiscalVoucherLine, FiscalVoucherConfig

NUMBER_FORMAT = Decimal("0.01")


def _format_decimal(value: Decimal | float | int | None) -> str:
    if value is None:
        value = Decimal("0")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return f"{value.quantize(NUMBER_FORMAT):.2f}"


def _add_text(parent: ET.Element, tag: str, text: str | None) -> ET.Element:
    elem = ET.SubElement(parent, tag)
    elem.text = text or ""
    return elem


def build_fiscal_voucher_xml(
    voucher: FiscalVoucher,
    *,
    line_items: Iterable[FiscalVoucherLine] | None = None,
    include_declaration: bool = True,
) -> str:
    """Return an XML representation of the fiscal voucher following DGII layout."""

    config: FiscalVoucherConfig | None = voucher.config
    if config is None:
        raise ValueError("El comprobante fiscal no tiene configuración asociada")

    if line_items is None:
        line_items = voucher.lineas.all()

    root = ET.Element("ECF")
    header = ET.SubElement(root, "Encabezado")
    _add_text(header, "Version", "1.0")
    _add_text(header, "RNCEmisor", config.rnc)
    _add_text(header, "RazonSocialEmisor", config.nombre_contribuyente)
    _add_text(header, "TipoECF", voucher.tipo)
    _add_text(header, "NumeroECF", voucher.numero_completo)
    _add_text(header, "FechaEmision", voucher.fecha_emision.isoformat())
    _add_text(header, "FechaVencimiento", voucher.fecha_vencimiento.isoformat() if voucher.fecha_vencimiento else "")
    _add_text(header, "RNCComprador", voucher.cliente_documento or (voucher.venta.cliente.documento if voucher.venta and voucher.venta.cliente else ""))
    _add_text(header, "NombreComprador", voucher.cliente_nombre or (voucher.venta.cliente.nombre if voucher.venta and voucher.venta.cliente else ""))
    _add_text(header, "TelefonoComprador", voucher.telefono_contacto)
    _add_text(header, "CorreoComprador", voucher.correo_envio)

    detalle_container = ET.SubElement(root, "Detalles")
    for index, linea in enumerate(line_items, start=1):
        detalle = ET.SubElement(detalle_container, "Detalle")
        _add_text(detalle, "NoLinea", str(index))
        _add_text(detalle, "Descripcion", linea.descripcion)
        _add_text(detalle, "Cantidad", _format_decimal(linea.cantidad))
        _add_text(detalle, "PrecioUnitario", _format_decimal(linea.precio_unitario))
        _add_text(detalle, "Subtotal", _format_decimal(linea.subtotal))
        _add_text(detalle, "Impuesto", _format_decimal(linea.impuesto))
        _add_text(detalle, "Total", _format_decimal(linea.total))

    totales = ET.SubElement(root, "Totales")
    _add_text(totales, "Subtotal", _format_decimal(voucher.subtotal))
    _add_text(totales, "ITBIS", _format_decimal(voucher.itbis))
    _add_text(totales, "OtrosImpuestos", _format_decimal(voucher.otros_impuestos))
    _add_text(totales, "Total", _format_decimal(voucher.total))
    _add_text(totales, "MontoPagado", _format_decimal(voucher.monto_pagado))

    pagos = ET.SubElement(root, "Pagos")
    _add_text(pagos, "MetodoPago", voucher.metodo_pago)
    _add_text(pagos, "Monto", _format_decimal(voucher.monto_pagado))

    meta = ET.SubElement(root, "Meta")
    _add_text(meta, "GeneradoEn", timezone.now().isoformat())
    if voucher.notas:
        _add_text(meta, "Notas", voucher.notas)

    xml_bytes = ET.tostring(root, encoding="utf-8")
    if include_declaration:
        return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" + xml_bytes.decode("utf-8")
    return xml_bytes.decode("utf-8")


__all__ = ["build_fiscal_voucher_xml"]
