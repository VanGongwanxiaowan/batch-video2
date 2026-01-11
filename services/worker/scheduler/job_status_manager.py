"""任务状态管理器

负责管理任务状态的更新和查询。
"""

from typing import Optional

from db.models import Job, get_beijing_time
from sqlalchemy.orm import Session

from core.exceptions import DatabaseException
from core.logging_config import setup_logging

logger = setup_logging("worker.scheduler.status_manager")


class JobStatusManager:
    """任务状态管理器"""
    
    @staticmethod
    def mark_job_failed(job: Optional[Job], detail: str, is_permanent: bool = False) -> None:
        """
        标记任务为失败状态
        
        Args:
            job: 任务对象
            detail: 失败详情
            is_permanent: 是否为永久失败（不应重试）
        """
        if not job:
            return
        
        job.status = "失败"
        if is_permanent:
            job.status_detail = f"{detail} (永久失败，不再重试)"
        else:
            job.status_detail = detail
        job.runorder = 0
        job.updated_at = get_beijing_time()
        logger.info(
            f"[mark_job_failed] 任务标记为失败 job_id={job.id}, "
            f"detail={detail}, is_permanent={is_permanent}"
        )
    
    @staticmethod
    def mark_job_completed(job: Optional[Job], detail: str = "视频生成并上传成功") -> None:
        """
        标记任务为已完成状态
        
        Args:
            job: 任务对象
            detail: 完成详情
        """
        if not job:
            return
        
        job.status = "已完成"
        job.status_detail = detail
        job.runorder = 0
        job.updated_at = get_beijing_time()
        logger.info(f"[mark_job_completed] 任务标记为已完成 job_id={job.id}, detail={detail}")
    
    @staticmethod
    def mark_job_processing(job: Job, detail: str = "开始处理") -> None:
        """
        标记任务为处理中状态
        
        Args:
            job: 任务对象
            detail: 处理详情
        """
        job.status = "处理中"
        job.status_detail = detail
        job.updated_at = get_beijing_time()
        logger.info(f"[mark_job_processing] 任务标记为处理中 job_id={job.id}, detail={detail}")
    
    @staticmethod
    def reset_processing_jobs_on_startup(db: Session) -> int:
        """
        服务启动时，将所有状态为"处理中"的任务重置为"待处理"
        
        Args:
            db: 数据库会话
            
        Returns:
            重置的任务数量
        """
        logger.info("[reset_processing_jobs_on_startup] 开始重置处理中任务")
        
        try:
            processing_jobs = db.query(Job).filter(
                Job.status == "处理中",
                Job.deleted_at == None
            ).all()
            
            count = 0
            for job in processing_jobs:
                job.status = "待处理"
                job.status_detail = "服务启动重置"
                job.updated_at = get_beijing_time()
                db.add(job)
                count += 1
            
            logger.info(f"[reset_processing_jobs_on_startup] 重置了 {count} 个任务")
            return count
            
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except DatabaseException as exc:
            # 数据库操作异常
            logger.error(f"[reset_processing_jobs_on_startup] 数据库操作异常: {exc}", exc_info=True)
            return 0
        except Exception as exc:
            # 其他异常
            logger.exception(f"[reset_processing_jobs_on_startup] 重置任务状态时发生异常: {exc}")
            return 0

