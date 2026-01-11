# 标准库导入
import os
import sys
from pathlib import Path
from typing import Type

# 第三方库导入
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.types import ASGIApp

# 路径设置（在导入本地模块之前）
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 本地模块导入（按字母顺序）
from api import account, job, language, topic, utils, voice
from api.account import auth_router
from api.health import health_router
from db.models import (  # 明确导入，避免使用 import *
    Account,
    Job,
    JobSplit,
    Language,
    Topic,
    User,
    Voice,
)
from db.session import Base, engine

from config import settings
from core.config import get_app_config, MonitoringConfig
from core.db import models as core_models  # noqa: F401  # 确保模型注册
from core.exceptions import (
    BatchShortException,
    JobNotFoundException,
    ServiceException,
    ValidationException,
)
from core.logging_config import setup_logging
from core.monitoring import (
    LoggingMiddleware,
    MetricsMiddleware,
    RequestIdMiddleware,
    init_metrics,
    init_tracing,
    setup_alerting,
)
from core.monitoring.db_metrics import setup_sqlalchemy_metrics

logger = setup_logging("backend.api")

# 获取应用配置
app_config = get_app_config()

# 获取监控配置
metrics_enabled = os.getenv("METRICS_ENABLED", "true").lower() == "true"
metrics_port = int(os.getenv("METRICS_PORT", str(MonitoringConfig.DEFAULT_METRICS_PORT)))
tracing_enabled = os.getenv("TRACING_ENABLED", "false").lower() == "true"
tracing_sample_rate = float(os.getenv("TRACING_SAMPLE_RATE", str(MonitoringConfig.DEFAULT_TRACING_SAMPLE_RATE)))
alerting_enabled = os.getenv("ALERTING_ENABLED", "false").lower() == "true"
alertmanager_url = os.getenv("ALERTMANAGER_URL", MonitoringConfig.DEFAULT_ALERTMANAGER_URL)

# 初始化监控功能
if metrics_enabled:
    try:
        init_metrics(
            service_name="backend",
            metrics_enabled=metrics_enabled,
            metrics_port=metrics_port,
        )
        logger.info(f"Prometheus metrics initialized on port {metrics_port}")
    except Exception as e:
        logger.warning(f"Failed to initialize metrics: {e}")

# 初始化分布式追踪
if tracing_enabled:
    try:
        init_tracing(
            enabled=tracing_enabled,
            sample_rate=tracing_sample_rate,
        )
        logger.info(f"Distributed tracing enabled (sample_rate={tracing_sample_rate})")
    except Exception as e:
        logger.warning(f"Failed to initialize tracing: {e}")

# 初始化告警系统
if alerting_enabled:
    try:
        setup_alerting(
            enabled=alerting_enabled,
            alertmanager_url=alertmanager_url,
        )
        logger.info(f"Alerting enabled (AlertManager: {alertmanager_url})")
    except Exception as e:
        logger.warning(f"Failed to initialize alerting: {e}")

# 创建 FastAPI 应用
app = FastAPI(
    title="BatchShort Backend API",
    description="批处理短视频生成系统 - 后端 API 服务",
    version=app_config.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 注意：在生产环境中，应该使用数据库迁移工具（如Alembic）而不是create_all
# create_all 仅用于开发环境
if settings.ENVIRONMENT == "development":
    logger.warning("开发环境：使用 create_all 创建数据库表，生产环境应使用迁移工具")
    Base.metadata.create_all(bind=engine)
else:
    logger.info("生产环境：跳过 create_all，请使用数据库迁移工具")

# 设置数据库监控
try:
    setup_sqlalchemy_metrics(engine)
    logger.info("Database metrics monitoring enabled")
except Exception as e:
    logger.warning(f"Failed to setup database metrics: {e}")


@app.middleware("http")
async def log_requests(request: Request, call_next: ASGIApp) -> Response:
    """简单请求级日志中间件，记录方法 / 路径 / 状态码。"""
    logger.info(
        "HTTP request started",
        extra={"method": request.method, "path": request.url.path}
    )
    try:
        response = await call_next(request)
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except BatchShortException:
        # 业务异常，由异常处理器处理，这里只记录
        raise
    except Exception as exc:
        # 捕获未处理的异常，写入错误日志
        logger.error(
            "Unhandled exception in request",
            exc_info=True,
            extra={"method": request.method, "path": request.url.path},
        )
        raise

    logger.info(
        "HTTP request finished",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code
        },
    )
    return response


def _status_for_exception(exc: BatchShortException) -> int:
    """根据异常类型返回对应的HTTP状态码。
    
    Args:
        exc: BatchShortException 异常实例
    
    Returns:
        HTTP状态码
    """
    if isinstance(exc, ValidationException):
        return 422
    if isinstance(exc, JobNotFoundException):
        return 404
    if isinstance(exc, ServiceException):
        return 502
    return 400


@app.exception_handler(BatchShortException)
async def batchshort_exception_handler(request: Request, exc: BatchShortException) -> JSONResponse:
    """统一将核心业务异常转成结构化JSON并写入日志。"""
    logger.error(
        "BatchShortException handled",
        exc_info=True,
        extra={
            "error_code": exc.error_code,
            "message": exc.message,
            "path": request.url.path,
            "method": request.method,
        },
    )
    status_code = _status_for_exception(exc)
    return JSONResponse(
        status_code=status_code,
        content={"code": exc.error_code, "message": exc.message},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
    allow_credentials=True,
)

# 添加监控中间件（按顺序添加）
# 1. 请求 ID 中间件（最外层）
app.add_middleware(RequestIdMiddleware)

# 2. 日志中间件
app.add_middleware(LoggingMiddleware)

# 3. Prometheus 指标中间件
if metrics_enabled:
    app.add_middleware(MetricsMiddleware, service_name="backend")

# 健康检查路由（不添加前缀）
app.include_router(health_router)

# API路由 - 添加版本前缀（从配置读取）
API_V1_PREFIX = f"{settings.API_PREFIX}/{settings.API_VERSION}"

app.include_router(job.job_router, tags=["job"], prefix=f"{API_V1_PREFIX}/jobs")
app.include_router(account.account_router, tags=["account"], prefix=f"{API_V1_PREFIX}/accounts")
app.include_router(voice.voice_router, tags=["voice"], prefix=f"{API_V1_PREFIX}/voices")
app.include_router(topic.topic_router, tags=["topic"], prefix=f"{API_V1_PREFIX}/topics")
app.include_router(language.language_router, tags=["language"], prefix=f"{API_V1_PREFIX}/languages")
app.include_router(utils.utils_router, tags=["utils"], prefix=f"{API_V1_PREFIX}/utils")
app.include_router(auth_router, tags=["auth"], prefix=f"{API_V1_PREFIX}/auth")


@app.get("/v2/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=f"{app.openapi_url}",
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.10.0/swagger-ui-bundle.js",
        swagger_css_url="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.10.0/swagger-ui.min.css",
        swagger_ui_parameters={"persistAuthorization": True},
    )


def start_env() -> None:
    """启动API服务器"""
    # 生产环境不应使用 reload=True
    reload = settings.ENVIRONMENT == "development"
    if reload:
        logger.warning("开发环境：启用自动重载，生产环境应禁用")
    else:
        logger.info("生产环境：禁用自动重载")
    
    uvicorn.run(
        "api_main:app",
        host="0.0.0.0",
        port=8006,
        reload=reload,
        log_level="info" if settings.ENVIRONMENT == "production" else "debug"
    )


if __name__ == "__main__":
    start_env()