from api.utils import get_current_user  # Import get_current_user
from db.session import get_db
from fastapi import APIRouter, Body, Depends, Path, Query
from schema.account import User  # Import User schema
from schema.language import (
    CreateLanguageRequest,
    CreateLanguageResponse,
    DeleteLanguageResponse,
    GetLanguageResponse,
)
from schema.language import Language as SchemaLanguage
from schema.language import (
    ListLanguageResponse,
    UpdateLanguageRequest,
    UpdateLanguageResponse,
)
from core.db.dao.base_dao import BaseDAO
from core.services.base_crud_service import BaseCRUDService
from db.models import Language as LanguageModel
from sqlalchemy.orm import Session

language_router = APIRouter()

@language_router.post("", response_model=CreateLanguageResponse, summary="新增语种")
def create_language(
    request: CreateLanguageRequest = Body(...), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> CreateLanguageResponse:
    """
    新增一个语种
    
    Args:
        request: 创建语种请求对象，包含语种名称、代码等信息
        db: 数据库会话对象
        current_user: 当前登录用户对象
        
    Returns:
        CreateLanguageResponse: 创建响应对象，包含新创建的语种ID
        
    Raises:
        ValidationException: 如果请求数据验证失败
        HTTPException: 如果语种代码已存在或其他业务错误
    """
    service = BaseCRUDService(db, BaseDAO(LanguageModel, db), LanguageModel)
    language = service.create(request, current_user.user_id)
    return CreateLanguageResponse(id=language.id)

@language_router.get("", response_model=ListLanguageResponse, summary="语种列表")
def list_languages(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ListLanguageResponse:
    """
    列出语种（分页）
    
    Args:
        page: 页码，从1开始，默认值为1
        page_size: 每页大小，默认值为10，最大值为100
        db: 数据库会话对象
        current_user: 当前登录用户对象
        
    Returns:
        ListLanguageResponse: 语种列表响应对象，包含总数和语种列表
        
    Raises:
        HTTPException: 如果分页参数无效
        
    Note:
        - 只返回当前用户创建的语种
        - 支持分页查询
    """
    from core.utils.schema_converter import create_schema_list
    
    service = BaseCRUDService(db, BaseDAO(LanguageModel, db), LanguageModel)
    result = service.list(page, page_size, current_user.user_id)
    items = create_schema_list(
        result["items"],
        SchemaLanguage,
        datetime_fields=['created_at', 'updated_at'],
    )
    return {"total": result["total"], "items": items}


@language_router.get(
    "/{language_id}", response_model=GetLanguageResponse, summary="获取指定语种的详细信息"
)
def get_language(
    language_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> GetLanguageResponse:
    """
    获取指定语种的详细信息
    """
    from core.utils.schema_converter import convert_to_response_schema
    
    service = BaseCRUDService(db, BaseDAO(LanguageModel, db), LanguageModel)
    language = service.get(language_id, current_user.user_id)
    return convert_to_response_schema(
        language,
        SchemaLanguage,
        GetLanguageResponse,
        datetime_fields=['created_at', 'updated_at'],
    )

@language_router.put("/{language_id}", response_model=UpdateLanguageResponse, summary="更新语种信息")
def update_language(
    language_id: int = Path(..., ge=1),
    request: UpdateLanguageRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UpdateLanguageResponse:
    """
    更新指定语种的信息
    """
    service = BaseCRUDService(db, BaseDAO(LanguageModel, db), LanguageModel)
    language = service.update(language_id, request, current_user.user_id)
    return UpdateLanguageResponse(id=language.id)

@language_router.delete("/{language_id}", response_model=DeleteLanguageResponse, summary="删除语种")
def delete_language(
    language_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> DeleteLanguageResponse:
    """
    删除指定语种
    """
    service = BaseCRUDService(db, BaseDAO(LanguageModel, db), LanguageModel)
    result = service.delete(language_id, current_user.user_id)
    return DeleteLanguageResponse(id=result["id"])