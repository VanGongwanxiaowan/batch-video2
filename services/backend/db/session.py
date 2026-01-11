# backend/app/db/session.py
# 描述: 数据库会话管理，包括数据库连接引擎、会话生成器和获取数据库会话的依赖函数。
#      用于FastAPI的依赖注入系统，确保每个请求都有独立的数据库会话。

from config import settings
from core.db import models  # 确保模型被注册

# 使用统一的数据库会话管理
from core.db.session import Base, DatabaseManager, get_db, get_session

# 为了向后兼容,保留这些导出
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# 创建数据库管理器
_db_manager = DatabaseManager(SQLALCHEMY_DATABASE_URL)
engine = _db_manager.engine
SessionLocal = _db_manager.SessionLocal

# 使用统一的get_db函数
__all__ = ["Base", "get_db", "get_session", "engine", "SessionLocal"]