"""Schema转换工具模块

提供通用的模型到Schema转换功能，消除重复的转换逻辑。
"""
from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar("T")
SchemaType = TypeVar("SchemaType")


def convert_datetime_fields(
    obj: Any,
    fields: Optional[list[str]] = None,
) -> Dict[str, str]:
    """
    将对象的datetime字段转换为ISO格式字符串
    
    Args:
        obj: 对象实例
        fields: 要转换的字段列表，如果为None则转换所有datetime字段
        
    Returns:
        包含转换后字段的字典
        
    Example:
        >>> from datetime import datetime
        >>> obj = type('Obj', (), {'created_at': datetime.now(), 'name': 'test'})()
        >>> convert_datetime_fields(obj, ['created_at'])
        {'created_at': '2025-01-01T12:00:00'}
    """
    from datetime import datetime
    
    result = {}
    if fields is None:
        # 自动检测datetime字段
        fields = [
            attr for attr in dir(obj)
            if not attr.startswith('_') and hasattr(obj, attr)
            and isinstance(getattr(obj, attr, None), datetime)
        ]
    
    for field in fields:
        value = getattr(obj, field, None)
        if value:
            if isinstance(value, datetime):
                result[field] = value.isoformat()
            else:
                result[field] = ""
        else:
            result[field] = ""
    
    return result


def convert_model_to_schema(
    model_obj: Any,
    schema_class: Type[SchemaType],
    field_mapping: Optional[Dict[str, str]] = None,
    datetime_fields: Optional[list[str]] = None,
    exclude_fields: Optional[list[str]] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> SchemaType:
    """
    将数据库模型对象转换为Schema对象
    
    Args:
        model_obj: 数据库模型实例
        schema_class: Schema类
        field_mapping: 字段映射字典，格式: {schema_field: model_field}
        datetime_fields: datetime字段列表，会自动转换为ISO格式
        exclude_fields: 要排除的字段列表
        extra_fields: 额外的字段字典
        
    Returns:
        Schema对象实例
        
    Example:
        >>> from schema.account import Account as SchemaAccount
        >>> account = Account(id=1, username='test', created_at=datetime.now())
        >>> schema = convert_model_to_schema(
        ...     account,
        ...     SchemaAccount,
        ...     datetime_fields=['created_at', 'updated_at']
        ... )
    """
    if model_obj is None:
        return None  # type: ignore
    
    # 默认datetime字段
    if datetime_fields is None:
        datetime_fields = ['created_at', 'updated_at']
    
    # 获取datetime字段的转换值
    datetime_values = convert_datetime_fields(model_obj, datetime_fields)
    
    # 构建字段字典
    data: Dict[str, Any] = {}
    
    # 获取Schema类的字段
    if hasattr(schema_class, 'model_fields'):
        # Pydantic v2
        schema_fields = schema_class.model_fields.keys()
    elif hasattr(schema_class, '__fields__'):
        # Pydantic v1
        schema_fields = schema_class.__fields__.keys()
    else:
        # 回退：使用dir获取所有属性
        schema_fields = [attr for attr in dir(schema_class) if not attr.startswith('_')]
    
    # 转换字段
    for schema_field in schema_fields:
        if exclude_fields and schema_field in exclude_fields:
            continue
        
        # 确定模型字段名
        model_field = field_mapping.get(schema_field, schema_field) if field_mapping else schema_field
        
        # 获取值
        if schema_field in datetime_values:
            value = datetime_values[schema_field]
        elif hasattr(model_obj, model_field):
            value = getattr(model_obj, model_field)
        else:
            continue
        
        data[schema_field] = value
    
    # 添加额外字段
    if extra_fields:
        data.update(extra_fields)
    
    # 创建Schema对象
    try:
        return schema_class(**data)
    except Exception as e:
        # 如果转换失败，尝试使用model_dump（Pydantic v2）
        if hasattr(model_obj, 'model_dump'):
            return schema_class(**model_obj.model_dump())
        raise ValueError(f"Failed to convert {type(model_obj)} to {schema_class}: {e}") from e


def convert_related_object(
    model_obj: Any,
    relation_field: str,
    schema_class: Type[SchemaType],
    **kwargs: Any,
) -> Optional[SchemaType]:
    """
    转换关联对象
    
    Args:
        model_obj: 主模型对象
        relation_field: 关联字段名
        schema_class: Schema类
        **kwargs: 传递给convert_model_to_schema的其他参数
        
    Returns:
        Schema对象或None
        
    Example:
        >>> job = Job(language=Language(id=1, name='zh'))
        >>> lang_schema = convert_related_object(job, 'language', SchemaLanguage)
    """
    related_obj = getattr(model_obj, relation_field, None)
    if related_obj is None:
        return None
    
    return convert_model_to_schema(related_obj, schema_class, **kwargs)


def create_schema_list(
    model_objs: list[Any],
    schema_class: Type[SchemaType],
    converter: Optional[Callable[[Any], SchemaType]] = None,
    **kwargs: Any,
) -> list[SchemaType]:
    """
    批量转换模型对象列表为Schema对象列表
    
    Args:
        model_objs: 模型对象列表
        schema_class: Schema类
        converter: 自定义转换函数，如果提供则使用此函数
        **kwargs: 传递给convert_model_to_schema的其他参数
        
    Returns:
        Schema对象列表
        
    Example:
        >>> accounts = [Account(...), Account(...)]
        >>> schemas = create_schema_list(accounts, SchemaAccount)
    """
    if converter:
        return [converter(obj) for obj in model_objs]
    
    return [
        convert_model_to_schema(obj, schema_class, **kwargs)
        for obj in model_objs
    ]


def convert_to_response_schema(
    model_obj: Any,
    schema_class: Type[SchemaType],
    response_class: Optional[Type[Any]] = None,
    **kwargs: Any,
) -> Any:
    """
    将模型对象转换为响应Schema对象
    
    这是一个辅助函数，用于简化常见的转换模式：
    convert_model_to_schema -> model_dump/dict -> ResponseClass
    
    Args:
        model_obj: 数据库模型实例
        schema_class: Schema类
        response_class: 响应类（可选），如果提供则使用model_dump/dict创建响应对象
        **kwargs: 传递给convert_model_to_schema的其他参数
        
    Returns:
        Schema对象或响应对象
        
    Example:
        >>> schema_account = convert_model_to_schema(account, Account)
        >>> response = GetAccountResponse(**schema_account.model_dump())
        # 可以简化为：
        >>> response = convert_to_response_schema(account, Account, GetAccountResponse)
    """
    schema_obj = convert_model_to_schema(model_obj, schema_class, **kwargs)
    
    if response_class:
        # 使用model_dump或dict方法获取字典
        if hasattr(schema_obj, 'model_dump'):
            return response_class(**schema_obj.model_dump())
        elif hasattr(schema_obj, 'dict'):
            return response_class(**schema_obj.dict())
        else:
            # 如果schema_obj本身就是字典，直接使用
            return response_class(**schema_obj) if isinstance(schema_obj, dict) else response_class(**vars(schema_obj))
    
    return schema_obj

