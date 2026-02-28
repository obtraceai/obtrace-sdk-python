from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .context import ensure_propagation_headers, random_hex
from .otlp import build_logs_payload, build_metric_payload, build_span_payload
from .types import ObtraceConfig, SDKContext


@dataclass(slots=True)
class _Queued:
    endpoint: str
    payload: Dict[str, Any]


class ObtraceClient:
    def __init__(self, cfg: ObtraceConfig):
        if not cfg.api_key or not cfg.ingest_base_url or not cfg.service_name:
            raise ValueError("api_key, ingest_base_url and service_name are required")
        self.cfg = cfg
        self._queue: List[_Queued] = []
        self._lock = threading.Lock()

    def log(self, level: str, message: str, context: Optional[SDKContext] = None) -> None:
        self._enqueue("/otlp/v1/logs", build_logs_payload(self.cfg, level, message, context))

    def metric(self, name: str, value: float, unit: str = "1", context: Optional[SDKContext] = None) -> None:
        self._enqueue("/otlp/v1/metrics", build_metric_payload(self.cfg, name, value, unit, context))

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
        t = trace_id if trace_id and len(trace_id) == 32 else random_hex(16)
        s = span_id if span_id and len(span_id) == 16 else random_hex(8)
        start = start_unix_nano or str(int(time.time() * 1_000_000_000))
        end = end_unix_nano or str(int(time.time() * 1_000_000_000))

        self._enqueue(
            "/otlp/v1/traces",
            build_span_payload(self.cfg, name, t, s, start, end, status_code, status_message, attrs),
        )
        return {"trace_id": t, "span_id": s}

    def inject_propagation(
        self,
        headers: Optional[Dict[str, str]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, str]:
        return ensure_propagation_headers(headers, trace_id, span_id, session_id)

    def flush(self) -> None:
        with self._lock:
            batch = list(self._queue)
            self._queue.clear()

        for item in batch:
            self._send(item)

    def shutdown(self) -> None:
        self.flush()

    def _enqueue(self, endpoint: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            if len(self._queue) >= self.cfg.max_queue_size:
                self._queue.pop(0)
            self._queue.append(_Queued(endpoint=endpoint, payload=payload))

    def _send(self, item: _Queued) -> None:
        body = json.dumps(item.payload).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.cfg.ingest_base_url.rstrip('/')}{item.endpoint}",
            method="POST",
            data=body,
            headers={
                "Authorization": f"Bearer {self.cfg.api_key}",
                "Content-Type": "application/json",
                **self.cfg.default_headers,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.request_timeout_sec) as res:
                code = int(getattr(res, "status", 200))
                if code >= 300 and self.cfg.debug:
                    print(f"[obtrace-sdk-python] status={code} endpoint={item.endpoint}")
        except urllib.error.URLError as exc:
            if self.cfg.debug:
                print(f"[obtrace-sdk-python] send failed endpoint={item.endpoint} err={exc}")
