"""带缓存的DAO基类"""
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast
from functools import wraps
import inspect

from sqlalchemy.orm import Session

from core.cache import CacheManager, cached
from core.config import settings
from core.db.models import Base
from .base_dao import BaseDAO, FilterType, OrderByType

ModelType = TypeVar('ModelType', bound=Base)


def auto_key_generator(prefix: str) -> Callable[..., str]:
    """自动生成缓存key的工厂函数"""
    def wrapper(func: Callable, *args: Any, **kwargs: Any) -> str:
        # 获取方法参数
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        # 构建key部分
        key_parts = [prefix]
        
        # 添加位置和关键字参数
        for name, value in bound_args.arguments.items():
            if name == 'self':
                continue
                
            if isinstance(value, (str, int, float, bool)) or value is None:
                key_parts.append(f"{name}={value}")
            elif hasattr(value, 'id'):
                key_parts.append(f"{name}_id={getattr(value, 'id')}")
            else:
                key_parts.append(f"{name}={str(value)}")
                
        return ":".join(key_parts)
    return wrapper


class CachedDAO(BaseDAO[ModelType]):
    """带缓存的DAO基类"""
    
    def __init__(
        self, 
        model: Type[ModelType], 
        session: Session,
        cache_namespace: Optional[str] = None,
        cache_ttl: Optional[int] = None
    ) -> None:
        """
        初始化带缓存的DAO
        
        Args:
            model: 模型类
            session: 数据库会话
            cache_namespace: 缓存命名空间，默认为模型类名小写
            cache_ttl: 缓存过期时间(秒)，默认为配置中的CACHE_DEFAULT_TTL
        """
        super().__init__(model, session)
        self.cache = CacheManager(namespace=cache_namespace or model.__name__.lower())
        self.cache_ttl = cache_ttl or settings.CACHE_DEFAULT_TTL
    
    def get(self, id: Any, *, include_deleted: bool = False) -> Optional[ModelType]:
        """重写get方法，添加缓存支持"""
        cache_key = f"get:{id}:{include_deleted}"
        
        @cached(
            key_prefix=cache_key,
            ttl=self.cache_ttl,
            namespace=self.cache.namespace
        )
        def _get() -> Optional[ModelType]:
            return super().get(id, include_deleted=include_deleted)
            
        return _get()
    
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
        """重写get_all方法，添加缓存支持"""
        # 对于分页查询，通常不缓存，或者只缓存第一页
        if skip > 0 or limit is not None:
            return super().get_all(
                skip=skip,
                limit=limit,
                filters=filters,
                order_by=order_by,
                include_deleted=include_deleted,
                load_only=load_only
            )
            
        # 为完整查询结果生成缓存key
        cache_key_parts = ["get_all"]
        if filters:
            cache_key_parts.append(f"filters={str(filters)}")
        if order_by:
            cache_key_parts.append(f"order_by={str(order_by)}")
        if include_deleted:
            cache_key_parts.append("include_deleted=True")
        if load_only:
            cache_key_parts.append(f"load_only={','.join(sorted(load_only))}")
            
        cache_key = ":".join(cache_key_parts)
        
        @cached(
            key_prefix=cache_key,
            ttl=self.cache_ttl,
            namespace=self.cache.namespace
        )
        def _get_all() -> List[ModelType]:
            return super().get_all(
                skip=skip,
                limit=limit,
                filters=filters,
                order_by=order_by,
                include_deleted=include_deleted,
                load_only=load_only
            )
            
        return _get_all()
    
    def create(self, obj: ModelType, *, commit: bool = True) -> ModelType:
        """重写create方法，使相关缓存失效"""
        result = super().create(obj, commit=commit)
        if commit:
            self._invalidate_related_caches()
        return result
    
    def update(
        self, 
        obj: ModelType, 
        update_data: Optional[Dict[str, Any]] = None, 
        *, 
        commit: bool = True
    ) -> ModelType:
        """重写update方法，使相关缓存失效"""
        result = super().update(obj, update_data, commit=commit)
        if commit:
            self._invalidate_related_caches(obj.id)
        return result
    
    def delete(self, id: Any, *, hard_delete: bool = False, commit: bool = True) -> bool:
        """重写delete方法，使相关缓存失效"""
        result = super().delete(id, hard_delete=hard_delete, commit=commit)
        if commit and result:
            self._invalidate_related_caches(id)
        return result
    
    def _invalidate_related_caches(self, *ids: Any) -> None:
        """使相关缓存失效"""
        # 使所有包含这些ID的缓存失效
        for id in ids:
            self.cache.delete(f"get:{id}:True", f"get:{id}:False")
        
        # 使所有get_all缓存失效
        self.cache.clear_namespace()
        
        # 可以在这里添加更多特定于模型的缓存失效逻辑


# 使用示例
class CachedJobDAO(CachedDAO[Job], JobDAO):
    """带缓存的任务DAO"""
    def __init__(self, session: Session) -> None:
        super().__init__(Job, session, cache_namespace="jobs")
        
    # 可以添加特定于Job的缓存方法
    def get_by_user_id(
        self, 
        user_id: str, 
        *, 
        skip: int = 0, 
        limit: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[Job]:
        """重写get_by_user_id方法，添加缓存支持"""
        # 对于分页查询，只缓存前几页
        if skip > 0 or limit is not None:
            return super().get_by_user_id(
                user_id, 
                skip=skip, 
                limit=limit, 
                order_by=order_by
            )
            
        cache_key = f"get_by_user_id:{user_id}:{order_by}"
        
        @cached(
            key_prefix=cache_key,
            ttl=self.cache_ttl,
            namespace=self.cache.namespace
        )
        def _get_by_user_id() -> List[Job]:
            return super().get_by_user_id(
                user_id, 
                skip=skip, 
                limit=limit, 
                order_by=order_by
            )
            
        return _get_by_user_id()
