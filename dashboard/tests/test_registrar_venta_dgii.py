"""Tests for registrar_venta_api DGII integration."""

from __future__ import annotations

import json
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ventas.models import (
    CashSession,
    Cliente,
    DetalleVenta,
    FiscalVoucher,
    FiscalVoucherConfig,
    Producto,
)


class RegistrarVentaDGIIIntegrationTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.cliente = Cliente.objects.create(
            nombre="Cliente Demo",
            documento="401000000",
            correo="cliente@example.com",
            telefono="8095550000",
        )
        self.producto = Producto.objects.create(
            nombre="Producto Demo",
            precio_compra=Decimal("50.00"),
            precio_venta=Decimal("100.00"),
            stock=10,
        )
        CashSession.objects.create(
            estado=CashSession.Estado.ABIERTA,
            monto_inicial=Decimal("100.00"),
            total_en_caja=Decimal("100.00"),
            total_ventas=Decimal("0.00"),
            total_impuesto=Decimal("0.00"),
            total_descuento=Decimal("0.00"),
            total_ventas_credito=Decimal("0.00"),
        )
        self.config = FiscalVoucherConfig.objects.create(
            nombre_contribuyente="Empresa Demo",
            rnc="131231231",
            tipo_por_defecto=FiscalVoucherConfig.VoucherType.B01,
            serie_por_defecto="B0101",
            api_submission_url="https://dgii.test/submit",
        )
        self.endpoint = reverse("dashboard:registrar_venta_api")

    def _build_payload(self, include_fiscal: bool = True) -> dict:
        payload = {
            "cliente_id": self.cliente.pk,
            "productos": [
                {
                    "producto_id": self.producto.pk,
                    "cantidad": 1,
                    "precio": "100.00",
                }
            ],
            "metodo_pago": "efectivo",
            "total_pagado": "100.00",
        }
        if include_fiscal:
            payload["fiscal"] = {
                "config_id": self.config.pk,
                "tipo": self.config.tipo_por_defecto,
                "serie": self.config.serie_por_defecto,
                "cliente_nombre": self.cliente.nombre,
                "cliente_documento": self.cliente.documento,
                "correo_envio": self.cliente.correo,
                "telefono_contacto": self.cliente.telefono,
            }
        return payload

    def test_calls_dgii_sender_when_fiscal_payload_present(self) -> None:
        def fake_sender(voucher_id: int) -> dict[str, object]:
            voucher = FiscalVoucher.objects.get(pk=voucher_id)
            voucher.dgii_estado = "enviado"
            voucher.dgii_track_id = "track-123"
            voucher.dgii_enviado_at = timezone.now()
            voucher.dgii_respuesta = {"trackId": "track-123"}
            voucher.save(update_fields=[
                "dgii_estado",
                "dgii_track_id",
                "dgii_enviado_at",
                "dgii_respuesta",
                "updated_at",
            ])
            return {"estado": "enviado", "track_id": "track-123"}

        with mock.patch("dashboard.views._send_fiscal_voucher_to_dgii", side_effect=fake_sender) as sender_mock:
            response = self.client.post(
                self.endpoint,
                data=json.dumps(self._build_payload()),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        sender_mock.assert_called_once()
        data = response.json()
        fiscal_info = data.get("comprobante_fiscal", {}).get("dgii", {})
        self.assertEqual(fiscal_info.get("track_id"), "track-123")
        self.assertEqual(fiscal_info.get("estado"), "enviado")

    def test_response_includes_dgii_error_when_sender_returns_error(self) -> None:
        with mock.patch("dashboard.views._send_fiscal_voucher_to_dgii", return_value={"error": "DGII down"}) as sender_mock:
            response = self.client.post(
                self.endpoint,
                data=json.dumps(self._build_payload()),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        sender_mock.assert_called_once()
        data = response.json()
        dgii_info = data.get("comprobante_fiscal", {}).get("dgii", {})
        self.assertEqual(dgii_info.get("error"), "DGII down")

        # Ensure voucher still exists and no duplicate detalles are present
        self.assertEqual(FiscalVoucher.objects.count(), 1)
        self.assertEqual(DetalleVenta.objects.count(), 1)
