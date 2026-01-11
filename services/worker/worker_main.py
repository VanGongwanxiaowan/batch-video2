"""Celery Worker 主入口

使用 Celery 替代 APScheduler + ThreadPoolExecutor 架构。
启动 Celery Worker 来处理异步任务。
"""
import sys
from pathlib import Path

# 路径设置（在导入本地模块之前）
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.config import get_celery_broker_url, get_celery_result_backend
from core.logging_config import setup_logging

# 配置日志记录器
logger = setup_logging("worker.main")


def main():
    """Celery Worker 主入口

    使用命令行参数启动 Celery Worker：
    - worker: 启动 worker 进程
    - beat: 启动 beat 调度器（定时任务）
    - flower: 启动 flower 监控界面
    """
    logger.info("[main] BatchShort Celery Worker")
    logger.info(f"[main] Broker: {get_celery_broker_url()}")
    logger.info(f"[main] Backend: {get_celery_result_backend()}")

    # 导入 Celery 应用
    from services.worker.tasks import app

    # 启动 Celery Worker
    # 使用命令行方式启动，支持更多参数
    from celery.bin import worker

    # 创建 worker 实例
    worker = worker.worker(app=app)

    # 配置 worker 参数
    worker_params = {
        # 日志配置
        'loglevel': 'info',
        'traceback': True,

        # 并发配置
        'concurrency': 1,  # 默认并发数，可通过命令行参数覆盖

        # 队列配置
        'queues': ('video_processing', 'maintenance', 'celery'),

        # 性能优化
        'prefetch_multiplier': 1,  # 预取倍数
        'max_tasks_per_child': 100,  # 每个 worker 处理任务数后重启

        # 任务配置
        'task_time_limit': 3600,  # 1小时硬限制
        'task_soft_time_limit': 3300,  # 55分钟软限制

        # 事件配置（用于监控）
        'events': True,

        # 其他
        'without_gossip': False,
        'without_mingle': False,
        'without_heartbeat': False,
    }

    logger.info(f"[main] Worker 配置: {worker_params}")

    # 启动 worker
    # 这会阻塞直到 worker 被停止
    worker.run(**worker_params)


def start_beat():
    """启动 Celery Beat 调度器

    用于处理定时任务，如：
    - 清理超时任务
    - 清理旧任务
    - 健康检查
    """
    logger.info("[beat] BatchShort Celery Beat")

    # 导入 Celery 应用
    from services.worker.tasks import app

    # 启动 Beat
    from celery.bin import beat

    beat_instance = beat.beat(app=app)

    beat_params = {
        'loglevel': 'info',
        'traceback': True,
    }

    logger.info("[beat] Beat 配置: scheduler=redis")
    beat_instance.run(**beat_params)


def start_flower(port: int = 5555):
    """启动 Flower 监控界面

    Args:
        port: Flower 服务端口，默认 5555
    """
    logger.info(f"[flower] BatchShort Celery Flower on port {port}")

    # 导入 Celery 应用
    from services.worker.tasks import app

    # 启动 Flower
    from flower import command as flower_command

    flower_params = {
        'broker': get_celery_broker_url(),
        'port': port,
        'basic_auth': 'admin:admin',  # 默认认证信息，生产环境应修改
    }

    logger.info(f"[flower] Flower 配置: {flower_params}")

    # Flower 启动
    flower_command.start_flower(**flower_params)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='BatchShort Celery Worker')
    parser.add_argument(
        'command',
        choices=['worker', 'beat', 'flower'],
        help='启动命令: worker(工作进程), beat(定时任务), flower(监控)'
    )
    parser.add_argument(
        '--concurrency',
        type=int,
        default=1,
        help='Worker 并发数 (默认: 1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5555,
        help='Flower 服务端口 (默认: 5555)'
    )
    parser.add_argument(
        '--loglevel',
        type=str,
        default='info',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        help='日志级别 (默认: info)'
    )

    args = parser.parse_args()

    # 根据命令启动相应服务
    if args.command == 'worker':
        logger.info(f"[main] 启动 Celery Worker，并发数: {args.concurrency}")
        # 设置环境变量供 Celery 使用
        import os
        os.environ['WORKER_CONCURRENCY'] = str(args.concurrency)
        main()

    elif args.command == 'beat':
        logger.info("[main] 启动 Celery Beat")
        start_beat()

    elif args.command == 'flower':
        logger.info(f"[main] 启动 Celery Flower，端口: {args.port}")
        start_flower(port=args.port)
