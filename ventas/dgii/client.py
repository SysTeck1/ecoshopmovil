"""DGII base HTTP client orchestration (stub)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, MutableMapping, Optional

from django.utils import timezone

from .auth import DGIIAuthClient, DGIIAuthError, DGIIAuthTokens
from ventas.models import FiscalVoucherConfig

HttpJsonRequest = Callable[[str, str, Mapping[str, str], Optional[Mapping[str, Any]]], Mapping[str, Any]]


class DGIIClientError(RuntimeError):
    """Raised when the DGII HTTP client cannot execute the request."""


@dataclass
class DGIIClientResponse:
    """Very small container for DGII API responses."""

    data: MutableMapping[str, Any] = field(default_factory=dict)
    status_code: int = 200


class DGIIHttpClient:
    """Combine authentication + HTTP requests for DGII endpoints."""

    def __init__(
        self,
        *,
        http_request: Optional[HttpJsonRequest] = None,
        auth_client: Optional[DGIIAuthClient] = None,
        clock_skew_margin: int = 30,
    ) -> None:
        self._http_request = http_request
        self._clock_skew_margin = int(clock_skew_margin)
        self._tokens: Optional[DGIIAuthTokens] = None

        if auth_client is not None:
            self._auth_client = auth_client
        elif http_request is not None:
            self._auth_client = DGIIAuthClient(http_post=self._http_post_from_request())
        else:
            self._auth_client = DGIIAuthClient()

    def _http_post_from_request(self) -> Callable[[str, Mapping[str, Any]], Mapping[str, Any]]:
        def http_post(url: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
            if self._http_request is None:
                raise DGIIClientError("No se configuró http_request para ejecutar peticiones")
            headers = {"Content-Type": "application/json"}
            return self._http_request("POST", url, headers, payload)

        return http_post

    # Token helpers -----------------------------------------------------------------

    def _token_expired(self) -> bool:
        if self._tokens is None:
            return True
        margin = dt.timedelta(seconds=self._clock_skew_margin)
        return timezone.now() + margin >= self._tokens.expires_at

    def _ensure_token(self, config: FiscalVoucherConfig) -> DGIIAuthTokens:
        if self._token_expired():
            self._tokens = self._auth_client.obtain_token(config)
        return self._tokens

    # Public API --------------------------------------------------------------------

    def post_json(
        self,
        *,
        config: FiscalVoucherConfig,
        url: str,
        payload: Optional[Mapping[str, Any]] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> DGIIClientResponse:
        """Execute a POST request with JSON payload and bearer token."""

        if not self._http_request:
            raise DGIIClientError(
                "No se configuró http_request; inyecta un callable para realizar la petición"
            )

        token = self._ensure_token(config)
        headers = {
            "Authorization": f"{token.token_type} {token.access_token}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        try:
            data = self._http_request("POST", url, headers, payload)
        except DGIIAuthError as exc:
            raise DGIIClientError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - guard rails for runtime errors
            raise DGIIClientError(f"Error ejecutando petición DGII: {exc}") from exc

        response = DGIIClientResponse(data=dict(data), status_code=int(data.get("status", 200)))
        return response


__all__ = ["DGIIHttpClient", "DGIIClientError", "DGIIClientResponse"]
