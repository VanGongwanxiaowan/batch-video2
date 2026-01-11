"""任务重试处理器

负责处理超时和失败任务的重试逻辑，支持最大重试次数和指数退避。
"""

from datetime import timedelta
from typing import Any, Dict, Tuple

from db.models import Job, get_beijing_time
from sqlalchemy.orm import Session

from config import settings
from core.logging_config import setup_logging

logger = setup_logging("worker.scheduler.retry_handler")


class JobRetryHandler:
    """任务重试处理器"""
    
    def __init__(self, running_jobs: Dict[int, Any]) -> None:
        """
        初始化重试处理器
        
        Args:
            running_jobs: 正在运行的任务字典，用于排除正在运行的任务
        """
        self.running_jobs = running_jobs
        self.max_retry_count = settings.MAX_RETRY_COUNT
        self.backoff_multiplier = settings.RETRY_BACKOFF_MULTIPLIER
    
    def handle_retries(self, db: Session) -> Tuple[int, int]:
        """
        检查并处理需要重试的任务
        
        Args:
            db: 数据库会话
            
        Returns:
            (超时任务数, 失败任务数) 元组
        """
        logger.info("[handle_retries] 开始检查超时/失败任务重试")
        
        timeout_count = self._retry_timeout_jobs(db)
        failed_count = self._retry_failed_jobs(db)
        
        logger.info(
            f"[handle_retries] 重试处理完成 "
            f"timeout={timeout_count}, failed={failed_count}"
        )
        
        return timeout_count, failed_count
    
    def _get_retry_count(self, job: Job) -> int:
        """
        获取任务的重试次数
        
        Args:
            job: 任务对象
            
        Returns:
            重试次数（从status_detail中解析，如果没有则返回0）
        """
        # 尝试从status_detail中解析重试次数
        # 格式: "超时重试 (1/3)" 或 "失败重试 (2/3)"
        if job.status_detail and "(" in job.status_detail:
            try:
                retry_info = job.status_detail.split("(")[1].split(")")[0]
                current_retry = int(retry_info.split("/")[0])
                return current_retry
            except (ValueError, IndexError):
                pass
        return 0
    
    def _should_retry(self, job: Job) -> bool:
        """
        判断任务是否应该重试
        
        Args:
            job: 任务对象
            
        Returns:
            是否应该重试
        """
        retry_count = self._get_retry_count(job)
        if retry_count >= self.max_retry_count:
            logger.warning(
                f"[_should_retry] 任务已达到最大重试次数，不再重试 "
                f"job_id={job.id}, retry_count={retry_count}, max={self.max_retry_count}"
            )
            return False
        return True
    
    def _calculate_backoff_delay(self, retry_count: int) -> timedelta:
        """
        计算指数退避延迟
        
        Args:
            retry_count: 当前重试次数
            
        Returns:
            延迟时间
        """
        # 基础延迟1小时，每次重试乘以backoff_multiplier
        base_delay_hours = 1.0
        delay_hours = base_delay_hours * (self.backoff_multiplier ** retry_count)
        # 最大延迟24小时
        delay_hours = min(delay_hours, 24.0)
        return timedelta(hours=delay_hours)
    
    def _retry_timeout_jobs(self, db: Session) -> int:
        """
        重试超时的处理中任务（带最大重试次数限制）
        
        Args:
            db: 数据库会话
            
        Returns:
            重试的任务数量
        """
        now = get_beijing_time()
        three_hour_ago = now - timedelta(hours=3)
        one_day_ago = now - timedelta(days=1)
        
        timeout_jobs = (
            db.query(Job)
            .filter(
                Job.status == "处理中",
                Job.updated_at < three_hour_ago,
                Job.created_at >= one_day_ago,
                ~Job.id.in_(self.running_jobs.keys()) if self.running_jobs else True,
            )
            .all()
        )
        
        count = 0
        skipped_count = 0
        for job in timeout_jobs:
            retry_count = self._get_retry_count(job)
            
            if not self._should_retry(job):
                # 标记为永久失败
                job.status = "失败"
                job.status_detail = f"超时重试次数已达上限 ({retry_count}/{self.max_retry_count})"
                job.updated_at = get_beijing_time()
                db.add(job)
                skipped_count += 1
                logger.warning(
                    f"[_retry_timeout_jobs] 任务超时重试次数已达上限 "
                    f"job_id={job.id}, retry_count={retry_count}"
                )
                continue
            
            new_retry_count = retry_count + 1
            logger.info(
                f"[_retry_timeout_jobs] 重试超时任务 "
                f"job_id={job.id}, title={job.title}, retry={new_retry_count}/{self.max_retry_count}"
            )
            job.status = "待处理"
            job.status_detail = f"超时重试 ({new_retry_count}/{self.max_retry_count})"
            job.updated_at = get_beijing_time()
            db.add(job)
            count += 1
        
        logger.info(
            f"[_retry_timeout_jobs] 重试了 {count} 个超时任务，"
            f"跳过 {skipped_count} 个已达最大重试次数的任务"
        )
        return count
    
    def _retry_failed_jobs(self, db: Session) -> int:
        """
        重试失败的任务（带最大重试次数限制和指数退避）
        
        Args:
            db: 数据库会话
            
        Returns:
            重试的任务数量
        """
        now = get_beijing_time()
        one_day_ago = now - timedelta(days=1)
        
        failed_jobs = (
            db.query(Job)
            .filter(
                Job.status == "失败",
                Job.created_at >= one_day_ago,
                ~Job.id.in_(self.running_jobs.keys()) if self.running_jobs else True,
            )
            .all()
        )
        
        count = 0
        skipped_count = 0
        for job in failed_jobs:
            retry_count = self._get_retry_count(job)
            
            if not self._should_retry(job):
                # 标记为永久失败
                job.status = "失败"
                job.status_detail = f"失败重试次数已达上限 ({retry_count}/{self.max_retry_count})"
                job.updated_at = get_beijing_time()
                db.add(job)
                skipped_count += 1
                logger.warning(
                    f"[_retry_failed_jobs] 任务失败重试次数已达上限 "
                    f"job_id={job.id}, retry_count={retry_count}"
                )
                continue
            
            # 计算指数退避延迟
            backoff_delay = self._calculate_backoff_delay(retry_count)
            next_retry_time = now + backoff_delay
            
            # 检查是否到了重试时间
            if job.updated_at > next_retry_time - backoff_delay:
                # 还没到重试时间，跳过
                continue
            
            new_retry_count = retry_count + 1
            logger.info(
                f"[_retry_failed_jobs] 重试失败任务 "
                f"job_id={job.id}, title={job.title}, retry={new_retry_count}/{self.max_retry_count}, "
                f"backoff_delay={backoff_delay}"
            )
            job.status = "待处理"
            job.status_detail = f"失败重试 ({new_retry_count}/{self.max_retry_count})"
            job.updated_at = get_beijing_time()
            db.add(job)
            count += 1
        
        logger.info(
            f"[_retry_failed_jobs] 重试了 {count} 个失败任务，"
            f"跳过 {skipped_count} 个已达最大重试次数的任务"
        )
        return count

