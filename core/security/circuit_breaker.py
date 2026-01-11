"""熔断器模块

实现熔断器模式，防止级联故障。
"""
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

from core.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class CircuitBreakerState(str, Enum):
    """熔断器状态"""
    CLOSED = "closed"  # 正常状态，允许请求通过
    OPEN = "open"  # 熔断状态，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，允许部分请求测试


class CircuitBreakerOpen(Exception):
    """熔断器开启异常"""
    def __init__(
        self,
        service_name: str,
        last_failure_time: datetime,
        retry_after: Optional[float] = None,
    ):
        self.service_name = service_name
        self.last_failure_time = last_failure_time
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker is open for service: {service_name}"
        )


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5  # 失败阈值
    success_threshold: int = 2  # 成功阈值（用于半开状态）
    timeout: float = 60.0  # 熔断超时时间（秒）
    window_size: int = 60  # 滑动窗口大小（秒）
    min_calls: int = 10  # 最小调用次数


@dataclass
class CallResult:
    """调用结果"""
    success: bool
    timestamp: float
    duration: float


class SlidingWindow:
    """滑动窗口

    用于记录固定时间窗口内的调用结果
    """

    def __init__(self, window_size: int):
        self.window_size = window_size
        self.calls: list = []

    def add(self, result: CallResult) -> None:
        """添加调用结果"""
        self.calls.append(result)
        self._cleanup()

    def _cleanup(self) -> None:
        """清理过期的记录"""
        now = time.time()
        cutoff = now - self.window_size
        self.calls = [c for c in self.calls if c.timestamp > cutoff]

    def get_stats(self) -> Dict[str, Any]:
        """获取窗口统计信息"""
        if not self.calls:
            return {
                "total": 0,
                "success": 0,
                "failure": 0,
                "failure_rate": 0.0,
            }

        total = len(self.calls)
        success = sum(1 for c in self.calls if c.success)
        failure = total - success

        return {
            "total": total,
            "success": success,
            "failure": failure,
            "failure_rate": failure / total if total > 0 else 0.0,
        }


class CircuitBreaker:
    """熔断器实现

    实现熔断器模式，防止级联故障。
    """

    def __init__(
        self,
        service_name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Args:
            service_name: 服务名称
            config: 熔断器配置
        """
        self.service_name = service_name
        self.config = config or CircuitBreakerConfig()

        # 熔断器状态
        self._state = CircuitBreakerState.CLOSED
        self._last_state_change = time.time()
        self._open_until: Optional[float] = None

        # 滑动窗口
        self._window = SlidingWindow(self.config.window_size)

        # 半开状态的成功计数
        self._half_open_success_count = 0

        logger.info(
            f"Circuit breaker initialized for service: {service_name}",
            extra={
                "service": service_name,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "timeout": self.config.timeout,
                },
            }
        )

    @property
    def state(self) -> CircuitBreakerState:
        """获取当前状态"""
        # 检查是否应该从 OPEN 转换到 HALF_OPEN
        if (
            self._state == CircuitBreakerState.OPEN
            and self._open_until
            and time.time() >= self._open_until
        ):
            self._transition_to(CircuitBreakerState.HALF_OPEN)

        return self._state

    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        """转换到新状态"""
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()

        if new_state == CircuitBreakerState.OPEN:
            self._open_until = time.time() + self.config.timeout
        else:
            self._open_until = None

        if new_state == CircuitBreakerState.HALF_OPEN:
            self._half_open_success_count = 0

        logger.info(
            f"Circuit breaker state transition",
            extra={
                "service": self.service_name,
                "old_state": old_state.value,
                "new_state": new_state.value,
            }
        )

    async def call(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """执行函数调用，带有熔断保护

        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数调用结果

        Raises:
            CircuitBreakerOpen: 如果熔断器处于开启状态
        """
        # 检查熔断器状态
        current_state = self.state
        if current_state == CircuitBreakerState.OPEN:
            retry_after = int(self._open_until - time.time()) if self._open_until else None
            raise CircuitBreakerOpen(
                service_name=self.service_name,
                last_failure_time=datetime.fromtimestamp(self._last_state_change),
                retry_after=retry_after,
            )

        # 执行函数调用
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            duration = time.time() - start_time
            self._on_success(duration)
            return result

        except Exception as e:
            duration = time.time() - start_time
            self._on_failure(duration, e)
            raise

    def _on_success(self, duration: float) -> None:
        """处理成功调用"""
        result = CallResult(
            success=True,
            timestamp=time.time(),
            duration=duration,
        )
        self._window.add(result)

        # 处理半开状态
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._half_open_success_count += 1
            if self._half_open_success_count >= self.config.success_threshold:
                self._transition_to(CircuitBreakerState.CLOSED)

    def _on_failure(self, duration: float, error: Exception) -> None:
        """处理失败调用"""
        result = CallResult(
            success=False,
            timestamp=time.time(),
            duration=duration,
        )
        self._window.add(result)

        # 获取窗口统计
        stats = self._window.get_stats()

        # 检查是否应该打开熔断器
        if (
            stats["total"] >= self.config.min_calls
            and stats["failure_rate"] >= 0.5
            and stats["failure"] >= self.config.failure_threshold
        ):
            self._transition_to(CircuitBreakerState.OPEN)

        # 半开状态下任何失败都会重新打开熔断器
        elif self._state == CircuitBreakerState.HALF_OPEN:
            self._transition_to(CircuitBreakerState.OPEN)

    def get_stats(self) -> Dict[str, Any]:
        """获取熔断器统计信息"""
        window_stats = self._window.get_stats()

        return {
            "service": self.service_name,
            "state": self.state.value,
            "last_state_change": datetime.fromtimestamp(self._last_state_change).isoformat(),
            "open_until": datetime.fromtimestamp(self._open_until).isoformat() if self._open_until else None,
            "window": window_stats,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
                "window_size": self.config.window_size,
            },
        }

    def reset(self) -> None:
        """重置熔断器"""
        self._state = CircuitBreakerState.CLOSED
        self._last_state_change = time.time()
        self._open_until = None
        self._window.calls.clear()
        self._half_open_success_count = 0
        logger.info(f"Circuit breaker reset for service: {self.service_name}")


# 全局熔断器注册表
_global_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    service_name: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> CircuitBreaker:
    """获取或创建熔断器

    Args:
        service_name: 服务名称
        config: 熔断器配置

    Returns:
        CircuitBreaker: 熔断器实例
    """
    if service_name not in _global_circuit_breakers:
        _global_circuit_breakers[service_name] = CircuitBreaker(
            service_name=service_name,
            config=config,
        )
    return _global_circuit_breakers[service_name]


def reset_all_circuit_breakers() -> None:
    """重置所有熔断器"""
    for cb in _global_circuit_breakers.values():
        cb.reset()


def get_all_circuit_breaker_stats() -> Dict[str, Dict[str, Any]]:
    """获取所有熔断器的统计信息"""
    return {
        name: cb.get_stats()
        for name, cb in _global_circuit_breakers.items()
    }


# 装饰器
def with_circuit_breaker(
    service_name: str,
    config: Optional[CircuitBreakerConfig] = None,
):
    """熔断器装饰器

    Args:
        service_name: 服务名称
        config: 熔断器配置

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            cb = get_circuit_breaker(service_name, config)
            return await cb.call(func, *args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            # 同步函数需要在事件循环中运行
            cb = get_circuit_breaker(service_name, config)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(cb.call(func, *args, **kwargs))

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
