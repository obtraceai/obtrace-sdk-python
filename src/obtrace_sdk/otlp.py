from __future__ import annotations

import time
from typing import Any, Dict, Optional

from .types import ObtraceConfig, SDKContext


def _now_unix_nano_str() -> str:
    return str(int(time.time() * 1_000_000_000))


def _attrs(attrs: Optional[Dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not attrs:
        return out
    for k, v in attrs.items():
        if isinstance(v, bool):
            val = {"boolValue": v}
        elif isinstance(v, (int, float)):
            val = {"doubleValue": float(v)}
        else:
            val = {"stringValue": str(v)}
        out.append({"key": str(k), "value": val})
    return out


def _resource(cfg: ObtraceConfig) -> list[dict[str, Any]]:
    base: Dict[str, Any] = {
        "service.name": cfg.service_name,
        "service.version": cfg.service_version,
        "deployment.environment": cfg.env or "dev",
        "runtime.name": "python",
    }
    if cfg.tenant_id:
        base["obtrace.tenant_id"] = cfg.tenant_id
    if cfg.project_id:
        base["obtrace.project_id"] = cfg.project_id
    if cfg.app_id:
        base["obtrace.app_id"] = cfg.app_id
    if cfg.env:
        base["obtrace.env"] = cfg.env
    return _attrs(base)


def build_logs_payload(cfg: ObtraceConfig, level: str, body: str, ctx: Optional[SDKContext] = None) -> Dict[str, Any]:
    context_attrs: Dict[str, Any] = {"obtrace.log.level": level}
    if ctx:
        if ctx.trace_id:
            context_attrs["obtrace.trace_id"] = ctx.trace_id
        if ctx.span_id:
            context_attrs["obtrace.span_id"] = ctx.span_id
        if ctx.session_id:
            context_attrs["obtrace.session_id"] = ctx.session_id
        if ctx.route_template:
            context_attrs["obtrace.route_template"] = ctx.route_template
        if ctx.endpoint:
            context_attrs["obtrace.endpoint"] = ctx.endpoint
        if ctx.method:
            context_attrs["obtrace.method"] = ctx.method
        if ctx.status_code is not None:
            context_attrs["obtrace.status_code"] = ctx.status_code
        for k, v in ctx.attrs.items():
            context_attrs[f"obtrace.attr.{k}"] = v

    return {
        "resourceLogs": [
            {
                "resource": {"attributes": _resource(cfg)},
                "scopeLogs": [
                    {
                        "scope": {"name": "obtrace-sdk-python", "version": "1.0.0"},
                        "logRecords": [
                            {
                                "timeUnixNano": _now_unix_nano_str(),
                                "severityText": level.upper(),
                                "body": {"stringValue": body},
                                "attributes": _attrs(context_attrs),
                            }
                        ],
                    }
                ],
            }
        ]
    }


def build_metric_payload(
    cfg: ObtraceConfig,
    metric_name: str,
    value: float,
    unit: str = "1",
    ctx: Optional[SDKContext] = None,
) -> Dict[str, Any]:
    return {
        "resourceMetrics": [
            {
                "resource": {"attributes": _resource(cfg)},
                "scopeMetrics": [
                    {
                        "scope": {"name": "obtrace-sdk-python", "version": "1.0.0"},
                        "metrics": [
                            {
                                "name": metric_name,
                                "unit": unit,
                                "gauge": {
                                    "dataPoints": [
                                        {
                                            "timeUnixNano": _now_unix_nano_str(),
                                            "asDouble": float(value),
                                            "attributes": _attrs(ctx.attrs if ctx else None),
                                        }
                                    ]
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }


def build_span_payload(
    cfg: ObtraceConfig,
    name: str,
    trace_id: str,
    span_id: str,
    start_unix_nano: str,
    end_unix_nano: str,
    status_code: Optional[int] = None,
    status_message: str = "",
    attrs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": _resource(cfg)},
                "scopeSpans": [
                    {
                        "scope": {"name": "obtrace-sdk-python", "version": "1.0.0"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": span_id,
                                "name": name,
                                "kind": 3,
                                "startTimeUnixNano": start_unix_nano,
                                "endTimeUnixNano": end_unix_nano,
                                "attributes": _attrs(attrs),
                                "status": {
                                    "code": 2 if (status_code is not None and status_code >= 400) else 1,
                                    "message": status_message,
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }
