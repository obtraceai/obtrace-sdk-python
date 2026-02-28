# HTTP Instrumentation

## requests

```python
import requests
from obtrace_sdk.http import instrument_requests

ob_request = instrument_requests(client, requests.request)
ob_request("GET", "https://httpbin.org/status/200")
```

## httpx

```python
from obtrace_sdk.http import instrument_httpx

ob_request = instrument_httpx(client, httpx_client.request)
await ob_request("GET", "https://httpbin.org/status/200")
```
