"""基础DAO类，提供通用CRUD操作和事务管理"""
from datetime import datetime
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, load_only

from core.config import settings
from core.db.session import Base
from core.logging_config import get_logger

logger = get_logger(__name__)
ModelType = TypeVar("ModelType", bound=Base)

# 类型别名
FilterType = Dict[str, Union[Any, Tuple[str, Any]]]
OrderByType = Union[str, Tuple[str, bool]]


class BaseDAO(Generic[ModelType]):
    """基础数据访问对象，提供通用CRUD操作和事务管理
    
    特性：
    - 支持软删除
    - 支持批量操作
    - 支持事务管理
    - 支持查询缓存
    - 支持分页和排序
    """

    def __init__(self, model: Type[ModelType], session: Session) -> None:
        """
        初始化DAO

        Args:
            model: SQLAlchemy模型类
            session: 数据库会话
        """
        self.model = model
        self.session = session
        self._has_soft_delete = hasattr(model, 'deleted_at')

    def get(self, id: Any, *, include_deleted: bool = False) -> Optional[ModelType]:
        """
        根据ID查询

        Args:
            id: 主键ID
            include_deleted: 是否包含已删除的记录

        Returns:
            模型实例或None
        """
        query = self.session.query(self.model).filter(self.model.id == id)
        
        if self._has_soft_delete and not include_deleted:
            query = query.filter(self.model.deleted_at.is_(None))
            
        return query.first()

    def get_by_field(
        self, 
        field_name: str, 
        value: Any, 
        *, 
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """
        根据字段查询

        Args:
            field_name: 字段名
            value: 字段值
            include_deleted: 是否包含已删除的记录

        Returns:
            模型实例或None
        """
        if not hasattr(self.model, field_name):
            raise AttributeError(f"Model {self.model.__name__} has no attribute '{field_name}'")
            
        query = self.session.query(self.model).filter(
            getattr(self.model, field_name) == value
        )
        
        if self._has_soft_delete and not include_deleted:
            query = query.filter(self.model.deleted_at.is_(None))
            
        return query.first()

    def get_all(
        self, 
        *, 
        skip: int = 0, 
        limit: Optional[int] = None,
        filters: Optional[FilterType] = None,
        order_by: Optional[Union[str, List[OrderByType]]] = None,
        include_deleted: bool = False,
        load_only: Optional[List[str]] = None
    ) -> List[ModelType]:
        """
        查询所有记录

        Args:
            skip: 跳过记录数
            limit: 返回记录数，None表示不限制
            filters: 过滤条件字典
            order_by: 排序字段，可以是字段名或(字段名, 是否降序)元组列表
            include_deleted: 是否包含已删除的记录
            load_only: 仅加载指定字段

        Returns:
            模型实例列表
        """
        query = self._build_query(
            filters=filters,
            include_deleted=include_deleted,
            load_only=load_only
        )
        
        # 应用排序
        if order_by:
            query = self._apply_ordering(query, order_by)
            
        # 应用分页
        if skip > 0:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
            
        return query.all()

    def create(self, obj: ModelType, *, commit: bool = True) -> ModelType:
        """
        创建记录

        Args:
            obj: 模型实例
            commit: 是否立即提交事务

        Returns:
            创建的模型实例
        """
        try:
            self.session.add(obj)
            if commit:
                self.session.commit()
                self.session.refresh(obj)
            return obj
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create {self.model.__name__}: {str(e)}")
            raise

    def update(
        self, 
        obj: ModelType, 
        update_data: Optional[Dict[str, Any]] = None, 
        *, 
        commit: bool = True
    ) -> ModelType:
        """
        更新记录

        Args:
            obj: 要更新的模型实例
            update_data: 要更新的字段字典，如果为None，则更新所有脏数据
            commit: 是否立即提交事务

        Returns:
            更新的模型实例
        """
        try:
            if update_data:
                for key, value in update_data.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                        
            if commit:
                self.session.commit()
                self.session.refresh(obj)
                
            return obj
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update {self.model.__name__} {obj.id}: {str(e)}")
            raise

    def update_by_id(
        self, 
        id: Any, 
        update_data: Dict[str, Any], 
        *, 
        commit: bool = True
    ) -> Optional[ModelType]:
        """
        根据ID更新记录

        Args:
            id: 主键ID
            update_data: 要更新的字段字典
            commit: 是否立即提交事务

        Returns:
            更新的模型实例或None
        """
        obj = self.get(id)
        if not obj:
            return None
            
        return self.update(obj, update_data, commit=commit)

    def delete(self, id: Any, *, hard_delete: bool = False, commit: bool = True) -> bool:
        """
        删除记录

        Args:
            id: 主键ID
            hard_delete: 是否物理删除，默认软删除
            commit: 是否立即提交事务

        Returns:
            是否删除成功
        """
        obj = self.get(id, include_deleted=True)
        if not obj:
            return False
            
        try:
            if self._has_soft_delete and not hard_delete:
                # 软删除
                obj.deleted_at = datetime.utcnow()
                if commit:
                    self.session.commit()
            else:
                # 物理删除
                self.session.delete(obj)
                if commit:
                    self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to delete {self.model.__name__} {id}: {str(e)}")
            return False

    def _build_query(
        self, 
        filters: Optional[FilterType] = None,
        include_deleted: bool = False,
        load_only: Optional[List[str]] = None
    ) -> Any:
        """
        构建基础查询

        Args:
            filters: 过滤条件
            include_deleted: 是否包含已删除的记录
            load_only: 仅加载指定字段

        Returns:
            SQLAlchemy查询对象
        """
        query = self.session.query(self.model)
        
        # 应用软删除过滤
        if self._has_soft_delete and not include_deleted:
            query = query.filter(self.model.deleted_at.is_(None))
            
        # 应用字段过滤
        if filters:
            conditions = []
            for key, value in filters.items():
                if not hasattr(self.model, key):
                    logger.warning(f"Model {self.model.__name__} has no attribute '{key}' for filtering")
                    continue
                    
                field = getattr(self.model, key)
                
                # 支持元组形式的操作符，如 ('created_at', '>', '2023-01-01')
                if isinstance(value, tuple) and len(value) == 2:
                    op, val = value
                    if op == '==':
                        conditions.append(field == val)
                    elif op == '!=':
                        conditions.append(field != val)
                    elif op == '>':
                        conditions.append(field > val)
                    elif op == '>=':
                        conditions.append(field >= val)
                    elif op == '<':
                        conditions.append(field < val)
                    elif op == '<=':
                        conditions.append(field <= val)
                    elif op == 'in':
                        conditions.append(field.in_(val))
                    elif op == 'like':
                        conditions.append(field.like(val))
                    elif op == 'ilike':
                        conditions.append(field.ilike(val))
                    else:
                        logger.warning(f"Unsupported operator: {op}")
                        conditions.append(field == val)
                else:
                    conditions.append(field == value)
                    
            if conditions:
                query = query.filter(and_(*conditions))
                
        # 应用字段选择
        if load_only:
            fields = []
            for field_name in load_only:
                if hasattr(self.model, field_name):
                    fields.append(getattr(self.model, field_name))
            if fields:
                query = query.options(load_only(*fields))
                
        return query
        
    def _apply_ordering(self, query: Any, order_by: Union[str, List[OrderByType]]) -> Any:
        """
        应用排序
        
        Args:
            query: SQLAlchemy查询对象
            order_by: 排序字段或字段列表
            
        Returns:
            排序后的查询对象
        """
        if isinstance(order_by, str):
            order_by = [order_by]
            
        for item in order_by:
            if isinstance(item, str):
                field_name = item
                desc = False
            else:
                field_name, desc = item
                
            if not hasattr(self.model, field_name):
                logger.warning(f"Model {self.model.__name__} has no attribute '{field_name}' for ordering")
                continue
                
            field = getattr(self.model, field_name)
            query = query.order_by(field.desc() if desc else field.asc())
            
        return query
        
    def count(
        self, 
        filters: Optional[FilterType] = None, 
        include_deleted: bool = False
    ) -> int:
        """
        统计记录数

        Args:
            filters: 过滤条件
            include_deleted: 是否包含已删除的记录

        Returns:
            记录数
        """
        query = self._build_query(filters, include_deleted)
        return query.count()
        
    def exists(self, **filters: Any) -> bool:
        """
        检查记录是否存在
        
        Args:
            **filters: 过滤条件
            
        Returns:
            是否存在匹配的记录
        """
        return self.count(filters) > 0
        
    def bulk_create(
        self, 
        objects: List[ModelType], 
        *, 
        commit: bool = True
    ) -> List[ModelType]:
        """
        批量创建记录
        
        Args:
            objects: 要创建的模型实例列表
            commit: 是否立即提交事务
            
        Returns:
            创建的模型实例列表
        """
        try:
            self.session.bulk_save_objects(objects)
            if commit:
                self.session.commit()
            return objects
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to bulk create {len(objects)} {self.model.__name__}: {str(e)}")
            raise
            
    def bulk_update(
        self, 
        objects: List[Dict[str, Any]], 
        *,
        commit: bool = True
    ) -> None:
        """
        批量更新记录

        Args:
            objects: 要更新的字典列表，每个字典必须包含主键
            commit: 是否立即提交事务
        """
        if not objects:
            return
            
        try:
            self.session.bulk_update_mappings(self.model, objects)
            if commit:
                self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to bulk update {len(objects)} {self.model.__name__}: {str(e)}")
            raise
            
    def execute_in_transaction(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        在事务中执行函数
        
        Args:
            func: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数的返回结果
            
        Raises:
            Exception: 如果事务失败，则回滚并重新抛出异常
        """
        try:
            result = func(*args, **kwargs)
            self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            logger.error(f"Transaction failed: {str(e)}")
            raise
            
    def get_or_create(
        self,
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Tuple[ModelType, bool]:
        """
        获取或创建记录
        
        Args:
            defaults: 创建记录时使用的默认值
            **kwargs: 查询条件
            
        Returns:
            (对象, 是否已创建) 元组
        """
        # Build a filter with kwargs that are valid model fields
        query_filters = {k: v for k, v in kwargs.items() if hasattr(self.model, k)}
        
        # Query using the constructed filter
        query = self._build_query(filters=query_filters)
        instance = query.first()

        if instance:
            return instance, False
        else:
            # Create a new instance
            if defaults:
                kwargs.update(defaults)
            
            # Ensure all kwargs correspond to model attributes before creating
            instance_data = {k: v for k, v in kwargs.items() if hasattr(self.model, k)}
            instance = self.model(**instance_data)
            
            return self.create(instance), True

