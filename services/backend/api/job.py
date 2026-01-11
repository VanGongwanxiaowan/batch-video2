import base64
import json
import os
import re
import shutil
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional

from api.utils import get_current_user
from db.session import get_db
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from ossutils import OssManager
from schema.account import User
from schema.job import CreateJobRequest, CreateJobResponse, Job, ListJobResponse
from schema.language import Language as SchemaLanguage
from schema.topic import Topic as SchemaTopic
from schema.voice import Voice as SchemaVoice
from service.job import JobService
from sqlalchemy.orm import Session

from config import settings
from core.config.constants import APIConfig, TextConfig
from core.exceptions import ValidationException
from core.logging_config import setup_logging

logger = setup_logging("backend.api.job")
job_router = APIRouter()

# ============================================================================
# Celery 任务导入
# ============================================================================

# 尝试导入 Celery 任务，如果不可用则使用降级方案
try:
    from services.worker.tasks import process_video_job
    CELERY_AVAILABLE = True
    logger.info("Celery 任务模块导入成功")
except ImportError as exc:
    CELERY_AVAILABLE = False
    logger.warning(
        f"Celery 任务模块导入失败: {exc}，"
        "任务将不会自动分发到 Worker"
    )


def safe_json_loads(json_str: str, default: Optional[dict] = None) -> dict:
    """安全地解析JSON字符串。
    
    如果JSON格式无效，会记录错误日志并抛出ValidationException。
    
    Args:
        json_str: JSON字符串
        default: 解析失败时的默认值，默认为None（返回空字典）
        
    Returns:
        dict: 解析后的字典对象
        
    Raises:
        ValidationException: 如果JSON格式无效
        
    Example:
        >>> safe_json_loads('{"key": "value"}')
        {'key': 'value'}
        >>> safe_json_loads('invalid json', {})
        {}
        >>> safe_json_loads('invalid json')  # 会抛出ValidationException
    """
    if not json_str:
        return default or {}
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # 记录错误日志（只记录前100个字符，避免日志过长）
        json_preview = json_str[:100] + "..." if len(json_str) > 100 else json_str
        logger.error(
            f"Invalid JSON format: {json_preview}, error: {e}",
            exc_info=True
        )
        raise ValidationException(
            f"Invalid JSON format in job_result_key: {str(e)}"
        ) from e


def _convert_language_to_schema(job: Any) -> Optional[SchemaLanguage]:
    """将数据库语言对象转换为Schema对象
    
    Args:
        job: 任务对象，包含language属性
        
    Returns:
        SchemaLanguage对象，如果language不存在则返回None
        
    Note:
        使用core.utils.schema_converter中的convert_related_object统一转换逻辑
    """
    from core.utils.schema_converter import convert_related_object
    
    return convert_related_object(
        job,
        'language',
        SchemaLanguage,
        datetime_fields=['created_at', 'updated_at'],
    )


def _convert_voice_to_schema(job: Any) -> Optional[SchemaVoice]:
    """将数据库语音对象转换为Schema对象
    
    Args:
        job: 任务对象，包含voice属性
        
    Returns:
        SchemaVoice对象，如果voice不存在则返回None
        
    Note:
        使用core.utils.schema_converter中的convert_related_object统一转换逻辑
    """
    from core.utils.schema_converter import convert_related_object
    
    return convert_related_object(
        job,
        'voice',
        SchemaVoice,
        datetime_fields=['created_at', 'updated_at'],
    )


def _convert_topic_to_schema(job: Any) -> Optional[SchemaTopic]:
    """将数据库主题对象转换为Schema对象
    
    Args:
        job: 任务对象，包含topic属性
        
    Returns:
        SchemaTopic对象，如果topic不存在则返回None
        
    Note:
        使用core.utils.schema_converter中的convert_related_object统一转换逻辑
    """
    from core.utils.schema_converter import convert_related_object
    
    return convert_related_object(
        job,
        'topic',
        SchemaTopic,
        datetime_fields=['created_at', 'updated_at'],
    )


def _get_cover_base64_from_oss(cover_key: str) -> Optional[str]:
    """从OSS获取封面图片并转换为base64
    
    Args:
        cover_key: OSS中的封面图片key
        
    Returns:
        base64编码的图片字符串，如果获取失败则返回None
        
    Note:
        此函数会创建临时文件，并在使用后自动清理
    """
    if not cover_key:
        return None
    
    oss_util = OssManager()
    temp_file_path = None
    try:
        with NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
            oss_util.download(cover_key, temp_file_path)
            # Read the file and convert to base64
            with open(temp_file_path, "rb") as f:
                cover_base64 = base64.b64encode(f.read()).decode("utf-8")
            return cover_base64
    except (OSError, IOError, PermissionError) as e:
        # 文件系统错误
        logger.error(f"[_get_cover_base64_from_oss] 文件操作失败: cover_key={cover_key}, error={e}", exc_info=True)
        return None
    except Exception as e:
        # 其他未预期的异常（OSS操作错误等）
        logger.error(f"[_get_cover_base64_from_oss] 获取封面失败: cover_key={cover_key}, error={e}", exc_info=True)
        return None
    finally:
        # 确保临时文件被清理
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError:
                # 忽略清理失败，但记录日志
                logger.warning(f"Failed to delete temporary file: {temp_file_path}")


def sanitize_text(text: str, max_length: int = TextConfig.MAX_DESCRIPTION_LENGTH) -> str:
    """清理文本内容，移除控制字符和标记内容。
    
    Args:
        text: 原始文本
        max_length: 最大长度限制，默认使用配置常量
        
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    
    # 移除标记内容（#@#...#@#）
    text = re.sub(r'#@#.*?#@#', '', text, flags=re.DOTALL)
    
    # 移除控制字符（保留换行符\n、制表符\t、回车符\r）
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # 限制长度
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()


def validate_job_request(request: CreateJobRequest) -> CreateJobRequest:
    """验证和清理任务请求。
    
    Args:
        request: 任务创建请求对象
        
    Returns:
        CreateJobRequest: 清理后的请求对象
        
    Note:
        使用配置常量限制各字段的最大长度
    """
    # 清理各个文本字段，使用配置常量
    if request.title:
        request.title = sanitize_text(request.title, max_length=TextConfig.MAX_TITLE_LENGTH)
    
    if request.content:
        request.content = sanitize_text(request.content, max_length=TextConfig.MAX_CONTENT_LENGTH)
    
    if request.description:
        request.description = sanitize_text(
            request.description,
            max_length=TextConfig.MAX_DESCRIPTION_LENGTH
        )
    
    if request.publish_title:
        request.publish_title = sanitize_text(
            request.publish_title,
            max_length=TextConfig.MAX_PUBLISH_TITLE_LENGTH
        )
    
    return request


@job_router.post("", response_model=CreateJobResponse, summary="创建任务")
def create_job(
    request: CreateJobRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CreateJobResponse:
    """
    创建一个新的任务

    注意：
        - 所有输入文本都会经过清理和验证
        - 移除控制字符和标记内容
        - 限制文本长度防止过长输入
        - 任务创建后立即通过 Celery 异步分发到 Worker 处理
    """
    logger.info(
        "Creating new job",
        extra={
            "user_id": current_user.user_id,
            "title": request.title[:50] if request.title else None,
            "topic_id": request.topic_id,
            "language_id": request.language_id,
        }
    )
    service = JobService(db)
    # 验证和清理输入
    request = validate_job_request(request)
    try:
        # 创建任务记录
        job = service.create_job(request, current_user.user_id)
        logger.info(
            "Job created successfully",
            extra={
                "job_id": job.id,
                "user_id": current_user.user_id,
            }
        )

        # 通过 Celery 异步分发任务到 Worker
        if CELERY_AVAILABLE:
            try:
                # 使用 delay() 方法异步调用任务
                # task_id 格式: job-{job_id}-{timestamp}
                task_result = process_video_job.delay(job_id=job.id)

                logger.info(
                    "Job dispatched to Celery worker successfully",
                    extra={
                        "job_id": job.id,
                        "user_id": current_user.user_id,
                        "task_id": task_result.id,
                    }
                )

            except Exception as celery_exc:
                # Celery 分发失败，记录错误但不影响任务创建
                logger.error(
                    "Failed to dispatch job to Celery worker",
                    exc_info=True,
                    extra={
                        "job_id": job.id,
                        "user_id": current_user.user_id,
                        "error": str(celery_exc),
                    }
                )
                # 任务仍会通过 Worker 轮询被处理
        else:
            logger.warning(
                "Celery not available, job will be processed by worker polling",
                extra={"job_id": job.id}
            )

        return CreateJobResponse(id=job.id)
    except Exception as e:
        logger.error(
            "Failed to create job",
            exc_info=True,
            extra={
                "user_id": current_user.user_id,
                "error": str(e),
            }
        )
        raise

@job_router.get("", response_model=ListJobResponse, summary="任务列表")
def list_jobs(
    page: int = Query(1, ge=1, le=APIConfig.MAX_PAGE_NUMBER, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=APIConfig.MAX_PAGE_SIZE, description="每页数量，最大100"),
    status: str = Query("", description="任务状态筛选"),
    account_id: int | None = Query(None, description="Filter by account ID"),
    language_id: int | None = Query(None, description="Filter by language ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ListJobResponse:
    """
    列出任务
    """
    logger.debug(
        "Listing jobs",
        extra={
            "user_id": current_user.user_id,
            "page": page,
            "page_size": page_size,
            "status": status,
            "account_id": account_id,
            "language_id": language_id,
        }
    )
    from core.utils.schema_converter import convert_datetime_fields, convert_model_to_schema
    
    service = JobService(db)
    result = service.list_jobs(page, page_size, status, current_user.user_id, account_id, language_id)
    
    logger.debug(
        "Jobs listed successfully",
        extra={
            "user_id": current_user.user_id,
            "total": result["total"],
            "items_count": len(result["items"]),
        }
    )
    
    # 使用工具函数转换模型到Schema
    items = []
    for item in result["items"]:
        # 转换datetime字段
        datetime_values = convert_datetime_fields(item, ['created_at', 'updated_at'])
        
        # 构建Job对象
        items.append(
            Job(
                id=item.id,
                runorder=item.runorder,
                title=item.title,
                content="",
                language_id=item.language_id,
                voice_id=item.voice_id,
                description=item.description,
                publish_title=item.publish_title,
                topic_id=item.topic_id,
                job_splits=[],
                speech_speed=item.speech_speed,
                status=item.status,
                status_detail=item.status_detail,
                job_result_key=item.job_result_key or '',
                created_at=datetime_values['created_at'],
                updated_at=datetime_values['updated_at'],
                is_horizontal=item.is_horizontal,
                account_id=item.account_id,
                extra=item.extra,
            )
        )
    return {
        "total": result["total"],
        "items": items
    }

@job_router.get("/{job_id}/desc", summary="获取任务描述，包括签名URL")
def get_job_desc(
    job_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    获取指定任务的描述，包括签名URL
    
    Returns:
        Dict[str, str]: 包含description和content的字典
    """
    service = JobService(db)
    job = service.get_job_with_topic(job_id, current_user.user_id)
    ossutils = OssManager()
    # 使用安全的JSON解析函数，避免JSON格式错误导致500错误
    job_result = safe_json_loads(job.job_result_key, {})
    desc = f"""#@#
完整视频地址：{ossutils.get_sign_url(job_result.get("logoed_video_oss_key", "")) if job_result.get("logoed_video_oss_key") else ""}

不带Logo和字幕的视频地址：{ossutils.get_sign_url(job_result.get("combined_video_oss_key", "")) if job_result.get("audio_oss_key") else ""}

视频字幕文件：{ossutils.get_sign_url(job_result.get("srt_oss_key", "")) if job_result.get("srt_oss_key") else ""}

视频音频文件：{ossutils.get_sign_url(job_result.get("audio_oss_key", "")) if job_result.get("audio_oss_key") else ""}
#@#"""
    description = desc + job.description if job.description else desc
    return {"description": description, "content": job.content}

@job_router.get("/{job_id}", response_model=Job, summary="获取指定任务的详细信息")
def get_job(
    job_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> Job:
    """
    获取指定任务的详细信息
    
    此函数已重构，提取了数据转换逻辑到辅助函数，提高了代码可维护性。
    
    Args:
        job_id: 任务ID
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        Job: 任务详细信息对象
    """
    service = JobService(db)
    job = service.get_job_with_topic(job_id, current_user.user_id)
    
    # 转换关联对象
    language = _convert_language_to_schema(job)
    voice = _convert_voice_to_schema(job)
    topic = _convert_topic_to_schema(job)
    
    # 获取封面图片base64
    job_result_key = safe_json_loads(job.job_result_key or "{}", {})
    cover_key = job_result_key.get("cover_oss_key", "")
    cover_base64 = _get_cover_base64_from_oss(cover_key) if cover_key else None
    
    return Job(
        id=job.id,
        title=job.title,
        language=language,
        language_id=job.language_id,
        voice=voice,
        voice_id=job.voice_id,
        description=job.description,
        publish_title=job.publish_title,
        topic=topic,
        topic_id=job.topic_id,
        status=job.status,
        status_detail=job.status_detail,
        created_at=job.created_at.isoformat() if job.created_at else "",
        updated_at=job.updated_at.isoformat() if job.updated_at else "",
        account_id=job.account_id,
        cover_base64=cover_base64,
        is_horizontal=job.is_horizontal,
        extra=job.extra,
        background=job.background,
    )

@job_router.delete("/{job_id}", summary="删除指定任务", response_model=CreateJobResponse)
def delete_job(
    job_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> CreateJobResponse:
    """
    删除指定任务
    """
    
    service = JobService(db)
    job = service.get_job(job_id, current_user.user_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {job_id} 不存在"
        )
    
    result = service.delete_job(job_id, current_user.user_id)
    user_id = current_user.user_id if current_user else None
    if user_id:
        assert_path = os.path.join(settings.ASSERT_PATH, str(user_id).replace("-", ""), job.title)
        logger.debug(f"[delete_job] 尝试删除资源目录: {assert_path}")
        if os.path.exists(assert_path):
            try:
                shutil.rmtree(assert_path)
                logger.info(f"[delete_job] 成功删除资源目录: {assert_path}")
            except (OSError, PermissionError) as e:
                # 文件系统错误，记录但不抛出异常
                logger.error(
                    f"[delete_job] 删除资源目录失败: {assert_path}, error={e}",
                    exc_info=True
                )
                # 不抛出异常，允许任务删除成功
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except Exception as e:
                # 其他未预期的异常
                logger.exception(
                    f"[delete_job] 删除资源目录时发生未知异常: {assert_path}, error={e}",
                    exc_info=True
                )
                # 不抛出异常，允许任务删除成功

    return CreateJobResponse(id=job_id)

@job_router.put("/{job_id}", response_model=Job, summary="更新指定任务信息")
def update_job(
    job_id: int = Path(..., ge=1), 
    job: Job = Body(...), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> Job:
    """
    更新指定任务
    """
    logger.info(
        "Updating job",
        extra={
            "job_id": job_id,
            "user_id": current_user.user_id,
            "status": job.status,
        }
    )
    service = JobService(db)
    try:
        updated_job = service.update_job(job_id, job, current_user.user_id)
        logger.info(
            "Job updated successfully",
            extra={
                "job_id": job_id,
                "user_id": current_user.user_id,
            }
        )
        # 使用统一的转换函数
        from core.utils.schema_converter import convert_related_object
        
        language = convert_related_object(
            updated_job,
            'language',
            SchemaLanguage,
            datetime_fields=['created_at', 'updated_at'],
        )
        voice = convert_related_object(
            updated_job,
            'voice',
            SchemaVoice,
            datetime_fields=['created_at', 'updated_at'],
        )
        topic = convert_related_object(
            updated_job,
            'topic',
            SchemaTopic,
            datetime_fields=['created_at', 'updated_at'],
        )
        
        return Job(
        id=updated_job.id,
        title=updated_job.title,
        language_id=updated_job.language_id,
        language=language,
        voice_id=updated_job.voice_id,
        voice=voice,
        description=updated_job.description,
        topic_id=updated_job.topic_id,
        topic=topic,
        # job_splits=job_splits,
        status=updated_job.status,
        status_detail=updated_job.status_detail,
        created_at=updated_job.created_at.isoformat() if updated_job.created_at else "",
        updated_at=updated_job.updated_at.isoformat() if updated_job.updated_at else "",
        account_id=updated_job.account_id,
        background=updated_job.background,
        )
    except Exception as e:
        logger.error(
            "Failed to update job",
            exc_info=True,
            extra={
                "job_id": job_id,
                "user_id": current_user.user_id,
                "error": str(e),
            }
        )
        raise

@job_router.post("/export/{job_id}", summary="导出任务视频")
def export_job(
    job_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    导出指定任务的视频
    
    Returns:
        Dict[str, Any]: 导出结果
    """
    service = JobService(db)
    result = service.export_job(job_id, current_user.user_id)
    return result

@job_router.post("/{job_id}/increase_priority", response_model=dict, summary="提升任务优先级")
def increase_job_priority(
    job_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    提升指定任务的优先级
    
    Returns:
        Dict[str, Any]: 操作结果
    """
    service = JobService(db)
    service.increase_job_priority(job_id, current_user.user_id)
    return {
        "code"  : 200,
        "message": "success",
        "data": {}
    }