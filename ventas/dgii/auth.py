"""HTTP authentication helpers for DGII e-CF services."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, MutableMapping, Optional

from django.utils import timezone

from ventas.models import FiscalVoucherConfig

AuthPayloadBuilder = Callable[[FiscalVoucherConfig], Mapping[str, Any]]
HttpPost = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]


class DGIIAuthError(RuntimeError):
    """Raised when the DGII authentication flow cannot continue."""


@dataclass(frozen=True)
class DGIIAuthRequest:
    """Minimal request payload definition for token retrieval."""

    url: str
    payload: Mapping[str, Any]


@dataclass
class DGIIAuthTokens:
    """Identity tokens returned by the DGII OAuth endpoints."""

    access_token: str
    expires_at: dt.datetime
    token_type: str = "Bearer"
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    raw: MutableMapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_response(cls, data: Mapping[str, Any]) -> "DGIIAuthTokens":
        access_token = data.get("access_token")
        if not access_token:
            raise DGIIAuthError("La respuesta DGII no incluye access_token")

        expires_in = data.get("expires_in") or data.get("expires")
        if expires_in is None:
            raise DGIIAuthError("La respuesta DGII no incluye expires_in")

        try:
            expires_seconds = int(expires_in)
        except (TypeError, ValueError) as exc:
            raise DGIIAuthError("Valor inválido para expires_in") from exc

        expires_at = timezone.now() + dt.timedelta(seconds=expires_seconds)

        return cls(
            access_token=str(access_token),
            token_type=str(data.get("token_type") or "Bearer"),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
            expires_at=expires_at,
            raw=dict(data),
        )


def build_auth_payload(config: FiscalVoucherConfig) -> Mapping[str, Any]:
    """Return the default client credentials payload for DGII."""

    if not config.api_client_id or not config.api_client_secret:
        raise DGIIAuthError("Config DGII incompleta: requiere client_id y client_secret")

    return {
        "client_id": config.api_client_id,
        "client_secret": config.api_client_secret,
        "grant_type": "client_credentials",
        "scope": "facturacion-electronica",
    }


class DGIIAuthClient:
    """Thin wrapper around an HTTP client to obtain DGII tokens."""

    def __init__(
        self,
        *,
        http_post: Optional[HttpPost] = None,
        payload_builder: AuthPayloadBuilder = build_auth_payload,
    ) -> None:
        self._http_post = http_post
        self._payload_builder = payload_builder

    def build_request(self, config: FiscalVoucherConfig) -> DGIIAuthRequest:
        if not config.api_auth_url:
            raise DGIIAuthError("Config DGII incompleta: falta api_auth_url")

        payload = self._payload_builder(config)
        return DGIIAuthRequest(url=config.api_auth_url, payload=payload)

    def obtain_token(self, config: FiscalVoucherConfig) -> DGIIAuthTokens:
        """Execute HTTP request to fetch tokens (stub)."""

        if self._http_post is None:
            raise DGIIAuthError(
                "No se configuró http_post; inyecta un cliente HTTP para realizar la petición"
            )

        request = self.build_request(config)
        response_data = self._http_post(request.url, request.payload)
        return DGIIAuthTokens.from_response(response_data)


__all__ = [
    "DGIIAuthClient",
    "DGIIAuthError",
    "DGIIAuthRequest",
    "DGIIAuthTokens",
    "build_auth_payload",
]
