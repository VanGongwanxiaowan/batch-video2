"""
详细的日志记录工具，专门用于记录非数字人视频生成过程的每一步

基于统一的日志系统，但支持 job_id 字段的特殊日志格式。
"""
import logging
import os
import sys
import traceback
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from core.config import get_path_manager
from core.logging_config import setup_logging

F = TypeVar('F', bound=Callable[..., Any])


class DetailedLogger:
    """详细的日志记录器，专门用于记录非数字人视频生成过程
    
    使用统一的日志系统作为基础，但添加自定义格式以支持 job_id 字段。
    """
    
    def __init__(self, log_dir: Optional[str] = None) -> None:
        """
        初始化详细日志记录器
        
        Args:
            log_dir: 日志文件目录（如果为None，使用PathManager的默认日志目录）
        """
        # 使用统一的日志系统创建基础logger
        service_name = "worker.detailed_logger"
        path_manager = get_path_manager()
        
        # 如果指定了自定义日志目录，使用它；否则使用PathManager的默认日志目录
        if log_dir:
            self.log_dir = Path(log_dir)
            self.log_dir.mkdir(exist_ok=True)
            log_file = self.log_dir / "non_human_detailed.log"
        else:
            self.log_dir = path_manager.logs_dir
            log_file = self.log_dir / "non_human_detailed.log"
        
        # 使用统一的日志系统创建基础logger
        self.logger = setup_logging(
            service_name,
            log_level="DEBUG",
            log_to_file=False,  # 我们将添加自定义的文件handler
            path_manager=path_manager
        )
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加handler
        if not any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
            # 文件handler - 详细日志（支持job_id字段）
            file_handler = logging.FileHandler(
                log_file, 
                encoding='utf-8',
                mode='a'
            )
            file_handler.setLevel(logging.DEBUG)
            
            # 自定义日志格式，支持job_id字段
            detailed_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [job_id: %(job_id)s] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(detailed_format)
            self.logger.addHandler(file_handler)
        
        # 控制台handler - 使用统一格式
        if not any(isinstance(h, logging.StreamHandler) for h in self.logger.handlers):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            # 控制台使用标准格式（不包含job_id，因为它需要在extra中提供）
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
    
    def log_step(
        self, 
        job_id: str, 
        step_name: str, 
        message: str, 
        level: str = "INFO", 
        **kwargs: Any
    ) -> None:
        """
        记录一个步骤的执行
        
        Args:
            job_id: 任务ID
            step_name: 步骤名称
            message: 消息内容
            level: 日志级别
            **kwargs: 额外的上下文信息
        """
        # 创建日志记录
        log_record = logging.LogRecord(
            name=self.logger.name,
            level=getattr(logging, level.upper()),
            pathname="",
            lineno=0,
            msg=f"[步骤: {step_name}] {message}",
            args=(),
            exc_info=None
        )
        log_record.job_id = job_id if job_id else "NA"
        
        # 添加额外信息
        if kwargs:
            extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            log_record.msg += f" | {extra_info}"
        
        self.logger.handle(log_record)
    
    def log_file_check(
        self, 
        job_id: str, 
        step_name: str, 
        file_path: str, 
        description: str = ""
    ) -> bool:
        """
        记录文件检查结果
        
        Args:
            job_id: 任务ID
            step_name: 步骤名称
            file_path: 文件路径
            description: 描述
            
        Returns:
            bool: 文件是否存在
        """
        exists = os.path.exists(file_path) if file_path else False
        size = os.path.getsize(file_path) if exists else 0
        
        self.log_step(
            job_id=job_id,
            step_name=step_name,
            message=f"文件检查: {description}",
            level="INFO",
            file_path=file_path,
            exists=exists,
            size_bytes=size,
            size_mb=round(size / 1024 / 1024, 2) if size > 0 else 0
        )
        
        return exists
    
    def log_function_call(
        self, 
        job_id: str, 
        func_name: str, 
        **kwargs: Any
    ) -> None:
        """
        记录函数调用
        
        Args:
            job_id: 任务ID
            func_name: 函数名称
            **kwargs: 函数参数
        """
        # 从kwargs中移除job_id，避免与log_step的第一个参数冲突
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'job_id'}
        self.log_step(
            job_id=job_id,
            step_name="函数调用",
            message=f"调用函数: {func_name}",
            level="DEBUG",
            **filtered_kwargs
        )
    
    def log_function_result(
        self, 
        job_id: str, 
        func_name: str, 
        result: Any, 
        duration: Optional[float] = None
    ) -> None:
        """
        记录函数执行结果
        
        Args:
            job_id: 任务ID
            func_name: 函数名称
            result: 执行结果
            duration: 执行耗时（秒）
        """
        self.log_step(
            job_id=job_id,
            step_name="函数结果",
            message=f"函数 {func_name} 执行完成",
            level="INFO",
            result=result,
            duration_seconds=round(duration, 2) if duration else None
        )
    
    def log_error(
        self, 
        job_id: str, 
        step_name: str, 
        error: Exception, 
        traceback_str: Optional[str] = None
    ) -> None:
        """
        记录错误
        
        Args:
            job_id: 任务ID
            step_name: 步骤名称
            error: 错误信息
            traceback_str: 错误堆栈
        """
        self.log_step(
            job_id=job_id,
            step_name=step_name,
            message=f"❌ 错误: {str(error)}",
            level="ERROR",
            error_type=type(error).__name__
        )
        
        if traceback_str:
            # 使用 log_step 记录错误堆栈，保持格式一致
            log_record = logging.LogRecord(
                name=self.logger.name,
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg=f"错误堆栈:\n{traceback_str}",
                args=(),
                exc_info=None
            )
            log_record.job_id = job_id if job_id else "NA"
            self.logger.handle(log_record)
    
    def log_oss_operation(self, job_id, operation, file_path, oss_key=None, 
                         success=None, error=None, duration=None):
        """
        记录OSS操作
        
        :param job_id: 任务ID
        :param operation: 操作类型（upload/download）
        :param file_path: 本地文件路径
        :param oss_key: OSS key
        :param success: 是否成功
        :param error: 错误信息
        :param duration: 耗时
        """
        status = "✅ 成功" if success else "❌ 失败" if success is False else "⏳ 进行中"
        
        kwargs = {
            "operation": operation,
            "file_path": file_path,
            "file_exists": os.path.exists(file_path) if file_path else False,
            "status": status
        }
        
        if oss_key:
            kwargs["oss_key"] = oss_key
        if duration:
            kwargs["duration_seconds"] = round(duration, 2)
        if error:
            kwargs["error"] = str(error)
        
        self.log_step(
            job_id=job_id,
            step_name="OSS操作",
            message=f"{operation.upper()} 操作: {os.path.basename(file_path) if file_path else 'N/A'}",
            level="INFO" if success else "ERROR",
            **kwargs
        )


# 全局日志实例
_detailed_logger = None


def get_detailed_logger() -> 'DetailedLogger':
    """获取全局详细日志记录器实例
    
    Returns:
        DetailedLogger: 详细日志记录器实例
    """
    global _detailed_logger
    if _detailed_logger is None:
        _detailed_logger = DetailedLogger()
    return _detailed_logger


def log_step_decorator(step_name: str) -> Callable[[F], F]:
    """
    装饰器：自动记录函数执行步骤
    
    Args:
        step_name: 步骤名称
        
    Returns:
        Callable: 装饰器函数
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 尝试从参数中获取job_id
            job_id = kwargs.get('job_id') or kwargs.get('job_id')
            if not job_id:
                # 尝试从args中获取
                for arg in args:
                    if hasattr(arg, 'id'):
                        job_id = arg.id
                        break
            
            logger = get_detailed_logger()
            
            # 记录函数开始 - 从kwargs中移除job_id和step_name，避免与log_function_call的参数冲突
            call_kwargs = {k: v for k, v in kwargs.items() if k not in ('job_id', 'step_name')}
            logger.log_function_call(
                job_id=job_id or "NA",
                func_name=func.__name__,
                **call_kwargs
            )
            
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                
                # 记录函数完成
                logger.log_function_result(
                    job_id=job_id or "NA",
                    func_name=func.__name__,
                    result=result,
                    duration=duration
                )
                
                return result
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except Exception as e:
                # 其他异常（函数执行错误等）
                duration = (datetime.now() - start_time).total_seconds()
                logger.log_error(
                    job_id=job_id or "NA",
                    step_name=step_name,
                    error=e,
                    traceback_str=traceback.format_exc()
                )
                raise
        
        return wrapper
    return decorator

