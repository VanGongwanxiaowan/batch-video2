"""异步工具模块

提供共享事件循环管理、asyncio 集成工具等。
用于解决频繁创建/销毁事件循环导致的性能问题。
"""
import asyncio
import threading
from typing import Any, Callable, Optional, TypeVar

from core.logging_config import setup_logging

logger = setup_logging("core.utils.asyncio_helpers")

T = TypeVar("T")


# ============================================================================
# 共享事件循环管理器
# ============================================================================

class _SharedEventLoopManager:
    """共享事件循环管理器

    提供单个长期运行的事件循环，用于在非异步上下文中执行异步代码。
    避免频繁创建/销毁事件循环带来的性能开销。

    线程安全：使用线程锁保护内部状态。
    """

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._initialized = False

    def _run_loop_forever(self) -> None:
        """在后台线程中运行事件循环"""
        try:
            self._loop.run_forever()
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获
            raise
        except Exception as e:
            logger.error(f"[SharedEventLoop] 事件循环异常: {e}", exc_info=True)

    def get_loop(self) -> asyncio.AbstractEventLoop:
        """获取共享事件循环

        如果尚未初始化，则创建新的事件循环并在后台线程中运行。

        Returns:
            共享的事件循环实例

        线程安全。
        """
        if not self._initialized:
            with self._lock:
                # 双重检查锁定
                if not self._initialized:
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)

                    # 在后台线程中运行事件循环
                    self._thread = threading.Thread(
                        target=self._run_loop_forever,
                        name="SharedEventLoopThread",
                        daemon=True
                    )
                    self._thread.start()
                    self._initialized = True

                    logger.info("[SharedEventLoop] 共享事件循环已初始化")

        return self._loop

    def run_coroutine(
        self,
        coro: Callable[..., T],
        *args: Any,
        timeout: Optional[float] = None,
        **kwargs: Any
    ) -> T:
        """在共享循环中运行协程

        Args:
            coro: 协程函数
            *args: 位置参数
            timeout: 超时时间（秒）
            **kwargs: 关键字参数

        Returns:
            协程的返回值

        Raises:
            TimeoutError: 超时
            Exception: 协程执行失败
        """
        loop = self.get_loop()

        # 如果已有参数，先创建协程对象
        if args or kwargs:
            actual_coro = coro(*args, **kwargs)
        else:
            actual_coro = coro

        future = asyncio.run_coroutine_threadsafe(actual_coro, loop)

        try:
            return future.result(timeout=timeout)
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获
            raise
        except Exception as e:
            logger.error(f"[SharedEventLoop] 协程执行失败: {e}", exc_info=True)
            raise

    def shutdown(self) -> None:
        """关闭共享事件循环

        通常在应用关闭时调用。
        """
        with self._lock:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
            self._initialized = False
            logger.info("[SharedEventLoop] 共享事件循环已关闭")


# 全局单例
_shared_loop_manager = _SharedEventLoopManager()


def get_shared_loop() -> asyncio.AbstractEventLoop:
    """获取共享事件循环

    这是便捷函数，推荐在大多数情况下使用。

    Returns:
        共享的事件循环实例
    """
    return _shared_loop_manager.get_loop()


def run_in_shared_loop(
    coro: Callable[..., T],
    *args: Any,
    timeout: Optional[float] = None,
    **kwargs: Any
) -> T:
    """在共享事件循环中运行协程

    Args:
        coro: 协程函数
        *args: 位置参数
        timeout: 超时时间（秒）
        **kwargs: 关键字参数

    Returns:
        协程的返回值

    Example:
        >>> async def my_async_func(x: int) -> int:
        ...     return x * 2
        >>> result = run_in_shared_loop(my_async_func, 5)  # returns 10
    """
    return _shared_loop_manager.run_coroutine(coro, *args, timeout=timeout, **kwargs)


def run_async(
    coro: Callable[..., T],
    *args: Any,
    timeout: Optional[float] = None,
    **kwargs: Any
) -> T:
    """运行异步函数（便捷别名）

    与 run_in_shared_loop 相同，提供更简洁的名称。

    Args:
        coro: 协程函数
        *args: 位置参数
        timeout: 超时时间（秒）
        **kwargs: 关键字参数

    Returns:
        协程的返回值
    """
    return run_in_shared_loop(coro, *args, timeout=timeout, **kwargs)


def shutdown_shared_loop() -> None:
    """关闭共享事件循环

    通常在应用关闭时调用。
    """
    _shared_loop_manager.shutdown()


# ============================================================================
# 便捷装饰器
# ============================================================================

def async_to_sync(timeout: Optional[float] = None):
    """将异步函数转换为同步函数的装饰器

    使用共享事件循环执行异步代码。

    Args:
        timeout: 超时时间（秒）

    Example:
        >>> @async_to_sync(timeout=30)
        ... async def fetch_data(url: str) -> dict:
        ...     async with aiohttp.ClientSession() as session:
        ...         async with session.get(url) as response:
        ...             return await response.json()
        >>> # 现在可以同步调用
        >>> data = fetch_data("https://api.example.com")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            return run_in_shared_loop(func, *args, timeout=timeout, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 共享循环管理
    "get_shared_loop",
    "run_in_shared_loop",
    "run_async",
    "shutdown_shared_loop",
    # 装饰器
    "async_to_sync",
]
