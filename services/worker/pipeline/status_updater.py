"""任务状态更新器

负责将任务状态更新到数据库。
遵循单一职责原则，只负责数据库状态更新。
"""
from typing import Optional

from sqlalchemy.orm import Session

from core.db.models import Job, JobExecution, get_beijing_time
from core.logging_config import setup_logging

logger = setup_logging("worker.pipeline.status_updater")


class JobStatusUpdater:
    """任务状态更新器

    职责：
    - 更新 JobExecution 记录的状态
    - 记录执行时间戳
    - 记录错误信息

    不负责：
    - 业务逻辑判断
    - 状态管理逻辑
    - 数据存储
    """

    def __init__(self, db: Session, job_id: int):
        """初始化状态更新器

        Args:
            db: 数据库会话
            job_id: 任务ID
        """
        self.db = db
        self.job_id = job_id

    def update_execution_status(
        self,
        execution: JobExecution,
        status: str,
        status_detail: str,
        error_message: Optional[str] = None,
    ) -> None:
        """更新执行记录的状态

        Args:
            execution: JobExecution 对象
            status: 新状态 (PENDING, RUNNING, SUCCESS, FAILED)
            status_detail: 状态详情
            error_message: 错误信息（可选）
        """
        execution.status = status
        execution.status_detail = status_detail
        execution.error_message = error_message

        # 更新时间戳
        now = get_beijing_time()
        execution.updated_at = now

        # 根据状态更新 started_at 或 finished_at
        if status == "RUNNING" and execution.started_at is None:
            execution.started_at = now
        elif status in ("SUCCESS", "FAILED"):
            execution.finished_at = now

        self._save(execution)

    def update_step_status(
        self,
        execution: JobExecution,
        step_name: str,
        status_detail: str
    ) -> None:
        """更新步骤执行状态

        Args:
            execution: JobExecution 对象
            step_name: 步骤名称
            status_detail: 状态详情
        """
        # 更新状态详情，包含步骤信息
        self.update_execution_status(
            execution=execution,
            status="RUNNING",
            status_detail=f"正在执行: {step_name}"
        )

    def mark_step_completed(
        self,
        execution: JobExecution,
        step_name: str
    ) -> None:
        """标记步骤完成

        Args:
            execution: JobExecution 对象
            step_name: 步骤名称
        """
        logger.debug(
            f"[StatusUpdater] 步骤完成: {step_name} "
            f"(execution_id={execution.id}, job_id={self.job_id})"
        )

    def mark_step_failed(
        self,
        execution: JobExecution,
        step_name: str,
        error: str
    ) -> None:
        """标记步骤失败

        Args:
            execution: JobExecution 对象
            step_name: 步骤名称
            error: 错误信息
        """
        self.update_execution_status(
            execution=execution,
            status="FAILED",
            status_detail=f"步骤失败: {step_name}",
            error_message=error
        )

    def _save(self, execution: JobExecution) -> None:
        """保存执行记录到数据库

        Args:
            execution: JobExecution 对象
        """
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        logger.debug(
            f"[StatusUpdater] 状态已保存 "
            f"(execution_id={execution.id}, job_id={self.job_id}, "
            f"status={execution.status})"
        )


__all__ = [
    "JobStatusUpdater",
]
