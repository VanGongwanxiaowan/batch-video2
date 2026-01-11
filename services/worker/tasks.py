"""Celery 任务模块

定义所有异步任务，包括视频生成、任务清理等。
使用 Celery 分布式任务队列实现任务处理。

架构更新：
- Job 表：只存储任务配置
- JobExecution 表：存储每次执行的记录
"""
import json
import os
import socket
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from celery import Task, shared_task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.orm import Session

# 添加项目根目录到 Python 路径
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config import settings
from core.config import (
    celery_app_config,
    celery_beat_schedule,
    get_celery_broker_url,
    get_celery_result_backend,
)
from core.db.models import Job, JobExecution, get_beijing_time
from core.exceptions import BatchShortException
from core.logging_config import setup_logging
from db.models import Job as DBJob
from db.session import db_session

from .job_processing import JobExecutor
from .job_processing.data_preparer import JobDataPreparer
from .job_processing.file_uploader import FileUploader
from .utils.oss_file_utils import FileStorage

logger = setup_logging("worker.tasks")

# ============================================================================
# Celery 应用实例
# ============================================================================

# 创建 Celery 应用
# 使用 shared_task 装饰器允许任务在多个 Celery 应用间共享
celery_app = None


def get_celery_app():
    """获取或创建 Celery 应用实例

    Returns:
        Celery: Celery 应用实例
    """
    global celery_app
    if celery_app is None:
        from celery import Celery

        celery_app = Celery(
            'batchshort_worker',
            broker=get_celery_broker_url(),
            backend=get_celery_result_backend(),
        )

        # 应用配置
        celery_app.config_from_object(celery_app_config)

        # 配置定时任务
        celery_app.conf.beat_schedule = celery_beat_schedule

        logger.info("Celery 应用初始化完成")
        logger.info(f"Broker: {get_celery_broker_url()}")
        logger.info(f"Backend: {get_celery_result_backend()}")

    return celery_app


# ============================================================================
# 自定义 Task 基类
# ============================================================================

class DatabaseTask(Task):
    """支持数据库会话的自定义 Task 基类

    提供:
    - 自动创建和关闭数据库会话
    - 任务开始/结束日志记录
    - 统一的异常处理
    """

    _db = None

    @property
    def db(self) -> Session:
        """获取数据库会话

        Returns:
            Session: 数据库会话
        """
        if self._db is None:
            self._db = db_session()
        return self._db

    def after_return(self, *args, **kwargs):
        """任务执行后清理资源"""
        # 关闭数据库会话
        if self._db is not None:
            self._db.close()
            self._db = None


# ============================================================================
# 辅助函数
# ============================================================================

def _create_job_execution(db: Session, job_id: int) -> Optional[JobExecution]:
    """创建新的 JobExecution 记录

    Args:
        db: 数据库会话
        job_id: 任务 ID

    Returns:
        JobExecution: 创建的执行记录，失败返回 None
    """
    execution = JobExecution(
        job_id=job_id,
        status="PENDING",
        status_detail="任务已创建",
        worker_hostname=socket.gethostname(),
        retry_count=0,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def _handle_task_failure(
    db: Session,
    execution: Optional[JobExecution],
    error_message: str,
    status_detail: str,
    finished: bool = True
) -> None:
    """处理任务失败的统一逻辑

    Args:
        db: 数据库会话
        execution: 执行记录对象
        error_message: 错误信息
        status_detail: 状态详情
        finished: 是否已完成
    """
    if not execution:
        return

    execution.status = "FAILED"
    execution.status_detail = status_detail
    execution.error_message = error_message

    if finished:
        execution.finished_at = get_beijing_time()

    db.add(execution)
    db.commit()


def _handle_task_retry(
    db: Session,
    execution: Optional[JobExecution],
    current_retry: int,
    max_retries: int
) -> bool:
    """处理任务重试逻辑

    Args:
        db: 数据库会话
        execution: 执行记录对象
        current_retry: 当前重试次数
        max_retries: 最大重试次数

    Returns:
        bool: 是否应该重试
    """
    if not execution or current_retry >= max_retries:
        return False

    execution.status = "PENDING"
    execution.status_detail = f"任务重试中 ({current_retry + 1}/{max_retries})"
    execution.retry_count = current_retry + 1
    db.add(execution)
    db.commit()
    return True


# ============================================================================
# 视频生成任务
# ============================================================================

@shared_task(
    bind=True,
    name='services.worker.tasks.process_video_job',
    base=DatabaseTask,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=3300,  # 55分钟软限制
    time_limit=3600,  # 1小时硬限制
)
def process_video_job(self, job_id: int) -> Dict[str, Any]:
    """处理视频生成任务

    这是核心任务，负责:
    1. 从数据库获取任务信息
    2. 创建 JobExecution 记录
    3. 执行视频生成流水线
    4. 更新执行状态

    Args:
        self: Celery 任务实例
        job_id: 任务ID

    Returns:
        Dict[str, Any]: 任务执行结果
    """
    job_id_for_log = job_id
    execution = None

    try:
        execution = _process_video_job_impl(self.db, job_id_for_log, self.max_retries)
        return {
            'job_id': job_id_for_log,
            'execution_id': execution.id,
            'status': 'success' if execution.status == 'SUCCESS' else 'failed',
            'message': '任务处理完成',
            'result_key': execution.result_key,
        }

    except SoftTimeLimitExceeded:
        return _handle_timeout(job_id_for_log, execution)

    except (SystemExit, KeyboardInterrupt):
        raise

    except BatchShortException as exc:
        _handle_task_failure(
            self.db, execution, str(exc),
            f"任务失败: {str(exc)}"
        )
        return _build_failure_result(job_id_for_log, execution, str(exc))

    except Exception as exc:
        should_retry = _handle_task_retry(
            self.db, execution, self.request.retries, self.max_retries
        )
        if should_retry:
            countdown = 2 ** self.request.retries * 60
            raise self.retry(exc=exc, countdown=countdown)

        # 达到最大重试次数
        _handle_task_failure(
            self.db, execution, str(exc),
            f"任务失败: 已达到最大重试次数 ({self.max_retries})"
        )
        return _build_failure_result(job_id_for_log, execution, f'已达到最大重试次数 - {str(exc)}')


def _process_video_job_impl(
    db: Session,
    job_id: int,
    max_retries: int
) -> JobExecution:
    """任务执行的核心实现

    Args:
        db: 数据库会话
        job_id: 任务 ID
        max_retries: 最大重试次数

    Returns:
        JobExecution: 执行记录

    Raises:
        BatchShortException: 任务执行失败时抛出
    """
    logger.info(f"[process_video_job] 开始处理任务 job_id={job_id}")

    # 查询任务
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.deleted_at == None
    ).first()

    if not job:
        raise BatchShortException(f'任务 {job_id} 不存在')

    # 检查是否有正在运行的执行记录
    _check_running_executions(db, job_id)

    # 创建新的 JobExecution 记录
    execution = _create_job_execution(db, job_id)
    logger.info(
        f"[process_video_job] 创建 JobExecution 记录 "
        f"(job_id={job_id}, execution_id={execution.id})"
    )

    # 执行任务
    _execute_job_with_components(db, job)

    # 刷新 execution 获取最新状态
    db.refresh(execution)

    logger.info(f"[process_video_job] 任务执行成功 (job_id={job_id}, execution_id={execution.id})")
    return execution


def _check_running_executions(db: Session, job_id: int) -> None:
    """检查是否有正在运行的执行记录

    Args:
        db: 数据库会话
        job_id: 任务 ID
    """
    running_execution = db.query(JobExecution).filter(
        JobExecution.job_id == job_id,
        JobExecution.status == "RUNNING"
    ).first()

    if running_execution:
        logger.warning(
            f"[process_video_job] 任务有正在运行的执行记录 "
            f"(job_id={job_id}, execution_id={running_execution.id})"
        )


def _execute_job_with_components(db: Session, job: Job) -> None:
    """使用组件执行任务

    Args:
        db: 数据库会话
        job: 任务对象
    """
    file_storage = FileStorage(settings)
    data_preparer = JobDataPreparer(file_storage)
    file_uploader = FileUploader(file_storage)
    job_executor = JobExecutor(
        settings=settings,
        file_storage=file_storage,
        data_preparer=data_preparer,
        file_uploader=file_uploader,
    )

    job_executor.execute_job(db, job)


def _handle_timeout(job_id: int, execution: Optional[JobExecution]) -> Dict[str, Any]:
    """处理超时异常

    Args:
        job_id: 任务 ID
        execution: 执行记录对象

    Returns:
        Dict[str, Any]: 失败结果
    """
    logger.error(f"[process_video_job] 任务执行超时 (软限制) job_id={job_id}")
    _handle_task_failure(
        None, execution, "任务执行超时",
        "任务执行超时"
    )
    return _build_failure_result(job_id, execution, "任务执行超时")


def _build_failure_result(
    job_id: int,
    execution: Optional[JobExecution],
    message: str
) -> Dict[str, Any]:
    """构建失败结果

    Args:
        job_id: 任务 ID
        execution: 执行记录对象
        message: 失败消息

    Returns:
        Dict[str, Any]: 失败结果
    """
    return {
        'job_id': job_id,
        'execution_id': getattr(execution, 'id', None),
        'status': 'failed',
        'message': message,
    }


# ============================================================================
# 维护任务
# ============================================================================

@shared_task(
    bind=True,
    name='services.worker.tasks.reset_stuck_jobs',
    base=DatabaseTask,
)
def reset_stuck_jobs(self) -> Dict[str, Any]:
    """重置卡住的任务

    将状态为"处理中"但长时间未更新的任务重置为"待处理"。
    定义"长时间"为: updated_at 距离现在超过 1 小时。

    Returns:
        Dict[str, Any]: 执行结果
            {
                'reset_count': int,  # 重置的任务数
                'message': str,
            }
    """
    logger.info("[reset_stuck_jobs] 开始重置卡住的任务")

    db: Session = self.db

    try:
        # 查询卡住的任务
        timeout_threshold = get_beijing_time() - timedelta(hours=1)

        stuck_jobs = db.query(Job).filter(
            Job.status == "处理中",
            Job.deleted_at == None,
            Job.updated_at < timeout_threshold
        ).all()

        reset_count = len(stuck_jobs)

        for job in stuck_jobs:
            job.status = "待处理"
            job.status_detail = "任务超时，自动重置"
            job.updated_at = get_beijing_time()
            db.add(job)

            logger.info(
                f"[reset_stuck_jobs] 重置任务 job_id={job.id}, "
                f"updated_at={job.updated_at}"
            )

        db.commit()

        logger.info(f"[reset_stuck_jobs] 重置了 {reset_count} 个卡住的任务")

        return {
            'reset_count': reset_count,
            'message': f'重置了 {reset_count} 个卡住的任务',
        }

    except Exception as exc:
        logger.exception("[reset_stuck_jobs] 重置任务失败")
        raise


@shared_task(
    bind=True,
    name='services.worker.tasks.cleanup_old_jobs',
    base=DatabaseTask,
)
def cleanup_old_jobs(self) -> Dict[str, Any]:
    """清理旧任务

    删除或软删除超过指定天数的已完成/失败任务。

    Returns:
        Dict[str, Any]: 执行结果
            {
                'deleted_count': int,  # 删除的任务数
                'message': str,
            }
    """
    logger.info("[cleanup_old_jobs] 开始清理旧任务")

    db: Session = self.db

    try:
        # 默认清理 30 天前的任务
        cleanup_days = int(os.getenv('CLEANUP_JOB_DAYS', '30'))
        cleanup_threshold = get_beijing_time() - timedelta(days=cleanup_days)

        # 查询需要清理的任务
        old_jobs = db.query(Job).filter(
            Job.status.in_(["已完成", "失败"]),
            Job.deleted_at == None,
            Job.updated_at < cleanup_threshold
        ).all()

        deleted_count = 0

        for job in old_jobs:
            # 软删除
            job.deleted_at = get_beijing_time()
            db.add(job)
            deleted_count += 1

            logger.info(
                f"[cleanup_old_jobs] 软删除任务 job_id={job.id}, "
                f"status={job.status}, updated_at={job.updated_at}"
            )

        db.commit()

        logger.info(f"[cleanup_old_jobs] 清理了 {deleted_count} 个旧任务")

        return {
            'deleted_count': deleted_count,
            'message': f'清理了 {deleted_count} 个旧任务',
        }

    except Exception as exc:
        logger.exception("[cleanup_old_jobs] 清理任务失败")
        raise


@shared_task(
    bind=True,
    name='services.worker.tasks.check_job_health',
    base=DatabaseTask,
)
def check_job_health(self) -> Dict[str, Any]:
    """检查任务健康状态

    统计各状态任务数量，用于监控。

    Returns:
        Dict[str, Any]: 健康检查结果
            {
                'pending': int,  # 待处理任务数
                'processing': int,  # 处理中任务数
                'completed': int,  # 已完成任务数
                'failed': int,  # 失败任务数
                'total': int,  # 总任务数
            }
    """
    logger.info("[check_job_health] 开始检查任务健康状态")

    db: Session = self.db

    try:
        # 统计各状态任务数量
        pending_count = db.query(Job).filter(
            Job.status == "待处理",
            Job.deleted_at == None
        ).count()

        processing_count = db.query(Job).filter(
            Job.status == "处理中",
            Job.deleted_at == None
        ).count()

        completed_count = db.query(Job).filter(
            Job.status == "已完成",
            Job.deleted_at == None
        ).count()

        failed_count = db.query(Job).filter(
            Job.status == "失败",
            Job.deleted_at == None
        ).count()

        total_count = pending_count + processing_count + completed_count + failed_count

        result = {
            'pending': pending_count,
            'processing': processing_count,
            'completed': completed_count,
            'failed': failed_count,
            'total': total_count,
        }

        logger.info(f"[check_job_health] 任务健康状态: {result}")

        return result

    except Exception as exc:
        logger.exception("[check_job_health] 检查失败")
        raise


# ============================================================================
# 批量任务
# ============================================================================

@shared_task(
    bind=True,
    name='services.worker.tasks.process_batch_jobs',
)
def process_batch_jobs(self, job_ids: list) -> Dict[str, Any]:
    """批量处理任务

    Args:
        job_ids: 任务ID列表

    Returns:
        Dict[str, Any]: 批量处理结果
            {
                'total': int,  # 总任务数
                'success': int,  # 成功数
                'failed': int,  # 失败数
                'results': list,  # 各任务结果列表
            }
    """
    logger.info(f"[process_batch_jobs] 开始批量处理 {len(job_ids)} 个任务")

    results = []
    success_count = 0
    failed_count = 0

    for job_id in job_ids:
        try:
            # 调用单个任务处理
            result = process_video_job.delay(job_id)
            results.append({
                'job_id': job_id,
                'status': 'submitted',
                'task_id': result.id,
            })
            success_count += 1

        except Exception as exc:
            logger.error(
                f"[process_batch_jobs] 提交任务失败 job_id={job_id}, error={exc}",
                exc_info=True
            )
            results.append({
                'job_id': job_id,
                'status': 'failed',
                'error': str(exc),
            })
            failed_count += 1

    logger.info(
        f"[process_batch_jobs] 批量处理完成 "
        f"total={len(job_ids)}, success={success_count}, failed={failed_count}"
    )

    return {
        'total': len(job_ids),
        'success': success_count,
        'failed': failed_count,
        'results': results,
    }


# ============================================================================
# 导出 Celery 应用
# ============================================================================

# 创建默认的 Celery 应用实例
app = get_celery_app()


# 导出所有任务
__all__ = [
    'app',
    'get_celery_app',
    'process_video_job',
    'reset_stuck_jobs',
    'cleanup_old_jobs',
    'check_job_health',
    'process_batch_jobs',
]
