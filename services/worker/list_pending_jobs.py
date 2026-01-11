#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
列出所有待处理的任务
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from typing import List

from db.models import Job, get_beijing_time
from db.session import db_session
from sqlalchemy.orm import Session

from core.logging_config import setup_logging

# 初始化日志记录器（用于错误和重要操作记录）
logger = setup_logging("worker.list_pending_jobs", log_to_file=False)

def list_pending_jobs() -> List[Job]:
    """列出所有待处理的任务
    
    Returns:
        List[Job]: 待处理任务列表
    """
    try:
        with db_session() as db:
            # 查询所有待处理的任务
            pending_jobs = db.query(Job).filter(
                Job.status == "待处理",
                Job.deleted_at == None
            ).order_by(Job.runorder.desc(), Job.id.asc()).all()
            
            print("=" * 80)
            print(f"待处理任务列表（共 {len(pending_jobs)} 个任务）")
            print("=" * 80)
            print(f"{'ID':<8} {'标题':<30} {'优先级':<8} {'创建时间':<20} {'更新时间':<20}")
            print("-" * 80)
            
            for job in pending_jobs:
                created_time = job.created_at.strftime('%Y-%m-%d %H:%M:%S') if job.created_at else 'N/A'
                updated_time = job.updated_at.strftime('%Y-%m-%d %H:%M:%S') if job.updated_at else 'N/A'
                title = job.title[:28] + '..' if len(job.title) > 30 else job.title
                print(f"{job.id:<8} {title:<30} {job.runorder:<8} {created_time:<20} {updated_time:<20}")
            
            print("=" * 80)
            print("\n执行顺序说明：")
            print("  - 按优先级（runorder）降序排列")
            print("  - 相同优先级按ID升序排列")
            print("  - Worker每10秒检查一次，按此顺序处理")
            
            logger.info(f"查询到 {len(pending_jobs)} 个待处理任务")
            return pending_jobs
        
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（查询错误等）
        error_msg = f"查询失败: {e}"
        print(f"❌ {error_msg}")
        logger.exception(error_msg)
        return []

if __name__ == "__main__":
    list_pending_jobs()

