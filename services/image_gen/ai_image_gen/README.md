# AI Image Generation Project

这是一个基于 Kafka 的 AI 图像生成项目，包含一个主服务（main service）和多个消费者工作节点（consumer workers）。

## 架构说明

Image Generation Service 使用统一的微服务架构规范：

- **统一配置**: 使用 `core.config.BaseConfig` 和 `PathManager`
- **统一日志**: 使用 `core.logging_config.setup_logging`
- **统一异常**: 使用 `core.exceptions` 中的异常类型
- **统一数据库**: 使用 `core.db` 中的模型和会话管理

### 配置说明

在 `.env` 文件或环境变量中配置以下参数：

- `KAFKA_BOOTSTRAP_SERVERS`: Kafka 服务器地址（默认: `10.147.20.156:9092`）
- `KAFKA_TOPICS`: Kafka 主题列表（逗号分隔）
- `MODEL_CACHE_DIR`: 模型缓存目录路径（可选，未指定时使用 `PathManager` 的默认路径）
- `DATABASE_URL`: 数据库连接 URL
- `BATCHSHORT_BASE_DIR`: 项目基础目录（可选，用于路径管理）

## 项目启动

### 1. 构建 Docker 镜像

在 `ai_image_gen` 目录下执行以下命令构建 Docker 镜像：

```bash
docker build -t ai_image_gen .
```

### 2. 启动 Main 服务 Docker

主服务负责接收图片上传请求，并将任务发送到 Kafka。只能有一个主服务实例。

```bash
docker-compose -f docker-compose.main.yml up -d
```

### 3. 启动 Worker 服务 Docker

工作节点负责从 Kafka 消费任务，生成图片，并将结果上传回主服务。在配置好 Kafka 后，工作节点可以在不同的机器上启动。

**注意：** 在启动 Worker 服务之前，请确保 Kafka 服务已正确配置并运行。

```bash
docker-compose -f docker-compose.worker.yml up -d
```

### 4. 挂载 Model Cache 目录

为了让工作节点能够访问 AI 模型，需要将模型缓存目录挂载到 Docker 容器中。在 `docker-compose.worker.yml` 中，`volumes` 部分已经配置了当前目录挂载到 `/app`。确保你的模型文件位于 `ai_image_gen/model_cache` 目录下，这样它们在容器内的路径就是 `/app/model_cache`。

例如，在 `docker-compose.worker.yml` 中：

```yaml
    volumes:
      - ./:/app
      # 如果模型缓存目录不在项目根目录，需要单独挂载
      # - /path/to/your/model_cache:/app/model_cache
```

## 项目工作流程

整个项目的图像生成流程如下：

1.  **上传图片到 Main 服务：** 用户通过 Main 服务的 API 接口上传原始图片。
2.  **Main 服务 -> Kafka：** Main 服务接收到图片后，将图片处理任务（例如，图片路径、生成参数等）作为消息发送到 Kafka 消息队列。
3.  **Kafka 消费：** 消费者工作节点（Consumer Worker）从 Kafka 订阅并消费这些图片处理任务消息。
4.  **工作节点调用 Main 接口上传图片到 Main 硬盘：** 消费者工作节点在完成图片生成后，会调用 Main 服务的接口，将生成的图片上传回 Main 服���的硬盘存储。
5.  **轮询 Main 服务检查处理状态：** 用户或客户端可以轮询 Main 服务的接口，查询特定图片生成任务的处理状态，直到任务完成并获取生成的图片。