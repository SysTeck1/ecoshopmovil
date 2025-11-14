"""Helpers to load DGII certificates and sign XML payloads (stub)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .secrets import (
    CertificateSecrets,
    DGIISecretsError,
    EncryptionBackendMissing,
    get_certificate_alias,
    get_certificate_bytes,
    get_certificate_password,
)

try:  # pragma: no cover - optional dependency import
    from lxml import etree
except Exception:  # pragma: no cover - missing dependency handled at runtime
    etree = None  # type: ignore

try:  # pragma: no cover - optional dependency import
    from signxml import XMLSigner, methods
except Exception:  # pragma: no cover - missing dependency handled at runtime
    XMLSigner = None  # type: ignore
    methods = None  # type: ignore

from cryptography.hazmat.primitives import serialization


class DGIISignerError(RuntimeError):
    """Raised when the signing helpers fail."""


@dataclass(frozen=True)
class CertificateBundle:
    """PKCS#12 contents unpacked for signing."""

    private_key: object
    certificate: object
    additional_certs: Optional[list[object]]
    alias: Optional[str]


def load_certificate_bundle() -> CertificateBundle:
    """Load PKCS#12 certificate contents using configured secrets."""

    secrets = _load_secrets()

    try:
        from cryptography import x509  # noqa: F401  # type: ignore
        from cryptography.hazmat.primitives.serialization import pkcs12  # type: ignore
        from cryptography.hazmat.backends import default_backend  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency optional
        raise DGIISignerError(
            "La librería 'cryptography' es requerida para manejar certificados PKCS#12"
        ) from exc

    try:
        private_key, cert, additional = pkcs12.load_key_and_certificates(
            data=secrets.certificate_bytes,
            password=secrets.password.encode("utf-8"),
            backend=default_backend(),
        )
    except (ValueError, TypeError) as exc:
        raise DGIISignerError("No se pudo cargar el certificado PKCS#12") from exc

    if cert is None or private_key is None:
        raise DGIISignerError("El certificado PKCS#12 no contiene llave privada o certificado")

    additional_list = list(additional or []) or None
    return CertificateBundle(
        private_key=private_key,
        certificate=cert,
        additional_certs=additional_list,
        alias=secrets.alias,
    )


def _load_secrets() -> CertificateSecrets:
    try:
        return CertificateSecrets(
            certificate_bytes=get_certificate_bytes(),
            password=get_certificate_password(),
            alias=get_certificate_alias(),
        )
    except (DGIISecretsError, EncryptionBackendMissing) as exc:
        raise DGIISignerError(str(exc)) from exc


class DGIIXMLSigner:
    """Generate enveloped XMLDSig signatures for DGII submissions."""

    def __init__(self) -> None:
        self._bundle: Optional[CertificateBundle] = None

    def ensure_bundle(self) -> CertificateBundle:
        if self._bundle is None:
            self._bundle = load_certificate_bundle()
        return self._bundle

    def sign_xml(self, xml_payload: str) -> str:
        if etree is None or XMLSigner is None or methods is None:
            raise DGIISignerError(
                "Las librerías 'lxml' y 'signxml' son requeridas para firmar el XML DGII"
            )

        bundle = self.ensure_bundle()

        try:
            parser = etree.XMLParser(remove_blank_text=True)
            xml_tree = etree.fromstring(xml_payload.encode("utf-8"), parser=parser)
        except Exception as exc:
            raise DGIISignerError("XML inválido para la firma DGII") from exc

        private_key = bundle.private_key
        certificate = bundle.certificate

        try:
            key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        except Exception as exc:
            raise DGIISignerError("No se pudo serializar la clave privada del certificado") from exc

        try:
            cert_bytes = certificate.public_bytes(serialization.Encoding.PEM)
        except Exception as exc:
            raise DGIISignerError("No se pudo serializar el certificado X.509") from exc

        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
        )

        try:
            signed_tree = signer.sign(
                xml_tree,
                key=key_bytes,
                cert=cert_bytes,
                key_name=bundle.alias or None,
            )
        except Exception as exc:
            raise DGIISignerError("Error al firmar el XML con el certificado DGII") from exc

        return etree.tostring(signed_tree, encoding="utf-8", xml_declaration=True).decode("utf-8")


__all__ = [
    "CertificateBundle",
    "DGIIXMLSigner",
    "DGIISignerError",
    "load_certificate_bundle",
]
