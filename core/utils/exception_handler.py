"""统一异常处理工具模块"""
import asyncio
import functools
import inspect
import logging
from contextlib import contextmanager
from typing import Any, Callable, Optional, TypeVar

from core.exceptions import ServiceException

F = TypeVar("F", bound=Callable[..., Any])
logger = logging.getLogger(__name__)


def handle_service_exceptions(
    service_name: str,
    operation_name: Optional[str] = None,
    raise_service_exception: bool = True,
) -> Callable[[F], F]:
    """
    装饰器：统一处理服务异常
    
    自动处理 SystemExit 和 KeyboardInterrupt，其他异常转换为 ServiceException
    
    Args:
        service_name: 服务名称（用于异常和日志）
        operation_name: 操作名称（用于日志，默认使用函数名）
        raise_service_exception: 是否将异常转换为 ServiceException
        
    Returns:
        装饰器函数
        
    Example:
        @handle_service_exceptions("IMAGE_GEN", "generate_image")
        async def generate_image(...):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            op_name = operation_name or func.__name__
            try:
                return await func(*args, **kwargs)
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except Exception as e:
                # 其他异常（服务错误等）
                error_msg = f"[{op_name}] {service_name} operation failed: {e}"
                logger.error(error_msg, exc_info=True)
                if raise_service_exception:
                    raise ServiceException(
                        f"{service_name} operation failed: {str(e)}", 
                        service_name
                    ) from e
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            op_name = operation_name or func.__name__
            try:
                return func(*args, **kwargs)
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except Exception as e:
                # 其他异常（服务错误等）
                error_msg = f"[{op_name}] {service_name} operation failed: {e}"
                logger.error(error_msg, exc_info=True)
                if raise_service_exception:
                    raise ServiceException(
                        f"{service_name} operation failed: {str(e)}", 
                        service_name
                    ) from e
                raise
        
        # 根据函数是否为协程返回对应的包装器
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator


@contextmanager
def exception_context(
    operation_name: str,
    logger_instance: Optional[logging.Logger] = None,
    reraise: bool = True,
    log_level: str = "error",
):
    """
    上下文管理器：统一异常处理上下文
    
    Args:
        operation_name: 操作名称
        logger_instance: 日志记录器实例
        reraise: 是否重新抛出异常
        log_level: 日志级别（error, warning, info）
        
    Example:
        with exception_context("process_job", logger):
            # 执行可能抛出异常的操作
            process_job(job_id)
    """
    log_func = getattr(
        logger_instance or logger,
        log_level,
        logger.error
    )
    
    try:
        yield
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        error_msg = f"[{operation_name}] Operation failed: {e}"
        log_func(error_msg, exc_info=True)
        if reraise:
            raise


def safe_execute(
    func: Callable[..., Any],
    *args: Any,
    operation_name: Optional[str] = None,
    logger_instance: Optional[logging.Logger] = None,
    default_return: Any = None,
    **kwargs: Any,
) -> Any:
    """
    安全执行函数，捕获所有异常（除了 SystemExit 和 KeyboardInterrupt）
    
    Args:
        func: 要执行的函数
        *args: 函数位置参数
        operation_name: 操作名称（用于日志）
        logger_instance: 日志记录器实例
        default_return: 异常时的默认返回值
        **kwargs: 函数关键字参数
        
    Returns:
        函数返回值或默认返回值
        
    Example:
        result = safe_execute(
            risky_function,
            arg1, arg2,
            operation_name="risky_operation",
            default_return=None
        )
    """
    op_name = operation_name or func.__name__
    log = logger_instance or logger
    
    try:
        return func(*args, **kwargs)
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:
        error_msg = f"[{op_name}] Execution failed: {e}"
        log.error(error_msg, exc_info=True)
        return default_return


def handle_service_method_exceptions(
    service_name: str,
    operation_name: Optional[str] = None,
    error_handler: Optional[Callable[[Exception], Dict[str, Any]]] = None,
) -> Callable[[F], F]:
    """
    装饰器：统一处理服务方法异常（返回字典结果）
    
    适用于返回Dict[str, Any]的服务方法，自动处理异常并返回错误字典
    
    Args:
        service_name: 服务名称
        operation_name: 操作名称（用于日志，默认使用函数名）
        error_handler: 自定义错误处理函数，接收异常返回字典
        
    Returns:
        装饰器函数
        
    Example:
        @handle_service_method_exceptions("TTS", "synthesize_azure")
        async def synthesize_azure(...) -> Dict[str, Any]:
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            op_name = operation_name or func.__name__
            try:
                return await func(self, *args, **kwargs)
            except (SystemExit, KeyboardInterrupt):
                raise
            except Exception as e:
                error_msg = f"[{op_name}] {service_name} operation failed: {e}"
                logger_instance = getattr(self, 'logger', logger)
                logger_instance.error(error_msg, exc_info=True)
                
                if error_handler:
                    return error_handler(e)
                elif hasattr(self, 'handle_error'):
                    return self.handle_error(e)
                else:
                    return {
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
        
        @functools.wraps(func)
        def sync_wrapper(self: Any, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            op_name = operation_name or func.__name__
            try:
                return func(self, *args, **kwargs)
            except (SystemExit, KeyboardInterrupt):
                raise
            except Exception as e:
                error_msg = f"[{op_name}] {service_name} operation failed: {e}"
                logger_instance = getattr(self, 'logger', logger)
                logger_instance.error(error_msg, exc_info=True)
                
                if error_handler:
                    return error_handler(e)
                elif hasattr(self, 'handle_error'):
                    return self.handle_error(e)
                else:
                    return {
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
        
        # 根据函数是否为协程返回对应的包装器
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator

