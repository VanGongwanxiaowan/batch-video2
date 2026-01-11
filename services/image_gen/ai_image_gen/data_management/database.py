"""数据库连接和会话管理

使用统一的 core/db/session.py 进行数据库管理，避免代码重复。
为了保持向后兼容，保留 get_db 和 get_db_context 函数。
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session

from config.settings import get_settings
from core.db.session import Base, db_session, get_database_manager
from core.db.session import get_db as core_get_db
from core.exceptions import DatabaseException
from core.logging_config import setup_logging

logger = setup_logging("ai_image_gen.database")

# 获取配置
setting = get_settings()
DATABASE_URL = setting.DATABASE_URL

# 使用统一的数据库管理器
_db_manager = get_database_manager(DATABASE_URL)
engine = _db_manager.engine
SessionLocal = _db_manager.SessionLocal

# 为了向后兼容，保留 Base 的导出
# 注意：ai_image_gen 的模型应该使用 core.db.session.Base
# 但为了保持现有代码兼容，这里也导出 Base
__all__ = ["Base", "engine", "SessionLocal", "get_db", "get_db_context", "init_db"]


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入函数，获取数据库会话。
    
    使用统一的 core/db/session.py 实现，但保持接口兼容。
    
    Yields:
        Session: 数据库会话对象
        
    示例:
        ```python
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
        ```
    """
    # 使用统一的 get_db 实现
    yield from core_get_db()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    上下文管理器方式获取数据库会话。
    
    用于非 FastAPI 依赖注入的场景。
    使用统一的 core/db/session.py 实现。
    
    Yields:
        Session: 数据库会话对象
        
    示例:
        ```python
        with get_db_context() as db:
            item = Item(name="test")
            db.add(item)
            # 自动提交
        ```
    """
    # 使用统一的 db_session 上下文管理器
    with db_session() as db:
        yield db


def init_db() -> None:
    """
    初始化数据库，创建所有表。
    
    使用统一的 core/db/session.py 实现。
    
    Raises:
        DatabaseException: 当初始化失败时
    """
    logger.info("Initializing database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（数据库初始化错误等）
        logger.error(f"[init_db] Failed to initialize database tables: {e}", exc_info=True)
        raise DatabaseException(f"Failed to initialize database tables: {e}", operation="init_db")


if __name__ == "__main__":
    # Example of how to initialize the database
    init_db()
