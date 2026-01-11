"""健康检查端点

提供服务健康状态、就绪状态和详细的服务状态检查。
"""

# 标准库导入
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

# 第三方库导入
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# 本地模块导入（按字母顺序）
from config import settings
from core.config import get_app_config
from core.logging_config import setup_logging
from core.monitoring.health import (
    HealthCheckRegistry,
    HealthStatus,
    check_database_health,
    check_service_health,
)
from db.session import get_db

logger = setup_logging("backend.api.health")
health_router = APIRouter()

# 获取应用配置
app_config = get_app_config()

# 全局健康检查注册表
_health_registry: Optional[HealthCheckRegistry] = None


def get_health_registry() -> HealthCheckRegistry:
    """获取健康检查注册表"""
    global _health_registry
    if _health_registry is None:
        _health_registry = HealthCheckRegistry()
    return _health_registry


@health_router.get("/health", summary="健康检查")
async def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """
    基础健康检查端点，用于负载均衡器和容器编排系统

    Returns:
        服务健康状态
    """
    try:
        # 检查数据库连接
        from sqlalchemy import text
        db.execute(text("SELECT 1"))

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": app_config.APP_NAME,
                "version": app_config.APP_VERSION,
                "environment": settings.ENVIRONMENT,
            }
        )
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:
        logger.error(f"[health_check] 健康检查失败: {e}", exc_info=True)
        error_detail = (
            str(e) if settings.ENVIRONMENT != "production"
            else "Health check failed"
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "service": app_config.APP_NAME,
                "error": error_detail,
            }
        )


@health_router.get("/ready", summary="就绪检查")
async def readiness_check(db: Session = Depends(get_db)) -> JSONResponse:
    """
    就绪检查端点，用于Kubernetes等容器编排系统

    Returns:
        JSONResponse: 服务就绪状态
    """
    try:
        # 检查数据库连接
        from sqlalchemy import text
        db.execute(text("SELECT 1"))

        # 检查关键配置
        config_errors = []
        if not settings.DATABASE_URL:
            config_errors.append("DATABASE_URL未配置")
        if not settings.ACCESS_SECRET or settings.ACCESS_SECRET == "":
            config_errors.append("ACCESS_SECRET未配置")

        if config_errors:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "not_ready",
                    "timestamp": datetime.now().isoformat(),
                    "errors": config_errors,
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "timestamp": datetime.now().isoformat(),
            }
        )
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:
        logger.error(f"[readiness_check] 就绪检查失败: {e}", exc_info=True)
        error_detail = (
            str(e) if settings.ENVIRONMENT != "production"
            else "Service unavailable"
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "timestamp": datetime.now().isoformat(),
                "error": error_detail,
            }
        )


@health_router.get("/health/extended", summary="扩展健康检查")
async def extended_health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """
    扩展健康检查端点，提供详细的服务状态信息

    Returns:
        详细的服务健康状态
    """
    health_info: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": app_config.APP_NAME,
        "version": app_config.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {},
    }

    # 数据库健康检查
    try:
        from sqlalchemy import text
        result = db.execute(text("SELECT 1"))
        if result.fetchone():
            health_info["checks"]["database"] = {
                "status": "healthy",
                "message": "Database connection is healthy",
            }
    except Exception as e:
        health_info["checks"]["database"] = {
            "status": "unhealthy",
            "message": str(e) if settings.ENVIRONMENT != "production" else "Connection failed",
        }
        health_info["status"] = "degraded"

    # 检查其他服务（如果配置了）
    registry = get_health_registry()

    # 检查 Redis（如果配置）
    try:
        redis_url = getattr(settings, "REDIS_URL", None)
        if redis_url:
            # 这里可以添加 Redis 健康检查
            health_info["checks"]["redis"] = {
                "status": "unknown",
                "message": "Redis health check not implemented",
            }
    except Exception:
        pass

    # 检查外部服务
    external_services = []
    try:
        # 检查 TTS 服务
        tts_url = getattr(settings, "TTS_SERVICE_URL", None)
        if tts_url:
            external_services.append(("tts_service", tts_url))

        # 检查图像生成服务
        image_gen_url = getattr(settings, "IMAGE_GEN_SERVICE_URL", None)
        if image_gen_url:
            external_services.append(("image_gen", image_gen_url))

        # 异步检查外部服务
        if external_services:
            for name, url in external_services:
                try:
                    result = await check_service_health(url, name=name)
                    health_info["checks"][name] = {
                        "status": result.status.value,
                        "message": result.message or "",
                        "response_time_ms": result.response_time_ms,
                    }
                except Exception as e:
                    health_info["checks"][name] = {
                        "status": "unhealthy",
                        "message": str(e) if settings.ENVIRONMENT != "production" else "Service unavailable",
                    }
                    health_info["status"] = "degraded"
    except Exception as e:
        logger.error(f"Error checking external services: {e}", exc_info=True)

    # 计算整体状态
    if any(c["status"] == "unhealthy" for c in health_info["checks"].values()):
        health_info["status"] = "unhealthy"
    elif any(c["status"] == "degraded" for c in health_info["checks"].values()):
        health_info["status"] = "degraded"

    # 返回适当的状态码
    status_code = status.HTTP_200_OK
    if health_info["status"] == "degraded":
        status_code = status.HTTP_200_OK  # 降级服务仍然可用
    elif health_info["status"] == "unhealthy":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(status_code=status_code, content=health_info)


@health_router.get("/health/live", summary="存活检查")
async def liveness_check() -> JSONResponse:
    """
    存活检查端点，用于Kubernetes liveness probe

    Returns:
        JSONResponse: 服务存活状态
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "alive",
            "timestamp": datetime.now().isoformat(),
        }
    )


@health_router.get("/health/metrics", summary="健康检查指标")
async def health_metrics(db: Session = Depends(get_db)) -> JSONResponse:
    """
    健康检查指标端点，返回监控相关的指标信息

    Returns:
        健康检查指标
    """
    import psutil

    # 获取系统资源信息
    process = psutil.Process()

    metrics: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "service": app_config.APP_NAME,
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used,
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent,
            },
        },
        "process": {
            "pid": process.pid,
            "cpu_percent": process.cpu_percent(interval=0.1),
            "memory_info": {
                "rss": process.memory_info().rss,
                "vms": process.memory_info().vms,
            },
            "num_threads": process.num_threads(),
            "connections": len(process.connections()),
        },
    }

    # 数据库连接池信息
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        if inspector:
            pool = db.bind.pool
            metrics["database_pool"] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
            }
    except Exception as e:
        logger.warning(f"Failed to get database pool metrics: {e}")

    return JSONResponse(content=metrics)

