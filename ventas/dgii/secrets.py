"""Secure helpers to load DGII certificates and secrets.

This module provides a pluggable mechanism to load and decrypt the
DGII signing certificate and password. The default backend expects the
file to be stored encrypted on disk and uses a symmetric key provided
via environment variables to decrypt it when required.

All operations are done lazily and cached in memory to avoid repeated
I/O and decryption costs.
"""

from __future__ import annotations

import base64
import functools
import os
from dataclasses import dataclass
from typing import Callable, Optional

from django.conf import settings

DEFAULT_CERT_PATH_ENV = "DGII_CERT_PATH"
DEFAULT_CERT_KEY_ENV = "DGII_CERT_KEY"
DEFAULT_CERT_PASSWORD_ENV = "DGII_CERT_PASSWORD_B64"


class DGIISecretsError(RuntimeError):
    """Generic error retrieving DGII secrets."""


class DGIISecretsNotConfigured(DGIISecretsError):
    """Raised when certificate configuration is missing."""


class EncryptionBackendMissing(DGIISecretsError):
    """Raised when no encryption backend is available for decrypt operations."""


@dataclass(frozen=True)
class CertificateSecrets:
    """In-memory representation of the certificate and password."""

    certificate_bytes: bytes
    password: str
    alias: Optional[str] = None


def _get_env(name: str) -> Optional[str]:
    return os.environ.get(name) or getattr(settings, name, None)


def _default_decrypt(cipher_bytes: bytes, key: str) -> bytes:
    """Decrypt bytes using Fernet (AES-128 in CBC) when available."""
    try:
        from cryptography.fernet import Fernet  # type: ignore
    except Exception as exc:  # pragma: no cover - cryptography optional
        raise EncryptionBackendMissing(
            "cryptography/fernet is required to decrypt DGII certificates"
        ) from exc

    fernet = Fernet(key.encode("utf-8"))
    return fernet.decrypt(cipher_bytes)


def _load_encrypted_file(path: str) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except FileNotFoundError as exc:
        raise DGIISecretsError(f"El certificado cifrado no existe: {path}") from exc
    except OSError as exc:
        raise DGIISecretsError(
            f"No se pudo leer el certificado cifrado en {path}: {exc}"
        ) from exc


def _load_certificate_decrypted(
    *,
    path: str,
    key: str,
    decrypt_callback: Optional[Callable[[bytes, str], bytes]] = None,
) -> bytes:
    encrypt_bytes = _load_encrypted_file(path)
    decrypt_fn = decrypt_callback or _default_decrypt
    return decrypt_fn(encrypt_bytes, key)


@functools.lru_cache(maxsize=1)
def get_certificate_secrets(
    *,
    path_env: str = DEFAULT_CERT_PATH_ENV,
    key_env: str = DEFAULT_CERT_KEY_ENV,
    password_env: str = DEFAULT_CERT_PASSWORD_ENV,
    decrypt_callback: Optional[Callable[[bytes, str], bytes]] = None,
) -> CertificateSecrets:
    """Return certificate bytes and password, caching the result."""

    path = _get_env(path_env)
    key = _get_env(key_env)
    password_b64 = _get_env(password_env)

    if not path or not key or not password_b64:
        raise DGIISecretsNotConfigured(
            "Variables DGII_CERT_PATH, DGII_CERT_KEY y DGII_CERT_PASSWORD_B64 son requeridas"
        )

    try:
        password_bytes = base64.b64decode(password_b64.encode("utf-8"))
        password = password_bytes.decode("utf-8")
    except Exception as exc:
        raise DGIISecretsError("No se pudo decodificar la contraseña del certificado.") from exc

    certificate = _load_certificate_decrypted(
        path=path,
        key=key,
        decrypt_callback=decrypt_callback,
    )

    alias = _get_env("DGII_CERT_ALIAS")
    return CertificateSecrets(certificate_bytes=certificate, password=password, alias=alias)


def refresh_cached_secrets() -> None:
    """Invalidate the LRU cache to force reloading secrets."""

    get_certificate_secrets.cache_clear()


def get_certificate_bytes() -> bytes:
    return get_certificate_secrets().certificate_bytes


def get_certificate_password() -> str:
    return get_certificate_secrets().password


def get_certificate_alias() -> Optional[str]:
    return get_certificate_secrets().alias
