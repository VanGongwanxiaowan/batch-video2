"""安全中间件模块

提供 FastAPI 安全中间件，集成限流、输入验证、HTTPS 强制等功能。
"""
import os
from typing import Callable, Dict, List, Optional, Set

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.config import get_app_config
from core.logging_config import get_logger
from .input_validation import (
    PathValidator,
    SQLInjectionDetector,
    ValidationError,
    XSSDetector,
)
from .rate_limit import RateLimitExceeded, get_rate_limiter

logger = get_logger(__name__)

# 获取应用配置
app_config = get_app_config()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件

    添加各种安全相关的 HTTP 响应头。
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        include_headers: Optional[Dict[str, str]] = None,
        exclude_headers: Optional[Set[str]] = None,
    ):
        """
        Args:
            app: ASGI 应用
            include_headers: 要包含的头
            exclude_headers: 要排除的头
        """
        super().__init__(app)
        self.include_headers = include_headers or self._get_default_headers()
        self.exclude_headers = exclude_headers or set()

    def _get_default_headers(self) -> Dict[str, str]:
        """获取默认的安全头"""
        return {
            # 防止点击劫持
            "X-Frame-Options": "DENY",

            # 防止 MIME 类型嗅探
            "X-Content-Type-Options": "nosniff",

            # XSS 保护
            "X-XSS-Protection": "1; mode=block",

            # 内容安全策略（默认宽松，生产环境应配置更严格）
            "Content-Security-Policy": "default-src 'self'",

            # 引用策略
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # HSTS（仅在 HTTPS 下启用）
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",

            # 权限策略
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并添加安全头"""
        response = await call_next(request)

        # 添加安全头
        for header_name, header_value in self.include_headers.items():
            if header_name not in self.exclude_headers:
                response.headers[header_name] = header_value

        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """HTTPS 重定向中间件

    强制将 HTTP 请求重定向到 HTTPS。
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        enabled: bool = True,
        allowed_hosts: Optional[Set[str]] = None,
    ):
        """
        Args:
            app: ASGI 应用
            enabled: 是否启用
            allowed_hosts: 允许的主机列表
        """
        super().__init__(app)
        self.enabled = enabled
        self.allowed_hosts = allowed_hosts

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并重定向 HTTP 到 HTTPS"""
        if not self.enabled:
            return await call_next(request)

        # 检查是否已经是 HTTPS
        if request.url.scheme == "https":
            return await call_next(request)

        # 在开发环境中禁用
        if app_config.ENVIRONMENT == "development":
            return await call_next(request)

        # 检查 X-Forwarded-Proto 头（用于代理）
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "").lower()
        if forwarded_proto == "https":
            return await call_next(request)

        # 构造 HTTPS URL
        url = request.url.replace(scheme="https")

        # 检查允许的主机
        if self.allowed_hosts and request.client:
            if url.hostname not in self.allowed_hosts:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid host"},
                )

        # 返回重定向响应
        return JSONResponse(
            status_code=status.HTTP_301_MOVED_PERMANENTLY,
            headers={"Location": str(url)},
            content={"detail": "Use HTTPS"},
        )


class InputValidationMiddleware(BaseHTTPMiddleware):
    """输入验证中间件

    验证请求输入，防止 XSS、SQL 注入等攻击。
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        skip_paths: Optional[List[str]] = None,
        enable_xss_check: bool = True,
        enable_sql_injection_check: bool = True,
        enable_path_validation: bool = True,
    ):
        """
        Args:
            app: ASGI 应用
            skip_paths: 要跳过的路径列表
            enable_xss_check: 是否启用 XSS 检查
            enable_sql_injection_check: 是否启用 SQL 注入检查
            enable_path_validation: 是否启用路径验证
        """
        super().__init__(app)
        self.skip_paths = set(skip_paths or ["/health", "/ready", "/metrics", "/docs"])
        self.enable_xss_check = enable_xss_check
        self.enable_sql_injection_check = enable_sql_injection_check
        self.enable_path_validation = enable_path_validation

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并验证输入"""
        # 跳过指定路径
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # 验证查询参数
        try:
            await self._validate_query_params(request)
        except ValidationError as e:
            logger.warning(f"Input validation failed: {e.message}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Invalid input: {e.message}"},
            )

        # 验证路径参数（如果需要）
        if self.enable_path_validation:
            try:
                self._validate_path(request.url.path)
            except ValidationError as e:
                logger.warning(f"Path validation failed: {e.message}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": f"Invalid path: {e.message}"},
                )

        return await call_next(request)

    async def _validate_query_params(self, request: Request) -> None:
        """验证查询参数"""
        for key, value in request.query_params.items():
            # XSS 检查
            if self.enable_xss_check and isinstance(value, str):
                if XSSDetector.detect_xss(value):
                    raise ValidationError(
                        f"Potentially dangerous input in parameter '{key}'",
                        field=key,
                    )

            # SQL 注入检查
            if self.enable_sql_injection_check and isinstance(value, str):
                if SQLInjectionDetector.detect_sql_injection(value):
                    raise ValidationError(
                        f"Potentially dangerous SQL pattern in parameter '{key}'",
                        field=key,
                    )

    def _validate_path(self, path: str) -> None:
        """验证路径"""
        if not PathValidator.validate_path(path):
            raise ValidationError("Invalid path format")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件

    基于 IP 或用户 ID 进行请求限流。
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        skip_paths: Optional[List[str]] = None,
    ):
        """
        Args:
            app: ASGI 应用
            skip_paths: 要跳过的路径列表
        """
        super().__init__(app)
        self.skip_paths = set(skip_paths or ["/health", "/ready", "/metrics", "/docs"])
        self.rate_limiter = get_rate_limiter()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并检查限流"""
        # 跳过指定路径
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # 检查限流
        try:
            await self.rate_limiter.check_rate_limit(request)
        except RateLimitExceeded as e:
            logger.warning(
                f"Rate limit exceeded for {request.client.host if request.client else 'unknown'}",
                extra={
                    "path": request.url.path,
                    "retry_after": e.retry_after,
                }
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": e.retry_after,
                },
                headers={
                    "Retry-After": str(e.retry_after),
                    "X-RateLimit-Limit": str(e.limit),
                    "X-RateLimit-Window": e.window,
                },
            )

        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """请求大小限制中间件

    防止过大的请求导致资源耗尽。
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
    ):
        """
        Args:
            app: ASGI 应用
            max_request_size: 最大请求大小（字节）
        """
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并检查大小"""
        # 检查 Content-Length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    logger.warning(
                        f"Request too large: {size} bytes",
                        extra={"client": request.client.host if request.client else "unknown"}
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "detail": f"Request too large. Maximum size is {self.max_request_size} bytes"
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """IP 白名单中间件

    只允许白名单中的 IP 访问。
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        allowed_ips: Optional[Set[str]] = None,
        trusted_proxies: Optional[Set[str]] = None,
    ):
        """
        Args:
            app: ASGI 应用
            allowed_ips: 允许的 IP 列表
            trusted_proxies: 受信任的代理列表
        """
        super().__init__(app)
        self.allowed_ips = allowed_ips or set()
        self.trusted_proxies = trusted_proxies or {"127.0.0.1", "::1"}

        # 如果没有配置白名单，则不启用
        self.enabled = len(self.allowed_ips) > 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并检查 IP"""
        if not self.enabled:
            return await call_next(request)

        # 获取客户端 IP
        client_ip = self._get_client_ip(request)

        # 检查 IP 是否在白名单中
        if client_ip not in self.allowed_ips:
            logger.warning(
                f"IP not in whitelist: {client_ip}",
                extra={"ip": client_ip, "path": request.url.path}
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"},
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        # 检查 X-Forwarded-For 头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 获取第一个 IP（原始客户端）
            ips = [ip.strip() for ip in forwarded_for.split(",")]
            return ips[0]

        # 检查 X-Real-IP 头
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 使用直接连接的 IP
        return request.client.host if request.client else "unknown"


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """CORS 安全中间件

    提供更严格的 CORS 控制。
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        allow_origins: Optional[List[str]] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        max_age: int = 600,
        allow_credentials: bool = False,
    ):
        """
        Args:
            app: ASGI 应用
            allow_origins: 允许的源列表
            allow_methods: 允许的方法列表
            allow_headers: 允许的头列表
            expose_headers: 暴露的头列表
            max_age: 预检请求缓存时间
            allow_credentials: 是否允许凭证
        """
        super().__init__(app)
        self.allow_origins = allow_origins or []
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE"]
        self.allow_headers = allow_headers or []
        self.expose_headers = expose_headers or []
        self.max_age = max_age
        self.allow_credentials = allow_credentials

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并添加 CORS 头"""
        # 获取请求的源
        origin = request.headers.get("Origin")

        # 检查源是否被允许
        if origin and self.allow_origins:
            if origin in self.allow_origins or "*" in self.allow_origins:
                response = await call_next(request)

                # 添加 CORS 头
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
                response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
                response.headers["Access-Control-Max-Age"] = str(self.max_age)

                if self.expose_headers:
                    response.headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)

                if self.allow_credentials:
                    response.headers["Access-Control-Allow-Credentials"] = "true"

                return response
            else:
                # 源不被允许
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Origin not allowed"},
                )

        # 没有 Origin 头或允许所有源
        return await call_next(request)
