"""任务执行器

负责执行任务的核心逻辑，协调各个组件的工作。
使用新的 Pipeline 架构（可组合步骤）替代旧的静态 Pipeline。

架构更新：
- Job 表：只存储任务配置
- JobExecution 表：存储每次执行的记录
- 使用共享事件循环优化性能
"""
import json
import socket
from typing import Any, Dict, Optional

from db.models import Job
from sqlalchemy.orm import Session

# 导入新的 Pipeline
from pipeline import PipelineBuilder, PipelineContext
from pipeline.steps import (
    DigitalHumanStep,
    ImageGenerationStep,
    PostProcessingStep,
    SubtitleGenerationStep,
    TextSplitStep,
    TTSGenerationStep,
    UploadStep,
    VideoCompositionStep,
)

# 导入旧的 Pipeline（向后兼容）
from pipeline import VideoGenerationPipeline

from core.db.models import JobExecution, get_beijing_time
from core.exceptions import BatchShortException
from core.logging_config import setup_logging
# 使用共享事件循环
from core.utils import run_async

from .data_preparer import JobDataPreparer
from .file_uploader import FileUploader

logger = setup_logging("worker.job_processing.job_executor")


# 状态映射：旧状态 -> 新状态
STATUS_MAP = {
    "待处理": "PENDING",
    "处理中": "RUNNING",
    "已完成": "SUCCESS",
    "失败": "FAILED",
}

# 逆向状态映射：新状态 -> 旧状态（用于向后兼容）
REVERSE_STATUS_MAP = {
    "PENDING": "待处理",
    "RUNNING": "处理中",
    "SUCCESS": "已完成",
    "FAILED": "失败",
}


class JobExecutor:
    """任务执行器

    负责执行任务的核心流程，包括：
    - 准备任务数据
    - 构建和执行 Pipeline
    - 更新任务状态

    现在支持两种 Pipeline 模式：
    1. 新的 Pipeline（推荐）：可组合步骤模式
    2. 旧的 Pipeline：向后兼容模式

    Attributes:
        settings: 配置对象
        file_storage: 文件存储服务实例
        data_preparer: 任务数据准备器
        file_uploader: 文件上传器
        use_new_pipeline: 是否使用新的 Pipeline 模式
    """

    def __init__(
        self,
        settings: Any,
        file_storage: Any,
        data_preparer: Optional[JobDataPreparer] = None,
        file_uploader: Optional[FileUploader] = None,
        pipeline: Optional[VideoGenerationPipeline] = None,
        use_new_pipeline: bool = True,  # 新增：控制使用哪种 Pipeline
    ) -> None:
        """初始化任务执行器

        Args:
            settings: 配置对象
            file_storage: 文件存储服务实例
            data_preparer: 任务数据准备器
            file_uploader: 文件上传器
            pipeline: 旧 Pipeline 实例（向后兼容）
            use_new_pipeline: 是否使用新的 Pipeline 模式，默认 True
        """
        self.settings = settings
        self.file_storage = file_storage
        self.use_new_pipeline = use_new_pipeline

        # 依赖注入
        self.data_preparer = data_preparer or JobDataPreparer(file_storage)
        self.file_uploader = file_uploader or FileUploader(file_storage)

        # 根据模式选择 Pipeline
        if use_new_pipeline:
            # 新 Pipeline：使用可组合步骤，不需要预初始化
            self.pipeline = None
        else:
            # 旧 Pipeline：使用预定义的 VideoGenerationPipeline
            self.pipeline = pipeline or VideoGenerationPipeline(settings)

    def execute_job(self, db: Session, job: Job) -> None:
        """执行任务

        创建新的 JobExecution 记录并执行任务。

        Args:
            db: 数据库会话
            job: 任务对象

        Raises:
            BatchShortException: 任务执行失败时抛出
        """
        job_id = job.id
        logger.info(f"[execute_job] 开始执行任务 job_id={job_id}, title={job.title}")

        # 创建执行记录
        execution = self._create_execution(db, job_id)
        execution_id = execution.id

        try:
            self._run_pipeline_job(db, job, execution)
            logger.info(f"[execute_job] 任务执行成功 job_id={job_id}, execution_id={execution_id}")

        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as exc:
            self._handle_execution_exception(db, execution, job_id, execution_id, exc)
            raise

    # ========================================================================
    # 辅助方法 - 单一职责
    # ========================================================================

    def _create_execution(self, db: Session, job_id: int) -> JobExecution:
        """创建 JobExecution 记录

        Args:
            db: 数据库会话
            job_id: 任务 ID

        Returns:
            JobExecution: 创建的执行记录
        """
        worker_hostname = socket.gethostname()

        execution = JobExecution(
            job_id=job_id,
            status="PENDING",
            status_detail="任务已创建",
            worker_hostname=worker_hostname,
            retry_count=0,
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        logger.info(
            f"[_create_execution] 创建 JobExecution 记录 "
            f"(job_id={job_id}, execution_id={execution.id})"
        )

        return execution

    def _run_pipeline_job(self, db: Session, job: Job, execution: JobExecution) -> None:
        """运行 Pipeline 任务

        Args:
            db: 数据库会话
            job: 任务对象
            execution: 执行记录对象

        Raises:
            Exception: Pipeline 执行失败时抛出
        """
        # 更新状态为 RUNNING
        self._update_execution_status(db, execution, "RUNNING", "开始处理")

        # 根据 Pipeline 模式执行
        if self.use_new_pipeline:
            self._execute_with_new_pipeline(db, job, execution)
        else:
            self._execute_with_old_pipeline(db, job, execution)

        # 更新状态为 SUCCESS
        self._update_execution_status(db, execution, "SUCCESS", "任务执行成功")

    def _handle_execution_exception(
        self,
        db: Session,
        execution: JobExecution,
        job_id: int,
        execution_id: int,
        exc: Exception
    ) -> None:
        """处理执行异常

        Args:
            db: 数据库会话
            execution: 执行记录对象
            job_id: 任务 ID
            execution_id: 执行记录 ID
            exc: 异常对象

        Raises:
            BatchShortException: 总是抛出，包装原始异常
        """
        # 业务异常：标记为失败但不记录详细错误
        if isinstance(exc, BatchShortException):
            self._update_execution_status(
                db, execution, "FAILED", f"任务失败: {str(exc)}", str(exc)
            )
            return

        # 数据错误：提供更清晰的错误消息
        if isinstance(exc, (ValueError, KeyError, AttributeError)):
            error_msg = f"数据错误: {str(exc)}"
            self._update_execution_status(
                db, execution, "FAILED", error_msg, error_msg
            )
            logger.error(
                f"[_handle_execution_exception] 数据错误 "
                f"job_id={job_id}, execution_id={execution_id}, error={exc}",
                exc_info=True
            )
            raise BatchShortException(f"任务执行失败：{error_msg}") from exc

        # 其他异常：通用错误处理
        error_msg = f"执行异常: {str(exc)}"
        self._update_execution_status(
            db, execution, "FAILED", error_msg, error_msg
        )
        logger.exception(
            f"[_handle_execution_exception] 任务执行异常 "
            f"job_id={job_id}, execution_id={execution_id}"
        )
        raise BatchShortException(f"任务执行失败: {error_msg}") from exc

    def _execute_with_new_pipeline(self, db: Session, job: Job, execution: JobExecution) -> None:
        """使用新的 Pipeline 架构执行任务

        Args:
            db: 数据库会话
            job: 任务对象
            execution: 执行记录对象
        """
        job_id = job.id
        execution_id = execution.id
        logger.info(
            f"[_execute_with_new_pipeline] 使用新的 Pipeline 架构 "
            f"(job_id={job_id}, execution_id={execution_id})"
        )

        # 创建 Pipeline 上下文
        context = PipelineContext.from_job(job, db)
        # 传递 execution_id 到上下文
        context.execution_id = execution_id

        # 加载任务配置到上下文
        self._load_job_config_to_context(context, job, db)

        # 构建 Pipeline（根据任务配置动态组装）
        pipeline = self._build_pipeline(context)

        # 执行 Pipeline
        pipeline.execute()

        # 保存上传结果到 execution
        if context.upload_results:
            execution.result_key = json.dumps(context.upload_results)
            db.add(execution)
            db.commit()
            logger.info(
                f"[_execute_with_new_pipeline] 上传结果已保存 "
                f"(job_id={job_id}, execution_id={execution_id}, results={context.upload_results})"
            )

    def _execute_with_old_pipeline(self, db: Session, job: Job, execution: JobExecution) -> None:
        """使用旧的 Pipeline 架构执行任务（向后兼容）

        Args:
            db: 数据库会话
            job: 任务对象
            execution: 执行记录对象
        """
        job_id = job.id
        execution_id = execution.id
        logger.info(
            f"[_execute_with_old_pipeline] 使用旧的 Pipeline 架构 "
            f"(job_id={job_id}, execution_id={execution_id})"
        )

        # 准备任务数据
        job_data = self.data_preparer.prepare_job_data(db, job)

        # 执行视频生成流水线
        result_files = self._run_old_video_pipeline(job, job_data)

        if not result_files:
            raise BatchShortException("视频生成失败：流水线返回空结果")

        # 上传生成的文件
        job_result_key_data = self.file_uploader.upload_generated_files(
            job=job,
            **result_files
        )

        # 验证上传的文件
        if not self.file_uploader.validate_uploaded_files(job_result_key_data):
            raise BatchShortException("视频生成失败：缺少必要文件")

        # 保存结果到 execution
        execution.result_key = json.dumps(job_result_key_data)
        db.add(execution)
        db.commit()

    def _load_job_config_to_context(
        self,
        context: PipelineContext,
        job: Job,
        db: Session
    ) -> None:
        """加载任务配置到上下文

        Args:
            context: Pipeline 上下文
            job: 任务对象
            db: 数据库会话
        """
        # 加载语言信息
        if job.language:
            context.language_name = job.language.name
            context.language_platform = job.language.platform or "edge"

        # 加载话题配置
        if job.topic:
            context.topic_prompts = {
                "prompt_gen_images": job.topic.prompt_gen_image,
                "prompt_image_prefix": job.topic.prompt_image_prefix,
                "prompt_cover_image": job.topic.prompt_cover_image,
            }

            # 加载 LoRA 配置
            if job.topic.loraname:
                context.loras = [{
                    "name": job.topic.loraname,
                    "weight": job.topic.loraweight / 100,
                }]

        # 加载音色路径
        if job.voice:
            context.reference_audio_path = job.voice.path

        # 加载 Logo
        context.logopath = job.account.logo if job.account else None

        # 加载账户信息
        context.account = job.account

        logger.debug(
            f"[_load_job_config_to_context] 配置加载完成 "
            f"(job_id={context.job_id}, "
            f"language={context.language_name}, "
            f"has_topic={job.topic is not None})"
        )

    def _build_pipeline(self, context: PipelineContext):
        """构建 Pipeline

        根据任务配置动态组装步骤。

        Args:
            context: Pipeline 上下文

        Returns:
            VideoPipeline: 构建好的 Pipeline
        """
        # 使用 PipelineBuilder 构建
        pipeline = VideoPipeline(context)

        # 添加基础步骤
        pipeline.add_step(TTSGenerationStep()) \
                .add_step(SubtitleGenerationStep()) \
                .add_step(TextSplitStep()) \
                .add_step(ImageGenerationStep()) \
                .add_step(VideoCompositionStep()) \
                .add_step(PostProcessingStep()) \
                .add_step(UploadStep())

        # 根据配置添加可选步骤
        # 数字人步骤（ConditionalStep 会自动判断是否执行）
        pipeline.add_step(DigitalHumanStep())

        logger.info(
            f"[_build_pipeline] Pipeline 构建完成 "
            f"(job_id={context.job_id}, 步骤数={pipeline.get_step_count()})"
        )

        return pipeline

    def _update_execution_status(
        self,
        db: Session,
        execution: JobExecution,
        status: str,
        status_detail: str,
        error_message: Optional[str] = None,
    ) -> None:
        """更新执行状态

        Args:
            db: 数据库会话
            execution: 执行记录对象
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

        db.add(execution)
        db.commit()
        db.refresh(execution)

        logger.info(
            f"[_update_execution_status] 执行状态已更新 "
            f"execution_id={execution.id}, job_id={execution.job_id}, status={status}"
        )

    # 为了向后兼容，保留旧的 _update_job_status 方法
    def _update_job_status(
        self,
        db: Session,
        job: Job,
        status: str,
        status_detail: str
    ) -> None:
        """更新任务状态（向后兼容，已废弃）

        .. deprecated::
            此方法已废弃，请使用 _update_execution_status 方法。
            保留此方法仅用于向后兼容。
        """
        # 获取或创建 JobExecution 记录
        execution = db.query(JobExecution).filter(
            JobExecution.job_id == job.id
        ).order_by(JobExecution.id.desc()).first()

        if not execution:
            # 创建新的执行记录
            import socket
            execution = JobExecution(
                job_id=job.id,
                status="PENDING",
                worker_hostname=socket.gethostname(),
                retry_count=0,
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)

        # 映射状态
        new_status = STATUS_MAP.get(status, "PENDING")

        # 更新执行状态
        self._update_execution_status(db, execution, new_status, status_detail)

    def _run_old_video_pipeline(
        self,
        job: Job,
        job_data: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """运行旧的视频生成流水线（向后兼容）

        使用共享事件循环优化性能，避免频繁创建/销毁循环。

        Args:
            job: 任务对象
            job_data: 准备好的任务数据

        Returns:
            Optional[Dict[str, str]]: 文件路径字典
        """
        job_id = job.id
        logger.info(f"[_run_old_video_pipeline] 开始执行旧 Pipeline job_id={job_id}")

        async def _run_pipeline():
            return await self.pipeline.generate_all(
                title=job.title,
                content=job.content,
                language=job_data['language_name'],
                prompt_gen_images=job_data['prompt_gen_images'],
                prompt_prefix=job_data['prompt_prefix'],
                prompt_cover_image=job_data['prompt_cover_image'],
                logopath=job_data['logopath'],
                reference_audio_path=job_data['reference_audio_path'],
                message=job_data['description'],
                speech_speed=job_data['speech_speed'],
                is_horizontal=job_data['is_horizontal'],
                loras=job_data['loras'],
                extra=job.extra,
                topic=job_data['topic_prompts'],
                user_id=str(job.user_id),
                job_id=job.id,
                platform=job_data['language_platform'],
                account=job_data['account'],
            )

        # 使用共享事件循环（性能优化）
        result = run_async(_run_pipeline, timeout=3600)

        if result and len(result) == 6:
            return {
                'logoed_video_path': result[0],
                'subtitled_video_path': result[1],
                'cover_image_path': result[2],
                'combined_video': result[3],
                'srtpath': result[4],
                'seedvc_mp3_audio': result[5],
            }
        return None

