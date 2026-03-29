from __future__ import annotations

import logging
import platform
import threading
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional
from urllib.request import Request, urlopen

from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.trace import StatusCode

from .otel_setup import setup_otel
from .semantic_metrics import is_semantic_metric
from .types import ObtraceConfig, SDKContext

_SDK_SCOPE = "obtrace-sdk-python"
_logger = logging.getLogger("obtrace")
_initialized = False


class ObtraceClient:
    def __init__(self, cfg: ObtraceConfig):
        global _initialized
        if not cfg.api_key or not cfg.ingest_base_url or not cfg.service_name:
            raise ValueError("api_key, ingest_base_url and service_name are required")
        if _initialized:
            _logger.warning("obtrace: ObtraceClient already initialized, creating duplicate instance")
        _initialized = True
        self.cfg = cfg
        self._providers = setup_otel(cfg)
        self._tracer = self._providers.tracer_provider.get_tracer(_SDK_SCOPE)
        self._meter = self._providers.meter_provider.get_meter(_SDK_SCOPE)
        self._logger = self._providers.logger_provider.get_logger(_SDK_SCOPE)
        self._counters: Dict[str, Any] = {}
        self._histograms: Dict[str, Any] = {}
        self._otel_logging_handler = LoggingHandler(
            level=logging.DEBUG,
            logger_provider=self._providers.logger_provider,
        )
        logging.root.addHandler(self._otel_logging_handler)
        self.initialized = False
        threading.Thread(target=self._handshake, daemon=True).start()

    def _handshake(self) -> None:
        import json
        base = self.cfg.ingest_base_url.rstrip("/")
        if not base:
            return
        try:
            payload = json.dumps({
                "sdk": "obtrace-sdk-python",
                "sdk_version": "1.0.0",
                "service_name": self.cfg.service_name,
                "service_version": self.cfg.service_version,
                "runtime": "python",
                "runtime_version": platform.python_version(),
            }).encode()
            req = Request(f"{base}/v1/init", data=payload, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {self.cfg.api_key}")
            with urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    self.initialized = True
                    if self.cfg.debug:
                        _logger.info("obtrace: init handshake OK")
                elif self.cfg.debug:
                    _logger.error("obtrace: init handshake failed: %d", resp.status)
        except Exception as e:
            if self.cfg.debug:
                _logger.error("obtrace: init handshake error: %s", e)

    def __enter__(self) -> ObtraceClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.shutdown()

    def log(self, level: str, message: str, context: Optional[SDKContext] = None) -> None:
        severity = _level_to_severity(level)
        attrs: Dict[str, Any] = {}
        if context:
            if context.trace_id:
                attrs["obtrace.trace_id"] = context.trace_id
            if context.span_id:
                attrs["obtrace.span_id"] = context.span_id
            if context.session_id:
                attrs["obtrace.session_id"] = context.session_id
            if context.route_template:
                attrs["obtrace.route_template"] = context.route_template
            if context.endpoint:
                attrs["obtrace.endpoint"] = context.endpoint
            if context.method:
                attrs["obtrace.method"] = context.method
            if context.status_code is not None:
                attrs["obtrace.status_code"] = context.status_code
            for k, v in context.attrs.items():
                attrs[f"obtrace.attr.{k}"] = v
        self._logger.emit(
            body=message,
            severity_text=level.upper(),
            severity_number=_severity_number_enum(severity),
            attributes=attrs if attrs else None,
        )

    def metric(self, name: str, value: float, unit: str = "1", context: Optional[SDKContext] = None) -> None:
        if self.cfg.validate_semantic_metrics and self.cfg.debug and not is_semantic_metric(name):
            print(f"[obtrace-sdk-python] non-canonical metric name: {name}")
        attrs = {}
        if context:
            attrs = dict(context.attrs)
        key = f"{name}:{unit}"
        if key not in self._counters:
            self._counters[key] = self._meter.create_gauge(name, unit=unit)
        self._counters[key].set(value, attributes=attrs)

    def span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        start_unix_nano: Optional[str] = None,
        end_unix_nano: Optional[str] = None,
        status_code: Optional[int] = None,
        status_message: str = "",
        attrs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        otel_span = self._tracer.start_span(name, attributes=attrs or {})
        if status_code is not None and status_code >= 400:
            otel_span.set_status(StatusCode.ERROR, status_message)
        else:
            otel_span.set_status(StatusCode.OK)
        otel_span.end()
        ctx = otel_span.get_span_context()
        return {
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
        }

    @contextmanager
    def start_span(self, name: str, attrs: Optional[Dict[str, Any]] = None) -> Iterator[Any]:
        with self._tracer.start_as_current_span(name, attributes=attrs or {}) as otel_span:
            yield otel_span

    def capture_error(self, error: Exception, attrs: Optional[Dict[str, Any]] = None) -> None:
        with self._tracer.start_as_current_span("exception") as otel_span:
            otel_span.set_status(StatusCode.ERROR, str(error))
            otel_span.record_exception(error, attributes=attrs or {})

    def inject_propagation(
        self,
        headers: Optional[Dict[str, str]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, str]:
        from opentelemetry.propagate import inject
        out = dict(headers or {})
        inject(out)
        if session_id:
            out.setdefault("x-obtrace-session-id", session_id)
        return out

    def flush(self) -> None:
        self._providers.tracer_provider.force_flush()
        self._providers.meter_provider.force_flush()
        self._providers.logger_provider.force_flush()

    def shutdown(self) -> None:
        global _initialized
        logging.root.removeHandler(self._otel_logging_handler)
        self._providers.tracer_provider.shutdown()
        self._providers.meter_provider.shutdown()
        self._providers.logger_provider.shutdown()
        _initialized = False


def _level_to_severity(level: str) -> int:
    mapping = {
        "debug": 5,
        "info": 9,
        "warn": 13,
        "warning": 13,
        "error": 17,
        "fatal": 21,
        "critical": 21,
    }
    return mapping.get(level.lower(), 9)


_SEVERITY_MAP = {
    5: SeverityNumber.DEBUG,
    9: SeverityNumber.INFO,
    13: SeverityNumber.WARN,
    17: SeverityNumber.ERROR,
    21: SeverityNumber.FATAL,
}


def _severity_number_enum(num: int) -> SeverityNumber:
    return _SEVERITY_MAP.get(num, SeverityNumber.INFO)
