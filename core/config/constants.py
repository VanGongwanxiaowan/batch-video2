"""配置常量模块

定义项目中使用的各种常量，避免魔法数字和硬编码值。
"""


class RetryConfig:
    """重试配置常量"""
    MAX_RETRIES = 5  # 最大重试次数
    MAX_RETRIES_TTS = 10  # TTS服务的最大重试次数
    BASE_DELAY_SECONDS = 2  # 指数退避的基础延迟（秒）
    MAX_DELAY_SECONDS = 60  # 最大延迟（秒）
    RETRY_SLEEP_MS = 300  # 重试间隔（毫秒）


class DatabaseConfig:
    """数据库配置常量"""
    DEFAULT_PAGE_SIZE = 10  # 默认分页大小
    MAX_PAGE_SIZE = 1000  # 最大分页大小
    BATCH_DELETE_SIZE = 1000  # 批量删除的批次大小


class FileConfig:
    """文件操作配置常量"""
    MAX_FILENAME_LENGTH = 255  # 最大文件名长度
    DEFAULT_CHUNK_SIZE = 8192  # 默认文件块大小（字节）


class TextConfig:
    """文本处理配置常量"""
    MAX_TITLE_LENGTH = 200  # 标题最大长度
    MAX_CONTENT_LENGTH = 50000  # 内容最大长度
    MAX_DESCRIPTION_LENGTH = 10000  # 描述最大长度
    MAX_PUBLISH_TITLE_LENGTH = 200  # 发布标题最大长度


class JobConfig:
    """任务相关配置常量"""
    DEFAULT_MAX_CONCURRENT_JOBS = 1  # 默认最大并发任务数
    DEFAULT_JOB_PAGE_SIZE = 10  # 默认任务列表分页大小
    MAX_JOB_PAGE_SIZE = 100  # 最大任务列表分页大小


class OSSConfig:
    """OSS配置常量"""
    DEFAULT_URL_EXPIRATION = 3600  # 默认URL过期时间（秒，1小时）
    MAX_URL_EXPIRATION = 86400  # 最大URL过期时间（秒，24小时）


class ImageConfig:
    """图像处理配置常量"""
    DEFAULT_IMAGE_WIDTH = 1360  # 默认图像宽度
    DEFAULT_IMAGE_HEIGHT = 768  # 默认图像高度
    DEFAULT_VERTICAL_WIDTH = 768  # 默认竖向图像宽度
    DEFAULT_VERTICAL_HEIGHT = 1360  # 默认竖向图像高度


class VideoConfig:
    """视频处理配置常量"""
    DEFAULT_VIDEO_WIDTH = 1360  # 默认视频宽度
    DEFAULT_VIDEO_HEIGHT = 768  # 默认视频高度
    DEFAULT_VERTICAL_VIDEO_WIDTH = 768  # 默认竖向视频宽度
    DEFAULT_VERTICAL_VIDEO_HEIGHT = 1360  # 默认竖向视频高度


class TimeoutConfig:
    """超时配置常量"""
    DEFAULT_HTTP_TIMEOUT = 30  # 默认HTTP请求超时（秒）
    DEFAULT_FILE_UPLOAD_TIMEOUT = 300  # 默认文件上传超时（秒，5分钟）
    DEFAULT_VIDEO_PROCESSING_TIMEOUT = 600  # 默认视频处理超时（秒，10分钟）
    DEFAULT_DATABASE_CONNECT_TIMEOUT = 10  # 默认数据库连接超时（秒）
    DEFAULT_DATABASE_READ_TIMEOUT = 30  # 默认数据库读取超时（秒）
    DEFAULT_DATABASE_WRITE_TIMEOUT = 30  # 默认数据库写入超时（秒）


class DatabasePoolConfig:
    """数据库连接池配置常量"""
    DEFAULT_POOL_SIZE = 10  # 默认连接池大小
    DEFAULT_MAX_OVERFLOW = 20  # 默认最大溢出连接数
    DEFAULT_POOL_RECYCLE = 3600  # 默认连接回收时间（秒，1小时）


class TTSConfig:
    """TTS服务配置常量"""
    DEFAULT_SEEDVC_BASE_URL = "http://127.0.0.1:8007"  # 默认SeedVC TTS服务地址
    DEFAULT_SLEEP_MS = 300  # 默认请求间隔（毫秒）
    MAX_REF_AUDIO_DURATION = 25  # 最大参考音频时长（秒）


class WorkerConfig:
    """Worker服务配置常量"""
    DEFAULT_MAX_CONCURRENT_JOBS = 1  # 默认最大并发任务数
    DEFAULT_SCHEDULER_INTERVAL_SECONDS = 60  # 默认调度器检查间隔（秒）
    DEFAULT_RETRY_DELAY_SECONDS = 2  # 默认重试延迟（秒）
    DEFAULT_CLEANUP_INTERVAL_HOURS = 3  # 默认清理任务间隔（小时）
    DEFAULT_SHUTDOWN_WAIT_SECONDS = 2  # 默认关闭等待时间（秒）
    DEFAULT_POLL_SLEEP_SECONDS = 0.1  # 默认轮询休眠时间（秒）
    DEFAULT_ERROR_SLEEP_SECONDS = 1  # 默认错误后等待时间（秒）
    DEFAULT_PROCESS_JOIN_TIMEOUT_SECONDS = 10  # 默认进程等待超时（秒）
    DEFAULT_BUSY_WAIT_SLEEP_SECONDS = 0.1  # 默认忙等待休眠时间（秒）
    DEFAULT_MAX_WORKERS = 4  # 默认最大工作线程数
    DEFAULT_MAX_WORKERS_CONTENT = 15  # 内容处理的最大工作线程数


class ImageGenConfig:
    """图像生成服务配置常量"""
    DEFAULT_MAX_KEEPALIVE_CONNECTIONS = 5  # 默认最大保持连接数
    DEFAULT_MAX_CONNECTIONS = 10  # 默认最大连接数
    DEFAULT_HTTP_TIMEOUT_SECONDS = 30  # 默认HTTP超时（秒）
    DEFAULT_IMAGE_GENERATION_TIMEOUT_SECONDS = 300  # 默认图像生成超时（秒，5分钟）


class APIConfig:
    """API相关配置常量"""
    MAX_PAGE_SIZE = 100  # 最大分页大小
    MAX_PAGE_NUMBER = 1000  # 最大页码
    DEFAULT_PAGE_SIZE = 10  # 默认分页大小
    DEFAULT_PAGE_NUMBER = 1  # 默认页码

    # 图像生成相关
    IMAGE_GENERATION_MAX_RETRIES = 30  # 图像生成最大重试次数
    IMAGE_GENERATION_RETRY_INTERVAL = 5  # 图像生成重试间隔（秒）

    # 文件上传相关
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 最大文件大小（10MB）
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}  # 允许的图片扩展名


class VideoProcessingConfigConstants:
    """视频处理配置常量"""
    DEFAULT_VIDEO_CODEC = "libx264"  # 默认视频编解码器
    DEFAULT_CRF = 23  # 默认 CRF 值（质量）
    DEFAULT_PRESET = "veryfast"  # 默认编码速度预设
    DEFAULT_DURATION_PER_IMAGE = 5.0  # 默认每张图片的视频时长（秒）
    DEFAULT_FPS = 24  # 默认帧率
    DEFAULT_PIXEL_FORMAT = "yuv420p"  # 默认像素格式
    TRANSITION_DURATION = 1.0  # 默认转场效果持续时间（秒）


class FFmpegConfigConstants:
    """FFmpeg 相关配置常量"""
    DEFAULT_FFMPEG_TIMEOUT = 300  # 默认 FFmpeg 超时时间（秒，5分钟）
    DEFAULT_THREADS = 4  # 默认线程数
    SHORTEST_FLAG = True  # 默认使用 -shortest 标志


class ColorConfig:
    """颜色配置常量"""
    DEFAULT_BACKGROUND_COLOR = "#578B2E"  # 默认背景颜色（绿色）
    DEFAULT_TEXT_COLOR = "#000000"  # 默认文本颜色（黑色）
    DEFAULT_OUTLINE_COLOR = "#FFFFFF"  # 默认描边颜色（白色）


class PathConfigConstants:
    """路径配置常量"""
    # 视频文件扩展名
    VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv")
    # 图片文件扩展名
    IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
    # 音频文件扩展名
    AUDIO_EXTENSIONS = (".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac")
    # 字幕文件扩展名
    SUBTITLE_EXTENSIONS = (".srt", ".vtt", ".ass", ".ssa")
    # 配置文件扩展名
    CONFIG_EXTENSIONS = (".json", ".yaml", ".yml", ".toml")


class MonitoringConfig:
    """监控相关配置常量"""
    # Prometheus 指标配置
    DEFAULT_METRICS_ENABLED = True  # 默认启用指标收集
    DEFAULT_METRICS_PORT = 9090  # 默认指标端口
    DEFAULT_METRICS_PATH = "/metrics"  # 默认指标路径

    # 分布式追踪配置
    DEFAULT_TRACING_ENABLED = False  # 默认禁用追踪
    DEFAULT_TRACING_SAMPLE_RATE = 0.1  # 默认采样率（10%）
    DEFAULT_JAEGER_AGENT_HOST = "localhost"  # Jaeger Agent 主机
    DEFAULT_JAEGER_AGENT_PORT = 6831  # Jaeger Agent 端口

    # 健康检查配置
    DEFAULT_HEALTH_CHECK_INTERVAL = 30  # 默认健康检查间隔（秒）
    DEFAULT_HEALTH_CHECK_TIMEOUT = 5  # 默认健康检查超时（秒）

    # 告警配置
    DEFAULT_ALERTING_ENABLED = False  # 默认禁用告警
    DEFAULT_ALERTMANAGER_URL = "http://localhost:9093"  # 默认 AlertManager URL

    # 日志聚合配置
    DEFAULT_LOKI_ENABLED = False  # 默认禁用 Loki
    DEFAULT_LOKI_URL = "http://localhost:3100"  # 默认 Loki URL

    # 性能监控阈值
    SLOW_QUERY_THRESHOLD_SECONDS = 1.0  # 慢查询阈值（秒）
    HIGH_ERROR_RATE_THRESHOLD = 0.05  # 高错误率阈值（5%）
    HIGH_LATENCY_THRESHOLD_SECONDS = 5.0  # 高延迟阈值（秒）
    MEMORY_USAGE_WARNING_THRESHOLD = 0.8  # 内存使用警告阈值（80%）
    CPU_USAGE_WARNING_THRESHOLD = 0.8  # CPU使用警告阈值（80%）

    # 指标标签
    SERVICE_NAME_LABEL = "service"  # 服务名标签
    INSTANCE_LABEL = "instance"  # 实例标签
    STATUS_LABEL = "status"  # 状态标签
    ERROR_TYPE_LABEL = "error_type"  # 错误类型标签
    ENDPOINT_LABEL = "endpoint"  # 端点标签
    METHOD_LABEL = "method"  # 方法标签


class SecurityConfig:
    """安全相关配置常量"""
    # API 限流配置
    DEFAULT_RATE_LIMIT_ENABLED = True  # 默认启用限流
    DEFAULT_RATE_LIMIT_PER_MINUTE = 60  # 默认每分钟请求数
    DEFAULT_RATE_LIMIT_PER_HOUR = 1000  # 默认每小时请求数
    DEFAULT_RATE_LIMIT_BURST_SIZE = 10  # 默认突发流量大小

    # 熔断器配置
    DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5  # 默认失败阈值
    DEFAULT_CIRCUIT_BREAKER_TIMEOUT = 60  # 默认熔断超时（秒）
    DEFAULT_CIRCUIT_BREAKER_SUCCESS_THRESHOLD = 2  # 默认成功阈值

    # 密钥轮换配置
    DEFAULT_KEY_ROTATION_ENABLED = False  # 默认禁用密钥轮换
    DEFAULT_KEY_ROTATION_PERIOD_DAYS = 90  # 默认密钥轮换周期（天）
    DEFAULT_KEY_EXPIRATION_DAYS = 180  # 默认密钥过期时间（天）

    # 加密配置
    DEFAULT_ENCRYPTION_ALGORITHM = "AES-256-GCM"  # 默认加密算法
    DEFAULT_KEY_SIZE = 32  # 默认密钥大小（256位）

    # HTTPS 配置
    DEFAULT_HTTPS_REDIRECT_ENABLED = True  # 默认启用 HTTPS 重定向
    DEFAULT_SSL_MIN_VERSION = "TLSv1.2"  # 默认最低 TLS 版本

    # 输入验证配置
    DEFAULT_MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 默认最大请求大小（10MB）
    DEFAULT_MAX_PATH_LENGTH = 255  # 默认最大路径长度
    DEFAULT_MAX_QUERY_LENGTH = 1000  # 默认最大查询字符串长度

    # 密码策略配置
    DEFAULT_PASSWORD_MIN_LENGTH = 8  # 默认最小密码长度
    DEFAULT_PASSWORD_MAX_LENGTH = 128  # 默认最大密码长度
    DEFAULT_PASSWORD_REQUIRE_UPPERCASE = True  # 默认要求大写字母
    DEFAULT_PASSWORD_REQUIRE_LOWERCASE = True  # 默认要求小写字母
    DEFAULT_PASSWORD_REQUIRE_DIGIT = True  # 默认要求数字
    DEFAULT_PASSWORD_REQUIRE_SPECIAL = True  # 默认要求特殊字符

    # Token 配置
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 默认访问令牌过期时间（分钟）
    DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 7  # 默认刷新令牌过期时间（天）

    # 会话配置
    DEFAULT_MAX_SESSIONS_PER_USER = 5  # 默认每用户最大会话数
    DEFAULT_SESSION_EXPIRE_HOURS = 24  # 默认会话过期时间（小时）

    # 安全头配置
    ENABLE_SECURITY_HEADERS = True  # 启用安全头
    ENABLE_CSP = True  # 启用内容安全策略
    ENABLE_HSTS = True  # 启用 HTTP 严格传输安全
    ENABLE_X_FRAME_OPTIONS = True  # 启用 X-Frame-Options


class HighAvailabilityConfig:
    """高可用性配置常量"""
    # 服务冗余配置
    DEFAULT_REPLICA_COUNT = 3  # 默认副本数
    DEFAULT_MIN_REPLICAS = 2  # 最小副本数
    DEFAULT_MAX_REPLICAS = 10  # 最大副本数

    # 负载均衡配置
    DEFAULT_LOAD_BALANCING_METHOD = "round_robin"  # 默认负载均衡方法
    DEFAULT_HEALTH_CHECK_INTERVAL = 10  # 健康检查间隔（秒）
    DEFAULT_UNHEALTHY_THRESHOLD = 3  # 不健康阈值

    # 故障转移配置
    DEFAULT_FAILOVER_TIMEOUT = 30  # 故障转移超时（秒）
    DEFAULT_FAILOVER_RETRY_LIMIT = 3  # 故障转移重试次数

    # 数据库主从配置
    DEFAULT_DB_MASTER_PORT = 3306  # 默认主数据库端口
    DEFAULT_DB_SLAVE_PORT = 3306  # 默认从数据库端口
    DEFAULT_DB_READ_TIMEOUT = 30  # 读超时（秒）
    DEFAULT_DB_WRITE_TIMEOUT = 30  # 写超时（秒）

    # Redis 哨兵配置
    DEFAULT_REDIS_SENTINEL_PORT = 26379  # 默认哨兵端口
    DEFAULT_REDIS_SENTINEL_QUORUM = 2  # 默认哨兵法定人数
    DEFAULT_REDIS_DOWN_AFTER_MILLISECONDS = 5000  # 默认下线时间（毫秒）
    DEFAULT_REDIS_FAILOVER_TIMEOUT = 3000  # 默认故障转移超时（毫秒）

    # Redis 集群配置
    DEFAULT_REDIS_CLUSTER_REPLICAS = 1  # 默认集群副本数
    DEFAULT_REDIS_CLUSTER_TIMEOUT = 2000  # 默认集群超时（毫秒）

    # 备份配置
    DEFAULT_BACKUP_RETENTION_DAYS = 30  # 默认备份保留天数
    DEFAULT_BACKUP_SCHEDULE = "0 2 * * *"  # 默认备份计划（Cron 表达式）
    DEFAULT_BACKUP_COMPRESSION = True  # 默认启用备份压缩

    # 恢复配置
    DEFAULT_RECOVERY_POINT_OBJECTIVE = 60  # 默认恢复点目标（分钟）
    DEFAULT_RECOVERY_TIME_OBJECTIVE = 120  # 默认恢复时间目标（分钟）

