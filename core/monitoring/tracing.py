"""分布式链路追踪模块

支持与 Jaeger/Zipkin 集成的分布式链路追踪功能。
"""

import functools
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Dict, Generator, Optional, TypeVar

from core.config import MonitoringConfig, get_app_config
from core.logging_config import get_logger

logger = get_logger(__name__)

# 类型变量
F = TypeVar('F', bound=Callable)

# 获取应用配置
app_config = get_app_config()
SERVICE_NAME = app_config.APP_NAME

# 追踪上下文变量
_trace_id_ctx: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
_span_id_ctx: ContextVar[Optional[str]] = ContextVar('span_id', default=None)
_parent_span_id_ctx: ContextVar[Optional[str]] = ContextVar('parent_span_id', default=None)

# 全局配置
_tracing_enabled = MonitoringConfig.DEFAULT_TRACING_ENABLED
_sample_rate = MonitoringConfig.DEFAULT_TRACING_SAMPLE_RATE


class Span:
    """分布式追踪 Span

    表示一个操作的时间范围和元数据。
    """

    def __init__(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        service_name: str = SERVICE_NAME,
    ):
        self.name = name
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.service_name = service_name
        self.start_time = None
        self.end_time = None
        self.tags: Dict[str, Any] = {}
        self.logs: list = []
        self.status = "started"

    def start(self) -> 'Span':
        """启动 Span"""
        self.start_time = time.time()
        self.status = "started"
        # 设置上下文
        _trace_id_ctx.set(self.trace_id)
        _span_id_ctx.set(self.span_id)
        _parent_span_id_ctx.set(self.parent_span_id)
        return self

    def finish(self) -> None:
        """完成 Span"""
        self.end_time = time.time()
        self.status = "finished"
        duration = self.end_time - self.start_time
        logger.debug(
            f"Span finished: {self.name}",
            extra={
                "trace_id": self.trace_id,
                "span_id": self.span_id,
                "parent_span_id": self.parent_span_id,
                "duration": duration,
                "tags": self.tags,
            }
        )

    def set_tag(self, key: str, value: Any) -> 'Span':
        """设置标签"""
        self.tags[key] = value
        return self

    def set_tags(self, tags: Dict[str, Any]) -> 'Span':
        """批量设置标签"""
        self.tags.update(tags)
        return self

    def log(self, message: str, level: str = "info") -> 'Span':
        """添加日志"""
        self.logs.append({
            "timestamp": time.time(),
            "message": message,
            "level": level,
        })
        return self

    def set_error(self, error: Exception) -> 'Span':
        """记录错误"""
        self.set_tag("error", True)
        self.set_tag("error.message", str(error))
        self.set_tag("error.type", type(error).__name__)
        self.log(f"Error: {str(error)}", level="error")
        return self

    def get_context(self) -> Dict[str, str]:
        """获取追踪上下文"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id or "",
        }

    def get_duration(self) -> Optional[float]:
        """获取持续时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class SpanContext:
    """Span 上下文管理器

    用于自动管理 Span 的生命周期。
    """

    def __init__(
        self,
        name: str,
        service_name: str = SERVICE_NAME,
        tags: Optional[Dict[str, Any]] = None,
        log_enabled: bool = True,
    ):
        self.name = name
        self.service_name = service_name
        self.tags = tags or {}
        self.log_enabled = log_enabled
        self.span: Optional[Span] = None

    def __enter__(self) -> Span:
        if not _tracing_enabled:
            return None  # type: ignore

        # 检查是否采样
        import random
        if random.random() > _sample_rate:
            return None  # type: ignore

        # 获取父 Span ID
        parent_span_id = _span_id_ctx.get()
        trace_id = _trace_id_ctx.get()

        # 创建并启动 Span
        self.span = Span(
            name=self.name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            service_name=self.service_name,
        )
        self.span.start()

        # 设置标签
        if self.tags:
            self.span.set_tags(self.tags)

        if self.log_enabled:
            logger.info(
                f"Span started: {self.name}",
                extra={
                    "trace_id": self.span.trace_id,
                    "span_id": self.span.span_id,
                    "parent_span_id": self.span.parent_span_id,
                }
            )

        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.span is None:
            return

        # 记录错误
        if exc_val is not None:
            self.span.set_error(exc_val)

        self.span.finish()


def init_tracing(
    enabled: bool = MonitoringConfig.DEFAULT_TRACING_ENABLED,
    sample_rate: float = MonitoringConfig.DEFAULT_TRACING_SAMPLE_RATE,
    jaeger_host: str = MonitoringConfig.DEFAULT_JAEGER_AGENT_HOST,
    jaeger_port: int = MonitoringConfig.DEFAULT_JAEGER_AGENT_PORT,
) -> None:
    """初始化分布式追踪

    Args:
        enabled: 是否启用追踪
        sample_rate: 采样率（0-1）
        jaeger_host: Jaeger Agent 主机
        jaeger_port: Jaeger Agent 端口
    """
    global _tracing_enabled, _sample_rate

    _tracing_enabled = enabled
    _sample_rate = sample_rate

    if not enabled:
        logger.info("Distributed tracing is disabled")
        return

    logger.info(
        f"Distributed tracing initialized: enabled={enabled}, "
        f"sample_rate={sample_rate}, jaeger={jaeger_host}:{jaeger_port}"
    )

    # 这里可以添加 Jaeger/Zipkin 客户端初始化代码
    # 例如：
    # try:
    #     from jaeger_client import Config
    #     config = Config(
    #         config={
    #             'sampler': {'type': 'probabilistic', 'param': sample_rate},
    #             'local_agent': {'reporting_host': jaeger_host, 'reporting_port': jaeger_port},
    #         },
    #         service_name=SERVICE_NAME,
    #     )
    #     tracer = config.initialize_tracer()
    #     logger.info("Jaeger tracer initialized")
    # except Exception as e:
    #     logger.warning(f"Failed to initialize Jaeger tracer: {e}")


def trace_function(
    name: Optional[str] = None,
    service_name: str = SERVICE_NAME,
    tags: Optional[Dict[str, Any]] = None,
) -> Callable:
    """函数追踪装饰器

    Args:
        name: Span 名称（默认使用函数名）
        service_name: 服务名称
        tags: 额外的标签

    Returns:
        装饰器函数
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _tracing_enabled:
                return await func(*args, **kwargs)

            span_name = name or f"{func.__module__}.{func.__name__}"

            with SpanContext(span_name, service_name, tags) as span:
                if span:
                    span.set_tag("function", func.__name__)
                    span.set_tag("module", func.__module__)

                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    if span:
                        span.set_error(e)
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _tracing_enabled:
                return func(*args, **kwargs)

            span_name = name or f"{func.__module__}.{func.__name__}"

            with SpanContext(span_name, service_name, tags) as span:
                if span:
                    span.set_tag("function", func.__name__)
                    span.set_tag("module", func.__module__)

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    if span:
                        span.set_error(e)
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def trace_method(
    name: Optional[str] = None,
    service_name: str = SERVICE_NAME,
    tags: Optional[Dict[str, Any]] = None,
) -> Callable:
    """方法追踪装饰器

    与 trace_function 类似，但专门用于类方法。

    Args:
        name: Span 名称（默认使用方法名）
        service_name: 服务名称
        tags: 额外的标签

    Returns:
        装饰器函数
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            if not _tracing_enabled:
                return await func(self, *args, **kwargs)

            span_name = name or f"{self.__class__.__name__}.{func.__name__}"

            with SpanContext(span_name, service_name, tags) as span:
                if span:
                    span.set_tag("method", func.__name__)
                    span.set_tag("class", self.__class__.__name__)

                try:
                    result = await func(self, *args, **kwargs)
                    return result
                except Exception as e:
                    if span:
                        span.set_error(e)
                    raise

        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            if not _tracing_enabled:
                return func(self, *args, **kwargs)

            span_name = name or f"{self.__class__.__name__}.{func.__name__}"

            with SpanContext(span_name, service_name, tags) as span:
                if span:
                    span.set_tag("method", func.__name__)
                    span.set_tag("class", self.__class__.__name__)

                try:
                    result = func(self, *args, **kwargs)
                    return result
                except Exception as e:
                    if span:
                        span.set_error(e)
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


@contextmanager
def trace_context(
    name: str,
    service_name: str = SERVICE_NAME,
    tags: Optional[Dict[str, Any]] = None,
) -> Generator[Span, None, None]:
    """追踪上下文管理器

    用于手动追踪代码块。

    Args:
        name: Span 名称
        service_name: 服务名称
        tags: 额外的标签

    Yields:
        Span: 追踪 Span 对象
    """
    if not _tracing_enabled:
        yield None  # type: ignore
        return

    with SpanContext(name, service_name, tags) as span:
        yield span


def get_trace_id() -> Optional[str]:
    """获取当前追踪 ID"""
    return _trace_id_ctx.get()


def get_span_id() -> Optional[str]:
    """获取当前 Span ID"""
    return _span_id_ctx.get()


def get_trace_context() -> Dict[str, Optional[str]]:
    """获取完整的追踪上下文"""
    return {
        "trace_id": _trace_id_ctx.get(),
        "span_id": _span_id_ctx.get(),
        "parent_span_id": _parent_span_id_ctx.get(),
    }


def is_tracing_enabled() -> bool:
    """检查追踪是否启用"""
    return _tracing_enabled
