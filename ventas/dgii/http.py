"""HTTP adapters for DGII integrations."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

try:  # pragma: no cover - requests is optional until installed
    import requests
    from requests import Session
except Exception:  # pragma: no cover - fallback declarations
    requests = None  # type: ignore
    Session = object  # type: ignore

HttpJsonRequest = Callable[[str, str, Mapping[str, str], Optional[Mapping[str, Any]]], Mapping[str, Any]]


class RequestsNotAvailable(RuntimeError):
    """Raised when the requests library is missing."""


def build_requests_http_request(session: Optional[Session] = None, timeout: float = 15.0) -> HttpJsonRequest:
    """Return an HttpJsonRequest callable backed by requests."""

    if requests is None:  # pragma: no cover - executed only when library missing
        raise RequestsNotAvailable("La librería 'requests' es requerida para esta integración")

    sess = session or requests.Session()
    default_timeout = timeout

    def http_request(
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        response = sess.request(
            method=method,
            url=url,
            json=body,
            headers=dict(headers),
            timeout=default_timeout,
        )
        response.raise_for_status()
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - guard for non-json
            raise RuntimeError("La respuesta DGII no es JSON válido") from exc

    return http_request


__all__ = ["build_requests_http_request", "HttpJsonRequest", "RequestsNotAvailable"]
