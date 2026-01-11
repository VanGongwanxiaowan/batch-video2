"""监控与可观测性模块

提供完整的监控、追踪和可观测性功能：
- Prometheus 指标收集
- 分布式链路追踪 (Jaeger/Zipkin)
- 健康检查
- 日志聚合支持
- 告警功能
"""

from .alerts import (
    AlertManager,
    AlertRule,
    check_alert_rules,
    send_alert,
    setup_alerting,
)
from .health import (
    HealthCheck,
    HealthCheckRegistry,
    HealthStatus,
    check_database_health,
    check_redis_health,
    check_service_health,
)
from .metrics import (
    REQUEST_COUNT,
    REQUEST_DURATION,
    REQUEST_IN_PROGRESS,
    ERROR_COUNT,
    get_metrics_registry,
    init_metrics,
    track_request_duration,
)
from .middleware import (
    MetricsMiddleware,
    RequestIdMiddleware,
    TracingMiddleware,
    get_request_id,
)
from .tracing import (
    init_tracing,
    trace_function,
    trace_method,
)

__all__ = [
    # 健康检查
    "HealthCheck",
    "HealthCheckRegistry",
    "HealthStatus",
    "check_database_health",
    "check_redis_health",
    "check_service_health",
    # 指标
    "REQUEST_COUNT",
    "REQUEST_DURATION",
    "REQUEST_IN_PROGRESS",
    "ERROR_COUNT",
    "get_metrics_registry",
    "init_metrics",
    "track_request_duration",
    # 中间件
    "MetricsMiddleware",
    "RequestIdMiddleware",
    "TracingMiddleware",
    "get_request_id",
    # 追踪
    "init_tracing",
    "trace_function",
    "trace_method",
    # 告警
    "AlertManager",
    "AlertRule",
    "check_alert_rules",
    "send_alert",
    "setup_alerting",
]
