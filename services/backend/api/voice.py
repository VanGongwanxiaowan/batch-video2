from api.utils import get_current_user
from db.session import get_db
from fastapi import APIRouter, Body, Depends, Path, Query
from schema.account import User
from schema.voice import (
    CreateVoiceRequest,
    CreateVoiceResponse,
    DeleteVoiceResponse,
    ListVoiceResponse,
    Voice,
)
from core.db.dao.base_dao import BaseDAO
from core.services.base_crud_service import BaseCRUDService
from db.models import Voice as VoiceModel
from sqlalchemy.orm import Session

from core.logging_config import setup_logging

logger = setup_logging("backend.api.voice")

voice_router = APIRouter()


@voice_router.post("", response_model=CreateVoiceResponse, summary="创建音色")
def create_voice(
    request: CreateVoiceRequest = Body(...), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> CreateVoiceResponse:
    """
    创建一个新的音色
    
    Args:
        request: 创建音色请求对象，包含音色名称、路径等信息
        db: 数据库会话对象
        current_user: 当前登录用户对象
        
    Returns:
        CreateVoiceResponse: 创建响应对象，包含新创建的音色ID
        
    Raises:
        ValidationException: 如果请求数据验证失败
        HTTPException: 如果音色名称已存在或其他业务错误
    """
    service = BaseCRUDService(db, BaseDAO(VoiceModel, db), VoiceModel)
    voice = service.create(request, current_user.user_id)
    return CreateVoiceResponse(id=voice.id)


@voice_router.get("/{voice_id}", response_model=Voice, summary="获取指定音色的详细信息")
def get_voice(
    voice_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> Voice:
    """
    获取指定音色的详细信息
    
    Args:
        voice_id: 音色ID，必须大于等于1
        db: 数据库会话对象
        current_user: 当前登录用户对象
        
    Returns:
        Voice: 音色详细信息对象
        
    Raises:
        HTTPException: 404 如果音色不存在或不属于当前用户
    """
    from core.utils.schema_converter import convert_model_to_schema
    
    service = BaseCRUDService(db, BaseDAO(VoiceModel, db), VoiceModel)
    voice = service.get(voice_id, current_user.user_id)
    schema_voice = convert_model_to_schema(
        voice,
        Voice,
        datetime_fields=['created_at', 'updated_at'],
    )
    return schema_voice


@voice_router.get("", response_model=ListVoiceResponse, summary="音色列表")
def list_voices(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ListVoiceResponse:
    """
    列出音色
    """
    from core.utils.schema_converter import create_schema_list
    
    service = BaseCRUDService(db, BaseDAO(VoiceModel, db), VoiceModel)
    result = service.list(page, page_size, current_user.user_id)
    logger.debug(f"List voices result: {result}")
    items = create_schema_list(
        result["items"],
        Voice,
        datetime_fields=['created_at', 'updated_at'],
    )
    return {"total": result["total"], "items": items}


@voice_router.delete(
    "/{voice_id}", response_model=DeleteVoiceResponse, summary="删除指定音色"
)
def delete_voice(
    voice_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> DeleteVoiceResponse:
    """
    删除指定音色
    """
    service = BaseCRUDService(db, BaseDAO(VoiceModel, db), VoiceModel)
    result = service.delete(voice_id, current_user.user_id)
    return DeleteVoiceResponse(id=result["id"])


# 更新
@voice_router.put("/{voice_id}", response_model=CreateVoiceResponse, summary="更新音色")
def update_voice(
    voice_id: int = Path(..., ge=1),
    request: CreateVoiceRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CreateVoiceResponse:
    """
    更新指定音色
    """
    service = BaseCRUDService(db, BaseDAO(VoiceModel, db), VoiceModel)
    voice = service.update(voice_id, request, current_user.user_id)
    return CreateVoiceResponse(id=voice.id)