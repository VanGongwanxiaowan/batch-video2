"""任务分割服务模块。

提供任务分割项的CRUD操作。
"""
import json
from typing import Any, Dict

from db.models import JobSplit, Language, Topic, Voice
from schema.job_split import JobSplit as SchemaJobSplit
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.config.constants import DatabaseConfig
from core.exceptions import JobNotFoundException


class JobSplitService:
    """任务分割服务类，负责处理任务分割项相关的业务逻辑。"""
    
    def __init__(self, db: Session) -> None:
        """初始化任务分割服务。
        
        Args:
            db: 数据库会话对象
        """
        self.db = db

    def get_job_split(self, split_id: int) -> JobSplit:
        """根据ID获取任务分割项。
        
        Args:
            split_id: 分割项ID
            
        Returns:
            JobSplit: 任务分割项对象
            
        Raises:
            JobNotFoundException: 如果分割项不存在
        """
        job_split = self.db.query(JobSplit).filter(JobSplit.id == split_id).first()
        if not job_split:
            raise JobNotFoundException(split_id)
        return job_split
    
    def update_job_splits(self, split_id: int, split_data: SchemaJobSplit) -> JobSplit:
        """更新任务分割项。
        
        Args:
            split_id: 分割项ID
            split_data: 分割项数据对象
            
        Returns:
            JobSplit: 更新后的分割项对象
            
        Raises:
            JobNotFoundException: 如果分割项不存在
        """
        job_split = self.db.query(JobSplit).filter(JobSplit.id == split_id).first()
        if not job_split:
            raise JobNotFoundException(split_id)
        job_split.selected = split_data.selected
        job_split.prompt = split_data.prompt
        job_split.save()
        return job_split
        
    def list_job_splits(
        self,
        job_id: int,
        page: int,
        page_size: int = DatabaseConfig.DEFAULT_PAGE_SIZE
    ) -> Dict[str, Any]:
        """列出任务的分割项列表。
        
        Args:
            job_id: 任务ID
            page: 页码（从1开始）
            page_size: 每页数量，默认使用配置常量
            
        Returns:
            Dict[str, Any]: 包含total（总数）和items（分割项列表）的字典
        """
        # 限制最大页面大小
        if page_size > DatabaseConfig.MAX_PAGE_SIZE:
            page_size = DatabaseConfig.MAX_PAGE_SIZE
        
        job_splits = (
            self.db.query(JobSplit)
            .filter(JobSplit.job_id == job_id)
            .order_by(JobSplit.index)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        total = self.db.query(func.count(JobSplit.id)).filter(
            JobSplit.job_id == job_id
        ).scalar()
        return {
            "total": total,
            "items": job_splits
        }
    def delete_by_job_id(self, job_id: int) -> Dict[str, Any]:
        """删除指定任务的所有分割项。
        
        使用批量删除优化性能，避免一次性加载大量数据。
        
        Args:
            job_id: 任务ID
            
        Returns:
            Dict[str, Any]: 包含成功消息和删除数量的字典
        """
        # 使用批量删除，避免一次性加载所有数据到内存
        # 先查询数量，然后分批删除
        total_count = self.db.query(func.count(JobSplit.id)).filter(
            JobSplit.job_id == job_id
        ).scalar()
        
        if total_count == 0:
            return {"message": "No job splits found to delete"}
        
        # 分批删除，使用配置常量
        batch_size = DatabaseConfig.BATCH_DELETE_SIZE
        deleted_count = 0
        
        while True:
            # 查询一批ID
            job_split_ids = [
                split.id for split in
                self.db.query(JobSplit.id)
                .filter(JobSplit.job_id == job_id)
                .limit(batch_size)
                .all()
            ]
            
            if not job_split_ids:
                break
            
            # 批量删除
            self.db.query(JobSplit).filter(
                JobSplit.id.in_(job_split_ids)
            ).delete(synchronize_session=False)
            
            deleted_count += len(job_split_ids)
            
            # 如果删除的数量小于批次大小，说明已经删除完毕
            if len(job_split_ids) < batch_size:
                break
        
        self.db.commit()
        return {
            "message": f"Job splits deleted successfully",
            "deleted_count": deleted_count
        }