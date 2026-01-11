#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询任务状态的脚本
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from typing import Optional

import pytz
from db.models import Job, get_beijing_time
from db.session import db_session
from sqlalchemy.orm import Session

from core.logging_config import setup_logging

# 初始化日志记录器（用于错误和重要操作记录）
logger = setup_logging("worker.check_job_status", log_to_file=False)

def check_job_status(title: Optional[str] = None, job_id: Optional[int] = None) -> None:
    """
    查询任务状态
    
    Args:
        title: 任务标题（可选）
        job_id: 任务ID（可选）
    """
    try:
        with db_session() as db:
            # 查询任务
            if job_id:
                job = db.query(Job).filter(Job.id == job_id, Job.deleted_at == None).first()
            elif title:
                # 查找包含标题的任务
                job = db.query(Job).filter(
                    Job.title.like(f"%{title}%"),
                    Job.deleted_at == None
                ).order_by(Job.updated_at.desc()).first()
            else:
                error_msg = "请提供任务ID或标题"
                print(error_msg)
                logger.warning(error_msg)
                return
            
            if not job:
                error_msg = f"未找到任务: {title or job_id}"
                print(f"❌ {error_msg}")
                logger.warning(error_msg)
                return
            
            print("=" * 80)
            print(f"任务信息:")
            print(f"  任务ID: {job.id}")
            print(f"  标题: {job.title}")
            print(f"  状态: {job.status}")
            print(f"  状态详情: {job.status_detail}")
            print(f"  创建时间: {job.created_at}")
            print(f"  更新时间: {job.updated_at}")
            
            # 计算处理时长
            if job.updated_at:
                now = get_beijing_time()
                # 处理时区问题
                if job.updated_at.tzinfo is None:
                    # 如果数据库中的时间是naive，假设是北京时间
                    tz = pytz.timezone('Asia/Shanghai')
                    job_updated_at = tz.localize(job.updated_at)
                else:
                    job_updated_at = job.updated_at
                duration = (now - job_updated_at).total_seconds()
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                seconds = int(duration % 60)
                print(f"  已处理时长: {hours}小时 {minutes}分钟 {seconds}秒")
            
            print(f"  用户ID: {job.user_id}")
            print(f"  账户ID: {job.account_id}")
            print(f"  主题ID: {job.topic_id}")
            print(f"  语言ID: {job.language_id}")
            print(f"  语音ID: {job.voice_id}")
            print(f"  运行顺序: {job.runorder}")
            print(f"  是否横屏: {job.is_horizontal}")
            
            if job.job_result_key:
                import json
                try:
                    result_data = json.loads(job.job_result_key)
                    print(f"  结果文件:")
                    for key, value in result_data.items():
                        print(f"    {key}: {value}")
                except (json.JSONDecodeError, TypeError) as e:
                    # JSON解析失败，直接显示原始字符串
                    print(f"  结果文件: {job.job_result_key}")
            
            print("=" * 80)
            logger.info(f"查询任务状态: ID={job.id}, 标题={job.title}, 状态={job.status}")
        
        # 检查日志文件（在db会话外，因为只是读取文件）
        log_file = "work_log/non_human_detailed.log"
        if os.path.exists(log_file):
            print(f"\n正在检查日志文件: {log_file}")
            print(f"查找任务 {job.id} 的日志记录...")
            
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                job_logs = []
                for line in lines:
                    if f"job_id: {job.id}" in line or f"job_id: {job.id}]" in line:
                        job_logs.append(line.strip())
                
                if job_logs:
                    print(f"\n找到 {len(job_logs)} 条日志记录:")
                    print("-" * 80)
                    # 显示最近的20条日志
                    for log in job_logs[-20:]:
                        print(log)
                    print("-" * 80)
                else:
                    print("未找到该任务的日志记录")
        
        # 检查worker详细日志
        worker_log_file = "work_log/worker_detailed.log"
        if os.path.exists(worker_log_file):
            print(f"\n正在检查worker日志文件: {worker_log_file}")
            print(f"查找任务 {job.id} 的日志记录...")
            
            with open(worker_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                job_logs = []
                for line in lines:
                    if f"job_id: {job.id}" in line or f"job_id: {job.id}]" in line:
                        job_logs.append(line.strip())
                
                if job_logs:
                    print(f"\n找到 {len(job_logs)} 条worker日志记录:")
                    print("-" * 80)
                    # 显示最近的20条日志
                    for log in job_logs[-20:]:
                        print(log)
                    print("-" * 80)
        
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（查询错误等）
        error_msg = f"查询失败: {e}"
        print(f"❌ {error_msg}")
        logger.exception(error_msg)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="查询任务状态")
    parser.add_argument("--title", type=str, help="任务标题（支持部分匹配）")
    parser.add_argument("--job-id", type=int, help="任务ID")
    
    args = parser.parse_args()
    
    if not args.title and not args.job_id:
        # 默认查询"知养科学坊 58"
        default_msg = "未指定参数，查询默认任务: 知养科学坊 58"
        print(default_msg)
        logger.info(default_msg)
        check_job_status(title="知养科学坊 58")
    else:
        logger.info(f"查询任务: title={args.title}, job_id={args.job_id}")
        check_job_status(title=args.title, job_id=args.job_id)

