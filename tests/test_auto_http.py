import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

import requests
import httpx

from obtrace_sdk.auto_http import (
    install_http_instrumentation,
    uninstall_http_instrumentation,
    _patched_requests,
    _patched_httpx,
    _patched_httpx_async,
)
from obtrace_sdk.client import ObtraceClient
from obtrace_sdk.types import ObtraceConfig


def _make_client(**overrides):
    defaults = dict(
        api_key="testkey",
        ingest_base_url="https://ingest.obtrace.ai",
        service_name="test-svc",
        auto_instrument_http=False,
    )
    defaults.update(overrides)
    return ObtraceClient(ObtraceConfig(**defaults))


class TestAutoInstrumentRequests(unittest.TestCase):
    def setUp(self):
        uninstall_http_instrumentation()

    def tearDown(self):
        uninstall_http_instrumentation()

    def test_requests_session_send_is_patched(self):
        original = requests.Session.send
        client = _make_client()
        install_http_instrumentation(client)
        self.assertIsNot(requests.Session.send, original)
        uninstall_http_instrumentation()
        self.assertIs(requests.Session.send, original)

    def test_requests_adds_traceparent_header(self):
        client = _make_client()
        install_http_instrumentation(client)

        prepared = requests.Request("GET", "https://example.com/api").prepare()
        self.assertNotIn("traceparent", prepared.headers)

        fake_response = requests.models.Response()
        fake_response.status_code = 200
        fake_response.url = "https://example.com/api"

        with patch.object(requests.adapters.HTTPAdapter, "send", return_value=fake_response):
            with patch("urllib.request.urlopen") as urlopen:
                cm = MagicMock()
                cm.__enter__.return_value.status = 202
                cm.__exit__.return_value = False
                urlopen.return_value = cm
                session = requests.Session()
                resp = session.send(prepared)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("traceparent", prepared.headers)
        self.assertTrue(prepared.headers["traceparent"].startswith("00-"))

    def test_requests_instruments_span_and_log(self):
        client = _make_client()
        install_http_instrumentation(client)

        fake_response = requests.models.Response()
        fake_response.status_code = 201
        fake_response.url = "https://example.com/items"

        with patch.object(client, "span", wraps=client.span) as span_mock, \
             patch.object(client, "log", wraps=client.log) as log_mock:
            with patch.object(requests.adapters.HTTPAdapter, "send", return_value=fake_response):
                with patch("urllib.request.urlopen"):
                    session = requests.Session()
                    prepared = requests.Request("POST", "https://example.com/items").prepare()
                    session.send(prepared)

            span_calls = [c for c in span_mock.call_args_list if "http.client" in str(c)]
            self.assertTrue(len(span_calls) >= 1)
            log_calls = [c for c in log_mock.call_args_list if "requests POST" in str(c)]
            self.assertTrue(len(log_calls) >= 1)

    def test_requests_error_path(self):
        client = _make_client()
        install_http_instrumentation(client)

        with patch.object(client, "span", wraps=client.span) as span_mock, \
             patch.object(client, "log", wraps=client.log) as log_mock:
            with patch.object(requests.adapters.HTTPAdapter, "send", side_effect=ConnectionError("refused")):
                session = requests.Session()
                prepared = requests.Request("GET", "https://down.example.com").prepare()
                with self.assertRaises(ConnectionError):
                    session.send(prepared)

            error_logs = [c for c in log_mock.call_args_list if "error" in str(c)]
            self.assertTrue(len(error_logs) >= 1)


class TestAutoInstrumentHttpx(unittest.TestCase):
    def setUp(self):
        uninstall_http_instrumentation()

    def tearDown(self):
        uninstall_http_instrumentation()

    def test_httpx_client_send_is_patched(self):
        original = httpx.Client.send
        client = _make_client()
        install_http_instrumentation(client)
        self.assertIsNot(httpx.Client.send, original)
        uninstall_http_instrumentation()
        self.assertIs(httpx.Client.send, original)

    def test_httpx_adds_traceparent_header(self):
        client = _make_client()
        install_http_instrumentation(client)

        fake_response = httpx.Response(200, request=httpx.Request("GET", "https://example.com"))

        with patch.object(httpx.Client, "_send_single_request", return_value=fake_response):
            with patch("urllib.request.urlopen") as urlopen:
                cm = MagicMock()
                cm.__enter__.return_value.status = 202
                cm.__exit__.return_value = False
                urlopen.return_value = cm
                with httpx.Client() as hc:
                    req = httpx.Request("GET", "https://example.com/test")
                    resp = hc.send(req)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("traceparent", req.headers)

    def test_httpx_instruments_span_and_log(self):
        client = _make_client()
        install_http_instrumentation(client)

        fake_response = httpx.Response(200, request=httpx.Request("GET", "https://example.com"))

        with patch.object(client, "span", wraps=client.span) as span_mock, \
             patch.object(client, "log", wraps=client.log) as log_mock:
            with patch.object(httpx.Client, "_send_single_request", return_value=fake_response):
                with patch("urllib.request.urlopen"):
                    with httpx.Client() as hc:
                        req = httpx.Request("GET", "https://example.com/test")
                        hc.send(req)

            span_calls = [c for c in span_mock.call_args_list if "http.client" in str(c)]
            self.assertTrue(len(span_calls) >= 1)
            log_calls = [c for c in log_mock.call_args_list if "httpx GET" in str(c)]
            self.assertTrue(len(log_calls) >= 1)


class TestAutoInstrumentHttpxAsync(unittest.TestCase):
    def setUp(self):
        uninstall_http_instrumentation()

    def tearDown(self):
        uninstall_http_instrumentation()

    def test_httpx_async_client_send_is_patched(self):
        original = httpx.AsyncClient.send
        client = _make_client()
        install_http_instrumentation(client)
        self.assertIsNot(httpx.AsyncClient.send, original)
        uninstall_http_instrumentation()
        self.assertIs(httpx.AsyncClient.send, original)

    def test_httpx_async_adds_traceparent_header(self):
        client = _make_client()
        install_http_instrumentation(client)

        fake_response = httpx.Response(200, request=httpx.Request("GET", "https://example.com"))

        async def run():
            with patch.object(httpx.AsyncClient, "_send_single_request", new_callable=AsyncMock, return_value=fake_response):
                with patch("urllib.request.urlopen") as urlopen:
                    cm = MagicMock()
                    cm.__enter__.return_value.status = 202
                    cm.__exit__.return_value = False
                    urlopen.return_value = cm
                    async with httpx.AsyncClient() as hc:
                        req = httpx.Request("GET", "https://example.com/async-test")
                        resp = await hc.send(req)
            return resp, req

        resp, req = asyncio.run(run())
        self.assertEqual(resp.status_code, 200)
        self.assertIn("traceparent", req.headers)

    def test_httpx_async_instruments_span_and_log(self):
        client = _make_client()
        install_http_instrumentation(client)

        fake_response = httpx.Response(200, request=httpx.Request("GET", "https://example.com"))

        async def run():
            with patch.object(client, "span", wraps=client.span) as span_mock, \
                 patch.object(client, "log", wraps=client.log) as log_mock:
                with patch.object(httpx.AsyncClient, "_send_single_request", new_callable=AsyncMock, return_value=fake_response):
                    with patch("urllib.request.urlopen"):
                        async with httpx.AsyncClient() as hc:
                            req = httpx.Request("GET", "https://example.com/async-test")
                            await hc.send(req)
                return span_mock, log_mock

        span_mock, log_mock = asyncio.run(run())
        span_calls = [c for c in span_mock.call_args_list if "http.client" in str(c)]
        self.assertTrue(len(span_calls) >= 1)
        log_calls = [c for c in log_mock.call_args_list if "httpx.async GET" in str(c)]
        self.assertTrue(len(log_calls) >= 1)

    def test_httpx_async_error_path(self):
        client = _make_client()
        install_http_instrumentation(client)

        async def run():
            with patch.object(client, "span", wraps=client.span) as span_mock, \
                 patch.object(client, "log", wraps=client.log) as log_mock:
                with patch.object(httpx.AsyncClient, "_send_single_request", new_callable=AsyncMock, side_effect=ConnectionError("refused")):
                    async with httpx.AsyncClient() as hc:
                        req = httpx.Request("GET", "https://down.example.com")
                        try:
                            await hc.send(req)
                        except ConnectionError:
                            pass
                        else:
                            raise AssertionError("Expected ConnectionError")
                return log_mock

        log_mock = asyncio.run(run())
        error_logs = [c for c in log_mock.call_args_list if "error" in str(c)]
        self.assertTrue(len(error_logs) >= 1)


class TestOptOut(unittest.TestCase):
    def setUp(self):
        uninstall_http_instrumentation()

    def tearDown(self):
        uninstall_http_instrumentation()

    def test_auto_instrument_http_false_skips_patching(self):
        original_requests = requests.Session.send
        original_httpx = httpx.Client.send
        _make_client(auto_instrument_http=False)
        self.assertIs(requests.Session.send, original_requests)
        self.assertIs(httpx.Client.send, original_httpx)

    def test_auto_instrument_http_true_patches(self):
        original_requests = requests.Session.send
        _make_client(auto_instrument_http=True)
        self.assertIsNot(requests.Session.send, original_requests)
        uninstall_http_instrumentation()


class TestGracefulSkipWhenMissing(unittest.TestCase):
    def setUp(self):
        uninstall_http_instrumentation()

    def tearDown(self):
        uninstall_http_instrumentation()

    def test_missing_requests_does_not_raise(self):
        import sys
        saved = sys.modules.get("requests")
        sys.modules["requests"] = None  # type: ignore[assignment]
        try:
            client = _make_client()
            install_http_instrumentation(client)
        finally:
            if saved is not None:
                sys.modules["requests"] = saved
            else:
                del sys.modules["requests"]

    def test_missing_httpx_does_not_raise(self):
        import sys
        saved = sys.modules.get("httpx")
        sys.modules["httpx"] = None  # type: ignore[assignment]
        try:
            client = _make_client()
            install_http_instrumentation(client)
        finally:
            if saved is not None:
                sys.modules["httpx"] = saved
            else:
                del sys.modules["httpx"]


if __name__ == "__main__":
    unittest.main()
