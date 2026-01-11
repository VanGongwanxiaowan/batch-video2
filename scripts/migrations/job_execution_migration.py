"""数据库迁移脚本：Job 表拆分为 Job + JobExecution

此脚本将现有的 Job 表拆分为两个表：
1. Job 表：只存储任务配置（不包含运行时状态）
2. JobExecution 表：存储每次执行的记录

迁移步骤：
1. 创建 job_executions 表
2. 从现有 jobs 表数据创建初始 JobExecution 记录
3. 删除 jobs 表中的运行时字段（status, status_detail, job_result_key）
4. 创建新的索引

使用方法:
    python -m scripts.migrations.job_execution_migration --dry-run  # 预览
    python -m scripts.migrations.job_execution_migration --execute  # 执行迁移
"""
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytz
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import settings
from core.logging_config import setup_logging

logger = setup_logging("migrations.job_execution")


def get_beijing_time() -> datetime:
    """获取北京时间"""
    tz = pytz.timezone("Asia/Shanghai")
    return datetime.now(tz)


def create_job_executions_table(engine):
    """创建 job_executions 表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS job_executions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        job_id INT NOT NULL,
        status ENUM('PENDING', 'RUNNING', 'SUCCESS', 'FAILED') DEFAULT 'PENDING' NOT NULL,
        status_detail VARCHAR(500) DEFAULT '',
        result_key TEXT NULL,
        worker_hostname VARCHAR(255) NULL,
        started_at DATETIME NULL,
        finished_at DATETIME NULL,
        retry_count INT DEFAULT 0 NOT NULL,
        error_message TEXT NULL,
        execution_metadata JSON NOT NULL DEFAULT (JSON_OBJECT()),
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        INDEX idx_job_id (job_id),
        INDEX idx_status (status),
        INDEX idx_job_status (job_id, status),
        INDEX idx_status_created (status, created_at),
        INDEX idx_worker_status (worker_hostname, status),
        INDEX idx_created_at (created_at),
        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
    logger.info("[create_job_executions_table] job_executions 表已创建")


def migrate_existing_data(engine, dry_run=True):
    """迁移现有数据：从 jobs 创建 JobExecution 记录

    状态映射：
    - 待处理 -> PENDING
    - 处理中 -> RUNNING
    - 已完成 -> SUCCESS
    - 失败 -> FAILED
    """
    status_map = {
        "待处理": "PENDING",
        "处理中": "RUNNING",
        "已完成": "SUCCESS",
        "失败": "FAILED",
    }

    # 查询所有现有 Job
    select_jobs_sql = """
    SELECT id, status, status_detail, job_result_key, created_at, updated_at
    FROM jobs
    WHERE deleted_at IS NULL
    ORDER BY id;
    """

    with engine.connect() as conn:
        result = conn.execute(text(select_jobs_sql))
        jobs = result.fetchall()

    if not jobs:
        logger.info("[migrate_existing_data] 没有需要迁移的 Job 数据")
        return 0

    logger.info(f"[migrate_existing_data] 找到 {len(jobs)} 个 Job 需要迁移")

    insert_count = 0
    for job in jobs:
        job_id = job[0]
        old_status = job[1]
        status_detail = job[2] or ""
        result_key = job[3]
        created_at = job[4]
        updated_at = job[5]

        # 映射状态
        new_status = status_map.get(old_status, "PENDING")

        # 创建 JobExecution 记录
        insert_sql = """
        INSERT INTO job_executions (
            job_id, status, status_detail, result_key,
            created_at, updated_at, started_at, finished_at,
            retry_count, execution_metadata
        ) VALUES (
            :job_id, :status, :status_detail, :result_key,
            :created_at, :updated_at, :started_at, :finished_at,
            :retry_count, :execution_metadata
        )
        """

        params = {
            "job_id": job_id,
            "status": new_status,
            "status_detail": status_detail,
            "result_key": result_key,
            "created_at": created_at,
            "updated_at": updated_at,
            "started_at": created_at if new_status in ["RUNNING", "SUCCESS", "FAILED"] else None,
            "finished_at": updated_at if new_status in ["SUCCESS", "FAILED"] else None,
            "retry_count": 0,
            "execution_metadata": "{}",
        }

        if dry_run:
            logger.info(
                f"[DRY RUN] 将为 Job #{job_id} 创建 JobExecution: "
                f"status={new_status} (原状态: {old_status})"
            )
            insert_count += 1
        else:
            with engine.connect() as conn:
                conn.execute(text(insert_sql), params)
                conn.commit()
            insert_count += 1

    if dry_run:
        logger.info(f"[migrate_existing_data] [DRY RUN] 将创建 {insert_count} 条 JobExecution 记录")
    else:
        logger.info(f"[migrate_existing_data] 已创建 {insert_count} 条 JobExecution 记录")

    return insert_count


def drop_job_runtime_columns(engine, dry_run=True):
    """删除 jobs 表中的运行时字段"""
    columns_to_drop = ["status", "status_detail", "job_result_key"]

    for column in columns_to_drop:
        alter_sql = f"ALTER TABLE jobs DROP COLUMN {column};"

        if dry_run:
            logger.info(f"[DRY RUN] 将删除 jobs.{column} 列")
        else:
            try:
                with engine.connect() as conn:
                    conn.execute(text(alter_sql))
                    conn.commit()
                logger.info(f"[drop_job_runtime_columns] 已删除 jobs.{column} 列")
            except Exception as e:
                logger.error(f"[drop_job_runtime_columns] 删除 jobs.{column} 失败: {e}")


def update_job_indexes(engine, dry_run=True):
    """更新 jobs 表的索引"""
    # 旧的索引需要删除（因为包含 status 字段）
    old_indexes = [
        "idx_status_deleted_runorder_id",
    ]

    for index_name in old_indexes:
        drop_index_sql = f"DROP INDEX {index_name} ON jobs;"
        if dry_run:
            logger.info(f"[DRY RUN] 将删除索引 jobs.{index_name}")
        else:
            try:
                with engine.connect() as conn:
                    conn.execute(text(drop_index_sql))
                    conn.commit()
                logger.info(f"[update_job_indexes] 已删除索引 jobs.{index_name}")
            except Exception as e:
                logger.warning(f"[update_job_indexes] 删除索引 jobs.{index_name} 失败（可能不存在）: {e}")

    # 创建新的索引
    new_indexes = [
        "CREATE INDEX idx_deleted_runorder_id ON jobs(deleted_at, runorder, id);",
    ]

    for index_sql in new_indexes:
        if dry_run:
            logger.info(f"[DRY RUN] 将创建新索引")
        else:
            try:
                with engine.connect() as conn:
                    conn.execute(text(index_sql))
                    conn.commit()
                logger.info(f"[update_job_indexes] 已创建新索引")
            except Exception as e:
                logger.warning(f"[update_job_indexes] 创建索引失败（可能已存在）: {e}")


def run_migration(dry_run=True):
    """执行完整的迁移流程"""
    logger.info("=" * 60)
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Job 表拆分迁移开始")
    logger.info("=" * 60)

    # 创建数据库连接
    database_url = str(settings.DATABASE_URL).replace("+aiomysql", "+pymysql")
    engine = create_engine(database_url, echo=False)

    try:
        # 步骤 1: 创建 job_executions 表
        logger.info("\n步骤 1: 创建 job_executions 表")
        create_job_executions_table(engine)

        # 步骤 2: 迁移现有数据
        logger.info("\n步骤 2: 迁移现有数据")
        migrate_existing_data(engine, dry_run=dry_run)

        # 步骤 3: 删除 jobs 表的运行时字段
        logger.info("\n步骤 3: 删除 jobs 表的运行时字段")
        drop_job_runtime_columns(engine, dry_run=dry_run)

        # 步骤 4: 更新索引
        logger.info("\n步骤 4: 更新索引")
        update_job_indexes(engine, dry_run=dry_run)

        logger.info("\n" + "=" * 60)
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}迁移完成!")
        logger.info("=" * 60)

    except Exception as e:
        logger.exception("迁移失败: %s", e)
        raise


def rollback_migration():
    """回滚迁移（慎用！）"""
    logger.warning("=" * 60)
    logger.warning("开始回滚迁移...")
    logger.warning("=" * 60)

    database_url = str(settings.DATABASE_URL).replace("+aiomysql", "+pymysql")
    engine = create_engine(database_url, echo=False)

    try:
        # 步骤 1: 删除 job_executions 表
        logger.info("步骤 1: 删除 job_executions 表")
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS job_executions;"))
            conn.commit()
        logger.info("job_executions 表已删除")

        # 步骤 2: 恢复 jobs 表字段
        logger.info("步骤 2: 恢复 jobs 表字段")
        alter_sqls = [
            "ALTER TABLE jobs ADD COLUMN status ENUM('待处理', '处理中', '已完成', '失败') DEFAULT '待处理' NOT NULL;",
            "ALTER TABLE jobs ADD COLUMN status_detail VARCHAR(255) DEFAULT '';",
            "ALTER TABLE jobs ADD COLUMN job_result_key TEXT NULL;",
        ]

        for sql in alter_sqls:
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
        logger.info("jobs 表字段已恢复")

        # 步骤 3: 恢复索引
        logger.info("步骤 3: 恢复索引")
        index_sql = "CREATE INDEX idx_status_deleted_runorder_id ON jobs(status, deleted_at, runorder, id);"
        with engine.connect() as conn:
            conn.execute(text(index_sql))
            conn.commit()
        logger.info("索引已恢复")

        logger.info("=" * 60)
        logger.info("回滚完成!")
        logger.warning("注意：已删除的 job_executions 数据无法恢复！")
        logger.warning("如果需要，请从备份中恢复。")
        logger.warning("=" * 60)

    except Exception as e:
        logger.exception("回滚失败: %s", e)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Job 表拆分迁移脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 预览迁移（不执行）
  python -m scripts.migrations.job_execution_migration --dry-run

  # 执行迁移
  python -m scripts.migrations.job_execution_migration --execute

  # 回滚迁移（慎用！）
  python -m scripts.migrations.job_execution_migration --rollback
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览迁移，不执行实际操作"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行迁移"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="回滚迁移（慎用！）"
    )

    args = parser.parse_args()

    if args.rollback:
        confirm = input("确认要回滚迁移吗？这将删除 job_executions 表！(yes/no): ")
        if confirm.lower() == "yes":
            rollback_migration()
        else:
            logger.info("回滚已取消")
    elif args.execute:
        run_migration(dry_run=False)
    else:
        # 默认执行 dry-run
        run_migration(dry_run=True)


if __name__ == "__main__":
    main()
