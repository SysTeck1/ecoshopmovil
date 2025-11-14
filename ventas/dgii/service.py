"""Orchestrator service for DGII interactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db import transaction

from .client import DGIIClientError, DGIIHttpClient, DGIIClientResponse
from .signer import DGIIXMLSigner, DGIISignerError
from ventas.models import FiscalVoucherConfig


class DGIIVoucherServiceError(RuntimeError):
    """High level error while interacting with DGII services."""


@dataclass(slots=True)
class DGIIServiceContext:
    config: FiscalVoucherConfig
    signer: DGIIXMLSigner
    http_client: DGIIHttpClient


class DGIIVoucherService:
    """Combine config, signer and HTTP client for fiscal workflows."""

    def __init__(
        self,
        *,
        http_client: Optional[DGIIHttpClient] = None,
        signer: Optional[DGIIXMLSigner] = None,
    ) -> None:
        self._http_client = http_client or DGIIHttpClient()
        self._signer = signer or DGIIXMLSigner()

    @transaction.atomic
    def send_xml(
        self,
        *,
        config: FiscalVoucherConfig,
        xml_payload: str,
        submission_url: Optional[str] = None,
    ) -> DGIIClientResponse:
        if not submission_url:
            submission_url = config.api_submission_url
        if not submission_url:
            raise DGIIVoucherServiceError("Config DGII incompleta: falta api_submission_url")

        try:
            signed_xml = self._signer.sign_xml(xml_payload)
        except DGIISignerError as exc:
            raise DGIIVoucherServiceError(str(exc)) from exc

        payload = {"xml": signed_xml}

        try:
            response = self._http_client.post_json(
                config=config,
                url=submission_url,
                payload=payload,
            )
        except DGIIClientError as exc:
            raise DGIIVoucherServiceError(str(exc)) from exc

        return response


def get_active_config() -> Optional[FiscalVoucherConfig]:
    return FiscalVoucherConfig.objects.first()


__all__ = [
    "DGIIVoucherService",
    "DGIIVoucherServiceError",
    "DGIIServiceContext",
    "get_active_config",
]
