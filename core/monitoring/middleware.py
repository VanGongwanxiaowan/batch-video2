"""监控中间件模块

提供 FastAPI 监控相关的中间件：
- 指标收集中间件
- 请求 ID 中间件
- 链路追踪中间件
"""

import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.config import MonitoringConfig
from core.logging_config import get_logger
from .metrics import (
    REQUEST_COUNT,
    REQUEST_DURATION,
    REQUEST_IN_PROGRESS,
    ERROR_COUNT,
    is_metrics_enabled,
)

logger = get_logger(__name__)

# 请求 ID 上下文变量
_request_id_ctx: Optional[str] = None


def get_request_id() -> str:
    """获取当前请求 ID"""
    global _request_id_ctx
    return _request_id_ctx or "system"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """请求 ID 中间件

    为每个请求生成唯一的请求 ID，并添加到请求状态和响应头中。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成或获取请求 ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # 设置请求 ID 到全局上下文
        global _request_id_ctx
        _request_id_ctx = request_id

        # 将请求 ID 添加到请求状态
        request.state.request_id = request_id

        # 处理请求
        response = await call_next(request)

        # 将请求 ID 添加到响应头
        response.headers["X-Request-ID"] = request_id

        # 清理上下文
        _request_id_ctx = None

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Prometheus 指标收集中间件

    自动收集 HTTP 请求的指标：
    - 请求计数
    - 请求持续时间
    - 当前进行中的请求
    - 错误计数
    """

    def __init__(
        self,
        app: ASGIApp,
        service_name: str = "batchshort",
        skip_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.service_name = service_name
        self.skip_paths = set(skip_paths or [
            "/health",
            "/ready",
            "/metrics",
        ])

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳过不需要监控的路径
        if request.url.path in self.skip_paths:
            return await call_next(request)

        if not is_metrics_enabled():
            return await call_next(request)

        # 解析请求信息
        method = request.method
        # 标准化路径（替换路径参数）
        path = self._normalize_path(request.url.path)

        # 增加进行中的请求计数
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).inc()

        # 记录开始时间
        start_time = time.time()

        try:
            # 处理请求
            response = await call_next(request)

            # 记录成功的请求
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status=str(response.status_code),
            ).inc()

            # 记录请求持续时间
            duration = time.time() - start_time
            REQUEST_DURATION.labels(
                method=method,
                endpoint=path,
            ).observe(duration)

            return response

        except Exception as exc:
            # 记录失败的请求
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status="500",
            ).inc()

            # 记录错误
            ERROR_COUNT.labels(
                error_type=type(exc).__name__,
                service=self.service_name,
            ).inc()

            # 记录持续时间
            duration = time.time() - start_time
            REQUEST_DURATION.labels(
                method=method,
                endpoint=path,
            ).observe(duration)

            raise

        finally:
            # 减少进行中的请求计数
            REQUEST_IN_PROGRESS.labels(
                method=method,
                endpoint=path,
            ).dec()

    def _normalize_path(self, path: str) -> str:
        """标准化路径，替换路径参数为占位符

        例如：
            /api/v1/jobs/123 -> /api/v1/jobs/{id}
            /api/v1/accounts/456/posts -> /api/v1/accounts/{id}/posts
        """
        # 定义路径参数的模式
        path_patterns = [
            "/jobs/",
            "/accounts/",
            "/voices/",
            "/topics/",
            "/languages/",
            "/splits/",
            "/users/",
        ]

        # 如果是静态文件或健康检查路径，直接返回
        if path.startswith(("/static", "/health", "/ready", "/metrics")):
            return path

        # 替换路径参数
        normalized = path
        for pattern in path_patterns:
            if pattern in normalized:
                # 找到参数的位置并替换
                parts = normalized.split(pattern)
                if len(parts) > 1:
                    # 获取参数后的部分
                    remaining = parts[1].split("/", 1)
                    param_id = remaining[0]
                    # 如果是数字或 UUID，替换为 {id}
                    if param_id.isdigit() or len(param_id) > 20:
                        if len(remaining) > 1:
                            normalized = f"{parts[0]}{pattern}{{id}}/{remaining[1]}"
                        else:
                            normalized = f"{parts[0]}{pattern}{{id}}"

        return normalized


class TracingMiddleware(BaseHTTPMiddleware):
    """链路追踪中间件

    为每个请求创建追踪 span，支持与 Jaeger/Zipkin 集成。
    """

    def __init__(
        self,
        app: ASGIApp,
        service_name: str = "batchshort",
        tracing_enabled: bool = False,
    ):
        super().__init__(app)
        self.service_name = service_name
        self.tracing_enabled = tracing_enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.tracing_enabled:
            return await call_next(request)

        # 获取请求 ID
        request_id = request.state.request_id if hasattr(request.state, "request_id") else str(uuid.uuid4())

        # 记录追踪信息
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
            }
        )

        # 处理请求
        response = await call_next(request)

        # 记录响应信息
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            }
        )

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件

    记录所有 HTTP 请求的详细信息，包括请求和响应。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取请求 ID
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # 记录请求开始
        logger.info(
            f"HTTP {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )

        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # 记录成功响应
            logger.info(
                f"HTTP {request.method} {request.url.path} - {response.status_code} - {duration:.3f}s",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration": duration,
                }
            )

            return response

        except Exception as exc:
            duration = time.time() - start_time

            # 记录错误
            logger.error(
                f"HTTP {request.method} {request.url.path} - Error: {str(exc)}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration,
                    "error_type": type(exc).__name__,
                }
            )
            raise
