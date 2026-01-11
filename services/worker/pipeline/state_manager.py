"""Pipeline 状态管理器

负责管理 Pipeline 执行过程中的状态信息。
遵循单一职责原则，只负责状态跟踪，不包含数据存储或业务逻辑。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from core.db.models import get_beijing_time
from core.logging_config import setup_logging

logger = setup_logging("worker.pipeline.state_manager")


@dataclass
class StepExecutionRecord:
    """步骤执行记录"""
    step_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "RUNNING"  # RUNNING, COMPLETED, FAILED
    error: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """获取执行时长（秒）"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class PipelineStateManager:
    """Pipeline 状态管理器

    职责：
    - 记录步骤执行状态
    - 跟踪执行进度
    - 计算执行时间

    不负责：
    - 数据存储（由 PipelineData 负责）
    - 数据库操作（由 JobStatusUpdater 负责）
    - 业务逻辑执行
    """

    def __init__(self, job_id: int):
        """初始化状态管理器

        Args:
            job_id: 任务ID
        """
        self.job_id = job_id
        self.started_at: datetime = get_beijing_time()
        self.executed_steps: List[str] = []
        self.step_records: dict[str, StepExecutionRecord] = {}

    def mark_step_started(self, step_name: str) -> None:
        """标记步骤开始

        Args:
            step_name: 步骤名称
        """
        self.executed_steps.append(step_name)
        self.step_records[step_name] = StepExecutionRecord(
            step_name=step_name,
            started_at=get_beijing_time(),
            status="RUNNING"
        )
        logger.info(
            f"[StateManager] 步骤开始: {step_name} "
            f"(job_id={self.job_id}, 已执行步骤数={len(self.executed_steps)})"
        )

    def mark_step_completed(self, step_name: str) -> None:
        """标记步骤完成

        Args:
            step_name: 步骤名称
        """
        if step_name in self.step_records:
            execution_record = self.step_records[step_name]
            execution_record.completed_at = get_beijing_time()
            execution_record.status = "COMPLETED"

        logger.info(
            f"[StateManager] 步骤完成: {step_name} "
            f"(job_id={self.job_id}, "
            f"耗时={self.step_records[step_name].duration:.2f}秒)"
        )

    def mark_step_failed(
        self,
        step_name: str,
        error: str
    ) -> None:
        """标记步骤失败

        Args:
            step_name: 步骤名称
            error: 错误信息
        """
        if step_name in self.step_records:
            execution_record = self.step_records[step_name]
            execution_record.completed_at = get_beijing_time()
            execution_record.status = "FAILED"
            execution_record.error = error

        logger.error(
            f"[StateManager] 步骤失败: {step_name} "
            f"(job_id={self.job_id}), error={error}"
        )

    def get_step_status(self, step_name: str) -> Optional[str]:
        """获取步骤状态

        Args:
            step_name: 步骤名称

        Returns:
            Optional[str]: 步骤状态，如果步骤不存在返回 None
        """
        execution_record = self.step_records.get(step_name)
        return execution_record.status if execution_record else None

    def get_step_duration(self, step_name: str) -> Optional[float]:
        """获取步骤执行时长

        Args:
            step_name: 步骤名称

        Returns:
            Optional[float]: 执行时长（秒），如果步骤未完成返回 None
        """
        execution_record = self.step_records.get(step_name)
        return execution_record.duration if execution_record else None

    def get_total_duration(self) -> float:
        """获取总执行时长（秒）

        Returns:
            float: 从开始到现在的秒数
        """
        return (get_beijing_time() - self.started_at).total_seconds()

    def get_failed_step(self) -> Optional[str]:
        """获取失败的步骤

        Returns:
            Optional[str]: 失败的步骤名称，如果没有失败返回 None
        """
        for step_name, record in self.step_records.items():
            if record.status == "FAILED":
                return step_name
        return None

    def get_step_summary(self) -> dict:
        """获取步骤执行摘要

        Returns:
            dict: 包含步骤执行统计的字典
        """
        total = len(self.step_records)
        completed = sum(1 for r in self.step_records.values() if r.status == "COMPLETED")
        failed = sum(1 for r in self.step_records.values() if r.status == "FAILED")
        running = sum(1 for r in self.step_records.values() if r.status == "RUNNING")

        return {
            "total_steps": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "total_duration": self.get_total_duration(),
        }

    def to_dict(self) -> dict:
        """转换为字典格式（用于日志和调试）

        Returns:
            dict: 状态管理器数据的字典表示
        """
        return {
            "job_id": self.job_id,
            "started_at": self.started_at.isoformat(),
            "executed_steps": self.executed_steps,
            "step_records": {
                name: {
                    "status": record.status,
                    "started_at": record.started_at.isoformat(),
                    "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                    "duration": record.duration,
                    "error": record.error,
                }
                for name, record in self.step_records.items()
            },
            "summary": self.get_step_summary(),
        }


__all__ = [
    "PipelineStateManager",
    "StepExecutionRecord",
]
