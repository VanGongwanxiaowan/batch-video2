"""服务基类定义。

提供所有服务类的通用接口和基础功能。
使用泛型支持类型安全的配置对象。
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar

from core.logging_config import setup_logging

# 配置类型变量，允许子类指定具体的配置类型
ConfigType = TypeVar('ConfigType')


class BaseService(ABC, Generic[ConfigType]):
    """服务基类。
    
    所有服务类都应该继承此类，实现process方法。
    提供统一的输入验证、错误处理等功能。
    使用泛型支持类型安全的配置对象。
    
    Attributes:
        config: 配置对象（类型由ConfigType指定）
        logger: 日志记录器
    """
    
    def __init__(
        self,
        config: ConfigType,
        logger: Optional[logging.Logger] = None
    ) -> None:
        """初始化服务。
        
        Args:
            config: 配置对象，类型由ConfigType指定
            logger: 日志记录器，如果为None则使用统一日志系统创建logger
                    （logger名称为类名）
        """
        self.config: ConfigType = config
        if logger is None:
            # 使用统一的日志系统
            service_name = f"worker.services.{self.__class__.__name__}"
            # 尝试从 config 获取 path_manager（如果存在）
            path_manager = getattr(config, 'path_manager', None)
            self.logger: logging.Logger = setup_logging(
                service_name,
                log_level="INFO",
                log_to_file=True,
                path_manager=path_manager
            )
        else:
            self.logger: logging.Logger = logger
    
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据（抽象方法，子类必须实现）。
        
        Args:
            data: 输入数据字典，包含处理所需的所有信息
            
        Returns:
            Dict[str, Any]: 处理结果字典，通常包含success字段表示是否成功
            
        Raises:
            子类可以抛出任何异常，建议使用core.exceptions中的异常类型
        """
        pass
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """验证输入数据。
        
        子类可以重写此方法以实现自定义验证逻辑。
        默认实现总是返回True（不进行验证）。
        
        Args:
            data: 输入数据字典
            
        Returns:
            bool: 如果验证通过返回True，否则返回False
            
        Raises:
            ValidationException: 子类可以抛出验证异常
        """
        return True
    
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """统一错误处理。
        
        记录错误日志并返回标准化的错误响应。
        
        Args:
            error: 异常对象
            
        Returns:
            Dict[str, Any]: 标准化的错误响应字典，包含：
                - success: False
                - error: 错误消息字符串
        """
        self.logger.error(
            f"Error in {self.__class__.__name__}: {error}",
            exc_info=True
        )
        return {
            "success": False,
            "error": str(error)
        }

