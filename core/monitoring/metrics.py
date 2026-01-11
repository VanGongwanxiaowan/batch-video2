"""Prometheus 指标定义和收集模块

提供 Prometheus 指标的定义、注册和收集功能。
"""

import time
from functools import wraps
from typing import Callable, Dict, List, Optional, TypeVar

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    CollectorRegistry,
    start_http_server,
    multiprocess,
)
from prometheus_client.openmetrics.exposition import generate_latest

from core.config import MonitoringConfig, get_app_config
from core.logging_config import get_logger

logger = get_logger(__name__)

# 类型变量
F = TypeVar('F', bound=Callable)

# 获取应用配置
app_config = get_app_config()
SERVICE_NAME = app_config.APP_NAME
SERVICE_VERSION = app_config.APP_VERSION

# 全局注册表
_registry: Optional[CollectorRegistry] = None
_metrics_enabled = MonitoringConfig.DEFAULT_METRICS_ENABLED
_metrics_port = MonitoringConfig.DEFAULT_METRICS_PORT


# ============= 应用信息指标 =============
APP_INFO = Info(
    'app_info',
    'Application information',
    registry=None
)


# ============= HTTP 请求指标 =============
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=None
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=None
)

REQUEST_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint'],
    registry=None
)

REQUEST_SIZE = Summary(
    'http_request_size_bytes',
    'HTTP request size',
    registry=None
)

RESPONSE_SIZE = Summary(
    'http_response_size_bytes',
    'HTTP response size',
    registry=None
)


# ============= 错误指标 =============
ERROR_COUNT = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'service'],
    registry=None
)


# ============= 业务指标 =============
JOB_COUNT = Counter(
    'jobs_total',
    'Total jobs processed',
    ['status'],
    registry=None
)

JOB_DURATION = Histogram(
    'job_duration_seconds',
    'Job processing duration',
    ['job_type'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
    registry=None
)

ACTIVE_JOBS = Gauge(
    'jobs_active',
    'Currently active jobs',
    registry=None
)


# ============= 系统指标 =============
SYSTEM_MEMORY_USAGE = Gauge(
    'system_memory_usage_bytes',
    'System memory usage',
    registry=None
)

SYSTEM_CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=None
)


# ============= 指标列表 =============
_ALL_METRICS = [
    APP_INFO,
    REQUEST_COUNT,
    REQUEST_DURATION,
    REQUEST_IN_PROGRESS,
    REQUEST_SIZE,
    RESPONSE_SIZE,
    ERROR_COUNT,
    JOB_COUNT,
    JOB_DURATION,
    ACTIVE_JOBS,
    SYSTEM_MEMORY_USAGE,
    SYSTEM_CPU_USAGE,
]


def get_metrics_registry() -> CollectorRegistry:
    """获取指标注册表"""
    global _registry
    if _registry is None:
        _registry = CollectorRegistry()
    return _registry


def init_metrics(
    service_name: str = SERVICE_NAME,
    metrics_enabled: bool = True,
    metrics_port: int = MonitoringConfig.DEFAULT_METRICS_PORT,
) -> None:
    """初始化 Prometheus 指标

    Args:
        service_name: 服务名称
        metrics_enabled: 是否启用指标收集
        metrics_port: 指标服务端口
    """
    global _metrics_enabled, _metrics_port

    _metrics_enabled = metrics_enabled
    _metrics_port = metrics_port

    if not _metrics_enabled:
        logger.info("Metrics collection is disabled")
        return

    try:
        # 获取注册表
        registry = get_metrics_registry()

        # 注册所有指标
        for metric in _ALL_METRICS:
            if metric.registry is None:
                # 将指标注册到我们的注册表
                metric._registry = registry  # type: ignore

        # 设置应用信息
        APP_INFO.info({
            'service': service_name,
            'version': SERVICE_VERSION,
        })

        # 启动指标服务器
        start_http_server(port=metrics_port, registry=registry)
        logger.info(f"Prometheus metrics initialized for {service_name} on port {metrics_port}")
        logger.info(f"Metrics available at http://0.0.0.0:{metrics_port}/metrics")

    except Exception as e:
        logger.error(f"Failed to initialize metrics: {e}", exc_info=True)


def track_request_duration(method: str, endpoint: str):
    """跟踪请求持续时间的装饰器

    Args:
        method: HTTP 方法
        endpoint: 端点路径
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _metrics_enabled:
                return await func(*args, **kwargs)

            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    status='success'
                ).inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    status='error'
                ).inc()
                ERROR_COUNT.labels(
                    error_type=type(e).__name__,
                    service=SERVICE_NAME
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                REQUEST_DURATION.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
                REQUEST_IN_PROGRESS.labels(
                    method=method,
                    endpoint=endpoint
                ).dec()

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _metrics_enabled:
                return func(*args, **kwargs)

            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    status='success'
                ).inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    status='error'
                ).inc()
                ERROR_COUNT.labels(
                    error_type=type(e).__name__,
                    service=SERVICE_NAME
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                REQUEST_DURATION.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
                REQUEST_IN_PROGRESS.labels(
                    method=method,
                    endpoint=endpoint
                ).dec()

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def increment_error_count(error_type: str, service: Optional[str] = None) -> None:
    """增加错误计数

    Args:
        error_type: 错误类型
        service: 服务名称
    """
    if not _metrics_enabled:
        return

    ERROR_COUNT.labels(
        error_type=error_type,
        service=service or SERVICE_NAME
    ).inc()


def track_job_status(status: str) -> None:
    """跟踪任务状态

    Args:
        status: 任务状态
    """
    if not _metrics_enabled:
        return

    JOB_COUNT.labels(status=status).inc()


def track_job_duration(job_type: str, duration_seconds: float) -> None:
    """跟踪任务处理时长

    Args:
        job_type: 任务类型
        duration_seconds: 处理时长（秒）
    """
    if not _metrics_enabled:
        return

    JOB_DURATION.labels(job_type=job_type).observe(duration_seconds)


def set_active_jobs(count: int) -> None:
    """设置当前活跃任务数

    Args:
        count: 活跃任务数
    """
    if not _metrics_enabled:
        return

    ACTIVE_JOBS.set(count)


def get_metrics_text() -> bytes:
    """获取 Prometheus 指标文本格式

    Returns:
        指标的文本格式
    """
    registry = get_metrics_registry()
    return generate_latest(registry)


def is_metrics_enabled() -> bool:
    """检查指标收集是否启用"""
    return _metrics_enabled
