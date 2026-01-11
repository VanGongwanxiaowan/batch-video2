#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动触发任务处理的脚本
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse

from db.models import Job, get_beijing_time
from db.session import db_session
from worker_main import _process_single_job

from core.logging_config import setup_logging

# 初始化日志记录器（用于错误和重要操作记录）
logger = setup_logging("worker.manual_process_job", log_to_file=False)

def manual_process_job(job_id: int) -> None:
    """
    手动触发处理指定任务
    """
    try:
        with db_session() as db:
            # 检查任务是否存在
            job = db.query(Job).filter(Job.id == job_id, Job.deleted_at == None).first()
            if not job:
                error_msg = f"任务 {job_id} 不存在或已删除"
                print(f"❌ {error_msg}")
                logger.warning(error_msg)
                return
            
            print("=" * 80)
            print(f"任务信息:")
            print(f"  任务ID: {job.id}")
            print(f"  标题: {job.title}")
            print(f"  当前状态: {job.status}")
            print(f"  创建时间: {job.created_at}")
            print(f"  更新时间: {job.updated_at}")
            print("=" * 80)
            
            if job.status == "处理中":
                print(f"⚠️  任务 {job_id} 已经在处理中，是否继续？")
                response = input("输入 'y' 继续，其他键取消: ")
                if response.lower() != 'y':
                    print("已取消")
                    return
            
            print(f"\n🚀 开始处理任务 {job_id}: {job.title}")
            print("-" * 80)
            logger.info(f"手动触发处理任务 {job_id}: {job.title}")
        
        # 调用处理函数（在db会话外，因为它会创建自己的会话）
        _process_single_job(job_id)
        
        print("\n" + "=" * 80)
        print("✅ 任务处理完成")
        print("=" * 80)
        logger.info(f"任务 {job_id} 处理完成")
        
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（任务处理错误等）
        error_msg = f"处理失败: {e}"
        print(f"❌ {error_msg}")
        logger.exception(error_msg)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="手动触发任务处理")
    parser.add_argument("--job-id", type=int, required=True, help="任务ID")
    
    args = parser.parse_args()
    manual_process_job(args.job_id)

