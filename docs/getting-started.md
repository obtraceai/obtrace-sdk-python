# Getting Started

```bash
pip install .
```

```python
from obtrace_sdk import ObtraceClient, ObtraceConfig

client = ObtraceClient(ObtraceConfig(
    api_key="<API_KEY>",
    ingest_base_url="https://inject.obtrace.ai",
    service_name="python-api",
    env="prod"
))

client.log("info", "service started")
client.flush()
```
