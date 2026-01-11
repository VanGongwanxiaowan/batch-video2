from api.utils import get_current_user
from db.session import get_db
from fastapi import APIRouter, Body, Depends, Path, Query
from schema.account import User
from schema.topic import (
    CreateTopicRequest,
    CreateTopicResponse,
    DeleteTopicResponse,
    GetTopicResponse,
    ListTopicResponse,
)
from schema.topic import Topic as SchemaTopic
from schema.topic import (
    UpdateTopicRequest,
    UpdateTopicResponse,
)
from core.db.dao.base_dao import BaseDAO
from core.services.base_crud_service import BaseCRUDService
from db.models import Topic as TopicModel
from sqlalchemy.orm import Session

topic_router = APIRouter()

@topic_router.post("", response_model=CreateTopicResponse, summary="新增话题")
def create_topic(
    request: CreateTopicRequest = Body(...), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> CreateTopicResponse:
    """
    新增一个话题
    
    Args:
        request: 创建话题请求对象，包含话题名称、描述等信息
        db: 数据库会话对象
        current_user: 当前登录用户对象
        
    Returns:
        CreateTopicResponse: 创建响应对象，包含新创建的话题ID
        
    Raises:
        ValidationException: 如果请求数据验证失败
        HTTPException: 如果话题名称已存在或其他业务错误
    """
    service = BaseCRUDService(db, BaseDAO(TopicModel, db), TopicModel)
    topic = service.create(request, current_user.user_id)
    return CreateTopicResponse(id=topic.id)

@topic_router.get("", response_model=ListTopicResponse, summary="话题列表")
def list_topics(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ListTopicResponse:
    """
    列出话题（分页）
    
    Args:
        page: 页码，从1开始，默认值为1
        page_size: 每页大小，默认值为10，最大值为100
        db: 数据库会话对象
        current_user: 当前登录用户对象
        
    Returns:
        ListTopicResponse: 话题列表响应对象，包含总数和话题列表
        
    Raises:
        HTTPException: 如果分页参数无效
        
    Note:
        - 只返回当前用户创建的话题
        - 支持分页查询
    """
    from core.utils.schema_converter import create_schema_list
    
    service = BaseCRUDService(db, BaseDAO(TopicModel, db), TopicModel)
    result = service.list(page, page_size, current_user.user_id)
    items = create_schema_list(
        result["items"],
        SchemaTopic,
        datetime_fields=['created_at', 'updated_at'],
    )
    return {"total": result["total"], "items": items}

@topic_router.get("/{topic_id}", response_model=GetTopicResponse, summary="获取指定话题的详细信息")
def get_topic(
    topic_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> GetTopicResponse:
    """
    获取指定话题的详细信息
    """
    from core.utils.schema_converter import convert_to_response_schema
    
    service = BaseCRUDService(db, BaseDAO(TopicModel, db), TopicModel)
    topic = service.get(topic_id, current_user.user_id)
    return convert_to_response_schema(
        topic,
        SchemaTopic,
        GetTopicResponse,
        datetime_fields=['created_at', 'updated_at'],
    )

@topic_router.put("/{topic_id}", response_model=UpdateTopicResponse, summary="更新话题信息")
def update_topic(
    topic_id: int = Path(..., ge=1),
    request: UpdateTopicRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UpdateTopicResponse:
    """
    更新指定话题的信息
    """
    service = BaseCRUDService(db, BaseDAO(TopicModel, db), TopicModel)
    topic = service.update(topic_id, request, current_user.user_id)
    return UpdateTopicResponse(id=topic.id)

@topic_router.delete("/{topic_id}", response_model=DeleteTopicResponse, summary="删除话题")
def delete_topic(
    topic_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> DeleteTopicResponse:
    """
    删除指定话题
    """
    service = BaseCRUDService(db, BaseDAO(TopicModel, db), TopicModel)
    result = service.delete(topic_id, current_user.user_id)
    return DeleteTopicResponse(id=result["id"])