"""异步基础DAO类"""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, cast, AsyncGenerator
from datetime import datetime
import logging

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, load_only as sqlalchemy_load_only
from sqlalchemy.sql.expression import Select

from core.logging_config import get_logger
from core.db.models import Base

logger = get_logger(__name__)

# 类型变量
ModelType = TypeVar('ModelType', bound=Base)
FilterType = Dict[str, Union[Any, tuple]]
OrderByType = Union[str, tuple]

class AsyncBaseDAO(Generic[ModelType]):
    """异步基础数据访问对象"""
    
    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        """
        初始化异步DAO
        
        Args:
            model: SQLAlchemy模型类
            session: 异步数据库会话
        """
        self.model = model
        self.session = session
        self._has_soft_delete = hasattr(model, 'deleted_at')
    
    async def get(self, id: Any, *, include_deleted: bool = False) -> Optional[ModelType]:
        """根据ID查询单条记录"""
        stmt = select(self.model).where(self.model.id == id)
        
        if self._has_soft_delete and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
            
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_field(
        self, 
        field_name: str, 
        value: Any, 
        *, 
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """根据字段查询单条记录"""
        if not hasattr(self.model, field_name):
            raise AttributeError(f"Model {self.model.__name__} has no attribute '{field_name}'")
            
        stmt = select(self.model).where(
            getattr(self.model, field_name) == value
        )
        
        if self._has_soft_delete and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
            
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(
        self, 
        *, 
        skip: int = 0, 
        limit: Optional[int] = None,
        filters: Optional[FilterType] = None,
        order_by: Optional[Union[str, List[OrderByType]]] = None,
        include_deleted: bool = False,
        load_only: Optional[List[str]] = None,
        joins: Optional[List[Any]] = None,
        options: Optional[List[Any]] = None
    ) -> List[ModelType]:
        """
        查询所有记录
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            filters: 过滤条件
            order_by: 排序字段
            include_deleted: 是否包含已删除的记录
            load_only: 仅加载指定字段
            joins: 关联表
            options: SQLAlchemy加载选项
            
        Returns:
            模型实例列表
        """
        stmt = await self._build_query(
            filters=filters,
            include_deleted=include_deleted,
            load_only=load_only,
            joins=joins,
            options=options
        )
        
        # 应用排序
        if order_by:
            stmt = await self._apply_ordering(stmt, order_by)
            
        # 应用分页
        if skip > 0:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
            
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def create(self, obj: ModelType, *, commit: bool = True) -> ModelType:
        """创建记录"""
        try:
            self.session.add(obj)
            if commit:
                await self.session.commit()
                await self.session.refresh(obj)
            return obj
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create {self.model.__name__}: {str(e)}")
            raise
    
    async def update(
        self, 
        obj: ModelType, 
        update_data: Optional[Dict[str, Any]] = None, 
        *, 
        commit: bool = True
    ) -> ModelType:
        """更新记录"""
        try:
            if update_data:
                for key, value in update_data.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                        
            if commit:
                await self.session.commit()
                await self.session.refresh(obj)
                
            return obj
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update {self.model.__name__} {obj.id}: {str(e)}")
            raise
    
    async def delete(self, id: Any, *, hard_delete: bool = False, commit: bool = True) -> bool:
        """删除记录"""
        obj = await self.get(id, include_deleted=True)
        if not obj:
            return False
            
        try:
            if self._has_soft_delete and not hard_delete:
                # 软删除
                obj.deleted_at = datetime.utcnow()
                if commit:
                    await self.session.commit()
            else:
                # 物理删除
                await self.session.delete(obj)
                if commit:
                    await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete {self.model.__name__} {id}: {str(e)}")
            return False
    
    async def _build_query(
        self, 
        filters: Optional[FilterType] = None,
        include_deleted: bool = False,
        load_only: Optional[List[str]] = None,
        joins: Optional[List[Any]] = None,
        options: Optional[List[Any]] = None
    ) -> Select:
        """构建基础查询"""
        stmt = select(self.model)
        
        # 应用关联加载
        if options:
            stmt = stmt.options(*options)
        
        # 应用关联表
        if joins:
            for join in joins:
                stmt = stmt.join(join)
        
        # 应用字段选择
        if load_only:
            fields = []
            for field_name in load_only:
                if hasattr(self.model, field_name):
                    fields.append(getattr(self.model, field_name))
            if fields:
                stmt = stmt.options(sqlalchemy_load_only(*fields))
        
        # 应用软删除过滤
        if self._has_soft_delete and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        
        # 应用过滤条件
        if filters:
            conditions = []
            for key, value in filters.items():
                if not hasattr(self.model, key):
                    logger.warning(f"Model {self.model.__name__} has no attribute '{key}' for filtering")
                    continue
                    
                field = getattr(self.model, key)
                
                # 支持元组形式的操作符
                if isinstance(value, tuple):
                    if len(value) == 2:
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
                        conditions.append(field.in_(value))
                else:
                    conditions.append(field == value)
                    
            if conditions:
                stmt = stmt.where(and_(*conditions))
                
        return stmt
    
    async def _apply_ordering(
        self, 
        stmt: Select, 
        order_by: Union[str, List[OrderByType]]
    ) -> Select:
        """应用排序"""
        if isinstance(order_by, str):
            order_by = [order_by]
            
        for item in order_by:
            if isinstance(item, str):
                if item.startswith('-'):
                    field_name = item[1:]
                    desc = True
                else:
                    field_name = item
                    desc = False
            else:
                field_name, desc = item
                
            if not hasattr(self.model, field_name):
                logger.warning(f"Model {self.model.__name__} has no attribute '{field_name}' for ordering")
                continue
                
            field = getattr(self.model, field_name)
            stmt = stmt.order_by(field.desc() if desc else field.asc())
            
        return stmt
    
    async def count(
        self, 
        filters: Optional[FilterType] = None, 
        include_deleted: bool = False
    ) -> int:
        """统计记录数"""
        stmt = await self._build_query(filters, include_deleted)
        stmt = stmt.with_only_columns([sqlalchemy.func.count()]).order_by(None)
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
    
    async def exists(self, **filters: Any) -> bool:
        """检查记录是否存在"""
        return await self.count(filters) > 0
    
    async def bulk_create(
        self, 
        objects: List[ModelType], 
        *, 
        commit: bool = True
    ) -> List[ModelType]:
        """批量创建记录"""
        try:
            self.session.add_all(objects)
            if commit:
                await self.session.commit()
            return objects
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to bulk create {len(objects)} {self.model.__name__}: {str(e)}")
            raise
    
    async def bulk_update(
        self, 
        objects: List[ModelType], 
        update_fields: Optional[List[str]] = None,
        *,
        commit: bool = True
    ) -> None:
        """批量更新记录"""
        if not objects:
            return
            
        try:
            for obj in objects:
                if update_fields:
                    update_data = {field: getattr(obj, field) for field in update_fields}
                else:
                    update_data = {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
                
                await self.session.execute(
                    update(self.model)
                    .where(self.model.id == obj.id)
                    .values(**update_data)
                )
                
            if commit:
                await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to bulk update {len(objects)} {self.model.__name__}: {str(e)}")
            raise
    
    async def execute_in_transaction(self, func: callable, *args: Any, **kwargs: Any) -> Any:
        """在事务中执行函数"""
        async with self.session.begin():
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Transaction failed: {str(e)}")
                raise
