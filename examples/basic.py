from obtrace_sdk import ObtraceClient, ObtraceConfig, SemanticMetrics

client = ObtraceClient(
    ObtraceConfig(
        api_key="devkey",
        service_name="python-example",
        tenant_id="tenant-dev",
        project_id="project-dev",
        app_id="python",
        env="dev",
        debug=True,
    )
)

client.log("info", "python sdk initialized")
client.metric(SemanticMetrics.RUNTIME_CPU_UTILIZATION, 0.41)
client.span("checkout.charge", attrs={"feature.name": "checkout", "payment.provider": "stripe"})
client.flush()
