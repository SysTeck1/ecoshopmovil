## Sistema POS

Proyecto de Punto de Venta desarrollado en Django.

### Integración DGII (Comprobantes fiscales electrónicos)
- ✅ Configuración interna de contribuyente, serie y secuencia.
- ✅ Modal de configuración ampliado con campos para endpoints, credenciales y certificados DGII.
- ✅ API y modelo `FiscalVoucherConfig` actualizados para almacenar datos del webservice.
- ✅ Servicio `ventas.dgii.secrets` para cargar certificado cifrado (Fernet) desde disco + variables de entorno.
- ✅ Helpers iniciales (`ventas.dgii.auth`, `ventas.dgii.signer`, `ventas.dgii.client`) para autenticación, carga de certificados y orquestación HTTP.
- 🟡 Próximo: implementar firma XML real y envío/consulta de e-CF.
- 🟡 Próximo: plan de pruebas de certificación (sandbox vs. producción, casos de rechazo/aceptación).

#### Configuración de entorno
Asegúrese de definir estas variables antes de iniciar el servicio que emite comprobantes:

| Variable | Descripción |
| -------- | ----------- |
| `DGII_CERT_PATH` | Ruta al archivo **cifrado** (PKCS#12) del certificado DGII. |
| `DGII_CERT_KEY` | Clave simétrica en formato Fernet para descifrar el archivo. |
| `DGII_CERT_PASSWORD_B64` | Contraseña original del certificado codificada en Base64. |
| `DGII_CERT_ALIAS` | (Opcional) Alias human-readable del certificado. |

> Nota: el archivo debe estar cifrado con la misma clave Fernet utilizada en `DGII_CERT_KEY`.

#### Uso de los helpers DGII

```python
from ventas.dgii import (
    DGIIHttpClient,
    DGIIAuthClient,
    DGIIXMLSigner,
    load_certificate_bundle,
)

from ventas.models import FiscalVoucherConfig


def enviar_factura(config: FiscalVoucherConfig, payload: dict) -> dict:
    # Inyecta un cliente HTTP; puede ser requests, httpx, etc.
    def http_request(method: str, url: str, headers: dict, body: dict | None) -> dict:
        # TODO: implementar llamada real
        raise NotImplementedError

    client = DGIIHttpClient(http_request=http_request)
    response = client.post_json(
        config=config,
        url=config.api_submission_url,
        payload=payload,
    )
    return response.data


def firmar_xml(xml: str) -> str:
    signer = DGIIXMLSigner()
    # load_certificate_bundle() se ejecuta internamente para validar el certificado.
    return signer.sign_xml(xml)
```

El flujo recomendado es:
1. Recuperar instancia de `FiscalVoucherConfig` (configuración activa).
2. Firmar el XML con `DGIIXMLSigner` (una vez implementada la firma real).
3. Enviar el XML firmado usando `DGIIHttpClient`, que refresca tokens automáticamente.
4. Manejar la respuesta y persistir los estados en el modelo de comprobante fiscal.
