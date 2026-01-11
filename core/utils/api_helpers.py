"""API路由辅助工具模块"""
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

T = TypeVar("T")


def create_list_response(
    items: List[Any],
    total: int,
    item_converter: Optional[Callable[[Any], Any]] = None,
) -> Dict[str, Any]:
    """
    创建标准列表响应
    
    Args:
        items: 数据项列表
        total: 总数
        item_converter: 可选的项转换函数
        
    Returns:
        标准列表响应字典
        
    Example:
        items = [Account(...), Account(...)]
        response = create_list_response(
            items, 
            total=100,
            item_converter=lambda acc: Account(
                id=acc.id,
                username=acc.username,
                ...
            )
        )
    """
    if item_converter:
        items = [item_converter(item) for item in items]
    return {"total": total, "items": items}


def get_or_404(
    session: Session,
    model: Type[T],
    id: Any,
    error_message: Optional[str] = None,
) -> T:
    """
    根据ID获取模型实例，如果不存在则抛出404异常
    
    Args:
        session: 数据库会话
        model: 模型类
        id: 主键ID
        error_message: 自定义错误消息
        
    Returns:
        模型实例
        
    Raises:
        HTTPException: 404 如果记录不存在
        
    Example:
        account = get_or_404(db, Account, account_id, "账号不存在")
    """
    instance = session.query(model).filter(model.id == id).first()
    if not instance:
        msg = error_message or f"{model.__name__} with id {id} not found"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg
        )
    return instance


def validate_pagination_params(
    page: int,
    page_size: int,
    max_page_size: int = 100,
) -> tuple[int, int]:
    """
    验证并规范化分页参数
    
    Args:
        page: 页码（从1开始）
        page_size: 每页大小
        max_page_size: 最大每页大小
        
    Returns:
        (skip, limit) 元组
        
    Raises:
        HTTPException: 如果参数无效
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be >= 1"
        )
    if page_size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be >= 1"
        )
    if page_size > max_page_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page size must be <= {max_page_size}"
        )
    
    skip = (page - 1) * page_size
    return skip, page_size


def convert_datetime_to_iso(obj: Any, field_name: str) -> str:
    """
    将datetime字段转换为ISO格式字符串
    
    Args:
        obj: 对象实例
        field_name: 字段名
        
    Returns:
        ISO格式字符串或空字符串
    """
    value = getattr(obj, field_name, None)
    if value:
        return value.isoformat()
    return ""

