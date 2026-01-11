#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 worker 中正在运行的任务
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

import pytz
from db.models import Job, get_beijing_time
from db.session import db_session
from sqlalchemy.orm import Session

from core.logging_config import setup_logging

# 初始化日志记录器（用于错误和重要操作记录）
logger = setup_logging("worker.check_running_jobs", log_to_file=False)

def check_running_jobs() -> None:
    """检查正在运行的任务"""
    try:
        with db_session() as db:
            # 查询所有状态为"处理中"的任务
            processing_jobs = db.query(Job).filter(
                Job.status == "处理中",
                Job.deleted_at == None
            ).order_by(Job.updated_at.desc()).all()
            
            print("=" * 80)
            print(f"正在运行的任务（状态为'处理中'）")
            print("=" * 80)
            
            if not processing_jobs:
                print("当前没有正在运行的任务")
                return
            
            for job in processing_jobs:
                print(f"\n任务ID: {job.id}")
                print(f"标题: {job.title}")
                print(f"状态: {job.status}")
                print(f"状态详情: {job.status_detail}")
                print(f"开始时间: {job.updated_at}")
                
                # 计算运行时长
                if job.updated_at:
                    now = get_beijing_time()
                    if job.updated_at.tzinfo is None:
                        tz = pytz.timezone('Asia/Shanghai')
                        job_start_time = tz.localize(job.updated_at)
                    else:
                        job_start_time = job.updated_at
                    duration = (now - job_start_time).total_seconds()
                    hours = int(duration // 3600)
                    minutes = int((duration % 3600) // 60)
                    seconds = int(duration % 60)
                    print(f"运行时长: {hours}小时 {minutes}分钟 {seconds}秒")
                
                print(f"用户ID: {job.user_id}")
                print(f"账户ID: {job.account_id}")
                print(f"主题ID: {job.topic_id}")
                print("-" * 80)
                
                # 检查该任务的最近日志
                log_file = "work_log/non_human_detailed.log"
                if os.path.exists(log_file):
                    print(f"\n最近日志记录:")
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        job_logs = []
                        for line in lines:
                            if f"job_id: {job.id}" in line or f"job_id: {job.id}]" in line:
                                job_logs.append(line.strip())
                        
                        if job_logs:
                            # 显示最后5条日志
                            for log in job_logs[-5:]:
                                print(f"  {log}")
                        else:
                            print("  未找到该任务的日志记录")
            
            print("\n" + "=" * 80)
            logger.info(f"查询到 {len(processing_jobs)} 个正在运行的任务")
        
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（查询错误等）
        error_msg = f"查询失败: {e}"
        print(f"❌ {error_msg}")
        logger.exception(error_msg)

if __name__ == "__main__":
    check_running_jobs()

