"""统一异常定义"""
from typing import Optional


class BatchShortException(Exception):
    """BatchShort系统基础异常类"""

    def __init__(self, message: str, error_code: Optional[str] = None) -> None:
        """
        初始化异常

        Args:
            message: 错误消息
            error_code: 错误代码
        """
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        super().__init__(self.message)

    def __str__(self) -> str:
        """返回异常字符串表示
        
        Returns:
            str: 格式化的异常信息
        """
        return f"[{self.error_code}] {self.message}"


class ValidationException(BatchShortException):
    """验证异常"""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        """
        初始化验证异常

        Args:
            message: 错误消息
            field: 验证失败的字段名
        """
        self.field = field
        error_code = f"VALIDATION_ERROR_{field.upper()}" if field else "VALIDATION_ERROR"
        super().__init__(message, error_code)


class ServiceException(BatchShortException):
    """服务异常基类"""

    def __init__(self, message: str, service_name: Optional[str] = None) -> None:
        """
        初始化服务异常

        Args:
            message: 错误消息
            service_name: 服务名称
        """
        self.service_name = service_name
        error_code = f"SERVICE_ERROR_{service_name.upper()}" if service_name else "SERVICE_ERROR"
        super().__init__(message, error_code)


class ServiceUnavailableException(ServiceException):
    """服务不可用异常"""

    def __init__(self, service_name: str, message: Optional[str] = None) -> None:
        """
        初始化服务不可用异常

        Args:
            service_name: 服务名称
            message: 错误消息
        """
        msg = message or f"Service {service_name} is unavailable"
        super().__init__(msg, service_name)
        self.error_code = f"SERVICE_UNAVAILABLE_{service_name.upper()}"


class ServiceTimeoutException(ServiceException):
    """服务超时异常"""

    def __init__(self, service_name: str, timeout: Optional[int] = None) -> None:
        """
        初始化服务超时异常

        Args:
            service_name: 服务名称
            timeout: 超时时间(秒)
        """
        msg = f"Service {service_name} request timeout"
        if timeout:
            msg += f" (timeout: {timeout}s)"
        super().__init__(msg, service_name)
        self.timeout = timeout
        self.error_code = f"SERVICE_TIMEOUT_{service_name.upper()}"


class FileException(BatchShortException):
    """文件操作异常"""

    def __init__(self, message: str, file_path: Optional[str] = None) -> None:
        """
        初始化文件异常

        Args:
            message: 错误消息
            file_path: 文件路径
        """
        self.file_path = file_path
        super().__init__(message, "FILE_ERROR")


class FileNotFoundException(FileException):
    """文件未找到异常"""

    def __init__(self, file_path: str) -> None:
        """
        初始化文件未找到异常

        Args:
            file_path: 文件路径
        """
        super().__init__(f"File not found: {file_path}", file_path)
        self.error_code = "FILE_NOT_FOUND"


class DatabaseException(BatchShortException):
    """数据库异常"""

    def __init__(self, message: str, operation: Optional[str] = None) -> None:
        """
        初始化数据库异常

        Args:
            message: 错误消息
            operation: 数据库操作
        """
        self.operation = operation
        error_code = f"DB_ERROR_{operation.upper()}" if operation else "DB_ERROR"
        super().__init__(message, error_code)


class ConfigurationException(BatchShortException):
    """配置异常"""

    def __init__(self, message: str, config_key: Optional[str] = None) -> None:
        """
        初始化配置异常

        Args:
            message: 错误消息
            config_key: 配置键
        """
        self.config_key = config_key
        error_code = f"CONFIG_ERROR_{config_key.upper()}" if config_key else "CONFIG_ERROR"
        super().__init__(message, error_code)


class JobException(BatchShortException):
    """任务异常"""

    def __init__(self, message: str, job_id: Optional[int] = None) -> None:
        """
        初始化任务异常

        Args:
            message: 错误消息
            job_id: 任务ID
        """
        self.job_id = job_id
        super().__init__(message, "JOB_ERROR")


class JobNotFoundException(JobException):
    """任务未找到异常"""

    def __init__(self, job_id: int) -> None:
        """
        初始化任务未找到异常

        Args:
            job_id: 任务ID
        """
        super().__init__(f"Job not found: {job_id}", job_id)
        self.error_code = "JOB_NOT_FOUND"


class JobProcessingException(JobException):
    """任务处理异常"""

    def __init__(self, message: str, job_id: Optional[int] = None) -> None:
        """
        初始化任务处理异常

        Args:
            message: 错误消息
            job_id: 任务ID
        """
        super().__init__(message, job_id)
        self.error_code = "JOB_PROCESSING_ERROR"

