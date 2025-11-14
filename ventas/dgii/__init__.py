"""DGII integration helpers for fiscal vouchers."""

from .auth import (
    DGIIAuthClient,
    DGIIAuthError,
    DGIIAuthRequest,
    DGIIAuthTokens,
    build_auth_payload,
)
from .client import DGIIClientError, DGIIClientResponse, DGIIHttpClient
from .http import HttpJsonRequest, RequestsNotAvailable, build_requests_http_request
from .secrets import (
    CertificateSecrets,
    DGIISecretsError,
    DGIISecretsNotConfigured,
    EncryptionBackendMissing,
    get_certificate_alias,
    get_certificate_bytes,
    get_certificate_password,
    get_certificate_secrets,
    refresh_cached_secrets,
)
from .signer import (
    CertificateBundle,
    DGIISignerError,
    DGIIXMLSigner,
    load_certificate_bundle,
)
from .service import (
    DGIIVoucherService,
    DGIIVoucherServiceError,
    DGIIServiceContext,
    get_active_config,
)
from .xml_builder import build_fiscal_voucher_xml

__all__ = [
    "DGIIAuthClient",
    "DGIIAuthError",
    "DGIIAuthRequest",
    "DGIIAuthTokens",
    "build_auth_payload",
    "DGIIClientError",
    "DGIIClientResponse",
    "DGIIHttpClient",
    "HttpJsonRequest",
    "RequestsNotAvailable",
    "build_requests_http_request",
    "CertificateSecrets",
    "DGIISecretsError",
    "DGIISecretsNotConfigured",
    "EncryptionBackendMissing",
    "get_certificate_alias",
    "get_certificate_bytes",
    "get_certificate_password",
    "get_certificate_secrets",
    "refresh_cached_secrets",
    "CertificateBundle",
    "DGIISignerError",
    "DGIIXMLSigner",
    "load_certificate_bundle",
    "DGIIVoucherService",
    "DGIIVoucherServiceError",
    "DGIIServiceContext",
    "get_active_config",
    "build_fiscal_voucher_xml",
]
