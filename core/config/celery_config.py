"""Celery 配置模块

提供 Celery 应用实例和配置，用于分布式任务队列。
"""
import os
from datetime import timedelta

from .settings import BaseConfig


class CeleryConfig(BaseConfig):
    """Celery 配置类"""

    # Broker 配置 (使用 Redis)
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # 任务配置
    CELERY_TASK_ALWAYS_EAGER: bool = False  # 生产环境设为 False
    CELERY_TASK_EAGER_PROPAGATES: bool = True
    CELERY_TASK_IGNORE_RESULT: bool = False

    # 任务序列化
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list = ["json"]

    # 时区设置
    CELERY_TIMEZONE: str = "Asia/Shanghai"
    CELERY_ENABLE_UTC: bool = True

    # 任务结果配置
    CELERY_RESULT_EXPIRES: int = 86400  # 结果保存 24 小时
    CELERY_RESULT_EXTENDED: bool = True

    # 任务执行配置
    CELERY_TASK_TRACK_STARTED: bool = True  # 跟踪任务开始时间
    CELERY_TASK_TIME_LIMIT: int = 3600  # 单个任务最大执行时间 (1小时)
    CELERY_TASK_SOFT_TIME_LIMIT: int = 3300  # 软限制 (55分钟)

    # Worker 配置
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1  # 预取倍数
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 100  # 每个 worker 处理任务数后重启

    # 任务重试配置
    CELERY_TASK_AUTORETRY_FOR: list = [
        "Exception",
    ]  # 自动重试的异常类型
    CELERY_TASK_RETRY_LIMIT: int = 3  # 最大重试次数
    CELERY_TASK_RETRY_BACKOFF: bool = True  # 启用指数退避
    CELERY_TASK_RETRY_BACKOFF_MAX: int = 600  # 最大退避时间 (10分钟)
    CELERY_TASK_RETRY_JITTER: bool = True  # 添加随机抖动

    # 任务路由配置 (按任务类型路由到不同队列)
    CELERY_TASK_ROUTES: dict = {
        "services.worker.tasks.process_video_job": {"queue": "video_processing"},
        "services.worker.tasks.cleanup_old_jobs": {"queue": "maintenance"},
    }

    # 任务优先级
    CELERY_TASK_DEFAULT_PRIORITY: int = 5
    CELERY_TASK_PRIORITY_MAX: int = 10
    CELERY_TASK_PRIORITY_MIN: int = 1

    # 安全配置
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP: bool = True
    CELERY_BROKER_CONNECTION_MAX_RETRIES: int = 10

    # 监控配置
    CELERY_SEND_EVENTS: bool = True  # 发送监控事件
    CELERY_SEND_TASK_SENT_EVENT: bool = True  # 发送任务发送事件
    CELERY_TASK_SEND_SENT_EVENT: bool = True


# 获取 Celery 配置实例
def get_celery_config() -> CeleryConfig:
    """获取 Celery 配置实例

    Returns:
        CeleryConfig: Celery 配置对象
    """
    return CeleryConfig()


# Celery 应用配置字典
celery_app_config = {
    # 基础配置
    "broker_url": lambda: get_celery_config().CELERY_BROKER_URL,
    "result_backend": lambda: get_celery_config().CELERY_RESULT_BACKEND,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "Asia/Shanghai",
    "enable_utc": True,

    # 任务配置
    "task_always_eager": False,
    "task_eager_propagates": True,
    "task_ignore_result": False,
    "task_track_started": True,
    "task_time_limit": 3600,  # 1小时
    "task_soft_time_limit": 3300,  # 55分钟

    # 结果配置
    "result_expires": 86400,  # 24小时
    "result_extended": True,

    # Worker 配置
    "worker_prefetch_multiplier": 1,
    "worker_max_tasks_per_child": 100,

    # 重试配置
    "task_autoretry_for": (Exception,),
    "task_retry_limit": 3,
    "task_retry_backoff": True,
    "task_retry_backoff_max": 600,
    "task_retry_jitter": True,

    # 任务路由
    "task_routes": {
        "services.worker.tasks.process_video_job": {"queue": "video_processing"},
        "services.worker.tasks.cleanup_old_jobs": {"queue": "maintenance"},
        "services.worker.tasks.reset_stuck_jobs": {"queue": "maintenance"},
    },

    # 优先级
    "task_default_priority": 5,
    "task_priority_max": 10,
    "task_priority_min": 1,

    # 安全配置
    "broker_connection_retry_on_startup": True,
    "broker_connection_max_retries": 10,

    # 监控配置
    "send_events": True,
    "task_send_sent_event": True,

    # 任务命名
    "task_name": lambda func_name: f"batchshort.{func_name}",
}


# Celery Beat 定时任务配置
celery_beat_schedule = {
    # 每 3 分钟清理一次超时任务
    "cleanup-stuck-jobs-every-3-minutes": {
        "task": "services.worker.tasks.reset_stuck_jobs",
        "schedule": timedelta(minutes=3),
        "options": {"queue": "maintenance"},
    },
    # 每天凌晨 2 点清理旧任务
    "cleanup-old-jobs-daily": {
        "task": "services.worker.tasks.cleanup_old_jobs",
        "schedule": timedelta(hours=24),
        "options": {"queue": "maintenance"},
    },
    # 每小时检查任务健康状态
    "check-job-health-hourly": {
        "task": "services.worker.tasks.check_job_health",
        "schedule": timedelta(hours=1),
        "options": {"queue": "maintenance"},
    },
}


def get_celery_broker_url() -> str:
    """获取 Celery Broker URL

    优先级: 环境变量 > 配置文件 > 默认值

    Returns:
        str: Broker URL
    """
    return os.getenv(
        "CELERY_BROKER_URL",
        get_celery_config().CELERY_BROKER_URL
    )


def get_celery_result_backend() -> str:
    """获取 Celery Result Backend URL

    Returns:
        str: Result Backend URL
    """
    return os.getenv(
        "CELERY_RESULT_BACKEND",
        get_celery_config().CELERY_RESULT_BACKEND
    )
