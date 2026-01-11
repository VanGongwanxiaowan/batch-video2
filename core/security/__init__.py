"""安全模块

提供生产级的安全功能，包括：
- API 限流和熔断
- 输入验证和清理
- 敏感数据加密
- HTTPS 强制
- 密钥轮换
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitBreakerState,
    get_circuit_breaker,
    with_circuit_breaker,
)
from .encryption import (
    AESCipher,
    DataEncryption,
    FieldLevelEncryption,
    Hasher,
    SecureRandom,
    SecureTokenGenerator,
    decrypt_data,
    encrypt_data,
    get_cipher,
)
from .input_validation import (
    HTMLSanitizer,
    InputValidator,
    PathValidator,
    SQLInjectionDetector,
    ValidationError,
    XSSDetector,
    sanitize_html,
    validate_email,
    validate_path,
    validate_sql_query,
    validate_url,
    validate_xss,
)
from .key_rotation import (
    FileKeyStorage,
    KeyManager,
    KeyMetadata,
    KeyRotationConfig,
    KeyStorage,
    KeyType,
    get_key_manager,
    rotate_all_keys,
)
from .middleware import (
    CORSSecurityMiddleware,
    HTTPSRedirectMiddleware,
    InputValidationMiddleware,
    IPWhitelistMiddleware,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from .rate_limit import (
    MemoryBackend,
    RateLimitBackend,
    RateLimitExceeded,
    RateLimiter,
    RedisBackend,
    SlidingWindowLimiter,
    TokenBucketLimiter,
    get_rate_limiter,
)

__all__ = [
    # 限流
    "RateLimiter",
    "RateLimitExceeded",
    "TokenBucketLimiter",
    "SlidingWindowLimiter",
    "RateLimitBackend",
    "MemoryBackend",
    "RedisBackend",
    "get_rate_limiter",
    # 熔断器
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerOpen",
    "get_circuit_breaker",
    "with_circuit_breaker",
    # 输入验证
    "InputValidator",
    "XSSDetector",
    "SQLInjectionDetector",
    "HTMLSanitizer",
    "PathValidator",
    "ValidationError",
    "validate_xss",
    "validate_sql_query",
    "sanitize_html",
    "validate_email",
    "validate_url",
    "validate_path",
    # 加密
    "DataEncryption",
    "AESCipher",
    "FieldLevelEncryption",
    "Hasher",
    "SecureRandom",
    "SecureTokenGenerator",
    "encrypt_data",
    "decrypt_data",
    "get_cipher",
    # 密钥轮换
    "KeyManager",
    "KeyType",
    "KeyMetadata",
    "KeyRotationConfig",
    "KeyStorage",
    "FileKeyStorage",
    "get_key_manager",
    "rotate_all_keys",
    # 中间件
    "SecurityHeadersMiddleware",
    "HTTPSRedirectMiddleware",
    "InputValidationMiddleware",
    "RateLimitMiddleware",
    "RequestSizeLimitMiddleware",
    "IPWhitelistMiddleware",
    "CORSSecurityMiddleware",
]
