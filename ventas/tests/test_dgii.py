"""Unit tests for ventas.dgii helper modules."""

from __future__ import annotations

import base64
import datetime as dt
import os
from unittest import mock

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from ventas.dgii import auth, client, http, secrets, service
from ventas.dgii.auth import DGIIAuthTokens
from ventas.dgii.http import RequestsNotAvailable
from ventas.dgii.service import DGIIVoucherServiceError
from ventas.models import FiscalVoucherConfig


class DGIISecretsTests(SimpleTestCase):
    def tearDown(self) -> None:
        secrets.refresh_cached_secrets()
        super().tearDown()

    def test_missing_environment_variables(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            secrets.refresh_cached_secrets()
            with self.assertRaises(secrets.DGIISecretsNotConfigured):
                secrets.get_certificate_secrets()

    def test_loads_certificate_and_caches_result(self) -> None:
        password = "clave-super-secreta"
        password_b64 = base64.b64encode(password.encode("utf-8")).decode("ascii")
        env = {
            "DGII_CERT_PATH": "/tmp/cert.enc",
            "DGII_CERT_KEY": "ZmFrZS1rZXktZmFrZS1rZXktZmFrZS1rZXktZmFrZS0=",
            "DGII_CERT_PASSWORD_B64": password_b64,
            "DGII_CERT_ALIAS": "Empresa Demo",
        }

        with mock.patch.dict(os.environ, env, clear=True), mock.patch(
            "ventas.dgii.secrets._load_certificate_decrypted",
            return_value=b"CERT-DATA",
        ) as load_mock:
            secrets.refresh_cached_secrets()
            first = secrets.get_certificate_secrets()
            second = secrets.get_certificate_secrets()

        self.assertIs(first, second)
        self.assertEqual(first.certificate_bytes, b"CERT-DATA")
        self.assertEqual(first.password, password)
        self.assertEqual(first.alias, "Empresa Demo")
        load_mock.assert_called_once_with(path="/tmp/cert.enc", key=env["DGII_CERT_KEY"], decrypt_callback=None)


class DGIIAuthTests(SimpleTestCase):
    def _make_config(self, **overrides) -> FiscalVoucherConfig:
        defaults = {
            "api_auth_url": "https://auth.dgii.test/token",
            "api_client_id": "client-id",
            "api_client_secret": "client-secret",
        }
        defaults.update(overrides)
        return FiscalVoucherConfig(**defaults)

    def test_build_auth_payload_requires_credentials(self) -> None:
        config = self._make_config(api_client_id="", api_client_secret="")
        with self.assertRaises(auth.DGIIAuthError):
            auth.build_auth_payload(config)

    def test_obtain_token_flow(self) -> None:
        config = self._make_config()
        response_payload = {
            "access_token": "abc123",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "facturacion-electronica",
        }

        fake_now = timezone.now()
        with mock.patch("ventas.dgii.auth.timezone.now", return_value=fake_now):
            client_instance = auth.DGIIAuthClient(http_post=lambda url, payload: response_payload)
            tokens = client_instance.obtain_token(config)

        self.assertEqual(tokens.access_token, "abc123")
        self.assertEqual(tokens.token_type, "Bearer")
        self.assertEqual(tokens.scope, "facturacion-electronica")
        self.assertEqual(tokens.expires_at, fake_now + dt.timedelta(seconds=3600))

    def test_obtain_token_requires_http_client(self) -> None:
        config = self._make_config()
        client_instance = auth.DGIIAuthClient()
        with self.assertRaises(auth.DGIIAuthError):
            client_instance.obtain_token(config)


class DGIIHttpClientTests(SimpleTestCase):
    def setUp(self) -> None:
        self.config = FiscalVoucherConfig(
            api_auth_url="https://auth.dgii.test/token",
            api_client_id="client-id",
            api_client_secret="client-secret",
        )
        super().setUp()

    def test_post_json_requires_http_callable(self) -> None:
        client_instance = client.DGIIHttpClient()
        with self.assertRaises(client.DGIIClientError):
            client_instance.post_json(config=self.config, url="https://dgii.test/api")

    def test_post_json_executes_request_with_bearer_token(self) -> None:
        captured: dict[str, object] = {}

        def http_request(method: str, url: str, headers: dict, body: dict | None) -> dict:
            captured.update({
                "method": method,
                "url": url,
                "headers": headers,
                "body": body,
            })
            return {"status": 202, "payload": {"ok": True}}

        tokens = DGIIAuthTokens(
            access_token="token-xyz",
            token_type="Bearer",
            expires_at=timezone.now() + dt.timedelta(minutes=5),
        )
        mock_auth_client = mock.Mock(spec=auth.DGIIAuthClient)
        mock_auth_client.obtain_token.return_value = tokens

        client_instance = client.DGIIHttpClient(
            http_request=http_request,
            auth_client=mock_auth_client,
        )

        response = client_instance.post_json(
            config=self.config,
            url="https://dgii.test/api/submit",
            payload={"foo": "bar"},
        )

        self.assertIsInstance(response, client.DGIIClientResponse)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data, {"status": 202, "payload": {"ok": True}})

        self.assertEqual(captured.get("method"), "POST")
        self.assertEqual(captured.get("url"), "https://dgii.test/api/submit")
        headers = captured.get("headers")
        self.assertIsInstance(headers, dict)
        self.assertEqual(headers.get("Authorization"), "Bearer token-xyz")
        self.assertEqual(headers.get("Content-Type"), "application/json")
        self.assertEqual(captured.get("body"), {"foo": "bar"})
        mock_auth_client.obtain_token.assert_called_once_with(self.config)

    def test_reuses_cached_token_when_valid(self) -> None:
        captured_calls = 0

        def http_request(method: str, url: str, headers: dict, body: dict | None) -> dict:
            nonlocal captured_calls
            captured_calls += 1
            return {"status": 200}

        valid_tokens = DGIIAuthTokens(
            access_token="cached-token",
            token_type="Bearer",
            expires_at=timezone.now() + dt.timedelta(hours=1),
        )
        mock_auth_client = mock.Mock(spec=auth.DGIIAuthClient)

        client_instance = client.DGIIHttpClient(
            http_request=http_request,
            auth_client=mock_auth_client,
        )
        client_instance._tokens = valid_tokens  # preload cache

        client_instance.post_json(
            config=self.config,
            url="https://dgii.test/api/check",
            payload=None,
        )

        self.assertEqual(captured_calls, 1)
        mock_auth_client.obtain_token.assert_not_called()


class DGIIHttpAdapterTests(SimpleTestCase):
    def test_requests_not_available(self) -> None:
        with mock.patch("ventas.dgii.http.requests", None):
            with self.assertRaises(RequestsNotAvailable):
                http.build_requests_http_request()

    def test_requests_adapter_executes_call(self) -> None:
        fake_response = mock.Mock()
        fake_response.json.return_value = {"status": 200}
        fake_response.raise_for_status.return_value = None

        session = mock.Mock()
        session.request.return_value = fake_response

        with mock.patch("ventas.dgii.http.requests", mock.Mock()):
            http_request = http.build_requests_http_request(session=session, timeout=8.0)
        result = http_request(
            "POST",
            "https://dgii.test/api",
            {"X-Test": "1"},
            {"foo": "bar"},
        )

        session.request.assert_called_once_with(
            method="POST",
            url="https://dgii.test/api",
            json={"foo": "bar"},
            headers={"X-Test": "1"},
            timeout=8.0,
        )
        self.assertEqual(result, {"status": 200})


class DGIIVoucherServiceTests(TestCase):
    def setUp(self) -> None:
        self.config = FiscalVoucherConfig(
            api_submission_url="https://dgii.test/submit",
            api_auth_url="https://dgii.test/token",
            api_client_id="client-id",
            api_client_secret="client-secret",
        )
        super().setUp()

    def test_send_xml_requires_submission_url(self) -> None:
        config = FiscalVoucherConfig()
        svc = service.DGIIVoucherService()
        with self.assertRaises(DGIIVoucherServiceError):
            svc.send_xml(config=config, xml_payload="<xml />")

    def test_send_xml_flows_through_signer_and_http(self) -> None:
        signer_mock = mock.Mock(spec=service.DGIIXMLSigner)
        signer_mock.sign_xml.return_value = "<xml firmada/>"

        http_response = client.DGIIClientResponse(data={"trackId": "123"}, status_code=202)
        http_client_mock = mock.Mock(spec=client.DGIIHttpClient)
        http_client_mock.post_json.return_value = http_response

        svc = service.DGIIVoucherService(http_client=http_client_mock, signer=signer_mock)
        response = svc.send_xml(config=self.config, xml_payload="<xml />")

        signer_mock.sign_xml.assert_called_once_with("<xml />")
        http_client_mock.post_json.assert_called_once_with(
            config=self.config,
            url="https://dgii.test/submit",
            payload={"xml": "<xml firmada/>"},
        )
        self.assertEqual(response, http_response)

    def test_send_xml_wraps_signer_errors(self) -> None:
        signer_mock = mock.Mock(spec=service.DGIIXMLSigner)
        signer_mock.sign_xml.side_effect = service.DGIISignerError("cert fail")

        svc = service.DGIIVoucherService(signer=signer_mock)
        with self.assertRaises(DGIIVoucherServiceError):
            svc.send_xml(config=self.config, xml_payload="<xml />")

    def test_send_xml_wraps_http_errors(self) -> None:
        signer_mock = mock.Mock(spec=service.DGIIXMLSigner)
        signer_mock.sign_xml.return_value = "<xml firmada/>"

        http_client_mock = mock.Mock(spec=client.DGIIHttpClient)
        http_client_mock.post_json.side_effect = client.DGIIClientError("boom")

        svc = service.DGIIVoucherService(http_client=http_client_mock, signer=signer_mock)
        with self.assertRaises(DGIIVoucherServiceError):
            svc.send_xml(config=self.config, xml_payload="<xml />")
