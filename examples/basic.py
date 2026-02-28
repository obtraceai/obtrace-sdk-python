from obtrace_sdk import ObtraceClient, ObtraceConfig

client = ObtraceClient(
    ObtraceConfig(
        api_key="devkey",
        ingest_base_url="https://inject.obtrace.ai",
        service_name="python-example",
        tenant_id="tenant-dev",
        project_id="project-dev",
        app_id="python",
        env="dev",
        debug=True,
    )
)

client.log("info", "python sdk initialized")
client.metric("python.example.metric", 1)
client.span("python.example.span")
client.flush()
