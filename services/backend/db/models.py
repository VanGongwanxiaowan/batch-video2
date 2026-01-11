# backend/app/db/models.py
# 描述: 从统一数据库模块导入模型
#      为了向后兼容,保留此文件作为导入入口

# 从统一的数据库模块导入所有模型
from core.db.models import (
    Account,
    Job,
    JobSplit,
    Language,
    Topic,
    User,
    Voice,
    get_beijing_time,
)

# 导出所有模型,保持向后兼容
__all__ = [
    "User",
    "Job",
    "JobSplit",
    "Account",
    "Voice",
    "Topic",
    "Language",
    "get_beijing_time",
]
