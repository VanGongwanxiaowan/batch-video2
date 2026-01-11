"""统一数据库会话管理模块。

提供安全的数据库连接和会话管理功能，包括：
- 连接池配置
- 会话生命周期管理
- 自动提交/回滚
- 资源清理
"""
from contextlib import contextmanager
from functools import lru_cache
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from core.config import BaseConfig
from core.config.constants import (
    DatabasePoolConfig,
    TimeoutConfig,
)

# SQLAlchemy声明式基类，所有模型都继承自此类
Base = declarative_base()


class DatabaseManager:
    """数据库管理器。

    管理数据库连接池和会话工厂，提供生产级别的数据库连接配置。
    """

    def __init__(self, database_url: str) -> None:
        """初始化数据库管理器。

        Args:
            database_url: 数据库连接URL，格式如：
                        mysql+mysqlconnector://user:password@host:port/database

        注意：
            - 使用连接池提高性能和资源利用率
            - 启用pool_pre_ping自动检测连接有效性
            - MySQL连接添加超时配置防止连接挂起
        """
        # 生产环境数据库连接池配置
        connect_args = {}
        if "mysql" in database_url.lower():
            connect_args = {
                "connect_timeout": TimeoutConfig.DEFAULT_DATABASE_CONNECT_TIMEOUT,
                "read_timeout": TimeoutConfig.DEFAULT_DATABASE_READ_TIMEOUT,
                "write_timeout": TimeoutConfig.DEFAULT_DATABASE_WRITE_TIMEOUT,
            }

        self.engine = create_engine(
            database_url,
            pool_size=DatabasePoolConfig.DEFAULT_POOL_SIZE,
            max_overflow=DatabasePoolConfig.DEFAULT_MAX_OVERFLOW,
            pool_recycle=DatabasePoolConfig.DEFAULT_POOL_RECYCLE,
            pool_pre_ping=True,  # 连接前ping，检测连接是否有效
            connect_args=connect_args,
            echo=False,  # 不打印SQL语句（生产环境）
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,  # 禁用自动提交，手动控制事务
            autoflush=False,  # 禁用自动刷新，手动控制
            bind=self.engine,
        )

    def create_tables(self) -> None:
        """创建所有数据库表。

        注意：
            - 仅在开发环境使用
            - 生产环境应使用Alembic等迁移工具
        """
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """获取数据库会话。

        Returns:
            Session: SQLAlchemy会话对象

        注意：
            - 调用者负责关闭会话
            - 建议使用上下文管理器或get_db()函数
        """
        return self.SessionLocal()


@lru_cache()
def get_database_manager(database_url: str) -> DatabaseManager:
    """获取缓存的数据库管理器实例。

    Args:
        database_url: 数据库连接URL

    Returns:
        DatabaseManager: 数据库管理器实例

    注意：
        - 使用lru_cache缓存管理器，相同URL返回同一个实例
        - 这确保连接池在所有调用间共享
    """
    return DatabaseManager(database_url)


def get_db(config: Optional[BaseConfig] = None) -> Generator[Session, None, None]:
    """获取数据库会话（用于FastAPI依赖注入）。

    这是一个生成器函数，可以安全地管理数据库会话的生命周期：
    - 自动创建会话
    - 自动关闭会话
    - 在异常时自动清理

    Args:
        config: 配置对象。如果为None，则从环境变量读取默认配置。

    Yields:
        Session: 数据库会话对象

    示例：
        ```python
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
        ```

    注意：
        - 会话在使用后自动关闭
        - 不自动提交，需要在业务逻辑中显式提交
    """
    if config is None:
        from core.config import get_app_config

        config = get_app_config()

    db_manager = get_database_manager(config.DATABASE_URL)
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


def get_session(config: Optional[BaseConfig] = None) -> Session:
    """获取数据库会话（直接返回，不用于依赖注入）。

    用于非FastAPI场景，直接获取会话对象。
    调用者必须负责关闭会话。

    Args:
        config: 配置对象。如果为None，则从环境变量读取默认配置。

    Returns:
        Session: 数据库会话对象

    示例：
        ```python
        db = get_session()
        try:
            items = db.query(Item).all()
        finally:
            db.close()
        ```

    注意：
        - 调用者必须手动关闭会话，避免连接泄漏
        - 建议使用db_session()上下文管理器
    """
    if config is None:
        from core.config import get_app_config

        config = get_app_config()

    db_manager = get_database_manager(config.DATABASE_URL)
    return db_manager.get_session()


@contextmanager
def db_session(config: Optional[BaseConfig] = None) -> Generator[Session, None, None]:
    """数据库会话上下文管理器，自动提交/回滚并释放资源。

    这是推荐使用的数据库会话管理方式：
    - 自动提交成功的事务
    - 自动回滚异常时的事务
    - 自动关闭会话释放资源

    Args:
        config: 配置对象。如果为None，则从环境变量读取默认配置。

    Yields:
        Session: 数据库会话对象

    示例：
        ```python
        with db_session() as db:
            item = Item(name="test")
            db.add(item)
            # 自动提交，如果异常则自动回滚
        ```

    注意：
        - 退出上下文时自动提交
        - 如果发生异常，自动回滚
        - 无论成功或失败，都会关闭会话
    """
    db = get_session(config)
    try:
        yield db
        db.commit()
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不处理，直接抛出（不捕获，让程序正常退出）
        db.rollback()
        raise
    except Exception:
        # 其他异常，回滚事务
        db.rollback()
        raise
    finally:
        db.close()

