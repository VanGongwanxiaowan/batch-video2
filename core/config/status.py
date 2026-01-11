"""执行状态枚举

提供统一的执行状态定义，替换硬编码的状态字符串。

代码重构说明：
- 将硬编码的状态字符串（"success", "failed", "processing" 等）替换为枚举
- 支持向后兼容的转换方法
- 提供状态转换验证
"""
from enum import Enum
from typing import Optional


class ExecutionStatus(str, Enum):
    """执行状态枚举

    定义 Pipeline 执行过程中所有可能的状态。

    状态值使用中文以保持向后兼容现有数据库和日志。

    Attributes:
        PENDING: 等待执行
        PROCESSING: 正在处理
        COMPLETED: 执行成功
        FAILED: 执行失败
        CANCELLED: 已取消
        TIMEOUT: 超时
        SKIPPED: 已跳过
    """
    PENDING = "等待"
    PROCESSING = "处理中"
    COMPLETED = "成功"
    FAILED = "失败"
    CANCELLED = "已取消"
    TIMEOUT = "超时"
    SKIPPED = "已跳过"

    def is_terminal(self) -> bool:
        """检查是否为终态

        终态是指状态不会再发生变化的状态。

        Returns:
            bool: 如果是终态返回 True
        """
        return self in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.SKIPPED,
        )

    def is_success(self) -> bool:
        """检查是否为成功状态

        Returns:
            bool: 如果是成功状态返回 True
        """
        return self == ExecutionStatus.COMPLETED

    def is_failure(self) -> bool:
        """检查是否为失败状态

        Returns:
            bool: 如果是失败状态返回 True
        """
        return self == ExecutionStatus.FAILED

    def can_transition_to(self, new_status: "ExecutionStatus") -> bool:
        """检查是否可以转换到新状态

        Args:
            new_status: 目标状态

        Returns:
            bool: 如果可以转换返回 True

        状态转换规则：
        - PENDING -> PROCESSING, CANCELLED
        - PROCESSING -> COMPLETED, FAILED, CANCELLED, TIMEOUT
        - 终态不能转换
        """
        # 终态不能转换
        if self.is_terminal():
            return False

        # 定义合法的状态转换
        valid_transitions = {
            ExecutionStatus.PENDING: {
                ExecutionStatus.PROCESSING,
                ExecutionStatus.CANCELLED,
            },
            ExecutionStatus.PROCESSING: {
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
                ExecutionStatus.TIMEOUT,
            },
        }

        return new_status in valid_transitions.get(self, set())

    @classmethod
    def from_legacy(cls, status: str) -> "ExecutionStatus":
        """从遗留状态字符串转换为枚举

        支持向后兼容，允许从旧的英文字符串状态转换。

        Args:
            status: 旧的状态字符串（中文或英文）

        Returns:
            ExecutionStatus: 对应的枚举值

        Raises:
            ValueError: 如果状态字符串无效

        Examples:
            >>> ExecutionStatus.from_legacy("success")
            <ExecutionStatus.COMPLETED: '成功'>
            >>> ExecutionStatus.from_legacy("成功")
            <ExecutionStatus.COMPLETED: '成功'>
        """
        # 英文到中文的映射
        legacy_mapping = {
            # 英文状态
            "pending": cls.PENDING,
            "waiting": cls.PENDING,
            "processing": cls.PROCESSING,
            "in_progress": cls.PROCESSING,
            "running": cls.PROCESSING,
            "success": cls.COMPLETED,
            "completed": cls.COMPLETED,
            "finished": cls.COMPLETED,
            "failed": cls.FAILED,
            "error": cls.FAILED,
            "cancelled": cls.CANCELLED,
            "canceled": cls.CANCELLED,
            "timeout": cls.TIMEOUT,
            "skipped": cls.SKIPPED,
        }

        # 先尝试英文映射
        status_lower = status.lower().strip()
        if status_lower in legacy_mapping:
            return legacy_mapping[status_lower]

        # 尝试直接匹配枚举值（中文）
        try:
            return cls(status)
        except ValueError:
            raise ValueError(
                f"无效的状态字符串: '{status}'. "
                f"有效值: {[s.value for s in cls]}"
            )

    def to_legacy(self, use_english: bool = False) -> str:
        """转换为遗留格式

        Args:
            use_english: 是否使用英文状态（默认 False 使用中文）

        Returns:
            str: 状态字符串

        Examples:
            >>> ExecutionStatus.COMPLETED.to_legacy()
            '成功'
            >>> ExecutionStatus.COMPLETED.to_legacy(use_english=True)
            'success'
        """
        if use_english:
            english_mapping = {
                cls.PENDING: "pending",
                cls.PROCESSING: "processing",
                cls.COMPLETED: "success",
                cls.FAILED: "failed",
                cls.CANCELLED: "cancelled",
                cls.TIMEOUT: "timeout",
                cls.SKIPPED: "skipped",
            }
            return english_mapping[self]
        return self.value


class JobStatus(str, Enum):
    """任务状态枚举

    用于 Job 数据模型的状态字段。

    这是 ExecutionStatus 的别名，保持与现有代码的兼容性。
    """
    PENDING = ExecutionStatus.PENDING.value
    PROCESSING = ExecutionStatus.PROCESSING.value
    COMPLETED = ExecutionStatus.COMPLETED.value
    FAILED = ExecutionStatus.FAILED.value
    CANCELLED = ExecutionStatus.CANCELLED.value
    TIMEOUT = ExecutionStatus.TIMEOUT.value
    SKIPPED = ExecutionStatus.SKIPPED.value

    @classmethod
    def from_execution_status(cls, status: ExecutionStatus) -> "JobStatus":
        """从 ExecutionStatus 转换

        Args:
            status: 执行状态

        Returns:
            JobStatus: 任务状态
        """
        return cls(status.value)

    def to_execution_status(self) -> ExecutionStatus:
        """转换为 ExecutionStatus

        Returns:
            ExecutionStatus: 执行状态
        """
        return ExecutionStatus(self.value)


def get_status(status: str) -> ExecutionStatus:
    """获取状态枚举的便捷函数

    自动检测输入类型并返回对应的枚举值。

    Args:
        status: 状态字符串或枚举

    Returns:
        ExecutionStatus: 状态枚举

    Examples:
        >>> get_status("success")
        <ExecutionStatus.COMPLETED: '成功'>
        >>> get_status(ExecutionStatus.COMPLETED)
        <ExecutionStatus.COMPLETED: '成功'>
    """
    if isinstance(status, ExecutionStatus):
        return status
    return ExecutionStatus.from_legacy(status)


def is_terminal_status(status: str) -> bool:
    """检查是否为终态的便捷函数

    Args:
        status: 状态字符串

    Returns:
        bool: 如果是终态返回 True
    """
    return get_status(status).is_terminal()


def is_success_status(status: str) -> bool:
    """检查是否为成功状态的便捷函数

    Args:
        status: 状态字符串

    Returns:
        bool: 如果是成功状态返回 True
    """
    return get_status(status).is_success()


def is_failure_status(status: str) -> bool:
    """检查是否为失败状态的便捷函数

    Args:
        status: 状态字符串

    Returns:
        bool: 如果是失败状态返回 True
    """
    return get_status(status).is_failure()


__all__ = [
    "ExecutionStatus",
    "JobStatus",
    "get_status",
    "is_terminal_status",
    "is_success_status",
    "is_failure_status",
]
