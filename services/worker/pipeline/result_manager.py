"""步骤结果管理器

负责管理 Pipeline 执行过程中各步骤的结果。

这是从 VideoPipeline 类中提取出来的专门模块，用于存储和查询步骤结果。
"""
from typing import TYPE_CHECKING, Optional

from core.logging_config import setup_logging

if TYPE_CHECKING:
    from .results import StepResult

logger = setup_logging("worker.pipeline.result_manager")


class StepResultManager:
    """步骤结果管理器

    管理 Pipeline 执行过程中各步骤的结果。

    提供：
    - 结果存储
    - 结果查询（按步骤名称）
    - 批量结果获取

    Attributes:
        step_results: 步骤结果字典 {step_name: StepResult}
    """

    def __init__(self):
        """初始化结果管理器"""
        self.step_results: dict = {}

    def store(self, step_name: str, result: "StepResult") -> None:
        """存储步骤结果

        Args:
            step_name: 步骤名称
            result: 步骤执行结果
        """
        self.step_results[step_name] = result
        logger.debug(f"[StepResultManager] 存储步骤结果: {step_name}")

    def get(self, step_name: str) -> Optional["StepResult"]:
        """获取指定步骤的结果

        Args:
            step_name: 步骤名称

        Returns:
            Optional[StepResult]: 步骤结果，如果不存在则返回 None
        """
        return self.step_results.get(step_name)

    def get_all(self) -> dict:
        """获取所有步骤的结果

        Returns:
            dict: 所有步骤的结果字典的副本
        """
        return self.step_results.copy()

    def clear(self) -> None:
        """清空所有结果"""
        self.step_results.clear()
        logger.debug("[StepResultManager] 清空所有步骤结果")

    def has_result(self, step_name: str) -> bool:
        """检查是否存在指定步骤的结果

        Args:
            step_name: 步骤名称

        Returns:
            bool: 如果存在结果返回 True，否则返回 False
        """
        return step_name in self.step_results

    def __len__(self) -> int:
        """获取结果数量"""
        return len(self.step_results)

    def __contains__(self, step_name: str) -> bool:
        """支持 'in' 操作符"""
        return step_name in self.step_results


__all__ = [
    "StepResultManager",
]
