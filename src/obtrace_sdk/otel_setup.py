from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("obtrace")

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .types import ObtraceConfig

_INSTRUMENTATION_MODULES = [
    ("opentelemetry.instrumentation.requests", "RequestsInstrumentor"),
    ("opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor"),
    ("opentelemetry.instrumentation.urllib", "URLLibInstrumentor"),
    ("opentelemetry.instrumentation.flask", "FlaskInstrumentor"),
    ("opentelemetry.instrumentation.fastapi", "FastAPIInstrumentor"),
    ("opentelemetry.instrumentation.django", "DjangoInstrumentor"),
    ("opentelemetry.instrumentation.logging", "LoggingInstrumentor"),
    ("opentelemetry.instrumentation.psycopg2", "Psycopg2Instrumentor"),
    ("opentelemetry.instrumentation.redis", "RedisInstrumentor"),
    ("opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor"),
    ("opentelemetry.instrumentation.celery", "CeleryInstrumentor"),
    ("opentelemetry.instrumentation.grpc", "GrpcInstrumentorClient"),
]


class OtelProviders:
    __slots__ = ("tracer_provider", "meter_provider", "logger_provider")

    def __init__(
        self,
        tracer_provider: TracerProvider,
        meter_provider: MeterProvider,
        logger_provider: LoggerProvider,
    ):
        self.tracer_provider = tracer_provider
        self.meter_provider = meter_provider
        self.logger_provider = logger_provider


def setup_otel(cfg: ObtraceConfig) -> OtelProviders:
    resource_attrs: dict[str, Any] = {
        "service.name": cfg.service_name,
        "service.version": cfg.service_version,
        "deployment.environment": cfg.env or "dev",
        "runtime.name": "python",
    }
    if cfg.tenant_id:
        resource_attrs["obtrace.tenant_id"] = cfg.tenant_id
    if cfg.project_id:
        resource_attrs["obtrace.project_id"] = cfg.project_id
    if cfg.app_id:
        resource_attrs["obtrace.app_id"] = cfg.app_id
    if cfg.env:
        resource_attrs["obtrace.env"] = cfg.env

    resource = Resource.create(resource_attrs)
    base_url = cfg.ingest_base_url.rstrip("/")
    headers = {
        **cfg.default_headers,
        "Authorization": f"Bearer {cfg.api_key}",
    }

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=f"{base_url}/otlp/v1/traces",
                headers=headers,
                timeout=int(cfg.request_timeout_sec),
            )
        )
    )
    try:
        trace.set_tracer_provider(tracer_provider)
    except Exception:
        pass

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=f"{base_url}/otlp/v1/metrics",
                    headers=headers,
                    timeout=int(cfg.request_timeout_sec),
                ),
                export_interval_millis=60000,
            )
        ],
    )
    try:
        metrics.set_meter_provider(meter_provider)
    except Exception:
        pass

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=f"{base_url}/otlp/v1/logs",
                headers=headers,
                timeout=int(cfg.request_timeout_sec),
            )
        )
    )

    providers = OtelProviders(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        logger_provider=logger_provider,
    )

    if cfg.auto_instrument_http:
        import threading
        threading.Thread(target=_auto_instrument, daemon=True).start()

    return providers


def _auto_instrument() -> None:
    import importlib

    for module_path, class_name in _INSTRUMENTATION_MODULES:
        try:
            mod = importlib.import_module(module_path)
            instrumentor = getattr(mod, class_name)()
            if not instrumentor.is_instrumented_by_opentelemetry:
                instrumentor.instrument()
        except (ImportError, Exception) as e:
            logger.debug("obtrace: skipped %s: %s", module_path, e)
