"""健康检查模块

提供服务健康检查功能，支持多种健康检查类型和自定义健康检查。
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.config import MonitoringConfig
from core.logging_config import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    response_time_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "response_time_ms": self.response_time_ms,
        }


class HealthCheck(ABC):
    """健康检查抽象基类"""

    def __init__(self, name: str, timeout: float = MonitoringConfig.DEFAULT_HEALTH_CHECK_TIMEOUT):
        self.name = name
        self.timeout = timeout

    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """执行健康检查

        Returns:
            HealthCheckResult: 健康检查结果
        """
        pass

    async def run(self) -> HealthCheckResult:
        """运行健康检查，带有超时控制"""
        start_time = datetime.now()
        try:
            result = await asyncio.wait_for(self.check(), timeout=self.timeout)
            result.timestamp = start_time
            result.response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout: {self.name}")
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timeout after {self.timeout}s",
                timestamp=start_time,
                response_time_ms=self.timeout * 1000,
            )
        except Exception as e:
            logger.error(f"Health check error: {self.name} - {e}", exc_info=True)
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                timestamp=start_time,
                response_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )


class DatabaseHealthCheck(HealthCheck):
    """数据库健康检查"""

    def __init__(
        self,
        name: str = "database",
        db_session_factory: Optional[Callable] = None,
        timeout: float = MonitoringConfig.DEFAULT_HEALTH_CHECK_TIMEOUT,
    ):
        super().__init__(name, timeout)
        self.db_session_factory = db_session_factory

    async def check(self) -> HealthCheckResult:
        """检查数据库连接"""
        if self.db_session_factory is None:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message="Database session factory not configured",
            )

        try:
            from sqlalchemy import text

            # 获取数据库会话
            Session = self.db_session_factory
            with Session() as session:
                # 执行简单查询
                result = session.execute(text("SELECT 1"))
                row = result.fetchone()

                if row and row[0] == 1:
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.HEALTHY,
                        message="Database connection is healthy",
                    )
                else:
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.UNHEALTHY,
                        message="Database query returned unexpected result",
                    )

        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
            )


class RedisHealthCheck(HealthCheck):
    """Redis 健康检查"""

    def __init__(
        self,
        name: str = "redis",
        redis_client: Optional[Any] = None,
        timeout: float = MonitoringConfig.DEFAULT_HEALTH_CHECK_TIMEOUT,
    ):
        super().__init__(name, timeout)
        self.redis_client = redis_client

    async def check(self) -> HealthCheckResult:
        """检查 Redis 连接"""
        if self.redis_client is None:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message="Redis client not configured",
            )

        try:
            # 执行 PING 命令
            result = await self.redis_client.ping()

            if result:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Redis connection is healthy",
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="Redis PING failed",
                )

        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
            )


class ServiceHealthCheck(HealthCheck):
    """外部服务健康检查"""

    def __init__(
        self,
        name: str,
        service_url: str,
        timeout: float = MonitoringConfig.DEFAULT_HEALTH_CHECK_TIMEOUT,
        health_path: str = "/health",
    ):
        super().__init__(name, timeout)
        self.service_url = service_url.rstrip("/")
        self.health_url = f"{self.service_url}{health_path}"

    async def check(self) -> HealthCheckResult:
        """检查外部服务健康状态"""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.health_url)

                if response.status_code == 200:
                    # 尝试解析响应
                    try:
                        data = response.json()
                        return HealthCheckResult(
                            name=self.name,
                            status=HealthStatus(data.get("status", HealthStatus.HEALTHY)),
                            message=data.get("message", "Service is healthy"),
                            details={"response": data},
                        )
                    except Exception:
                        return HealthCheckResult(
                            name=self.name,
                            status=HealthStatus.HEALTHY,
                            message="Service is healthy",
                        )
                else:
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Service returned status code {response.status_code}",
                        details={"status_code": response.status_code},
                    )

        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Service health check failed: {str(e)}",
            )


class CustomHealthCheck(HealthCheck):
    """自定义健康检查"""

    def __init__(
        self,
        name: str,
        check_func: Callable[[], Any],
        timeout: float = MonitoringConfig.DEFAULT_HEALTH_CHECK_TIMEOUT,
    ):
        """
        Args:
            name: 检查名称
            check_func: 检查函数，可以是同步或异步函数
                       返回 HealthCheckResult 或可转换为结果的值
            timeout: 超时时间
        """
        super().__init__(name, timeout)
        self.check_func = check_func

    async def check(self) -> HealthCheckResult:
        """执行自定义健康检查"""
        try:
            # 检查是否是异步函数
            if asyncio.iscoroutinefunction(self.check_func):
                result = await self.check_func()
            else:
                result = self.check_func()

            # 如果返回的是 HealthCheckResult，直接返回
            if isinstance(result, HealthCheckResult):
                return result

            # 如果返回的是布尔值
            if isinstance(result, bool):
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    message="Check passed" if result else "Check failed",
                )

            # 如果返回的是字符串
            if isinstance(result, str):
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message=result,
                )

            # 默认返回健康
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Check completed",
            )

        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Custom health check failed: {str(e)}",
            )


class HealthCheckRegistry:
    """健康检查注册表

    管理多个健康检查，并提供统一的检查接口。
    """

    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}

    def register(self, check: HealthCheck) -> None:
        """注册健康检查

        Args:
            check: 健康检查实例
        """
        self.checks[check.name] = check
        logger.info(f"Registered health check: {check.name}")

    def unregister(self, name: str) -> None:
        """取消注册健康检查

        Args:
            name: 健康检查名称
        """
        if name in self.checks:
            del self.checks[name]
            logger.info(f"Unregistered health check: {name}")

    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """执行所有健康检查

        Returns:
            包含所有检查结果的字典
        """
        if not self.checks:
            logger.warning("No health checks registered")
            return {}

        results = {}
        tasks = [check.run() for check in self.checks.values()]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)

        for check, result in zip(self.checks.values(), check_results):
            if isinstance(result, Exception):
                results[check.name] = HealthCheckResult(
                    name=check.name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(result),
                )
            else:
                results[check.name] = result

        return results

    async def get_overall_status(self) -> HealthStatus:
        """获取整体健康状态

        Returns:
            HealthStatus: 整体健康状态
        """
        results = await self.check_all()

        if not results:
            return HealthStatus.UNKNOWN

        # 检查是否有任何不健康的检查
        unhealthy = any(r.status == HealthStatus.UNHEALTHY for r in results.values())
        if unhealthy:
            return HealthStatus.UNHEALTHY

        # 检查是否有任何降级的检查
        degraded = any(r.status == HealthStatus.DEGRADED for r in results.values())
        if degraded:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY


# 便捷函数
async def check_database_health(
    db_session_factory: Callable,
    name: str = "database",
    timeout: float = MonitoringConfig.DEFAULT_HEALTH_CHECK_TIMEOUT,
) -> HealthCheckResult:
    """检查数据库健康状态

    Args:
        db_session_factory: 数据库会话工厂
        name: 检查名称
        timeout: 超时时间

    Returns:
        HealthCheckResult: 健康检查结果
    """
    check = DatabaseHealthCheck(name, db_session_factory, timeout)
    return await check.run()


async def check_redis_health(
    redis_client: Any,
    name: str = "redis",
    timeout: float = MonitoringConfig.DEFAULT_HEALTH_CHECK_TIMEOUT,
) -> HealthCheckResult:
    """检查 Redis 健康状态

    Args:
        redis_client: Redis 客户端
        name: 检查名称
        timeout: 超时时间

    Returns:
        HealthCheckResult: 健康检查结果
    """
    check = RedisHealthCheck(name, redis_client, timeout)
    return await check.run()


async def check_service_health(
    service_url: str,
    name: Optional[str] = None,
    health_path: str = "/health",
    timeout: float = MonitoringConfig.DEFAULT_HEALTH_CHECK_TIMEOUT,
) -> HealthCheckResult:
    """检查外部服务健康状态

    Args:
        service_url: 服务 URL
        name: 检查名称（默认从 URL 提取）
        health_path: 健康检查路径
        timeout: 超时时间

    Returns:
        HealthCheckResult: 健康检查结果
    """
    if name is None:
        name = service_url.replace("https://", "").replace("http://", "").split("/")[0]

    check = ServiceHealthCheck(name, service_url, timeout, health_path)
    return await check.run()
