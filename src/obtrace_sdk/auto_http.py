from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .context import create_traceparent, random_hex
from .types import SDKContext

if TYPE_CHECKING:
    from .client import ObtraceClient

_original_requests_send = None
_original_httpx_send = None
_original_httpx_async_send = None
_patched_requests = False
_patched_httpx = False
_patched_httpx_async = False


def _patch_requests(client: ObtraceClient) -> None:
    global _original_requests_send, _patched_requests
    if _patched_requests:
        return
    try:
        import requests
    except ImportError:
        return

    _original_requests_send = requests.Session.send

    def _instrumented_send(self: Any, request: Any, **kwargs: Any) -> Any:
        method = getattr(request, "method", "GET") or "GET"
        url = str(getattr(request, "url", ""))
        trace_id = random_hex(16)
        span_id = random_hex(8)
        traceparent = create_traceparent(trace_id, span_id)
        request.headers.setdefault("traceparent", traceparent)

        started = time.time()
        try:
            response = _original_requests_send(self, request, **kwargs)
            dur_ms = int((time.time() - started) * 1000)
            status = getattr(response, "status_code", 0)
            client.span(
                f"http.client {method.upper()} {url}",
                trace_id=trace_id,
                span_id=span_id,
                start_unix_nano=str(int(started * 1_000_000_000)),
                end_unix_nano=str(int(time.time() * 1_000_000_000)),
                status_code=status,
                attrs={"http.method": method.upper(), "http.url": url, "http.status_code": status, "duration_ms": dur_ms},
            )
            client.log(
                "info",
                f"requests {method.upper()} {url} -> {status}",
                SDKContext(
                    trace_id=trace_id,
                    span_id=span_id,
                    method=method.upper(),
                    endpoint=url,
                    status_code=status,
                    attrs={"duration_ms": dur_ms},
                ),
            )
            return response
        except Exception as exc:
            dur_ms = int((time.time() - started) * 1000)
            client.span(
                f"http.client {method.upper()} {url}",
                trace_id=trace_id,
                span_id=span_id,
                start_unix_nano=str(int(started * 1_000_000_000)),
                end_unix_nano=str(int(time.time() * 1_000_000_000)),
                status_code=500,
                status_message=str(exc),
                attrs={"http.method": method.upper(), "http.url": url, "duration_ms": dur_ms},
            )
            client.log(
                "error",
                f"requests {method.upper()} {url} failed: {exc}",
                SDKContext(
                    trace_id=trace_id,
                    span_id=span_id,
                    method=method.upper(),
                    endpoint=url,
                    attrs={"duration_ms": dur_ms},
                ),
            )
            raise

    requests.Session.send = _instrumented_send  # type: ignore[assignment]
    _patched_requests = True


def _patch_httpx(client: ObtraceClient) -> None:
    global _original_httpx_send, _patched_httpx
    if _patched_httpx:
        return
    try:
        import httpx
    except ImportError:
        return

    _original_httpx_send = httpx.Client.send

    def _instrumented_send(self: Any, request: Any, **kwargs: Any) -> Any:
        method = str(getattr(request, "method", "GET"))
        url = str(getattr(request, "url", ""))
        trace_id = random_hex(16)
        span_id = random_hex(8)
        traceparent = create_traceparent(trace_id, span_id)
        if hasattr(request, "headers"):
            request.headers.setdefault("traceparent", traceparent)

        started = time.time()
        try:
            response = _original_httpx_send(self, request, **kwargs)
            dur_ms = int((time.time() - started) * 1000)
            status = getattr(response, "status_code", 0)
            client.span(
                f"http.client {method.upper()} {url}",
                trace_id=trace_id,
                span_id=span_id,
                start_unix_nano=str(int(started * 1_000_000_000)),
                end_unix_nano=str(int(time.time() * 1_000_000_000)),
                status_code=status,
                attrs={"http.method": method.upper(), "http.url": url, "http.status_code": status, "duration_ms": dur_ms},
            )
            client.log(
                "info",
                f"httpx {method.upper()} {url} -> {status}",
                SDKContext(
                    trace_id=trace_id,
                    span_id=span_id,
                    method=method.upper(),
                    endpoint=url,
                    status_code=status,
                    attrs={"duration_ms": dur_ms},
                ),
            )
            return response
        except Exception as exc:
            dur_ms = int((time.time() - started) * 1000)
            client.span(
                f"http.client {method.upper()} {url}",
                trace_id=trace_id,
                span_id=span_id,
                start_unix_nano=str(int(started * 1_000_000_000)),
                end_unix_nano=str(int(time.time() * 1_000_000_000)),
                status_code=500,
                status_message=str(exc),
                attrs={"http.method": method.upper(), "http.url": url, "duration_ms": dur_ms},
            )
            client.log(
                "error",
                f"httpx {method.upper()} {url} failed: {exc}",
                SDKContext(
                    trace_id=trace_id,
                    span_id=span_id,
                    method=method.upper(),
                    endpoint=url,
                    attrs={"duration_ms": dur_ms},
                ),
            )
            raise

    httpx.Client.send = _instrumented_send  # type: ignore[assignment]
    _patched_httpx = True


def _patch_httpx_async(client: ObtraceClient) -> None:
    global _original_httpx_async_send, _patched_httpx_async
    if _patched_httpx_async:
        return
    try:
        import httpx
    except ImportError:
        return

    _original_httpx_async_send = httpx.AsyncClient.send

    async def _instrumented_async_send(self: Any, request: Any, **kwargs: Any) -> Any:
        method = str(getattr(request, "method", "GET"))
        url = str(getattr(request, "url", ""))
        trace_id = random_hex(16)
        span_id = random_hex(8)
        traceparent = create_traceparent(trace_id, span_id)
        if hasattr(request, "headers"):
            request.headers.setdefault("traceparent", traceparent)

        started = time.time()
        try:
            response = await _original_httpx_async_send(self, request, **kwargs)
            dur_ms = int((time.time() - started) * 1000)
            status = getattr(response, "status_code", 0)
            client.span(
                f"http.client {method.upper()} {url}",
                trace_id=trace_id,
                span_id=span_id,
                start_unix_nano=str(int(started * 1_000_000_000)),
                end_unix_nano=str(int(time.time() * 1_000_000_000)),
                status_code=status,
                attrs={"http.method": method.upper(), "http.url": url, "http.status_code": status, "duration_ms": dur_ms},
            )
            client.log(
                "info",
                f"httpx.async {method.upper()} {url} -> {status}",
                SDKContext(
                    trace_id=trace_id,
                    span_id=span_id,
                    method=method.upper(),
                    endpoint=url,
                    status_code=status,
                    attrs={"duration_ms": dur_ms},
                ),
            )
            return response
        except Exception as exc:
            dur_ms = int((time.time() - started) * 1000)
            client.span(
                f"http.client {method.upper()} {url}",
                trace_id=trace_id,
                span_id=span_id,
                start_unix_nano=str(int(started * 1_000_000_000)),
                end_unix_nano=str(int(time.time() * 1_000_000_000)),
                status_code=500,
                status_message=str(exc),
                attrs={"http.method": method.upper(), "http.url": url, "duration_ms": dur_ms},
            )
            client.log(
                "error",
                f"httpx.async {method.upper()} {url} failed: {exc}",
                SDKContext(
                    trace_id=trace_id,
                    span_id=span_id,
                    method=method.upper(),
                    endpoint=url,
                    attrs={"duration_ms": dur_ms},
                ),
            )
            raise

    httpx.AsyncClient.send = _instrumented_async_send  # type: ignore[assignment]
    _patched_httpx_async = True


def install_http_instrumentation(client: ObtraceClient) -> None:
    _patch_requests(client)
    _patch_httpx(client)
    _patch_httpx_async(client)


def _unpatch_requests() -> None:
    global _original_requests_send, _patched_requests
    if not _patched_requests:
        return
    try:
        import requests
        requests.Session.send = _original_requests_send  # type: ignore[assignment]
    except ImportError:
        pass
    _original_requests_send = None
    _patched_requests = False


def _unpatch_httpx() -> None:
    global _original_httpx_send, _patched_httpx
    if not _patched_httpx:
        return
    try:
        import httpx
        httpx.Client.send = _original_httpx_send  # type: ignore[assignment]
    except ImportError:
        pass
    _original_httpx_send = None
    _patched_httpx = False


def _unpatch_httpx_async() -> None:
    global _original_httpx_async_send, _patched_httpx_async
    if not _patched_httpx_async:
        return
    try:
        import httpx
        httpx.AsyncClient.send = _original_httpx_async_send  # type: ignore[assignment]
    except ImportError:
        pass
    _original_httpx_async_send = None
    _patched_httpx_async = False


def uninstall_http_instrumentation() -> None:
    _unpatch_requests()
    _unpatch_httpx()
    _unpatch_httpx_async()
