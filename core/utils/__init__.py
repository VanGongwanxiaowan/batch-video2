"""
Core utilities module
"""

from .api_helpers import (
    convert_datetime_to_iso,
    create_list_response,
    get_or_404,
    validate_pagination_params,
)
from .asyncio_helpers import (
    async_to_sync,
    get_shared_loop,
    run_async,
    run_in_shared_loop,
    shutdown_shared_loop,
)
from .crud_helpers import CRUDHelper, register_crud_routes
from .exception_handler import (
    exception_context,
    handle_service_exceptions,
    handle_service_method_exceptions,
    safe_execute,
)
from .ffmpeg import FFmpegError, FFmpegUtils, ffmpeg_utils, run_ffmpeg, validate_path
from .password import hash_password, verify_password
from .retry import (
    retry_for_file_operation,
    retry_for_http_request,
    retry_for_image_generation,
    retry_for_tts,
    retry_on_condition,
    retry_with_backoff,
    should_retry_on_http_status,
)
from .schema_converter import (
    convert_datetime_fields,
    convert_model_to_schema,
    convert_related_object,
    create_schema_list,
)
from .time_formatter import format_time_ms_to_srt, format_time_seconds_to_srt

__all__ = [
    'FFmpegUtils',
    'ffmpeg_utils',
    'FFmpegError',
    'run_ffmpeg',
    'validate_path',
    'hash_password',
    'verify_password',
    'handle_service_exceptions',
    'handle_service_method_exceptions',
    'exception_context',
    'safe_execute',
    'create_list_response',
    'get_or_404',
    'validate_pagination_params',
    'convert_datetime_to_iso',
    'CRUDHelper',
    'register_crud_routes',
    'convert_model_to_schema',
    'convert_datetime_fields',
    'convert_related_object',
    'create_schema_list',
    'format_time_ms_to_srt',
    'format_time_seconds_to_srt',
    # 异步工具
    'get_shared_loop',
    'run_in_shared_loop',
    'run_async',
    'shutdown_shared_loop',
    'async_to_sync',
    # 重试装饰器
    'retry_with_backoff',
    'retry_on_condition',
    'retry_for_image_generation',
    'retry_for_tts',
    'retry_for_http_request',
    'retry_for_file_operation',
    'should_retry_on_http_status',
]