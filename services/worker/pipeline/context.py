"""Pipeline 数据容器

重构后的 PipelineContext：
- 使用组合模式将职责分离到专门的类
- 遵循单一职责原则
- 保持向后兼容性

新的架构：
- PipelineData: 纯数据容器
- PipelineStateManager: 状态管理
- JobStatusUpdater: 数据库状态更新
- PipelineContext: 组合以上组件，提供统一接口

代码重构说明：
- 使用 core.config.status.ExecutionStatus 枚举替换硬编码状态字符串
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from sqlalchemy.orm import Session

from core.config.status import ExecutionStatus, get_status
from core.db.models import Job, get_beijing_time
from core.logging_config import setup_logging

from .data import PipelineData
from .state_manager import PipelineStateManager
from .status_updater import JobStatusUpdater

logger = setup_logging("worker.pipeline.context")


class PipelineContext:
    """Pipeline 上下文 (重构版)

    现在使用组合模式，将职责分离到专门的类：
    - data: PipelineData - 数据存储
    - state_manager: PipelineStateManager - 状态跟踪
    - status_updater: JobStatusUpdater - 数据库更新

    向后兼容：
    - 保留所有原有属性和方法的访问接口
    - 内部委托给专门的组件处理

    Attributes:
        job_id: 任务ID
        db: 数据库会话
        job: 任务对象
        execution: 执行记录对象
    """

    # ========================================================================
    # 初始化
    # ========================================================================

    def __init__(
        self,
        job_id: int,
        db: Session,
        job: Optional[Job] = None,
        execution: Optional['JobExecution'] = None,
        workspace_dir: Optional[Path] = None,
        user_id: Optional[str] = None,
    ):
        """初始化 Pipeline 上下文

        Args:
            job_id: 任务ID
            db: 数据库会话
            job: 任务对象
            execution: JobExecution 对象
            workspace_dir: 工作目录
            user_id: 用户ID
        """
        # 核心标识
        self.job_id = job_id
        self.db = db
        self.job = job
        self.execution = execution

        # 组合专门的组件
        self._data = PipelineData(
            job_id=job_id,
            workspace_dir=workspace_dir,
            user_id=user_id,
        )
        self._state_manager = PipelineStateManager(job_id)
        self._status_updater = JobStatusUpdater(db, job_id) if execution else None

    # ========================================================================
    # 类方法工厂
    # ========================================================================

    @classmethod
    def from_job(
        cls,
        job: Job,
        db: Session,
        execution: Optional['JobExecution'] = None
    ) -> "PipelineContext":
        """从任务对象创建上下文

        Args:
            job: 任务对象
            db: 数据库会话
            execution: JobExecution 对象

        Returns:
            PipelineContext: 初始化好的上下文
        """
        from config import path_manager

        # 创建工作目录
        workspace_dir = path_manager.worker_jobs_dir / str(job.user_id).replace("-", "") / str(job.id)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        context = cls(
            job_id=job.id,
            db=db,
            job=job,
            execution=execution,
            workspace_dir=workspace_dir,
            user_id=str(job.user_id) if job.user_id else None,
        )

        # 从任务对象加载数据到 _data
        context._data.title = job.title or ""
        context._data.content = job.content or ""
        context._data.speech_speed = job.speech_speed or 0.9
        context._data.is_horizontal = job.is_horizontal if job.is_horizontal is not None else True
        context._data.extra = job.extra or {}

        return context

    # ========================================================================
    # 数据访问属性 (向后兼容)
    # ========================================================================

    @property
    def workspace_dir(self) -> Optional[Path]:
        return self._data.workspace_dir

    @workspace_dir.setter
    def workspace_dir(self, value: Optional[Path]) -> None:
        self._data.workspace_dir = value

    @property
    def user_id(self) -> Optional[str]:
        return self._data.user_id

    @user_id.setter
    def user_id(self, value: Optional[str]) -> None:
        self._data.user_id = value

    @property
    def title(self) -> str:
        return self._data.title

    @title.setter
    def title(self, value: str) -> None:
        self._data.title = value

    @property
    def content(self) -> str:
        return self._data.content

    @content.setter
    def content(self, value: str) -> None:
        self._data.content = value

    @property
    def language_name(self) -> str:
        return self._data.language_name

    @language_name.setter
    def language_name(self, value: str) -> None:
        self._data.language_name = value

    @property
    def language_platform(self) -> str:
        return self._data.language_platform

    @language_platform.setter
    def language_platform(self, value: str) -> None:
        self._data.language_platform = value

    @property
    def speech_speed(self) -> float:
        return self._data.speech_speed

    @speech_speed.setter
    def speech_speed(self, value: float) -> None:
        self._data.speech_speed = value

    @property
    def is_horizontal(self) -> bool:
        return self._data.is_horizontal

    @is_horizontal.setter
    def is_horizontal(self, value: bool) -> None:
        self._data.is_horizontal = value

    @property
    def reference_audio_path(self) -> Optional[str]:
        return self._data.reference_audio_path

    @reference_audio_path.setter
    def reference_audio_path(self, value: Optional[str]) -> None:
        self._data.reference_audio_path = value

    @property
    def logopath(self) -> Optional[str]:
        return self._data.logopath

    @logopath.setter
    def logopath(self, value: Optional[str]) -> None:
        self._data.logopath = value

    @property
    def topic_prompts(self) -> Optional[Dict[str, Any]]:
        return self._data.topic_prompts

    @topic_prompts.setter
    def topic_prompts(self, value: Optional[Dict[str, Any]]) -> None:
        self._data.topic_prompts = value

    @property
    def loras(self) -> Optional[list]:
        return self._data.loras

    @loras.setter
    def loras(self, value: Optional[list]) -> None:
        self._data.loras = value

    @property
    def extra(self) -> Dict[str, Any]:
        return self._data.extra

    @extra.setter
    def extra(self, value: Dict[str, Any]) -> None:
        self._data.extra = value

    @property
    def account(self) -> Optional[Any]:
        return self._data.account

    @account.setter
    def account(self, value: Optional[Any]) -> None:
        self._data.account = value

    # 步骤中间结果
    @property
    def audio_path(self) -> Optional[str]:
        return self._data.audio_path

    @audio_path.setter
    def audio_path(self, value: Optional[str]) -> None:
        self._data.audio_path = value

    @property
    def srt_path(self) -> Optional[str]:
        return self._data.srt_path

    @srt_path.setter
    def srt_path(self, value: Optional[str]) -> None:
        self._data.srt_path = value

    @property
    def splits(self) -> list:
        return self._data.splits

    @splits.setter
    def splits(self, value: list) -> None:
        self._data.splits = value

    @property
    def image_paths(self) -> list:
        return self._data.image_paths

    @image_paths.setter
    def image_paths(self, value: list) -> None:
        self._data.image_paths = value

    @property
    def selected_images(self) -> list:
        return self._data.selected_images

    @selected_images.setter
    def selected_images(self, value: list) -> None:
        self._data.selected_images = value

    @property
    def combined_video(self) -> Optional[str]:
        return self._data.combined_video

    @combined_video.setter
    def combined_video(self, value: Optional[str]) -> None:
        self._data.combined_video = value

    @property
    def human_video_path(self) -> Optional[str]:
        return self._data.human_video_path

    @human_video_path.setter
    def human_video_path(self, value: Optional[str]) -> None:
        self._data.human_video_path = value

    @property
    def final_video_path(self) -> Optional[str]:
        return self._data.final_video_path

    @final_video_path.setter
    def final_video_path(self, value: Optional[str]) -> None:
        self._data.final_video_path = value

    @property
    def upload_results(self) -> Dict[str, str]:
        return self._data.upload_results

    @upload_results.setter
    def upload_results(self, value: Dict[str, str]) -> None:
        self._data.upload_results = value

    # 状态访问属性 (向后兼容)
    @property
    def executed_steps(self) -> list:
        return self._state_manager.executed_steps

    @property
    def failed_step_name(self) -> Optional[str]:
        """获取失败的步骤名称

        Returns:
            Optional[str]: 失败的步骤名称，如果没有失败返回 None
        """
        return self._state_manager.get_failed_step()

    @property
    def error_message(self) -> Optional[str]:
        for record in self._state_manager.step_records.values():
            if record.status == ExecutionStatus.FAILED.value:
                return record.error
        return None

    @property
    def started_at(self):
        return self._state_manager.started_at

    # ========================================================================
    # 状态管理方法 (委托给 StateManager)
    # ========================================================================

    def mark_step_started(self, step_name: str) -> None:
        """标记步骤开始"""
        self._state_manager.mark_step_started(step_name)

        # 同时更新数据库
        if self.execution and self._status_updater:
            self._status_updater.update_step_status(
                self.execution,
                step_name,
                f"正在执行: {step_name}"
            )

    def mark_step_completed(self, step_name: str) -> None:
        """标记步骤完成"""
        self._state_manager.mark_step_completed(step_name)

        if self.execution and self._status_updater:
            self._status_updater.mark_step_completed(
                self.execution,
                step_name
            )

    def mark_step_failed(self, step_name: str, error: str) -> None:
        """标记步骤失败"""
        self._state_manager.mark_step_failed(step_name, error)

        if self.execution and self._status_updater:
            self._status_updater.mark_step_failed(
                self.execution,
                step_name,
                error
            )

    def get_duration(self) -> float:
        """获取已执行时长（秒）"""
        return self._state_manager.get_total_duration()

    # ========================================================================
    # 数据库更新方法 (委托给 StatusUpdater)
    # ========================================================================

    def update_job_status(
        self,
        status: Union[str, ExecutionStatus],
        status_detail: str = ""
    ) -> None:
        """更新任务状态到数据库

        Args:
            status: 任务状态，支持字符串或 ExecutionStatus 枚举
            status_detail: 状态详情

        代码重构说明：
            支持传入 ExecutionStatus 枚举，同时保持向后兼容字符串
        """
        # 转换为字符串值（中文）
        if isinstance(status, ExecutionStatus):
            status_value = status.value
        else:
            # 使用 get_status 验证并转换
            status_value = get_status(status).value

        if self.execution and self._status_updater:
            self._status_updater.update_execution_status(
                execution=self.execution,
                status=status_value,
                status_detail=status_detail
            )

        # 同时更新 job 对象（向后兼容）
        if self.job:
            self.job.status = status_value
            self.job.status_detail = status_detail
            self.job.updated_at = get_beijing_time()
            self.db.add(self.job)
            self.db.commit()

    # ========================================================================
    # 工具方法
    # ========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志和调试）"""
        result = self._data.to_dict()
        result.update({
            "executed_steps": self.executed_steps,
            "failed_step_name": self.failed_step_name,
            "error_message": self.error_message,
            "duration_seconds": self.get_duration(),
        })
        return result

    def __str__(self) -> str:
        """字符串表示"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


__all__ = ["PipelineContext"]
