from datetime import timedelta

from api.utils import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, get_current_user
from db.session import get_db
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status

from schema.account import (
    Account,
    CreateAccountRequest,
    CreateAccountResponse,
    DeleteAccountResponse,
    GetAccountResponse,
    ListAccountResponse,
    Token,
    UpdateAccountRequest,
    UpdateAccountResponse,
    User,
    UserCreate,
    UserLogin,
    UserSync,
)
from core.db.dao.base_dao import BaseDAO
from core.services.base_crud_service import BaseCRUDService
from db.models import Account as AccountModel
from service.user import UserService
from sqlalchemy.orm import Session

from core.exceptions import ValidationException

account_router = APIRouter()
auth_router = APIRouter()


@account_router.post("", response_model=CreateAccountResponse, summary="新增账号")
def create_account(
    request: CreateAccountRequest = Body(...), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> CreateAccountResponse:
    """
    新增一个账号
    
    Args:
        request: 创建账号请求对象，包含账号信息
        db: 数据库会话对象
        current_user: 当前登录用户对象
        
    Returns:
        CreateAccountResponse: 创建响应对象，包含新创建的账号ID
        
    Raises:
        ValidationException: 如果请求数据验证失败
        HTTPException: 如果账号已存在或其他业务错误
        
    Example:
        ```json
        POST /api/v1/accounts
        {
            "username": "test_account",
            "password": "secure_password",
            ...
        }
        ```
    """
    logger.info(
        "Creating new account",
        extra={
            "user_id": current_user.user_id,
            "username": request.username if hasattr(request, 'username') else None,
            "platform": request.platform if hasattr(request, 'platform') else None,
        }
    )
    try:
        service = BaseCRUDService(db, BaseDAO(AccountModel, db), AccountModel)
        account = service.create(request, current_user.user_id)
        logger.info(
            "Account created successfully",
            extra={
                "account_id": account.id,
                "user_id": current_user.user_id,
            }
        )
        return CreateAccountResponse(id=account.id)
    except Exception as e:
        logger.error(
            "Failed to create account",
            exc_info=True,
            extra={
                "user_id": current_user.user_id,
                "error": str(e),
            }
        )
        raise


@account_router.get("", response_model=ListAccountResponse, summary="账号列表")
def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Protect this endpoint
) -> ListAccountResponse:
    """
    列出账号（分页）
    
    Args:
        page: 页码，从1开始，默认值为1
        page_size: 每页大小，默认值为10，最大值为100
        db: 数据库会话对象
        current_user: 当前登录用户对象
        
    Returns:
        ListAccountResponse: 账号列表响应对象，包含总数和账号列表
        
    Raises:
        HTTPException: 如果分页参数无效
        
    Note:
        - 只返回当前用户创建的账号
        - 支持分页查询
    """
    from core.utils.schema_converter import create_schema_list
    
    service = BaseCRUDService(db, BaseDAO(AccountModel, db), AccountModel)
    result = service.list(page, page_size, current_user.user_id)
    # Convert db.models.Account objects to schema.account.Account objects
    items = create_schema_list(
        result["items"],
        Account,
        datetime_fields=['created_at', 'updated_at'],
    )
    return {"total": result["total"], "items": items}


@account_router.get(
    "/{account_id}", response_model=GetAccountResponse, summary="获取指定账号的详细信息"
)
def get_account(
    account_id: int = Path(..., ge=1), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> GetAccountResponse:
    """
    获取指定账号的详细信息
    
    Args:
        account_id: 账号ID，必须大于等于1
        db: 数据库会话对象
        current_user: 当前登录用户对象
        
    Returns:
        GetAccountResponse: 账号详细信息响应对象
        
    Raises:
        HTTPException: 404 如果账号不存在或不属于当前用户
        
    Note:
        - 只能获取当前用户创建的账号
    """
    
    from core.utils.schema_converter import convert_to_response_schema
    
    service = BaseCRUDService(db, BaseDAO(AccountModel, db), AccountModel)
    account = service.get(account_id, current_user.user_id)
    return convert_to_response_schema(
        account,
        Account,
        GetAccountResponse,
        datetime_fields=['created_at', 'updated_at'],
    )


@account_router.put(
    "/{account_id}", response_model=UpdateAccountResponse, summary="更新账号信息"
)
def update_account(
    account_id: int,
    request: UpdateAccountRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UpdateAccountResponse:
    """
    更新指定账号的信息
    
    Args:
        account_id: 账号ID，必须大于等于1
        request: 更新账号请求对象，包含要更新的账号信息
        db: 数据库会话对象
        current_user: 当前登录用户对象
        
    Returns:
        UpdateAccountResponse: 更新响应对象，包含更新后的账号ID
        
    Raises:
        HTTPException: 404 如果账号不存在或不属于当前用户
        ValidationException: 如果请求数据验证失败
    """
    service = BaseCRUDService(db, BaseDAO(AccountModel, db), AccountModel)
    account = service.update(account_id, request, current_user.user_id)
    return UpdateAccountResponse(id=account.id)


@account_router.delete(
    "/{account_id}", response_model=DeleteAccountResponse, summary="删除账号"
)
def delete_account(
    account_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> DeleteAccountResponse:
    """
    删除指定账号
    
    Args:
        account_id: 账号ID，必须大于等于1
        db: 数据库会话对象
        current_user: 当前登录用户对象
        
    Returns:
        DeleteAccountResponse: 删除响应对象，包含已删除的账号ID
        
    Raises:
        HTTPException: 404 如果账号不存在或不属于当前用户
    """
    service = BaseCRUDService(db, BaseDAO(AccountModel, db), AccountModel)
    result = service.delete(account_id, current_user.user_id)
    return DeleteAccountResponse(id=result["id"])




@auth_router.post("/register", response_model=User, summary="用户注册")
def register_user(user: UserCreate, db: Session = Depends(get_db)) -> User:
    """
    用户注册接口
    
    Args:
        user: 用户创建请求对象，包含用户名、密码等信息
        db: 数据库会话对象
        
    Returns:
        User: 创建的用户对象
        
    Raises:
        HTTPException: 400 如果用户名已存在或数据验证失败
        
    Note:
        - 密码会自动进行哈希处理
        - 用户名必须唯一
    """
    user_service = UserService(db)
    try:
        return user_service.create_user(user)
    except ValidationException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message
        ) from exc

@auth_router.post("/sync", response_model=User, summary="用户同步")
def sync_user(user: UserSync, db: Session = Depends(get_db)) -> User:
    """
    用户同步接口
    
    Args:
        user: 用户同步请求对象，包含用户同步信息
        db: 数据库会话对象
        
    Returns:
        User: 同步后的用户对象
        
    Raises:
        HTTPException: 如果同步失败
        
    Note:
        - 用于从外部系统同步用户信息
    """
    user_service = UserService(db)
    return user_service.sync_user(user)



@auth_router.post("/login", response_model=Token, summary="用户登录")
def login_for_access_token(user_login: UserLogin, db: Session = Depends(get_db)) -> Token:
    """
    用户登录接口
    
    Args:
        user_login: 用户登录请求对象，包含用户名和密码
        db: 数据库会话对象
        
    Returns:
        Token: 访问令牌对象，包含access_token和token_type
        
    Raises:
        HTTPException: 401 如果用户名或密码错误
        
    Note:
        - 令牌有效期由ACCESS_TOKEN_EXPIRE_MINUTES配置决定
        - 使用JWT格式生成访问令牌
    """
    logger.info(
        "User login attempt",
        extra={
            "username": user_login.username,
        }
    )
    user_service = UserService(db)
    try:
        user = user_service.authenticate_user(user_login)
        logger.info(
            "User logged in successfully",
            extra={
                "user_id": user.user_id,
                "username": user.username,
            }
        )
    except ValidationException as exc:
        logger.warning(
            "User login failed",
            extra={
                "username": user_login.username,
                "error": exc.message,
            }
        )
        # 转成HTTP异常以兼容前端；详细错误信息仍由核心异常承载并被全局handler记录
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.user_id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.get("/users/me/", response_model=User, summary="获取当前登录用户信息")
def read_users_me(current_user: User = Depends(get_current_user)) -> User:
    """获取当前登录用户信息
    
    Args:
        current_user: 当前登录用户对象
        
    Returns:
        User: 当前登录用户信息
    """
    return current_user
