import unittest

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider

from obtrace_sdk.client import ObtraceClient
from obtrace_sdk.types import ObtraceConfig, SDKContext


def _make_client(**overrides):
    defaults = dict(
        api_key="devkey",
        service_name="py-test",
        auto_instrument_http=False,
    )
    defaults.update(overrides)
    return ObtraceClient(ObtraceConfig(**defaults))


class ClientTests(unittest.TestCase):
    def test_creates_otel_providers(self):
        c = _make_client()
        self.assertIsInstance(c._providers.tracer_provider, TracerProvider)
        self.assertIsInstance(c._providers.meter_provider, MeterProvider)
        self.assertIsInstance(c._providers.logger_provider, LoggerProvider)
        c.shutdown()

    def test_log_does_not_raise(self):
        c = _make_client()
        c.log("info", "hello")
        c.log("error", "bad thing", SDKContext(trace_id="a" * 32, span_id="b" * 16))
        c.shutdown()

    def test_metric_does_not_raise(self):
        c = _make_client()
        c.metric("m", 1.0)
        c.metric("m2", 42.0, unit="ms", context=SDKContext(attrs={"env": "test"}))
        c.shutdown()

    def test_span_returns_trace_and_span_id(self):
        c = _make_client()
        result = c.span("test-span", attrs={"key": "value"})
        self.assertIn("trace_id", result)
        self.assertIn("span_id", result)
        self.assertEqual(len(result["trace_id"]), 32)
        self.assertEqual(len(result["span_id"]), 16)
        c.shutdown()

    def test_span_error_status(self):
        c = _make_client()
        result = c.span("error-span", status_code=500, status_message="internal error")
        self.assertIn("trace_id", result)
        c.shutdown()

    def test_capture_error(self):
        c = _make_client()
        c.capture_error(ValueError("test error"), attrs={"component": "db"})
        c.shutdown()

    def test_context_manager(self):
        with _make_client() as c:
            c.log("info", "inside context")

    def test_start_span_context_manager(self):
        c = _make_client()
        with c.start_span("my-operation", attrs={"step": "1"}) as span:
            span.set_attribute("result", "ok")
        c.shutdown()

    def test_inject_propagation(self):
        c = _make_client()
        headers = c.inject_propagation(session_id="sess-123")
        self.assertIn("x-obtrace-session-id", headers)
        self.assertEqual(headers["x-obtrace-session-id"], "sess-123")
        c.shutdown()

    def test_flush_does_not_raise(self):
        c = _make_client()
        c.log("info", "pre-flush")
        c.flush()
        c.shutdown()

    def test_validation_error_on_missing_fields(self):
        with self.assertRaises(ValueError):
            ObtraceClient(ObtraceConfig(api_key="", service_name="svc"))


if __name__ == "__main__":
    unittest.main()
