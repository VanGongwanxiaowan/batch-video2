"""重试装饰器和工具函数

提供统一的重试机制，替换重复的重试逻辑。

代码重构说明：
- 将重复的重试逻辑集中管理
- 提供针对不同服务的专用装饰器
- 支持指数退避和自定义重试条件
"""
import functools
import logging
import random
import time
from typing import (
    Callable,
    Optional,
    Type,
    TypeVar,
    Union,
)

from core.logging_config import setup_logging

logger = setup_logging("core.utils.retry")

T = TypeVar("T")


# ============================================================================
# 基础重试装饰器
# ============================================================================

def retry_with_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Union[Type[Exception], tuple] = Exception,
    on_retry: Optional[Callable] = None,
) -> Callable:
    """带指数退避的重试装饰器

    Args:
        max_retries: 最大重试次数（默认 5）
        base_delay: 基础延迟时间（秒，默认 1.0）
        max_delay: 最大延迟时间（秒，默认 60.0）
        exponential_base: 指数退避基数（默认 2.0）
        jitter: 是否添加随机抖动（默认 True）
        exceptions: 要捕获的异常类型（默认 Exception）
        on_retry: 重试时的回调函数

    Returns:
        装饰器函数

    Examples:
        ```python
        @retry_with_backoff(max_retries=3, base_delay=2.0)
        def unreliable_function():
            # 可能失败的函数
            pass
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            retry_count = 0
            last_exception = None

            while retry_count <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    retry_count += 1

                    if retry_count > max_retries:
                        logger.error(
                            f"[retry_with_backoff] {func.__name__} 达到最大重试次数 "
                            f"({max_retries}次)，放弃重试"
                        )
                        raise

                    # 计算延迟时间
                    delay = min(
                        base_delay * (exponential_base ** (retry_count - 1)),
                        max_delay
                    )

                    # 添加随机抖动
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"[retry_with_backoff] {func.__name__} 第 {retry_count} 次重试，"
                        f"等待 {delay:.2f} 秒后重试。错误: {exc}"
                    )

                    # 调用回调
                    if on_retry:
                        on_retry(retry_count, exc)

                    time.sleep(delay)

            # 应该不会到这里，但为了类型检查
            raise last_exception

        return wrapper
    return decorator


def retry_on_condition(
    condition: Callable[[Exception], bool],
    max_retries: int = 5,
    base_delay: float = 1.0,
) -> Callable:
    """基于条件的重试装饰器

    Args:
        condition: 判断是否应该重试的函数
        max_retries: 最大重试次数
        base_delay: 基础延迟时间

    Returns:
        装饰器函数

    Examples:
        ```python
        def is_network_error(exc):
            return isinstance(exc, (ConnectionError, TimeoutError))

        @retry_on_condition(is_network_error, max_retries=3)
        def fetch_data():
            # 网络请求函数
            pass
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            retry_count = 0
            last_exception = None

            while retry_count <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    retry_count += 1

                    if retry_count > max_retries or not condition(exc):
                        logger.error(
                            f"[retry_on_condition] {func.__name__} "
                            f"达到最大重试次数或条件不满足，放弃重试"
                        )
                        raise

                    delay = base_delay * retry_count
                    logger.warning(
                        f"[retry_on_condition] {func.__name__} 第 {retry_count} 次重试，"
                        f"等待 {delay:.2f} 秒"
                    )
                    time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


# ============================================================================
# 专用重试装饰器
# ============================================================================

def retry_for_image_generation(
    max_retries: int = 30,
    base_delay: float = 5.0,
) -> Callable:
    """图像生成重试装饰器

    专门为图像生成API设计的重试装饰器。
    图像生成可能需要较长时间，且有配额限制。

    Args:
        max_retries: 最大重试次数（默认 30）
        base_delay: 基础延迟时间（秒，默认 5.0）

    Returns:
        装饰器函数

    Examples:
        ```python
        @retry_for_image_generation(max_retries=30)
        def generate_image(prompt):
            # 图像生成函数
            pass
        ```
    """
    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=60.0,
        exponential_base=1.2,  # 较慢的指数增长
        jitter=True,
    )


def retry_for_tts(
    max_retries: int = 10,
    base_delay: float = 2.0,
) -> Callable:
    """TTS（文本转语音）重试装饰器

    专门为 TTS API 设计的重试装饰器。

    Args:
        max_retries: 最大重试次数（默认 10）
        base_delay: 基础延迟时间（秒，默认 2.0）

    Returns:
        装饰器函数

    Examples:
        ```python
        @retry_for_tts(max_retries=10)
        def synthesize_speech(text):
            # TTS 函数
            pass
        ```
    """
    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=30.0,
        exponential_base=1.5,
        jitter=True,
    )


def retry_for_http_request(
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Callable:
    """HTTP 请求重试装饰器

    专门为 HTTP 请求设计的重试装饰器。

    Args:
        max_retries: 最大重试次数（默认 3）
        base_delay: 基础延迟时间（秒，默认 1.0）

    Returns:
        装饰器函数
    """
    import requests

    network_exceptions = (
        requests.ConnectionError,
        requests.Timeout,
        requests.RequestException,
    )

    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True,
        exceptions=network_exceptions,
    )


def retry_for_file_operation(
    max_retries: int = 3,
    base_delay: float = 0.5,
) -> Callable:
    """文件操作重试装饰器

    专门为文件操作设计的重试装饰器。
    用于处理文件系统暂时不可用的情况。

    Args:
        max_retries: 最大重试次数（默认 3）
        base_delay: 基础延迟时间（秒，默认 0.5）

    Returns:
        装饰器函数
    """
    file_exceptions = (
        FileNotFoundError,
        PermissionError,
        OSError,
    )

    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=5.0,
        exponential_base=1.5,
        jitter=False,  # 文件操作不需要抖动
        exceptions=file_exceptions,
    )


# ============================================================================
# 辅助函数
# ============================================================================

def should_retry_on_http_status(status_code: int) -> bool:
    """判断 HTTP 状态码是否应该重试

    Args:
        status_code: HTTP 状态码

    Returns:
        bool: 如果应该重试返回 True

    可重试的状态码：
    - 408 Request Timeout
    - 429 Too Many Requests
    - 500 Internal Server Error
    - 502 Bad Gateway
    - 503 Service Unavailable
    - 504 Gateway Timeout
    """
    retryable_status_codes = {408, 429, 500, 502, 503, 504}
    return status_code in retryable_status_codes


def get_retry_logger(name: str) -> logging.Logger:
    """获取重试日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger: 日志记录器
    """
    return setup_logging(f"core.utils.retry.{name}")


__all__ = [
    # 基础装饰器
    "retry_with_backoff",
    "retry_on_condition",
    # 专用装饰器
    "retry_for_image_generation",
    "retry_for_tts",
    "retry_for_http_request",
    "retry_for_file_operation",
    # 辅助函数
    "should_retry_on_http_status",
    "get_retry_logger",
]
