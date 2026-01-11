"""基础CRUD服务类

提供通用的CRUD操作，消除Service层的重复代码。
"""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.db.dao.base_dao import BaseDAO
from core.exceptions import ServiceException

ModelType = TypeVar("ModelType")
CreateRequestType = TypeVar("CreateRequestType")
UpdateRequestType = TypeVar("UpdateRequestType")


class BaseCRUDService(Generic[ModelType, CreateRequestType, UpdateRequestType]):
    """基础CRUD服务类
    
    提供通用的CRUD操作，包括：
    - create: 创建资源
    - get: 获取单个资源
    - list: 列出资源
    - update: 更新资源
    - delete: 删除资源
    
    所有操作都支持用户权限验证。
    
    Attributes:
        db: 数据库会话
        dao: 数据访问对象
        model_class: 模型类
    """
    
    def __init__(
        self,
        db: Session,
        dao: BaseDAO[ModelType],
        model_class: Type[ModelType],
    ) -> None:
        """
        初始化CRUD服务
        
        Args:
            db: 数据库会话
            dao: 数据访问对象
            model_class: 模型类
        """
        self.db = db
        self.dao = dao
        self.model_class = model_class
    
    def create(
        self,
        request: CreateRequestType,
        user_id: str,
        **kwargs: Any,
    ) -> ModelType:
        """
        创建资源
        
        Args:
            request: 创建请求对象
            user_id: 用户ID
            **kwargs: 额外的字段
            
        Returns:
            创建的模型实例
            
        Raises:
            ServiceException: 如果创建失败
        """
        # 将请求对象转换为字典
        if hasattr(request, 'model_dump'):
            data = request.model_dump()
        elif hasattr(request, 'dict'):
            data = request.dict()
        else:
            data = dict(request)
        
        # 添加user_id
        data['user_id'] = user_id
        
        # 添加额外字段
        data.update(kwargs)
        
        # 创建模型实例
        model_instance = self.model_class(**data)
        self.db.add(model_instance)
        self.db.commit()
        self.db.refresh(model_instance)
        return model_instance
    
    def get(
        self,
        item_id: int,
        user_id: str,
        error_message: Optional[str] = None,
    ) -> ModelType:
        """
        获取单个资源
        
        Args:
            item_id: 资源ID
            user_id: 用户ID（用于权限验证）
            error_message: 自定义错误消息
            
        Returns:
            模型实例
            
        Raises:
            ServiceException: 如果资源不存在或不属于该用户
        """
        item = self.dao.get(item_id)
        if not item:
            msg = error_message or f"{self.model_class.__name__} not found: {item_id}"
            raise ServiceException(
                msg,
                service_name=f"backend.{self.model_class.__name__.lower()}"
            )
        
        # 验证用户权限
        if hasattr(item, 'user_id') and item.user_id != user_id:
            raise ServiceException(
                f"{self.model_class.__name__} {item_id} does not belong to user {user_id}",
                service_name=f"backend.{self.model_class.__name__.lower()}"
            )
        
        return item
    
    def list(
        self,
        page: int,
        page_size: int,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        列出资源
        
        Args:
            page: 页码（从1开始）
            page_size: 每页数量
            user_id: 用户ID（用于过滤）
            filters: 额外的过滤条件
            order_by: 排序字段
            
        Returns:
            包含total（总数）和items（资源列表）的字典
        """
        # 构建过滤条件
        if filters is None:
            filters = {}
        
        # 添加用户过滤
        if hasattr(self.model_class, 'user_id'):
            filters['user_id'] = user_id
        
        # 计算skip
        skip = (page - 1) * page_size
        
        # 查询
        items = self.dao.get_all(skip=skip, limit=page_size, filters=filters)
        total = self.dao.count(filters=filters)
        
        return {"total": total, "items": items}
    
    def update(
        self,
        item_id: int,
        request: UpdateRequestType,
        user_id: str,
        **kwargs: Any,
    ) -> ModelType:
        """
        更新资源
        
        Args:
            item_id: 资源ID
            request: 更新请求对象（只更新提供的字段）
            user_id: 用户ID（用于权限验证）
            **kwargs: 额外的字段
            
        Returns:
            更新后的模型实例
            
        Raises:
            ServiceException: 如果资源不存在
        """
        # 获取资源（会验证权限）
        item = self.get(item_id, user_id)
        
        # 将请求对象转换为字典
        if hasattr(request, 'model_dump'):
            data = request.model_dump(exclude_unset=True)
        elif hasattr(request, 'dict'):
            data = request.dict(exclude_unset=True)
        else:
            data = dict(request)
        
        # 添加额外字段
        data.update(kwargs)
        
        # 更新字段
        for field, value in data.items():
            if hasattr(item, field):
                # 特殊处理extra字段（合并而不是替换）
                if field == 'extra' and hasattr(item, 'extra') and item.extra:
                    existing_extra = item.extra if isinstance(item.extra, dict) else item.extra.model_dump()
                    merged_extra = {**existing_extra, **value}
                    setattr(item, field, merged_extra)
                else:
                    setattr(item, field, value)
        
        self.db.commit()
        self.db.refresh(item)
        return item
    
    def delete(
        self,
        item_id: int,
        user_id: str,
    ) -> Dict[str, int]:
        """
        删除资源
        
        Args:
            item_id: 资源ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            包含已删除资源ID的字典
            
        Raises:
            ServiceException: 如果资源不存在或删除失败
        """
        # 验证资源存在且属于该用户
        self.get(item_id, user_id)
        
        # 执行删除
        success = self.dao.delete(item_id)
        if not success:
            raise ServiceException(
                f"Failed to delete {self.model_class.__name__}: {item_id}",
                service_name=f"backend.{self.model_class.__name__.lower()}"
            )
        
        return {"id": item_id}

