"""CRUD操作辅助工具模块

提供通用的CRUD操作辅助函数，减少API路由中的重复代码。
"""
from typing import Any, Callable, Dict, Generic, Optional, Type, TypeVar

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from core.utils.api_helpers import convert_datetime_to_iso, create_list_response
from core.utils.schema_converter import convert_model_to_schema, create_schema_list

T = TypeVar("T")
CreateRequest = TypeVar("CreateRequest")
UpdateRequest = TypeVar("UpdateRequest")
CreateResponse = TypeVar("CreateResponse")
GetResponse = TypeVar("GetResponse")
ListResponse = TypeVar("ListResponse")
UpdateResponse = TypeVar("UpdateResponse")
DeleteResponse = TypeVar("DeleteResponse")


class CRUDHelper:
    """CRUD操作辅助类
    
    提供通用的CRUD操作辅助方法，用于简化API路由代码。
    """
    
    def __init__(
        self,
        service_class: Type[Any],
        schema_class: Type[Any],
        create_request_class: Type[CreateRequest],
        update_request_class: Type[UpdateRequest],
        create_response_class: Type[CreateResponse],
        get_response_class: Type[GetResponse],
        list_response_class: Type[ListResponse],
        update_response_class: Type[UpdateResponse],
        delete_response_class: Type[DeleteResponse],
        resource_name: str = "resource",
    ):
        """
        初始化CRUD辅助类
        
        Args:
            service_class: Service类
            schema_class: Schema类（用于列表项）
            create_request_class: 创建请求类
            update_request_class: 更新请求类
            create_response_class: 创建响应类
            get_response_class: 获取响应类
            list_response_class: 列表响应类
            update_response_class: 更新响应类
            delete_response_class: 删除响应类
            resource_name: 资源名称（用于错误消息）
        """
        self.service_class = service_class
        self.schema_class = schema_class
        self.create_request_class = create_request_class
        self.update_request_class = update_request_class
        self.create_response_class = create_response_class
        self.get_response_class = get_response_class
        self.list_response_class = list_response_class
        self.update_response_class = update_response_class
        self.delete_response_class = delete_response_class
        self.resource_name = resource_name
    
    def create_handler(
        self,
        request: CreateRequest,
        db: Session,
        current_user: Any,
    ) -> CreateResponse:
        """
        创建资源处理函数
        
        Args:
            request: 创建请求对象
            db: 数据库会话
            current_user: 当前用户对象
            
        Returns:
            创建响应对象
        """
        service = self.service_class(db)
        create_method = getattr(service, f"create_{self.resource_name}", None)
        if not create_method:
            create_method = getattr(service, "create", None)
        
        if not create_method:
            raise ValueError(
                f"Service {self.service_class.__name__} must have "
                f"create_{self.resource_name} or create method"
            )
        
        item = create_method(request, current_user.user_id)
        return self.create_response_class(id=item.id)
    
    def list_handler(
        self,
        page: int,
        page_size: int,
        db: Session,
        current_user: Any,
        item_converter: Optional[Callable[[Any], Any]] = None,
        **filters: Any,
    ) -> ListResponse:
        """
        列表查询处理函数
        
        Args:
            page: 页码
            page_size: 每页大小
            db: 数据库会话
            current_user: 当前用户对象
            item_converter: 可选的项转换函数
            **filters: 额外的过滤参数
            
        Returns:
            列表响应对象
        """
        service = self.service_class(db)
        list_method = getattr(service, f"list_{self.resource_name}s", None)
        if not list_method:
            list_method = getattr(service, "list", None)
        
        if not list_method:
            raise ValueError(
                f"Service {self.service_class.__name__} must have "
                f"list_{self.resource_name}s or list method"
            )
        
        result = list_method(page, page_size, current_user.user_id, **filters)
        
        # 转换项
        if item_converter:
            items = [item_converter(item) for item in result["items"]]
        else:
            # 使用默认转换
            items = create_schema_list(
                result["items"],
                self.schema_class,
                datetime_fields=['created_at', 'updated_at'],
            )
        
        return self.list_response_class(
            total=result["total"],
            items=items,
        )
    
    def get_handler(
        self,
        item_id: int,
        db: Session,
        current_user: Any,
        item_converter: Optional[Callable[[Any], Any]] = None,
    ) -> GetResponse:
        """
        获取详情处理函数
        
        Args:
            item_id: 资源ID
            db: 数据库会话
            current_user: 当前用户对象
            item_converter: 可选的项转换函数
            
        Returns:
            获取响应对象
        """
        service = self.service_class(db)
        get_method = getattr(service, f"get_{self.resource_name}", None)
        if not get_method:
            get_method = getattr(service, "get", None)
        
        if not get_method:
            raise ValueError(
                f"Service {self.service_class.__name__} must have "
                f"get_{self.resource_name} or get method"
            )
        
        item = get_method(item_id, current_user.user_id)
        
        # 转换项
        if item_converter:
            schema_item = item_converter(item)
        else:
            # 使用默认转换
            schema_item = convert_model_to_schema(
                item,
                self.schema_class,
                datetime_fields=['created_at', 'updated_at'],
            )
        
        # 构建响应对象
        response_data = {}
        if hasattr(schema_item, 'model_dump'):
            response_data = schema_item.model_dump()
        elif hasattr(schema_item, 'dict'):
            response_data = schema_item.dict()
        else:
            response_data = dict(schema_item)
        
        return self.get_response_class(**response_data)
    
    def update_handler(
        self,
        item_id: int,
        request: UpdateRequest,
        db: Session,
        current_user: Any,
    ) -> UpdateResponse:
        """
        更新资源处理函数
        
        Args:
            item_id: 资源ID
            request: 更新请求对象
            db: 数据库会话
            current_user: 当前用户对象
            
        Returns:
            更新响应对象
        """
        service = self.service_class(db)
        update_method = getattr(service, f"update_{self.resource_name}", None)
        if not update_method:
            update_method = getattr(service, "update", None)
        
        if not update_method:
            raise ValueError(
                f"Service {self.service_class.__name__} must have "
                f"update_{self.resource_name} or update method"
            )
        
        item = update_method(item_id, request, current_user.user_id)
        return self.update_response_class(id=item.id)
    
    def delete_handler(
        self,
        item_id: int,
        db: Session,
        current_user: Any,
    ) -> DeleteResponse:
        """
        删除资源处理函数
        
        Args:
            item_id: 资源ID
            db: 数据库会话
            current_user: 当前用户对象
            
        Returns:
            删除响应对象
        """
        service = self.service_class(db)
        delete_method = getattr(service, f"delete_{self.resource_name}", None)
        if not delete_method:
            delete_method = getattr(service, "delete", None)
        
        if not delete_method:
            raise ValueError(
                f"Service {self.service_class.__name__} must have "
                f"delete_{self.resource_name} or delete method"
            )
        
        result = delete_method(item_id, current_user.user_id)
        return self.delete_response_class(id=result.get("id", item_id))


def register_crud_routes(
    router: APIRouter,
    helper: CRUDHelper,
    prefix: str = "",
    get_current_user: Callable = None,
    get_db: Callable = None,
) -> None:
    """
    注册CRUD路由到FastAPI路由器
    
    Args:
        router: FastAPI路由器
        helper: CRUD辅助类实例
        prefix: 路由前缀
        get_current_user: 获取当前用户的依赖函数
        get_db: 获取数据库会话的依赖函数
        
    Example:
        >>> helper = CRUDHelper(...)
        >>> register_crud_routes(router, helper, get_current_user=get_current_user, get_db=get_db)
    """
    if get_current_user is None or get_db is None:
        raise ValueError("get_current_user and get_db must be provided")
    
    # 创建路由
    @router.post(f"{prefix}", response_model=helper.create_response_class, summary=f"创建{helper.resource_name}")
    def create(
        request: helper.create_request_class = Body(...),  # type: ignore
        db: Session = Depends(get_db),
        current_user: Any = Depends(get_current_user),
    ):
        return helper.create_handler(request, db, current_user)
    
    @router.get(f"{prefix}", response_model=helper.list_response_class, summary=f"{helper.resource_name}列表")
    def list_items(
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1),
        db: Session = Depends(get_db),
        current_user: Any = Depends(get_current_user),
    ):
        return helper.list_handler(page, page_size, db, current_user)
    
    @router.get(f"{prefix}/{{item_id}}", response_model=helper.get_response_class, summary=f"获取{helper.resource_name}详情")
    def get_item(
        item_id: int = Path(..., ge=1),
        db: Session = Depends(get_db),
        current_user: Any = Depends(get_current_user),
    ):
        return helper.get_handler(item_id, db, current_user)
    
    @router.put(f"{prefix}/{{item_id}}", response_model=helper.update_response_class, summary=f"更新{helper.resource_name}")
    def update_item(
        item_id: int = Path(..., ge=1),
        request: helper.update_request_class = Body(...),  # type: ignore
        db: Session = Depends(get_db),
        current_user: Any = Depends(get_current_user),
    ):
        return helper.update_handler(item_id, request, db, current_user)
    
    @router.delete(f"{prefix}/{{item_id}}", response_model=helper.delete_response_class, summary=f"删除{helper.resource_name}")
    def delete_item(
        item_id: int = Path(..., ge=1),
        db: Session = Depends(get_db),
        current_user: Any = Depends(get_current_user),
    ):
        return helper.delete_handler(item_id, db, current_user)

