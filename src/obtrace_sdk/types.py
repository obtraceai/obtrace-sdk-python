from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(slots=True)
class ObtraceConfig:
    api_key: str
    ingest_base_url: str
    service_name: str
    service_version: str = "0.0.0"
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    app_id: Optional[str] = None
    env: Optional[str] = None
    request_timeout_sec: float = 5.0
    validate_semantic_metrics: bool = False
    debug: bool = False
    auto_instrument_http: bool = True
    default_headers: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class SDKContext:
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    session_id: Optional[str] = None
    route_template: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    attrs: Dict[str, Any] = field(default_factory=dict)
