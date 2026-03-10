class SemanticMetrics:
    THROUGHPUT = "http_requests_total"
    ERROR_RATE = "http_5xx_total"
    LATENCY_P95 = "latency_p95"
    RUNTIME_CPU_UTILIZATION = "runtime.cpu.utilization"
    RUNTIME_MEMORY_USAGE = "runtime.memory.usage"
    RUNTIME_THREAD_COUNT = "runtime.thread.count"
    RUNTIME_GC_PAUSE = "runtime.gc.pause"
    RUNTIME_EVENTLOOP_LAG = "runtime.eventloop.lag"
    CLUSTER_CPU_UTILIZATION = "cluster.cpu.utilization"
    CLUSTER_MEMORY_USAGE = "cluster.memory.usage"
    CLUSTER_NODE_COUNT = "cluster.node.count"
    CLUSTER_POD_COUNT = "cluster.pod.count"
    DB_OPERATION_LATENCY = "db.operation.latency"
    DB_CLIENT_ERRORS = "db.client.errors"
    DB_CONNECTIONS_USAGE = "db.connections.usage"
    MESSAGING_CONSUMER_LAG = "messaging.consumer.lag"
    WEB_VITAL_LCP = "web.vital.lcp"
    WEB_VITAL_FCP = "web.vital.fcp"
    WEB_VITAL_INP = "web.vital.inp"
    WEB_VITAL_CLS = "web.vital.cls"
    WEB_VITAL_TTFB = "web.vital.ttfb"
    USER_ACTIONS = "obtrace.sim.web.react.actions"


def is_semantic_metric(name: str) -> bool:
    return name in {
        SemanticMetrics.THROUGHPUT,
        SemanticMetrics.ERROR_RATE,
        SemanticMetrics.LATENCY_P95,
        SemanticMetrics.RUNTIME_CPU_UTILIZATION,
        SemanticMetrics.RUNTIME_MEMORY_USAGE,
        SemanticMetrics.RUNTIME_THREAD_COUNT,
        SemanticMetrics.RUNTIME_GC_PAUSE,
        SemanticMetrics.RUNTIME_EVENTLOOP_LAG,
        SemanticMetrics.CLUSTER_CPU_UTILIZATION,
        SemanticMetrics.CLUSTER_MEMORY_USAGE,
        SemanticMetrics.CLUSTER_NODE_COUNT,
        SemanticMetrics.CLUSTER_POD_COUNT,
        SemanticMetrics.DB_OPERATION_LATENCY,
        SemanticMetrics.DB_CLIENT_ERRORS,
        SemanticMetrics.DB_CONNECTIONS_USAGE,
        SemanticMetrics.MESSAGING_CONSUMER_LAG,
        SemanticMetrics.WEB_VITAL_LCP,
        SemanticMetrics.WEB_VITAL_FCP,
        SemanticMetrics.WEB_VITAL_INP,
        SemanticMetrics.WEB_VITAL_CLS,
        SemanticMetrics.WEB_VITAL_TTFB,
        SemanticMetrics.USER_ACTIONS,
    }
