"""AI图像生成API服务主入口

.. deprecated::
    此 API 服务使用 Kafka 进行异步任务处理，现已废弃。
    推荐使用 flux_server 提供的同步 HTTP API。

迁移指南:
    - 旧 API (Kafka 模式): POST /generate_image -> 返回 task_id，需轮询
    - 新 API (同步模式): POST /generate_image/ -> 直接返回图像二进制数据

flux_server 地址: http://localhost:8010
"""
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from api_service.kafka_producer import KafkaProducer
from api_service.schemas import ImageGenerationRequest, TaskStatusResponse
from data_management.database import get_db, init_db
from data_management.models import Task
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from core.exceptions import (
    BatchShortException,
    ConfigurationException,
    DatabaseException,
    FileException,
    FileNotFoundException,
    JobNotFoundException,
    JobProcessingException,
    ServiceException,
    ServiceUnavailableException,
)
from core.logging_config import setup_logging

# Configure logging
logger = setup_logging("ai_image_gen.api")

# 初始化 Kafka Producer (已废弃)
kafka_producer = KafkaProducer()

# Directory to save generated images - use absolute path for security
GENERATED_IMAGES_DIR = os.path.abspath("uploads_images")
os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up API service...")
    # Ensure Kafka producer is connected on startup
    if not kafka_producer.producer:
        kafka_producer._connect_kafka()
    # Initialize database tables if they don't exist
    try:
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise
    yield
    logger.info("Shutting down API service...")
    kafka_producer.close()


app = FastAPI(
    title="AI Image Generation API (Deprecated - Kafka Mode)",
    description="API for generating images using various AI models. **DEPRECATED**: Please use flux_server synchronous API instead.",
    version="1.0.0-deprecated",
    lifespan=lifespan,
)


# ============================================================================
# 废弃警告中间件
# ============================================================================

@app.middleware("http")
async def deprecation_warning_middleware(request: Request, call_next):
    """为 Kafka 相关端点添加废弃警告头"""
    response = await call_next(request)

    # 为 Kafka 相关端点添加废弃警告
    kafka_endpoints = ["/generate_image", "/upload_image", "/check_status/", "/get_image/"]
    if any(request.url.path.startswith(ep) for ep in kafka_endpoints):
        response.headers["X-API-Deprecated"] = "true"
        response.headers["X-API-Recommended-Alternative"] = "flux_server:8010/generate_image/"
        logger.warning(
            f"[DEPRECATED] Kafka API endpoint accessed: {request.url.path}. "
            f"Please use flux_server synchronous API instead."
        )

    return response


@app.post(
    "/generate_image",
    response_model=TaskStatusResponse,
    summary="Submit an image generation task to Kafka (DEPRECATED)",
    deprecated=True,
)
async def generate_image(
    request: ImageGenerationRequest, db: Session = Depends(get_db)
):
    """
    Receives an image generation request, assigns a task ID, and sends it to the appropriate Kafka topic.

    .. deprecated::
        此端点已废弃。请使用 flux_server 的同步 API:
        POST http://flux_server:8010/generate_image/

    旧模式流程:
        1. 提交任务到此端点，获得 task_id
        2. 轮询 /check_status/{task_id} 查询状态
        3. 从 /get_image/{task_id} 获取图片

    新模式流程:
        1. 直接调用 flux_server 的 /generate_image/ 端点
        2. 同步等待，直接获取图像二进制数据
    """
    task_id = str(uuid.uuid4())

    topic = request.topic  # Directly use topic from request

    task_data = {
        "task_id": task_id,
        "model_name": request.model_name,
        "prompt": request.prompt,
        "negative_prompt": request.negative_prompt,
        "image_params": request.image_params.dict(),
        "loras": request.loras if request.loras else [],
        "user_id": request.user_id,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # Create a new task entry in the database
        db_task = Task(
            id=task_id,
            user_id=request.user_id,
            model_name=request.model_name,
            topic=request.topic,  # Save topic to database
            loras=request.loras,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            image_params=request.image_params.dict(),
            status="queued",
            submitted_at=datetime.now(),
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        logger.info(f"Task {task_id} created in database with status 'queued'.")

        # Send message to Kafka
        await kafka_producer.send_message(topic, task_data)
        logger.info(
            f"Task {task_id} for model {request.model_name} sent to Kafka topic {topic}"
        )
        return TaskStatusResponse(task_id=task_id, status="queued")
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        db.rollback()
        raise
    except ServiceException:
        db.rollback()
        raise
    except Exception as e:
        # 其他异常（数据库错误、Kafka错误等）
        db.rollback()
        logger.error(f"[generate_image] Failed to submit task {task_id}: {e}", exc_info=True)
        raise ServiceException(f"Failed to submit task: {e}", service_name="image_gen.api")


@app.post(
    "/upload_image",
    summary="Upload a generated image and save its metadata (DEPRECATED)",
    deprecated=True,
)
async def upload_image(
    task_id: str,
    image: UploadFile = File(None),
    error_message: str = None,
    db: Session = Depends(get_db),
):
    """
    Receives a generated image from the consumer worker, saves it to disk,
    and updates the task status in the database.
    If no image is provided, marks the task as 'failed' with an optional error message.

    .. deprecated::
        此端点已废弃。flux_server 同步模式不需要此端点。
    """
    try:
        db_task = db.query(Task).filter(Task.id == task_id).first()
        if not db_task:
            logger.warning(
                f"Task {task_id} not found in database during image upload/status update. Creating new entry."
            )
            db_task = Task(
                id=task_id,
                user_id="unknown",  # Placeholder, as user_id is not available here
                model_name="unknown",  # Placeholder
                topic="unknown",  # Placeholder for topic
                prompt="unknown",  # Placeholder
                image_params={},  # Placeholder
                submitted_at=datetime.now(),
            )
            db.add(db_task)
            db.commit()
            db.refresh(db_task)

        if image:
            # Validate file extension for security
            file_extension = (
                image.filename.split(".")[-1].lower() if "." in image.filename else "png"
            )
            # Only allow safe image extensions
            allowed_extensions = {"png", "jpg", "jpeg", "webp"}
            if file_extension not in allowed_extensions:
                file_extension = "png"
            
            # Use task_id as filename to prevent path traversal
            image_filename = f"{task_id}.{file_extension}"
            image_path = os.path.abspath(
                os.path.join(GENERATED_IMAGES_DIR, image_filename)
            )
            
            # Security check: ensure the path is within the allowed directory
            if not image_path.startswith(os.path.abspath(GENERATED_IMAGES_DIR)):
                raise FileException(
                    f"Invalid image path: {image_path}",
                    file_path=image_path
                )

            # Save image to disk
            try:
                with open(image_path, "wb") as buffer:
                    content = await image.read()
                    buffer.write(content)
                logger.info(f"Image for task {task_id} saved to {image_path}")

                db_task.status = "completed"
                db_task.image_url = image_path
                db_task.completed_at = datetime.now()
                db.commit()
                db.refresh(db_task)
                logger.info(
                    f"Task {task_id} status updated to 'completed' and image path saved in database."
                )
                return JSONResponse(
                    content={
                        "message": "Image uploaded and metadata saved successfully",
                        "task_id": task_id,
                        "status": "completed",
                        "image_path": image_path,
                    }
                )
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                db.rollback()
                raise
            except (OSError, PermissionError, FileNotFoundError) as save_error:
                # 文件系统错误
                db.rollback()
                logger.error(f"[upload_image] 文件系统错误 task_id={task_id}: {save_error}", exc_info=True)
                raise FileException(
                    f"Failed to save image: {save_error}",
                    file_path=image_path
                )
            except Exception as save_error:
                # 其他异常（数据库错误等）
                db.rollback()
                logger.error(f"[upload_image] Failed to save image for task {task_id}: {save_error}", exc_info=True)
                raise FileException(
                    f"Failed to save image: {save_error}",
                    file_path=image_path
                )
        else:
            db_task.status = "failed"
            db_task.error_message = error_message
            db_task.completed_at = datetime.now()  # Mark as completed (failed)
            db.commit()
            db.refresh(db_task)
            logger.info(
                f"Task {task_id} status updated to 'failed' with error: {error_message}"
            )
            return JSONResponse(
                content={
                    "message": "Task marked as failed",
                    "task_id": task_id,
                    "status": "failed",
                    "error_message": error_message,
                }
            )

    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        db.rollback()
        raise
    except (FileException, DatabaseException) as e:
        db.rollback()
        logger.error(f"[upload_image] Failed to process upload/status update for task {task_id}: {e}")
        raise
    except Exception as e:
        # 其他异常
        db.rollback()
        logger.error(f"[upload_image] Failed to process upload/status update for task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to process task update: {e}"
        )


@app.get(
    "/check_status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Check the status of an image generation task (DEPRECATED)",
    deprecated=True,
)
async def check_status(task_id: str, db: Session = Depends(get_db)):
    """
    Checks the status of a submitted image generation task.
    Returns the image path if the task is completed.

    .. deprecated::
        此端点已废弃。flux_server 同步模式直接返回结果，不需要轮询状态。
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if db_task:
        return TaskStatusResponse(
            task_id=task_id,
            status=db_task.status,
            image_url=db_task.image_url,
            error_message=db_task.error_message,
        )

    from core.exceptions import JobNotFoundException
    raise JobNotFoundException(job_id=int(task_id) if task_id.isdigit() else 0)


@app.get(
    "/get_image/{task_id}",
    summary="Retrieve the generated image for a completed task (DEPRECATED)",
    deprecated=True,
)
async def get_image(task_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the generated image for a completed task.
    Returns the image file if the task is completed, otherwise returns an error.

    .. deprecated::
        此端点已废弃。flux_server 同步模式在响应中直接返回图像数据。
    """
    from core.exceptions import FileNotFoundException, JobNotFoundException, JobProcessingException
    
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise JobNotFoundException(job_id=int(task_id) if task_id.isdigit() else 0)

    if db_task.status != "completed":
        raise JobProcessingException(
            f"Task {task_id} is not completed. Current status: {db_task.status}",
            job_id=int(task_id) if task_id.isdigit() else 0
        )

    if not db_task.image_url:
        raise FileNotFoundException("")

    # Security check: ensure the path is within the allowed directory
    image_path = os.path.abspath(db_task.image_url)
    if not image_path.startswith(os.path.abspath(GENERATED_IMAGES_DIR)):
        raise FileException(
            f"Invalid image path: {image_path}",
            file_path=image_path
        )
    
    if not os.path.exists(image_path):
        raise FileNotFoundException(image_path)

    return FileResponse(image_path)


def _status_for_exception(exc: BatchShortException) -> int:
    """根据异常类型返回对应的HTTP状态码。
    
    Args:
        exc: BatchShortException 异常实例
    
    Returns:
        HTTP状态码
    """
    if isinstance(exc, (FileNotFoundException, JobNotFoundException)):
        return 404
    if isinstance(exc, ConfigurationException):
        return 503
    if isinstance(exc, ServiceException):
        return 502
    if isinstance(exc, (FileException, DatabaseException, JobProcessingException)):
        return 500
    return 400


@app.exception_handler(BatchShortException)
async def batchshort_exception_handler(request: Request, exc: BatchShortException) -> JSONResponse:
    """统一处理 BatchShort 异常"""
    status_code = _status_for_exception(exc)
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
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
            "message": "服务器内部错误",
            "success": False
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_service.main:app", host="0.0.0.0", port=8000, reload=True)
