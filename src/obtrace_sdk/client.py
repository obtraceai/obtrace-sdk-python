from __future__ import annotations

import atexit
import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .context import ensure_propagation_headers, random_hex
from .otlp import build_logs_payload, build_metric_payload, build_span_payload
from .semantic_metrics import is_semantic_metric
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
        self._circuit_failures = 0
        self._circuit_open_until = 0.0
        atexit.register(self.flush)
        self._auto_instrument()

    def _auto_instrument(self) -> None:
        from .logging_handler import install_logging_hook
        install_logging_hook(self)

    def __enter__(self) -> ObtraceClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.flush()

    @staticmethod
    def _truncate(s: str, max_len: int) -> str:
        if len(s) <= max_len:
            return s
        return s[:max_len] + "...[truncated]"

    def log(self, level: str, message: str, context: Optional[SDKContext] = None) -> None:
        self._enqueue("/otlp/v1/logs", build_logs_payload(self.cfg, level, self._truncate(message, 32768), context))

    def metric(self, name: str, value: float, unit: str = "1", context: Optional[SDKContext] = None) -> None:
        if self.cfg.validate_semantic_metrics and self.cfg.debug and not is_semantic_metric(name):
            print(f"[obtrace-sdk-python] non-canonical metric name: {name}")
        self._enqueue("/otlp/v1/metrics", build_metric_payload(self.cfg, self._truncate(name, 1024), value, unit, context))

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

        truncated_name = self._truncate(name, 32768)
        if attrs:
            attrs = {k: self._truncate(v, 4096) if isinstance(v, str) else v for k, v in attrs.items()}

        self._enqueue(
            "/otlp/v1/traces",
            build_span_payload(self.cfg, truncated_name, t, s, start, end, status_code, status_message, attrs),
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
            now = time.time()
            if now < self._circuit_open_until:
                return
            half_open = self._circuit_failures >= 5
            if half_open:
                batch = self._queue[:1]
                self._queue = self._queue[1:]
            else:
                batch = list(self._queue)
                self._queue.clear()

        for item in batch:
            try:
                self._send(item)
                with self._lock:
                    if self._circuit_failures > 0:
                        if self.cfg.debug:
                            print("[obtrace-sdk-python] circuit breaker closed")
                        self._circuit_failures = 0
                        self._circuit_open_until = 0.0
            except Exception:  # noqa: BLE001
                with self._lock:
                    self._circuit_failures += 1
                    if self._circuit_failures >= 5:
                        self._circuit_open_until = time.time() + 30.0
                        if self.cfg.debug:
                            print("[obtrace-sdk-python] circuit breaker opened")
                if self.cfg.debug:
                    import traceback
                    traceback.print_exc()

    def shutdown(self) -> None:
        self.flush()

    def _enqueue(self, endpoint: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            if len(self._queue) >= self.cfg.max_queue_size:
                if self.cfg.debug:
                    print(f"[obtrace-sdk-python] queue full, dropping oldest item")
                self._queue.pop(0)
            self._queue.append(_Queued(endpoint=endpoint, payload=payload))

    def _send(self, item: _Queued) -> None:
        try:
            body = json.dumps(item.payload).encode("utf-8")
        except (TypeError, ValueError):
            if self.cfg.debug:
                print(f"[obtrace-sdk-python] failed to serialize payload for {item.endpoint}")
            return

        req = urllib.request.Request(
            url=f"{self.cfg.ingest_base_url.rstrip('/')}{item.endpoint}",
            method="POST",
            data=body,
            headers={
                **self.cfg.default_headers,
                "Authorization": f"Bearer {self.cfg.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.request_timeout_sec) as res:
                code = int(getattr(res, "status", 200))
                if code >= 300 and self.cfg.debug:
                    print(f"[obtrace-sdk-python] status={code} endpoint={item.endpoint}")
        except (urllib.error.URLError, TypeError, ValueError, OSError) as exc:
            if self.cfg.debug:
                print(f"[obtrace-sdk-python] send failed endpoint={item.endpoint} err={exc}")
