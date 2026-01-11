"""缓存模块，提供缓存装饰器和工具函数"""
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union
import pickle
import hashlib
import json
import logging
from datetime import timedelta

import redis
from redis.exceptions import RedisError

from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)

# 类型变量
T = TypeVar('T')

# Redis连接池
_redis_pool = None

def get_redis_connection() -> redis.Redis:
    """获取Redis连接"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=False  # 统一使用bytes
        )
    return redis.Redis(connection_pool=_redis_pool)


def cache_key_generator(prefix: str, *args, **kwargs) -> str:
    """生成缓存key"""
    key_parts = [prefix]
    
    # 处理位置参数
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        elif arg is not None:
            key_parts.append(hashlib.md5(pickle.dumps(arg)).hexdigest())
    
    # 处理关键字参数
    for k, v in sorted(kwargs.items()):
        if v is not None:
            key_parts.append(f"{k}={v}")
    
    return ":".join(key_parts)


def cached(
    key_prefix: str,
    ttl: int = 300,
    namespace: Optional[str] = None,
    key_func: Optional[Callable[..., str]] = None,
    cache_none: bool = False
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    缓存装饰器
    
    Args:
        key_prefix: 缓存key前缀
        ttl: 缓存过期时间(秒)
        namespace: 命名空间，用于区分不同环境的缓存
        key_func: 自定义key生成函数
        cache_none: 是否缓存None结果
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if not settings.CACHE_ENABLED:
                return func(*args, **kwargs)
                
            try:
                # 生成缓存key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = cache_key_generator(key_prefix, *args, **kwargs)
                    
                if namespace:
                    cache_key = f"{namespace}:{cache_key}"
                
                # 尝试从缓存获取
                redis_client = get_redis_connection()
                cached_value = redis_client.get(cache_key)
                
                if cached_value is not None:
                    try:
                        return pickle.loads(cached_value)
                    except (pickle.PickleError, TypeError) as e:
                        logger.warning(f"Failed to unpickle cached value for {cache_key}: {e}")
                
                # 缓存未命中，调用原函数
                result = func(*args, **kwargs)
                
                # 缓存结果
                if result is not None or cache_none:
                    try:
                        redis_client.setex(
                            cache_key,
                            time=ttl,
                            value=pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL)
                        )
                    except (pickle.PickleError, TypeError, RedisError) as e:
                        logger.error(f"Failed to cache result for {cache_key}: {e}")
                
                return result
                
            except Exception as e:
                logger.error(f"Cache error in {func.__name__}: {e}", exc_info=True)
                return func(*args, **kwargs)
                
        return wrapper
    return decorator


def invalidate_cache(key: str, namespace: Optional[str] = None) -> bool:
    """
    使缓存失效
    
    Args:
        key: 缓存key
        namespace: 命名空间
        
    Returns:
        bool: 是否成功删除缓存
    """
    if namespace:
        key = f"{namespace}:{key}"
        
    try:
        redis_client = get_redis_connection()
        return bool(redis_client.delete(key))
    except RedisError as e:
        logger.error(f"Failed to invalidate cache {key}: {e}")
        return False


class CacheManager:
    """缓存管理器，提供更高级的缓存操作"""
    
    def __init__(self, namespace: str = None):
        """
        初始化缓存管理器
        
        Args:
            namespace: 命名空间
        """
        self.namespace = namespace or settings.APP_NAME
        self.redis = get_redis_connection()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        try:
            cache_key = self._get_namespaced_key(key)
            value = self.redis.get(cache_key)
            if value is not None:
                return pickle.loads(value)
            return default
        except (pickle.PickleError, RedisError) as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            cache_key = self._get_namespaced_key(key)
            serialized = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            if ttl is not None:
                return self.redis.setex(cache_key, time=ttl, value=serialized)
            return self.redis.set(cache_key, serialized)
        except (pickle.PickleError, RedisError) as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, *keys: str) -> int:
        """删除缓存"""
        if not keys:
            return 0
            
        try:
            namespaced_keys = [self._get_namespaced_key(key) for key in keys]
            return self.redis.delete(*namespaced_keys)
        except RedisError as e:
            logger.error(f"Cache delete error for keys {keys}: {e}")
            return 0
    
    def clear_namespace(self) -> bool:
        """清除当前命名空间下的所有缓存"""
        try:
            pattern = f"{self.namespace}:*"
            keys = []
            cursor = '0'
            
            while cursor != 0:
                cursor, partial_keys = self.redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=1000
                )
                if partial_keys:
                    self.redis.delete(*partial_keys)
            
            return True
        except RedisError as e:
            logger.error(f"Failed to clear namespace {self.namespace}: {e}")
            return False
    
    def _get_namespaced_key(self, key: str) -> str:
        """获取带命名空间的key"""
        return f"{self.namespace}:{key}" if self.namespace else key
