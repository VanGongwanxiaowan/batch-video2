"""数据库性能监控指标"""
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast
from functools import wraps
import logging

from prometheus_client import Counter, Gauge, Histogram, start_http_server
from sqlalchemy import event
from sqlalchemy.engine import Engine

from core.config import MonitoringConfig, get_app_config
from core.logging_config import get_logger

logger = get_logger(__name__)

# 获取应用配置
app_config = get_app_config()
SERVICE_NAME = app_config.APP_NAME

# 类型变量
F = TypeVar('F', bound=Callable[..., Any])

# 定义Prometheus指标
DB_QUERY_COUNT = Counter(
    'db_query_count',
    'Number of database queries',
    ['operation', 'model', 'status']
)

DB_QUERY_DURATION = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'model'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
)

DB_ACTIVE_CONNECTIONS = Gauge(
    'db_active_connections',
    'Number of active database connections',
    ['db_name']
)

DB_POOL_SIZE = Gauge(
    'db_pool_size',
    'Size of the database connection pool',
    ['db_name']
)

DB_POOL_OVERFLOW = Gauge(
    'db_pool_overflow',
    'Number of overflow connections in the pool',
    ['db_name']
)

# 全局变量
_metrics_started = False
_metrics_enabled = MonitoringConfig.DEFAULT_METRICS_ENABLED


def start_metrics_server(port: int = MonitoringConfig.DEFAULT_METRICS_PORT) -> None:
    """启动Prometheus指标服务器"""
    global _metrics_started, _metrics_enabled

    if not _metrics_enabled:
        logger.info("Metrics collection is disabled")
        return

    try:
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
        _metrics_started = True
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")


def track_query_metrics(operation: str, model_name: str = ""):
    """
    跟踪数据库查询指标的装饰器
    
    Args:
        operation: 操作类型，如 'select', 'insert', 'update', 'delete'
        model_name: 模型名称，用于标记指标
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not _metrics_started or not _metrics_enabled:
                return await func(*args, **kwargs)
                
            start_time = time.monotonic()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Database operation failed: {e}", exc_info=True)
                raise
            finally:
                duration = time.monotonic() - start_time
                DB_QUERY_DURATION.labels(operation=operation, model=model_name).observe(duration)
                DB_QUERY_COUNT.labels(operation=operation, model=model_name, status=status).inc()
                
        return cast(F, wrapper)
    return decorator


def setup_sqlalchemy_metrics(engine: Engine) -> None:
    """设置SQLAlchemy事件监听器以收集指标"""
    if not _metrics_enabled:
        return
    
    db_name = engine.url.database or "unknown"
    
    @event.listens_for(engine, 'before_cursor_execute')
    def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
        conn.info.setdefault('query_start_time', []).append(time.monotonic())

    @event.listens_for(engine, 'after_cursor_execute')
    def receive_after_cursor_execute(conn, cursor, statement, params, context, executemany):
        duration = time.monotonic() - conn.info['query_start_time'].pop(-1)
        
        # 解析SQL语句类型
        sql_type = statement.split()[0].lower()
        if sql_type not in ['select', 'insert', 'update', 'delete']:
            sql_type = 'other'
            
        # 记录查询指标
        DB_QUERY_DURATION.labels(operation=sql_type, model="").observe(duration)
        DB_QUERY_COUNT.labels(operation=sql_type, model="", status="success").inc()
    
    @event.listens_for(engine, 'checkout')
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        DB_ACTIVE_CONNECTIONS.labels(db_name=db_name).inc()

    @event.listens_for(engine, 'checkin')
    def receive_checkin(dbapi_connection, connection_record):
        DB_ACTIVE_CONNECTIONS.labels(db_name=db_name).dec()
    
    # 连接池指标
    @event.listens_for(engine, 'first_connect')
    def receive_first_connect(dbapi_connection, connection_record):
        DB_POOL_SIZE.labels(db_name=db_name).set(engine.pool.size())
        DB_POOL_OVERFLOW.labels(db_name=db_name).set(engine.pool.overflow())
    
    @event.listens_for(engine, 'connect')
    def receive_connect(dbapi_connection, connection_record):
        DB_POOL_SIZE.labels(db_name=db_name).set(engine.pool.size())
        DB_POOL_OVERFLOW.labels(db_name=db_name).set(engine.pool.overflow())
    
    @event.listens_for(engine, 'close')
    def receive_close(dbapi_connection, connection_record):
        DB_POOL_SIZE.labels(db_name=db_name).set(engine.pool.size())
        DB_POOL_OVERFLOW.labels(db_name=db_name).set(engine.pool.overflow())


class DatabaseMetrics:
    """数据库指标收集器"""
    
    def __init__(self, engine):
        self.engine = engine
        self.db_name = engine.url.database or "unknown"
        
    def get_connection_metrics(self) -> Dict[str, float]:
        """获取连接池指标"""
        return {
            "connections_in_use": self.engine.pool.checkedin(),
            "connections_in_pool": self.engine.pool.checkedout(),
            "pool_size": self.engine.pool.size(),
            "pool_overflow": self.engine.pool.overflow(),
            "pool_timeout": self.engine.pool.timeout(),
        }
    
    def get_query_metrics(self) -> Dict[str, Any]:
        """获取查询指标"""
        # 这里可以添加自定义的查询指标收集逻辑
        return {}
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            "connection_pool": self.get_connection_metrics(),
            "queries": self.get_query_metrics()
        }
