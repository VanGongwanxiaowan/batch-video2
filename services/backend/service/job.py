"""任务服务模块。

提供任务的创建、查询、更新、删除等业务逻辑。
遵循单一职责原则，只负责任务相关的业务逻辑。
"""
import json
from typing import Any, Dict, Optional

from db.models import Job  # noqa: E402
from schema.job import CreateJobRequest  # noqa: E402
from schema.job import Job as SchemaJob  # noqa: E402
from sqlalchemy.orm import Session, joinedload

from core.db.dao.job_dao import JobDAO  # noqa: E402
from core.db.models import get_beijing_time  # noqa: E402
from core.exceptions import JobException, JobNotFoundException  # noqa: E402


class JobService:
    """任务服务类，负责处理任务相关的业务逻辑。
    
    提供任务的CRUD操作，包括创建、查询、更新、删除等。
    所有操作都会验证用户权限，确保用户只能操作自己的任务。
    遵循单一职责原则，只负责任务相关的业务逻辑。
    
    Attributes:
        db: 数据库会话对象
        job_dao: 任务数据访问对象
    """
    
    def __init__(self, db: Session) -> None:
        """初始化任务服务。
        
        Args:
            db: 数据库会话对象
        """
        self.db = db
        self.job_dao = JobDAO(db)

    def create_job(self, request: CreateJobRequest, user_id: str) -> Job:
        """创建新任务。
        
        Args:
            request: 创建任务请求对象
            user_id: 用户ID
            
        Returns:
            Job: 创建的任务对象
            
        Raises:
            JobException: 如果创建失败
        """
        db_job = Job(
            title=request.title,
            content=request.content,
            language_id=request.language_id if request.language_id != 0 else None,
            voice_id=request.voice_id,
            description=request.description,
            topic_id=request.topic_id,
            status=request.status,
            publish_title=request.publish_title,
            status_detail=request.status_detail,
            account_id=request.account_id,
            speech_speed=request.speech_speed,
            is_horizontal=request.is_horizontal,
            extra=request.extra,
            user_id=user_id # Set user_id here
        )
        self.db.add(db_job)
        self.db.commit()
        self.db.refresh(db_job)
        return db_job

    def get_job(self, job_id: int, user_id: str) -> Job:
        """根据ID获取任务。
        
        Args:
            job_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Job: 任务对象
            
        Raises:
            JobNotFoundException: 如果任务不存在或不属于该用户
        """
        job = self.job_dao.get(job_id)
        if not job:
            raise JobNotFoundException(job_id)
        # 验证任务是否属于该用户
        if job.user_id != user_id:
            raise JobNotFoundException(job_id)
        return job

    def get_job_with_topic(self, job_id: int, user_id: str) -> Job:
        """获取任务及其关联的主题、语言和语音信息。
        
        使用joinedload优化查询，避免N+1查询问题。
        
        Args:
            job_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Job: 任务对象，包含关联的topic、language和voice属性
            
        Raises:
            JobNotFoundException: 如果任务不存在或不属于该用户
        """
        # 先验证任务存在且属于该用户
        job = self.get_job(job_id, user_id)
        
        # 使用joinedload预加载关联数据
        job = (
            self.db.query(Job)
            .options(
                joinedload(Job.topic),
                joinedload(Job.language),
                joinedload(Job.voice)
            )
            .filter(Job.id == job_id)
            .first()
        )
        return job

    def list_jobs(
        self,
        page: int,
        page_size: int,
        status: str,
        user_id: str,
        account_id: Optional[int] = None,
        language_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """列出用户的任务列表。
        
        Args:
            page: 页码（从1开始）
            page_size: 每页数量
            status: 任务状态，如果为"所有"则不过滤状态
            user_id: 用户ID
            account_id: 账户ID（可选）
            language_id: 语言ID（可选）
            
        Returns:
            Dict[str, Any]: 包含total（总数）和items（任务列表）的字典
        """
        # 构建过滤条件
        filters: Dict[str, Any] = {
            "user_id": user_id,
            "deleted_at": None
        }
        if status and status != "所有":
            filters["status"] = status
        if account_id is not None:
            filters["account_id"] = account_id
        if language_id is not None:
            filters["language_id"] = language_id
        
        # 使用DAO进行查询，但需要手动处理排序和分页
        # 因为BaseDAO的get_all方法不支持排序
        query = self.db.query(Job).filter(
            Job.user_id == user_id,
            Job.deleted_at.is_(None)
        )
        
        if status and status != "所有":
            query = query.filter(Job.status == status)
        if account_id is not None:
            query = query.filter(Job.account_id == account_id)
        if language_id is not None:
            query = query.filter(Job.language_id == language_id)
        
        # 使用joinedload预加载关联对象，避免N+1查询问题
        from sqlalchemy.orm import joinedload
        
        query = query.options(
            joinedload(Job.language),
            joinedload(Job.voice),
            joinedload(Job.topic),
            joinedload(Job.account)
        )
        
        total = query.count()
        items = query.order_by(Job.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        
        return {"total": total, "items": items}

    def update_job(self, job_id: int, job_data: SchemaJob, user_id: str) -> Job:
        """更新任务信息。
        
        Args:
            job_id: 任务ID
            job_data: 任务数据对象（只更新提供的字段）
            user_id: 用户ID
            
        Returns:
            Job: 更新后的任务对象
            
        Raises:
            JobNotFoundException: 如果任务不存在
        """
        # 使用joinedload预加载关联对象，避免N+1查询
        from sqlalchemy.orm import joinedload
        
        db_job = (
            self.db.query(Job)
            .options(
                joinedload(Job.language),
                joinedload(Job.voice),
                joinedload(Job.topic),
                joinedload(Job.account)
            )
            .filter(Job.id == job_id, Job.user_id == user_id)
            .first()
        )
        
        if not db_job:
            raise JobNotFoundException(job_id)
        for field, value in job_data.model_dump(exclude_unset=True).items():
            if field == "job_splits":
                setattr(db_job, field, json.dumps([js.model_dump() for js in value]))
            elif field == "voice_id":
                setattr(db_job, field, value)
            else:
                setattr(db_job, field, value)
        self.db.commit()
        self.db.refresh(db_job)
        return db_job

    def delete_job(self, job_id: int, user_id: str) -> Dict[str, str]:
        """软删除任务（标记为已删除，不实际删除数据）。
        
        Args:
            job_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Dict[str, str]: 包含成功消息的字典
            
        Raises:
            JobNotFoundException: 如果任务不存在或不属于该用户
        """
        # 验证任务存在且属于该用户
        self.get_job(job_id, user_id)
        # 使用DAO的soft_delete方法
        success = self.job_dao.soft_delete(job_id)
        if not success:
            raise JobNotFoundException(job_id)
        return {"message": f"任务 {job_id} 已假删除"}

    def export_job(self, job_id: int, user_id: str) -> Dict[str, str]:
        """导出任务（验证任务结果键的有效性）。
        
        Args:
            job_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Dict[str, str]: 包含导出信息的字典
            
        Raises:
            JobNotFoundException: 如果任务不存在
            JobException: 如果任务结果键格式无效
        """
        job = self.get_job(job_id, user_id)
        try:
            json.loads(job.job_result_key or "{}")
        except json.JSONDecodeError as exc:
            raise JobException(
                f"Invalid job_result_key for job {job_id}",
                job_id=job_id
            ) from exc
        return {"message": f"任务 {job_id} 的视频已导出 job info {job.job_result_key}"}

    def increase_job_priority(self, job_id: int, user_id: str) -> Job:
        """增加任务优先级（runorder + 1）。
        
        Args:
            job_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Job: 更新后的任务对象
            
        Raises:
            JobNotFoundException: 如果任务不存在
        """
        db_job = self.get_job(job_id, user_id)
        db_job.runorder += 1
        self.db.commit()
        self.db.refresh(db_job)
        return db_job

    def reset_job_priority(self, job_id: int, user_id: str) -> Job:
        """重置任务优先级（runorder = 0）。
        
        Args:
            job_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Job: 更新后的任务对象
            
        Raises:
            JobNotFoundException: 如果任务不存在
        """
        db_job = self.get_job(job_id, user_id)
        db_job.runorder = 0
        self.db.commit()
        self.db.refresh(db_job)
        return db_job
