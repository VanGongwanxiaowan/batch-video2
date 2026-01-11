"""API 限流模块

提供多种限流算法和后端存储支持。
"""
import asyncio
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request, status

from core.config import get_app_config
from core.logging_config import get_logger

logger = get_logger(__name__)

# 获取应用配置
app_config = get_app_config()


@dataclass
class RateLimitConfig:
    """限流配置"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    enabled: bool = True


class RateLimitExceeded(HTTPException):
    """限流异常"""
    def __init__(
        self,
        limit: int,
        window: str,
        retry_after: Optional[int] = None,
    ):
        self.limit = limit
        self.window = window
        self.retry_after = retry_after or 60
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": limit,
                "window": window,
                "retry_after": self.retry_after,
            },
        )


class RateLimitBackend(ABC):
    """限流后端抽象基类"""

    @abstractmethod
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> Tuple[bool, int]:
        """检查是否允许请求

        Args:
            key: 限流键（通常是用户ID或IP）
            limit: 限制数量
            window: 时间窗口（秒）

        Returns:
            Tuple[是否允许, 重试时间（秒）]
        """
        pass

    @abstractmethod
    async def reset(self, key: str) -> None:
        """重置限流计数器"""
        pass


class MemoryBackend(RateLimitBackend):
    """内存限流后端

    使用内存存储限流状态，适用于单实例部署。
    使用滑动窗口算法实现。
    """

    def __init__(self):
        # 存储每个key的请求时间戳列表
        self._requests: Dict[str, list] = {}
        # 清理锁，防止并发问题
        self._locks: Dict[str, asyncio.Lock] = {}

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> Tuple[bool, int]:
        """检查是否允许请求"""
        now = time.time()
        window_start = now - window

        # 获取或创建锁
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        async with self._locks[key]:
            # 获取或初始化请求列表
            if key not in self._requests:
                self._requests[key] = []

            # 清理过期的请求记录
            requests = self._requests[key]
            # 使用列表推导式过滤，保持时间戳顺序
            valid_requests = [t for t in requests if t > window_start]
            self._requests[key] = valid_requests

            # 检查是否超过限制
            current_count = len(valid_requests)
            if current_count >= limit:
                # 计算最旧请求的过期时间
                oldest_request = valid_requests[0]
                retry_after = int(oldest_request + window - now) + 1
                return False, retry_after

            # 添加当前请求
            self._requests[key].append(now)
            return True, 0

    async def reset(self, key: str) -> None:
        """重置限流计数器"""
        async with self._locks.get(key, asyncio.Lock()):
            if key in self._requests:
                del self._requests[key]


class RedisBackend(RateLimitBackend):
    """Redis 限流后端

    使用 Redis 存储限流状态，支持分布式部署。
    使用滑动窗口算法实现。
    """

    def __init__(self, redis_client=None):
        """初始化 Redis 后端

        Args:
            redis_client: Redis 客户端实例
        """
        self._redis = redis_client
        self._enabled = redis_client is not None

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> Tuple[bool, int]:
        """检查是否允许请求"""
        if not self._enabled or self._redis is None:
            # 降级到内存实现
            return await MemoryBackend().is_allowed(key, limit, window)

        try:
            now = time.time()
            window_start = now - window
            redis_key = f"ratelimit:{key}"

            # 使用 Redis sorted set 实现滑动窗口
            pipe = self._redis.pipeline()

            # 移除窗口外的记录
            pipe.zremrangebyscore(redis_key, 0, window_start)

            # 获取当前窗口内的请求数
            pipe.zcard(redis_key)

            # 添加当前请求
            pipe.zadd(redis_key, {str(now): now})

            # 设置过期时间
            pipe.expire(redis_key, window)

            results = await pipe.execute()

            current_count = results[1]

            if current_count >= limit:
                # 计算最旧请求的过期时间
                oldest = await self._redis.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window - now) + 1
                else:
                    retry_after = window
                return False, retry_after

            return True, 0

        except Exception as e:
            logger.error(f"Redis rate limit error: {e}", exc_info=True)
            # 降级到允许通过，避免影响服务可用性
            return True, 0

    async def reset(self, key: str) -> None:
        """重置限流计数器"""
        if self._enabled and self._redis:
            try:
                await self._redis.delete(f"ratelimit:{key}")
            except Exception as e:
                logger.error(f"Failed to reset rate limit: {e}", exc_info=True)


class TokenBucketLimiter(RateLimiter):
    """令牌桶算法限流器

    以固定速率向桶中添加令牌，请求消耗令牌。
    适用于需要平滑处理突发流量的场景。
    """

    def __init__(
        self,
        rate: int = 10,  # 每秒添加的令牌数
        capacity: int = 100,  # 桶的容量
        backend: Optional[RateLimitBackend] = None,
    ):
        self.rate = rate
        self.capacity = capacity
        self.backend = backend or MemoryBackend()
        # 存储每个key的状态
        self._tokens: Dict[str, float] = {}
        self._last_update: Dict[str, float] = {}

    async def is_allowed(
        self,
        key: str,
        tokens: int = 1,
    ) -> Tuple[bool, int]:
        """检查是否允许请求

        Args:
            key: 限流键
            tokens: 需要的令牌数

        Returns:
            Tuple[是否允许, 重试时间（秒）]
        """
        now = time.time()

        # 获取当前令牌数
        if key not in self._tokens:
            self._tokens[key] = float(self.capacity)
            self._last_update[key] = now

        # 计算应该添加的令牌数
        time_passed = now - self._last_update[key]
        new_tokens = time_passed * self.rate

        # 更新令牌数，不超过容量
        self._tokens[key] = min(
            self.capacity,
            self._tokens[key] + new_tokens
        )
        self._last_update[key] = now

        # 检查是否有足够的令牌
        if self._tokens[key] >= tokens:
            self._tokens[key] -= tokens
            return True, 0
        else:
            # 计算需要等待的时间
            wait_time = (tokens - self._tokens[key]) / self.rate
            return False, int(wait_time) + 1


class SlidingWindowLimiter:
    """滑动窗口限流器

    使用滑动窗口算法进行限流，比固定窗口更平滑。
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
        backend: Optional[RateLimitBackend] = None,
    ):
        """
        Args:
            requests_per_minute: 每分钟请求数限制
            requests_per_hour: 每小时请求数限制
            burst_size: 突发流量大小
            backend: 限流后端
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        self.backend = backend or MemoryBackend()

    async def is_allowed(self, key: str) -> Tuple[bool, int]:
        """检查是否允许请求"""
        # 检查分钟级限制
        minute_allowed, minute_retry = await self.backend.is_allowed(
            f"{key}:minute",
            self.requests_per_minute,
            60,
        )

        if not minute_allowed:
            return False, minute_retry

        # 检查小时级限制
        hour_allowed, hour_retry = await self.backend.is_allowed(
            f"{key}:hour",
            self.requests_per_hour,
            3600,
        )

        return hour_allowed, hour_retry


class RateLimiter:
    """统一限流器接口

    提供多种限流策略的统一接口。
    """

    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        backend: Optional[RateLimitBackend] = None,
    ):
        self.config = config or RateLimitConfig()
        self.backend = backend or MemoryBackend()

        # 创建滑动窗口限流器
        self.sliding_window = SlidingWindowLimiter(
            requests_per_minute=self.config.requests_per_minute,
            requests_per_hour=self.config.requests_per_hour,
            burst_size=self.config.burst_size,
            backend=self.backend,
        )

    async def check_rate_limit(
        self,
        request: Request,
    ) -> None:
        """检查请求是否超过限流

        Args:
            request: FastAPI 请求对象

        Raises:
            RateLimitExceeded: 如果超过限流
        """
        if not self.config.enabled:
            return

        # 获取限流键
        key = self._get_rate_limit_key(request)

        # 检查限流
        allowed, retry_after = await self.sliding_window.is_allowed(key)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for key: {key}",
                extra={"key": key, "retry_after": retry_after}
            )
            raise RateLimitExceeded(
                limit=self.config.requests_per_minute,
                window="minute",
                retry_after=retry_after,
            )

    def _get_rate_limit_key(self, request: Request) -> str:
        """获取限流键

        优先使用用户ID，然后使用IP地址
        """
        # 尝试从请求中获取用户信息
        # 这里可以根据实际的认证方式调整
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # 使用客户端IP
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"


# 全局限流器实例
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(
    config: Optional[RateLimitConfig] = None,
    backend: Optional[RateLimitBackend] = None,
) -> RateLimiter:
    """获取全局限流器实例

    Args:
        config: 限流配置
        backend: 限流后端

    Returns:
        RateLimiter: 限流器实例
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        # 尝试从环境变量获取配置
        requests_per_minute = int(
            os.getenv("RATE_LIMIT_PER_MINUTE", str(config.requests_per_minute if config else 60))
        )
        requests_per_hour = int(
            os.getenv("RATE_LIMIT_PER_HOUR", str(config.requests_per_hour if config else 1000))
        )
        enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

        rate_config = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            enabled=enabled,
        )

        _global_rate_limiter = RateLimiter(
            config=rate_config,
            backend=backend,
        )
    return _global_rate_limiter
