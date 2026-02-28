from __future__ import annotations

import secrets
from typing import Dict, Optional


def random_hex(nbytes: int) -> str:
    return secrets.token_hex(nbytes)


def create_traceparent(trace_id: Optional[str] = None, span_id: Optional[str] = None) -> str:
    t = trace_id if trace_id and len(trace_id) == 32 else random_hex(16)
    s = span_id if span_id and len(span_id) == 16 else random_hex(8)
    return f"00-{t}-{s}-01"


def ensure_propagation_headers(
    headers: Optional[Dict[str, str]] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    session_id: Optional[str] = None,
    trace_header_name: str = "traceparent",
    session_header_name: str = "x-obtrace-session-id",
) -> Dict[str, str]:
    out = dict(headers or {})
    lower = {k.lower(): k for k in out.keys()}
    if trace_header_name.lower() not in lower:
        out[trace_header_name] = create_traceparent(trace_id, span_id)
    if session_id and session_header_name.lower() not in lower:
        out[session_header_name] = session_id
    return out
