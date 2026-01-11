"""任务调度器

负责调度和执行待处理的任务。

代码重构说明：
- 提取 _try_update_job_status 方法减少重复代码
- 保持原有异常处理逻辑不变
"""

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict, Optional

from db.models import Job
from db.session import db_session
from sqlalchemy.orm import Session

from core.config.constants import JobConfig
from core.exceptions import BatchShortException, DatabaseException, JobNotFoundException
from core.logging_config import setup_logging

from .job_status_manager import JobStatusManager

logger = setup_logging("worker.scheduler.job_scheduler")


class JobScheduler:
    """任务调度器

    负责：
    - 查询待处理任务
    - 提交任务到线程池执行
    - 跟踪正在运行的任务

    注意：
        - 使用线程锁保护running_jobs字典，确保线程安全
    """

    def __init__(
        self,
        executor: ThreadPoolExecutor,
        job_executor,
        max_concurrent_jobs: int = JobConfig.DEFAULT_MAX_CONCURRENT_JOBS
    ):
        """
        初始化任务调度器

        Args:
            executor: 线程池执行器
            job_executor: 任务执行器实例
            max_concurrent_jobs: 最大并发任务数
        """
        self.executor = executor
        self.job_executor = job_executor
        self.max_concurrent_jobs = max_concurrent_jobs
        self.running_jobs: Dict[int, Future] = {}
        self._running_jobs_lock = threading.Lock()  # 线程锁，保护running_jobs字典
        self.status_manager = JobStatusManager()

    def _try_update_job_status(self, job_id: int) -> None:
        """尝试更新任务状态到数据库

        这是一个辅助方法，用于减少重复的数据库更新异常处理代码。
        会在独立的数据库会话中尝试提交任务状态更新。

        Args:
            job_id: 任务ID
        """
        try:
            with db_session() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    db.add(job)
                    db.commit()
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except DatabaseException as db_exc:
            logger.error(f"[_try_update_job_status] 更新任务状态失败 job_id={job_id}: {db_exc}")
        except (ValueError, AttributeError) as db_exc:
            # 数据错误
            logger.warning(
                f"[_try_update_job_status] 更新任务状态时发生数据错误 job_id={job_id}: {db_exc}",
                exc_info=True
            )
        except Exception as db_exc:
            # 其他未预期的异常
            logger.warning(
                f"[_try_update_job_status] 更新任务状态时发生未知异常 job_id={job_id}: {db_exc}",
                exc_info=True
            )
    
    def process_pending_jobs(self) -> int:
        """
        处理待处理的任务
        
        Returns:
            提交的任务数量
        """
        logger.info("[process_pending_jobs] 开始检查待处理任务")
        
        try:
            with db_session() as db:
                current_running_count = len(self.running_jobs)
                logger.info(
                    f"[process_pending_jobs] 当前运行任务数={current_running_count}, "
                    f"最大并发数={self.max_concurrent_jobs}"
                )
                
                if current_running_count >= self.max_concurrent_jobs:
                    logger.info(
                        f"[process_pending_jobs] 已达到最大并发数，跳过新任务处理"
                    )
                    return 0
                
                # 查询待处理任务（需要先获取running_jobs的键列表，避免在查询时持有锁）
                with self._running_jobs_lock:
                    running_job_ids = list(self.running_jobs.keys())
                
                # 查询待处理任务
                pending_jobs = (
                    db.query(Job)
                    .filter(
                        Job.status == "待处理",
                        Job.deleted_at == None,
                        ~Job.id.in_(running_job_ids),
                    )
                    .order_by(Job.runorder.desc(), Job.id.asc())
                    .limit(self.max_concurrent_jobs - current_running_count)
                    .all()
                )
                
                logger.info(f"[process_pending_jobs] 查询到待处理任务数量={len(pending_jobs)}")
                
                # 提交任务到线程池（使用锁保护，确保线程安全）
                submitted_count = 0
                for job in pending_jobs:
                    with self._running_jobs_lock:  # 使用锁保护running_jobs字典
                        if job.id not in self.running_jobs:
                            future = self.executor.submit(self._process_single_job, job.id)
                            self.running_jobs[job.id] = future
                            submitted_count += 1
                            logger.info(
                                f"[process_pending_jobs] 任务已提交到执行器 "
                                f"job_id={job.id}, title={job.title}"
                            )
                
                return submitted_count
                
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except DatabaseException as exc:
            logger.error(f"[process_pending_jobs] 数据库操作异常: {exc}")
            return 0
        except (ValueError, KeyError, AttributeError) as exc:
            # 数据错误
            logger.error(
                f"[process_pending_jobs] 数据错误: {exc}",
                exc_info=True
            )
            return 0
        except Exception as exc:
            # 其他未预期的异常
            logger.exception(
                f"[process_pending_jobs] 处理待处理任务时发生未知异常: {exc}",
                exc_info=True
            )
            return 0
    
    def _process_single_job(self, job_id: int) -> None:
        """
        处理单个任务的逻辑，每个任务在一个独立的线程中运行

        Args:
            job_id: 任务ID

        代码重构说明：
            使用 _try_update_job_status 辅助方法减少重复代码
            保持原有异常处理逻辑不变
        """
        logger.info(f"[_process_single_job] 开始处理任务 job_id={job_id}")

        job: Optional[Job] = None
        try:
            with db_session() as db:
                job = db.query(Job).filter(
                    Job.id == job_id,
                    Job.deleted_at == None
                ).first()

                if not job:
                    raise JobNotFoundException(job_id)

                # 执行任务
                self.job_executor.execute_job(db, job)
                self.status_manager.mark_job_completed(job)
                db.add(job)
                db.commit()

                logger.info(f"[_process_single_job] 任务执行成功 job_id={job_id}")

        except JobNotFoundException:
            logger.warning(f"[_process_single_job] 任务未找到或已删除 job_id={job_id}")
        except BatchShortException as exc:
            logger.error(
                f"[_process_single_job] 任务处理出现业务异常 job_id={job_id}, error={exc}",
                exc_info=True
            )
            if job:
                self.status_manager.mark_job_failed(job, str(exc))
                self._try_update_job_status(job_id)

        except (OSError, IOError) as exc:
            logger.exception(
                f"[_process_single_job] 处理任务时发生IO异常 job_id={job_id}",
                exc_info=True
            )
            if job:
                self.status_manager.mark_job_failed(job, f"IO错误: {exc}")
                self._try_update_job_status(job_id)

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise

        except Exception as exc:
            logger.exception(
                f"[_process_single_job] 处理任务时发生未知异常 job_id={job_id}",
                exc_info=True
            )
            if job:
                self.status_manager.mark_job_failed(job, f"处理失败: {exc}")
                self._try_update_job_status(job_id)

        finally:
            # 从运行任务列表中移除（使用锁保护，确保线程安全）
            with self._running_jobs_lock:
                if job_id in self.running_jobs:
                    del self.running_jobs[job_id]
                    logger.info(
                        f"[_process_single_job] 从运行任务列表中移除 job_id={job_id}, "
                        f"当前运行任务数={len(self.running_jobs)}"
                    )
    
    def cleanup_completed_futures(self) -> int:
        """
        清理已完成的Future对象，避免内存泄漏
        
        Returns:
            清理的Future数量
            
        注意：
            使用锁保护，确保线程安全
        """
        cleaned_count = 0
        with self._running_jobs_lock:  # 使用锁保护running_jobs字典
            completed_job_ids = [
                job_id for job_id, future in self.running_jobs.items()
                if future.done()
            ]
            for job_id in completed_job_ids:
                del self.running_jobs[job_id]
                cleaned_count += 1
                logger.debug(f"[cleanup_completed_futures] 移除已完成的Future job_id={job_id}")
        
        return cleaned_count

