"""任务数据访问对象，提供任务相关的数据库操作"""
from typing import List, Optional, Dict, Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from core.db.models import Job
from core.logging_config import get_logger
from .base_dao import BaseDAO

logger = get_logger(__name__)


class JobDAO(BaseDAO[Job]):
    """任务数据访问对象，提供任务相关的数据库操作"""

    def __init__(self, session: Session) -> None:
        super().__init__(Job, session)

    def get_by_user_id(
        self, 
        user_id: str, 
        *, 
        skip: int = 0, 
        limit: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[Job]:
        """
        根据用户ID查询任务
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            order_by: 排序字段，例如 '-created_at' 表示按创建时间降序
            
        Returns:
            任务列表
        """
        return self.get_all(
            skip=skip,
            limit=limit,
            filters={"user_id": user_id},
            order_by=order_by or [("created_at", True)]  # 默认按创建时间降序
        )

    def get_by_status(
        self, 
        status: str, 
        *, 
        skip: int = 0, 
        limit: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[Job]:
        """
        根据状态查询任务
        
        Args:
            status: 任务状态
            skip: 跳过的记录数
            limit: 返回的最大记录数
            order_by: 排序字段
            
        Returns:
            任务列表
        """
        return self.get_all(
            skip=skip,
            limit=limit,
            filters={"status": status},
            order_by=order_by or ["created_at"]
        )

    def get_pending_jobs(
        self, 
        limit: int = 10, 
        priority: Optional[int] = None
    ) -> List[Job]:
        """
        获取待处理任务
        
        Args:
            limit: 返回的最大记录数
            priority: 优先级，如果指定则只返回该优先级的任务
            
        Returns:
            待处理任务列表
        """
        filters: Dict[str, Any] = {"status": "待处理"}
        if priority is not None:
            filters["priority"] = priority
            
        return self.get_all(
            limit=limit,
            filters=filters,
            order_by=["priority", "created_at"]
        )
        
    def update_status(
        self, 
        job_id: int, 
        status: str, 
        error: Optional[str] = None,
        commit: bool = True
    ) -> Optional[Job]:
        """
        更新任务状态
        
        Args:
            job_id: 任务ID
            status: 新状态
            error: 错误信息（如果有）
            commit: 是否立即提交事务
            
        Returns:
            更新后的任务对象，如果任务不存在则返回None
        """
        update_data = {"status": status}
        if error:
            update_data["error"] = error
            
        return self.update_by_id(job_id, update_data, commit=commit)
    
    def get_by_user_and_status(
        self,
        user_id: str,
        status: str,
        *,
        skip: int = 0,
        limit: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[Job]:
        """
        根据用户ID和状态查询任务
        
        Args:
            user_id: 用户ID
            status: 任务状态
            skip: 跳过的记录数
            limit: 返回的最大记录数
            order_by: 排序字段
            
        Returns:
            任务列表
        """
        return self.get_all(
            skip=skip,
            limit=limit,
            filters={
                "user_id": user_id,
                "status": status
            },
            order_by=order_by or [("created_at", True)]
        )
        
    def bulk_update_status(
        self, 
        job_ids: List[int], 
        status: str, 
        commit: bool = True
    ) -> int:
        """
        批量更新任务状态
        
        Args:
            job_ids: 任务ID列表
            status: 新状态
            commit: 是否立即提交事务
            
        Returns:
            更新的记录数
        """
        if not job_ids:
            return 0
            
        # 使用批量更新提高性能
        updated = self.session.query(self.model)\
            .filter(self.model.id.in_(job_ids))\
            .update(
                {"status": status},
                synchronize_session=False
            )
            
        if commit:
            self.session.commit()
            
        return updated

