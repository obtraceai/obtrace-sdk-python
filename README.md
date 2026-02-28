# obtrace-sdk-python

Python backend SDK for Obtrace telemetry transport and instrumentation.

## Scope
- OTLP logs/traces/metrics transport
- Context propagation
- HTTP instrumentation (requests/httpx)
- Framework helpers (FastAPI, Flask)

## Design Principle
SDK is thin/dumb.
- No business logic authority in client SDK.
- Policy and product logic are server-side.

## Install

```bash
pip install .
```

## Configuration

Required:
- `api_key`
- `ingest_base_url`
- `service_name`

Recommended:
- `tenant_id`
- `project_id`
- `app_id`
- `env`
- `service_version`

## Quickstart

```python
from obtrace_sdk import ObtraceClient, ObtraceConfig

client = ObtraceClient(
    ObtraceConfig(
        api_key="<API_KEY>",
        ingest_base_url="https://injet.obtrace.ai",
        service_name="python-api",
        env="prod",
    )
)

client.log("info", "started")
client.metric("orders.count", 1)
client.span("job.process")
client.flush()
```

## Frameworks and HTTP

- Framework helpers: FastAPI and Flask
- HTTP instrumentation: `requests` and `httpx`
- Reference docs:
  - `docs/frameworks.md`
  - `docs/http-instrumentation.md`

## Production Hardening

1. Keep `api_key` only in server-side secret storage.
2. Use one key per environment and rotate periodically.
3. Keep fail-open behavior (telemetry must not break request flow).
4. Validate ingestion after deploy using Query Gateway and ClickHouse checks.

## Troubleshooting

- No telemetry: validate `ingest_base_url`, API key, and egress connectivity.
- Missing correlation: ensure propagation headers are injected on outbound HTTP.
- Short-lived workers: call `flush()` before process exit.

## Documentation
- Docs index: `docs/index.md`
- LLM context file: `llm.txt`
- MCP metadata: `mcp.json`

## Reference
