from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from .client import ObtraceClient
from .types import SDKContext


def instrument_requests(client: ObtraceClient, request_func: Callable[..., Any]) -> Callable[..., Any]:
    def wrapped(method: str, url: str, **kwargs: Any) -> Any:
        started = time.time()
        trace = client.span(f"http.client {method.upper()}", attrs={"http.method": method.upper(), "http.url": url})

        headers = dict(kwargs.pop("headers", {}) or {})
        headers = client.inject_propagation(headers, trace_id=trace["trace_id"], span_id=trace["span_id"])
        kwargs["headers"] = headers

        try:
            res = request_func(method, url, **kwargs)
            dur_ms = int((time.time() - started) * 1000)
            client.log(
                "info",
                f"requests {method.upper()} {url} -> {getattr(res, 'status_code', 200)}",
                SDKContext(
                    trace_id=trace["trace_id"],
                    span_id=trace["span_id"],
                    method=method.upper(),
                    endpoint=url,
                    status_code=int(getattr(res, "status_code", 200)),
                    attrs={"duration_ms": dur_ms},
                ),
            )
            return res
        except Exception as exc:  # noqa: BLE001
            dur_ms = int((time.time() - started) * 1000)
            client.log(
                "error",
                f"requests {method.upper()} {url} failed: {exc}",
                SDKContext(
                    trace_id=trace["trace_id"],
                    span_id=trace["span_id"],
                    method=method.upper(),
                    endpoint=url,
                    attrs={"duration_ms": dur_ms},
                ),
            )
            raise

    return wrapped


def instrument_httpx(client: ObtraceClient, request_func: Callable[..., Any]) -> Callable[..., Any]:
    async def wrapped(method: str, url: str, **kwargs: Any) -> Any:
        started = time.time()
        trace = client.span(f"http.client {method.upper()}", attrs={"http.method": method.upper(), "http.url": url})

        headers = dict(kwargs.pop("headers", {}) or {})
        headers = client.inject_propagation(headers, trace_id=trace["trace_id"], span_id=trace["span_id"])
        kwargs["headers"] = headers

        try:
            res = await request_func(method, url, **kwargs)
            dur_ms = int((time.time() - started) * 1000)
            client.log(
                "info",
                f"httpx {method.upper()} {url} -> {getattr(res, 'status_code', 200)}",
                SDKContext(
                    trace_id=trace["trace_id"],
                    span_id=trace["span_id"],
                    method=method.upper(),
                    endpoint=url,
                    status_code=int(getattr(res, "status_code", 200)),
                    attrs={"duration_ms": dur_ms},
                ),
            )
            return res
        except Exception as exc:  # noqa: BLE001
            dur_ms = int((time.time() - started) * 1000)
            client.log(
                "error",
                f"httpx {method.upper()} {url} failed: {exc}",
                SDKContext(
                    trace_id=trace["trace_id"],
                    span_id=trace["span_id"],
                    method=method.upper(),
                    endpoint=url,
                    attrs={"duration_ms": dur_ms},
                ),
            )
            raise

    return wrapped


def fastapi_middleware(client: ObtraceClient):
    async def middleware(request: Any, call_next: Callable[..., Any]) -> Any:
        started = time.time()
        trace = client.span(
            f"http.server {getattr(request, 'method', 'GET')}",
            attrs={"http.method": getattr(request, "method", "GET"), "http.route": str(getattr(request, "url", ""))},
        )
        try:
            response = await call_next(request)
            dur_ms = int((time.time() - started) * 1000)
            client.log(
                "info",
                f"fastapi {request.method} {request.url.path} {response.status_code}",
                SDKContext(
                    trace_id=trace["trace_id"],
                    span_id=trace["span_id"],
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code,
                    attrs={"duration_ms": dur_ms},
                ),
            )
            return response
        except Exception as exc:  # noqa: BLE001
            dur_ms = int((time.time() - started) * 1000)
            client.log(
                "error",
                f"fastapi request failed: {exc}",
                SDKContext(
                    trace_id=trace["trace_id"],
                    span_id=trace["span_id"],
                    method=getattr(request, "method", "GET"),
                    endpoint=str(getattr(request, "url", "")),
                    attrs={"duration_ms": dur_ms},
                ),
            )
            raise

    return middleware


def flask_before_after(client: ObtraceClient):
    def before() -> Dict[str, Any]:
        started = time.time()
        trace = client.span("http.server request")
        return {"started": started, "trace": trace}

    def after(meta: Dict[str, Any], method: str, path: str, status_code: int) -> None:
        dur_ms = int((time.time() - meta["started"]) * 1000)
        tr = meta["trace"]
        client.log(
            "info",
            f"flask {method} {path} {status_code}",
            SDKContext(
                trace_id=tr["trace_id"],
                span_id=tr["span_id"],
                method=method,
                endpoint=path,
                status_code=status_code,
                attrs={"duration_ms": dur_ms},
            ),
        )

    return before, after
