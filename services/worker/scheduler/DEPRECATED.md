# Scheduler 模块 - 已废弃

> **注意**: 此模块已被 Celery 分布式任务队列替代，保留仅为向后兼容。

## 废弃说明

从版本 2.0.0 开始，BatchShort 系统已从 APScheduler + ThreadPoolExecutor 架构迁移到 Celery 分布式任务队列。

### 旧架构 (已废弃)

```
APScheduler + ThreadPoolExecutor
├── JobScheduler          # 任务调度器
├── JobRetryHandler       # 重试处理器
└── JobStatusManager      # 状态管理器
```

### 新架构 (Celery)

```
Celery 分布式任务队列
├── services/worker/tasks.py        # Celery 任务定义
├── core/config/celery_config.py    # Celery 配置
└── worker_main.py                  # Celery Worker 入口
```

## 迁移对照表

| 旧组件 | 新组件 | 说明 |
|-------|-------|------|
| JobScheduler | Celery Worker | 任务调度和执行 |
| JobRetryHandler | Celery 自动重试 | 任务重试机制 |
| JobStatusManager | Celery 结果存储 | 任务状态管理 |
| APScheduler | Celery Beat | 定时任务调度 |

## 功能对比

| 功能 | 旧架构 | 新架构 |
|------|-------|-------|
| 任务分发 | 轮询数据库 | 事件驱动 (Celery) |
| 响应延迟 | 轮询间隔 (~60秒) | 实时 (<1秒) |
| 并发控制 | ThreadPoolExecutor | Celery Worker Pool |
| 重试机制 | 自定义实现 | Celery 内置 |
| 监控 | 日志文件 | Flower Web UI |
| 可扩展性 | 单机 | 分布式 |
| 可靠性 | 进程崩溃丢失任务 | 任务持久化 |

## 使用新架构

### 启动 Worker

```bash
# 旧方式 (已废弃)
python worker_main.py

# 新方式
python worker_main.py worker --concurrency 2
```

### 提交任务

```python
# 旧方式 (已废弃)
job = Job(id=123, status="待处理")
db.add(job)
db.commit()
# 等待 JobScheduler 轮询...

# 新方式
from services.worker.tasks import process_video_job
task = process_video_job.delay(job_id=123)
# 任务立即提交到队列
```

### 查看任务状态

```python
# 旧方式 (已废弃)
job = db.query(Job).filter(Job.id == 123).first()
print(job.status)

# 新方式
from celery.result import AsyncResult
task = AsyncResult(task_id)
print(task.state)
print(task.result)
```

## 废弃时间表

- **2024-12**: 新架构实现完成
- **2025-01**: 旧架构标记为废弃
- **2025-06**: 旧架构代码移除计划

## 兼容性说明

为了平滑迁移，旧代码暂时保留，但不再维护：

1. **向后兼容**: 旧 API 仍然可用，但会记录警告日志
2. **降级方案**: 如果 Celery 不可用，系统会自动降级到轮询模式
3. **迁移期**: 2025年1月-6月为迁移期

## 迁移指南

详见项目文档: `/docs/celery-migration-guide.md`

## 联系方式

如有疑问，请联系开发团队。
