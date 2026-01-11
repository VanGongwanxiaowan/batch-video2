# Image Generation Service

AI 图像生成服务，基于 Kafka 的分布式图像生成系统。

## 概述

该服务包含两个主要组件：
- **API Service**: 接收图像生成请求，将任务发送到 Kafka 队列
- **Consumer Worker**: 从 Kafka 消费任务，执行图像生成，并将结果上传回 API Service

## 环境要求

- Python 3.8+
- Kafka 服务（已配置并运行）
- 模型文件（位于 `model_cache/` 目录）

## 配置

### 环境变量

在 `config/settings.py` 中配置以下参数：

- `KAFKA_BOOTSTRAP_SERVERS`: Kafka 服务器地址
- `KAFKA_TOPIC_PREFIX`: Kafka 主题前缀
- `MODEL_CACHE_DIR`: 模型缓存目录路径

### 模型文件

确保模型文件位于 `model_cache/` 目录下，例如：
- `model_cache/flux-1-dev/`
- `model_cache/stable-diffusion-v1-5/`

## 启动方式

### 方式一：使用 Docker（推荐）

#### 1. 构建镜像

```bash
cd services/image_gen/ai_image_gen
docker build -t ai_image_gen .
```

#### 2. 启动 API Service

```bash
docker-compose -f docker-compose.main.yml up -d
```

API Service 将在 `http://localhost:8000` 启动。

#### 3. 启动 Consumer Worker

```bash
docker-compose -f docker-compose.worker.yml up -d
```

**注意**: 在启动 Worker 之前，确保 Kafka 服务已正确配置并运行。

### 方式二：本地开发（Conda 环境）

#### 1. 激活 Conda 环境

```bash
conda activate <你的环境名>
```

#### 2. 安装依赖

```bash
cd services/image_gen/ai_image_gen
pip install -r requirements.txt
```

#### 3. 启动 API Service

```bash
python -m api_service.main
# 或
cd api_service
python main.py
```

API Service 将在 `http://localhost:8000` 启动。

#### 4. 启动 Consumer Worker

```bash
python -m consumer_worker.worker
# 或
cd consumer_worker
python worker.py
```

## API 文档

启动服务后，访问以下地址查看 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 主要 API 端点

### 提交图像生成任务

```bash
POST /generate_image
Content-Type: application/json

{
  "model_name": "flux-1-dev",
  "prompt": "a beautiful landscape",
  "negative_prompt": "blurry, low quality",
  "image_params": {
    "width": 1024,
    "height": 1024,
    "steps": 30
  },
  "loras": [],
  "user_id": "user123",
  "topic": "online_task"
}
```

### 检查任务状态

```bash
GET /check_status/{task_id}
```

### 获取生成的图像

```bash
GET /get_image/{task_id}
```

## 工作流程

1. **客户端提交任务**: 通过 API Service 提交图像生成请求
2. **任务入队**: API Service 将任务发送到 Kafka 队列
3. **Worker 消费**: Consumer Worker 从 Kafka 消费任务
4. **图像生成**: Worker 使用 AI 模型生成图像
5. **结果上传**: Worker 将生成的图像上传回 API Service
6. **状态查询**: 客户端轮询 API Service 检查任务状态

## 日志

日志文件位于项目根目录的 `logs/` 目录下：
- `logs/ai_image_gen.api.log`: API Service 日志
- `logs/ai_image_gen.consumer_worker.log`: Consumer Worker 日志

## 故障排查

### Kafka 连接失败

- 检查 Kafka 服务是否运行
- 验证 `KAFKA_BOOTSTRAP_SERVERS` 配置是否正确
- 检查网络连接

### 模型文件未找到

- 确认模型文件位于 `model_cache/` 目录
- 检查 Docker 挂载配置（如果使用 Docker）

### 任务处理失败

- 查看 Worker 日志文件
- 检查模型文件完整性
- 验证 GPU/CPU 资源是否充足

## 与 Worker 服务的关系

Image Generation Service 是独立的服务，与 Worker 服务（视频生成）无直接依赖关系。两个服务可以独立运行和扩展。

