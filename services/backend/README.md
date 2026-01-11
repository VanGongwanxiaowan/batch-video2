## Backend 服务说明

重构后 Backend 服务已迁移到 `services/backend/` 目录，并使用统一的 `core` 配置与日志体系。

### 架构说明

Backend 服务使用统一的微服务架构规范：

- **统一配置**: 使用 `core.config.BaseConfig` 和 `PathManager`
- **统一日志**: 使用 `core.logging_config.setup_logging`
- **统一异常**: 使用 `core.exceptions` 中的异常类型
- **统一数据库**: 使用 `core.db` 中的模型和会话管理

### 一、在本地（conda 环境）启动 Backend

1. **进入项目根目录**

```bash
cd /Users/gongfan/Desktop/公司项目/batchshort1_副本
```

2. **激活你的 conda 环境**（示例）

```bash
conda activate <你的环境名>
```

3. **安装依赖（如未安装）**

```bash
pip install -r services/backend/requirements.txt  # 若无单独requirements，可用项目根的依赖清单
```

4. **启动 Backend 服务**

方式一（推荐，从项目根目录启动模块）：

```bash
python -m services.backend.api_main
```

方式二（进入 backend 目录启动）：

```bash
cd services/backend
python api_main.py
```

服务默认监听：`http://0.0.0.0:8006`

5. **访问接口文档**

```text
http://127.0.0.1:8006/v2/docs
```

### 二、Backend 与 Worker 的关系

- Backend 负责：
  - 账号 / 话题 / 语种 / 音色等基础配置的增删改查；
  - 创建 Job 任务（写入数据库）；
  - 提供任务状态、结果查询等 HTTP API。
- Worker（`services/worker/worker_main.py`）负责：
  - 轮询数据库中的待处理 Job；
  - 调用 TTS / 图像 / 视频 / 数字人等子服务生成最终视频；
  - 更新 Job 状态和结果字段（如 `job_result_key`），供 Backend 查询。

只要 Backend 和 Worker 使用相同的数据库配置（`core/db` + `core/config`），
就可以在 **同一套 Job 数据** 上协同工作：  
Frontend → Backend 创建任务 → Worker 消费任务并写入结果 → Backend API 提供查询。
