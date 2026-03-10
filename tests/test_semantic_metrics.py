from obtrace_sdk import SemanticMetrics, is_semantic_metric


def test_semantic_metrics_expose_canonical_names() -> None:
    assert SemanticMetrics.RUNTIME_CPU_UTILIZATION == "runtime.cpu.utilization"
    assert SemanticMetrics.DB_OPERATION_LATENCY == "db.operation.latency"
    assert SemanticMetrics.WEB_VITAL_INP == "web.vital.inp"
    assert is_semantic_metric(SemanticMetrics.WEB_VITAL_INP) is True
    assert is_semantic_metric("orders.count") is False
