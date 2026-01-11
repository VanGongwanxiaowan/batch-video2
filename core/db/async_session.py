"""异步数据库会话管理"""
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)

# 异步引擎
_async_engine = None
_async_session_factory = None


def get_async_engine():
    """获取异步数据库引擎"""
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.ASYNC_DATABASE_URL,
            echo=settings.SQL_ECHO,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            poolclass=QueuePool,
        )
    return _async_engine


def get_async_session() -> async_sessionmaker[AsyncSession]:
    """获取异步会话工厂"""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖注入"""
    session_factory = get_async_session()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            await session.close()


class AsyncDatabaseManager:
    """异步数据库管理器"""
    
    def __init__(self):
        self.engine = get_async_engine()
        self.session_factory = get_async_session()
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database error in session: {e}", exc_info=True)
                raise
            finally:
                await session.close()
    
    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed.")


# 全局数据库管理器
async_db_manager = AsyncDatabaseManager()
