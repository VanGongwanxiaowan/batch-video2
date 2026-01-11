"""Azure TTS Server 主应用入口."""

import uvicorn
from api import router
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_azure_tts_config
from core.exceptions import BatchShortException
from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("azure_tts_server", log_to_file=True)

# 获取配置
config = get_azure_tts_config()

# 创建 FastAPI 应用
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="Azure TTS 语音合成服务",
    docs_url="/docs" if config.DEBUG else None,
    redoc_url="/redoc" if config.DEBUG else None,
)

# 配置 CORS
cors_origins = config.cors_origins_list if config.cors_origins_list else (
    ["*"] if config.DEBUG else []
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# 注册路由
app.include_router(router)

# 统一异常处理
@app.exception_handler(BatchShortException)
async def batchshort_exception_handler(request: Request, exc: BatchShortException):
    """统一处理 BatchShort 异常"""
    # 根据异常类型确定 HTTP 状态码
    if isinstance(exc, ConfigurationException):
        status_code = 503  # Service Unavailable
    elif isinstance(exc, ServiceException):
        status_code = 502  # Bad Gateway
    else:
        status_code = 500  # Internal Server Error

    logger.error(
        f"BatchShortException: {exc.error_code} - {exc.message}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code
        }
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "code": exc.error_code,
            "message": exc.message,
            "success": False
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理未预期的异常"""
    logger.exception(
        f"未预期的异常: {type(exc).__name__} - {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误" if not config.DEBUG else str(exc),
            "success": False
        }
    )

# 启动和关闭事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化."""
    logger.info(
        f"{config.APP_NAME} v{config.APP_VERSION} 启动成功 - "
        f"监听地址: {config.HOST}:{config.PORT}"
    )


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理."""
    logger.info(f"{config.APP_NAME} 正在关闭...")


@app.get("/")
async def root():
    """根路径."""
    return {
        "service": config.APP_NAME,
        "version": config.APP_VERSION,
        "status": "running",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        log_level="info" if not config.DEBUG else "debug",
        reload=config.DEBUG,
    )
