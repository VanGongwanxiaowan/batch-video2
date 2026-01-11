# BatchVideo - 批处理短视频生成系统

> 一个基于微服务架构的企业级短视频生成平台，支持从文本、图像和音频自动生成高质量短视频内容，实现用户输入文字，自动生成视频和数字人视频，并支持多种语言的 TTS 服务，支持批量任务处理，支持智能文本分割，支持字幕自动生成，支持视频后处理，支持云端存储集成，支持完善的监控体系。注意：为了避免平台检测纯AI视频 需要支持按照一定比例去为改分镜生成视频 或者 匹配一些随机的动态视频如风景动物。

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68%2B-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-support-blue)](https://www.docker.com/)

---

## 目录

- [系统概述](#系统概述)
- [作品展示](#作品展示)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [数据模型设计](#数据模型设计)
- [完整代码逻辑流程](#完整代码逻辑流程)
- [业务流程详解](#业务流程详解)
- [API 接口文档](#api-接口文档)
- [Pipeline 处理系统](#pipeline-处理系统)
- [Celery 任务队列](#celery-任务队列)
- [监控与可观测性](#监控与可观测性)
- [安全功能](#安全功能)
- [高可用性部署](#高可用性部署)
- [开发指南](#开发指南)
- [部署指南](#部署指南)
- [故障排查](#故障排查)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

- [系统概述](#系统概述)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [数据模型设计](#数据模型设计)
- [业务流程详解](#业务流程详解)
- [API 接口文档](#api-接口文档)
- [Pipeline 处理系统](#pipeline-处理系统)
- [Celery 任务队列](#celery-任务队列)
- [监控与可观测性](#监控与可观测性)
- [安全功能](#安全功能)
- [高可用性部署](#高可用性部署)
- [开发指南](#开发指南)
- [部署指南](#部署指南)
- [故障排查](#故障排查)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 系统概述

BatchVideo 是一个功能完整的批处理短视频生成系统，采用现代化的微服务架构设计。系统支持用户输入文本内容，通过 AI 技术自动生成包含语音、字幕、图像和视频的完整短视频。

### 主要功能

- **多模态内容生成**：支持文本转语音（TTS）、AI 图像生成、视频合成
- **数字人视频合成**：集成数字人技术，生成真实感视频内容
- **多语言支持**：支持多种语言的 TTS 服务
- **批量任务处理**：基于 Celery 的分布式任务队列，支持高并发处理
- **智能文本分割**：自动将长文本分割为适合视频的片段
- **字幕自动生成**：根据音频时长自动生成 SRT 格式字幕
- **视频后处理**：支持水印、Logo 添加、转场效果等
- **云端存储集成**：支持阿里云 OSS 等对象存储服务
- **完善的监控体系**：集成 Prometheus、Grafana 实现全方位监控

---

## 作品展示

以下是通过本系统生成的视频 YouTube 频道示例：

| 频道名称 | 频道链接 | 内容类型 |
|---------|---------|---------|
| 明心养生堂 | [https://www.youtube.com/@明心养生堂](https://www.youtube.com/@%E6%98%8E%E5%BF%83%E5%85%BB%E7%94%9F%E5%A0%82) | 养生健康类视频 |
| 暖心时光屋 | [https://www.youtube.com/@暖心时光屋](https://www.youtube.com/@%E6%9A%96%E5%BF%83%E6%97%B6%E5%85%89%E5%B1%8B) | 生活情感类视频 |
| 时光忆暖居 | [https://www.youtube.com/@时光忆暖居](https://www.youtube.com/@%E6%97%B6%E5%85%89%E5%BF%86%E6%9A%96%E5%B1%85) | 回忆温情类视频 |


---

## 核心特性

### 1. 微服务架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   前端应用    │    │   后端API   │    │   数据库     │
│   Vue.js    │◄──►│   FastAPI   │◄──►│   MySQL     │
└─────────────┘    └──────┬──────┘    └─────────────┘
                          │
                          │
                   ┌──────┴──────┐
                   │             │
            ┌──────▼──────┐ ┌────▼─────┐
            │  Celery     │ │  Redis   │
            │   Worker    │ │  缓存    │
            └─────────────┘ └──────────┘
                   │
            ┌──────┴──────────────────┐
            │                         │
     ┌──────▼──────┐          ┌──────▼──────┐
     │   TTS服务   │          │  AI图像生成 │
     │ (SeedVC)   │          │  (Flux)     │
     └─────────────┘          └─────────────┘
```

### 2. 任务执行流程

系统采用 Pipeline 模式设计，将视频生成分解为多个可组合的步骤：

1. **TTS 生成步骤 (TTSGenerationStep)**
   - 调用 TTS 服务将文本转换为语音
   - 支持多种 TTS 引擎（SeedVC、Azure TTS）
   - 自动提取音频时长和元数据

2. **字幕生成步骤 (SubtitleGenerationStep)**
   - 根据音频时长生成 SRT 格式字幕
   - 自动分割文本片段
   - 计算每个片段的时间戳

3. **文本分割步骤 (TextSplitStep)**
   - 智能分割长文本为适合视频的片段
   - 考虑语速、停顿等因素
   - 为每个片段生成图像提示词

4. **图像生成步骤 (ImageGenerationStep)**
   - 使用 Flux AI 模型生成图像
   - 支持批量生成和重试机制
   - 根据文本内容自动生成提示词

5. **视频合成步骤 (VideoCompositionStep)**
   - 使用 FFmpeg 合成视频
   - 支持横竖屏切换
   - 添加转场效果和背景音乐

6. **数字人步骤 (DigitalHumanStep)**（可选）
   - 集成数字人视频合成
   - 语音同步和表情控制
   - 生成真实感数字人视频

7. **后处理步骤 (PostProcessingStep)**
   - 添加 Logo 和水印
   - 视频压缩和优化
   - 格式转换

8. **上传步骤 (UploadStep)**
   - 上传视频到 OSS
   - 生成签名 URL
   - 更新任务状态

### 3. 数据库设计原则

系统采用任务配置与执行分离的设计：

- **Job 表**：存储任务配置和定义（模板）
- **JobExecution 表**：存储每次执行的记录（状态）
- **JobSplit 表**：存储任务分割片段

这种设计支持：
- 任务可多次执行
- 完整的历史追溯
- 清晰的职责分离
- 性能优化

---

## 系统架构

### 整体架构图

```
┌──────────────────────────────────────────────────────────────────┐
│                         前端层 (Frontend)                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │           Vue.js 单页应用 (SPA)                             │  │
│  │  - 任务管理界面                                              │  │
│  │  - 实时状态显示                                              │  │
│  │  - 视频预览播放                                              │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │ HTTP/WebSocket
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                       API 网关层 (Gateway)                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Nginx 反向代理                           │  │
│  │  - 负载均衡                                                  │  │
│  │  - SSL 终止                                                 │  │
│  │  - 静态文件服务                                              │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                      应用服务层 (Services)                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │   后端服务        │  │   Worker 服务     │  │  图像生成服务   │  │
│  │   (FastAPI)      │  │   (Celery)       │  │  (Flux API)    │  │
│  │                  │  │                  │  │                │  │
│  │ - 用户认证        │  │ - 任务调度        │  │ - AI 绘图      │  │
│  │ - 任务管理        │  │ - Pipeline 执行   │  │ - 图像处理     │  │
│  │ - 资源管理        │  │ - 文件处理        │  │ - 批量生成     │  │
│  │ - 状态查询        │  │ - 结果上传        │  │                │  │
│  └──────────────────┘  └──────────────────┘  └────────────────┘  │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │   TTS 服务       │  │  数字人服务       │  │  监控服务      │  │
│  │                  │  │                  │  │                │  │
│  │ - SeedVC TTS    │  │ - 视频合成        │  │ - Prometheus  │  │
│  │ - Azure TTS     │  │ - 语音同步        │  │ - Grafana     │  │
│  │ - 音频处理       │  │ - 表情控制        │  │ - AlertManager│  │
│  └──────────────────┘  └──────────────────┘  └────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                       数据层 (Data Layer)                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │   MySQL 数据库   │  │   Redis 缓存     │  │   OSS 存储     │  │
│  │                  │  │                  │  │                │  │
│  │ - 用户数据        │  │ - 会话存储        │  │ - 视频文件     │  │
│  │ - 任务配置        │  │ - 任务队列        │  │ - 图像文件     │  │
│  │ - 执行记录        │  │ - 结果缓存        │  │ - 音频文件     │  │
│  │ - 资源配置        │  │ - 分布式锁        │  │ - 字幕文件     │  │
│  └──────────────────┘  └──────────────────┘  └────────────────┘  │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐                       │
│  │  Kafka 消息队列  │  │  本地文件系统     │                       │
│  │                  │  │                  │                       │
│  │ - 任务分发        │  │ - 临时文件        │                       │
│  │ - 事件通知        │  │ - 缓存文件        │                       │
│  │ - 日志收集        │  │ - 工作目录        │                       │
│  └──────────────────┘  └──────────────────┘                       │
└──────────────────────────────────────────────────────────────────┘
```

### 目录结构

```
new_project/
├── core/                          # 核心库模块
│   ├── clients/                   # 服务客户端
│   │   ├── __init__.py
│   │   ├── base_client.py         # 基础客户端类
│   │   ├── tts_client.py          # TTS 服务客户端
│   │   ├── image_client.py        # 图像生成客户端
│   │   └── flux_client.py         # Flux 模型客户端
│   ├── config/                    # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py            # 应用配置
│   │   ├── constants.py           # 配置常量
│   │   ├── paths.py               # 路径管理
│   │   ├── validation.py          # 配置验证
│   │   ├── api.py                 # API 端点常量
│   │   ├── status.py              # 状态枚举
│   │   └── celery_config.py       # Celery 配置
│   ├── db/                        # 数据库层
│   │   ├── __init__.py
│   │   ├── models.py              # 数据模型定义
│   │   ├── session.py             # 数据库会话
│   │   └── repositories/          # 数据仓库
│   ├── interfaces/                # 接口定义
│   │   ├── service_interfaces.py  # 服务接口
│   │   └── step_factory.py        # 步骤工厂接口
│   ├── utils/                     # 工具函数
│   │   ├── __init__.py
│   │   ├── retry.py               # 重试机制
│   │   ├── async_utils.py         # 异步工具
│   │   ├── time_utils.py          # 时间工具
│   │   ├── ffmpeg_utils.py        # FFmpeg 工具
│   │   └── schema_converter.py    # 模型转换器
│   ├── monitoring/                # 监控模块
│   │   ├── __init__.py
│   │   ├── metrics.py             # Prometheus 指标
│   │   ├── middleware.py          # 监控中间件
│   │   ├── health.py              # 健康检查
│   │   ├── tracing.py             # 分布式追踪
│   │   └── alerts.py              # 告警系统
│   ├── security/                  # 安全模块
│   │   ├── __init__.py
│   │   ├── rate_limit.py          # API 限流
│   │   ├── circuit_breaker.py     # 熔断器
│   │   ├── input_validation.py    # 输入验证
│   │   ├── encryption.py          # 加密工具
│   │   ├── key_rotation.py        # 密钥轮换
│   │   └── middleware.py          # 安全中间件
│   ├── exceptions.py              # 异常定义
│   └── logging_config.py          # 日志配置
│
├── services/                      # 服务模块
│   ├── backend/                   # 后端 API 服务
│   │   ├── api/                   # API 端点
│   │   │   ├── __init__.py
│   │   │   ├── account.py         # 用户账户 API
│   │   │   ├── file.py            # 文件管理 API
│   │   │   ├── job.py             # 任务管理 API
│   │   │   ├── job_split.py       # 任务分片 API
│   │   │   ├── language.py        # 语言管理 API
│   │   │   ├── topic.py           # 话题管理 API
│   │   │   ├── voice.py           # 音色管理 API
│   │   │   └── health.py          # 健康检查 API
│   │   ├── db/                    # 数据库
│   │   ├── schema/                # 数据模型 (Pydantic)
│   │   ├── service/               # 业务逻辑
│   │   ├── api_main.py            # FastAPI 应用入口
│   │   └── Dockerfile             # Docker 镜像
│   │
│   ├── worker/                    # Worker 服务
│   │   ├── pipeline/              # Pipeline 系统
│   │   │   ├── context.py         # Pipeline 上下文
│   │   │   ├── data.py            # 数据容器
│   │   │   ├── state_manager.py   # 状态管理
│   │   │   ├── factory.py         # 步骤工厂
│   │   │   ├── pipeline.py        # Pipeline 类
│   │   │   └── steps/             # 步骤实现
│   │   ├── job_processing/        # 任务处理
│   │   ├── scheduler/             # 任务调度
│   │   ├── services/              # 服务集成
│   │   ├── clients/               # 客户端
│   │   ├── utils/                 # 工具函数
│   │   ├── tasks.py               # Celery 任务
│   │   └── worker_main.py         # Worker 入口
│   │
│   └── image_gen/                 # 图像生成服务 (可选)
│
├── deploy/                        # 部署配置
│   ├── nginx/                     # Nginx 配置
│   ├── mysql/                     # MySQL 配置
│   ├── redis/                     # Redis 配置
│   ├── prometheus/                # Prometheus 配置
│   └── grafana/                   # Grafana 配置
│
├── docs/                          # 文档
│   ├── 01-快速开始.md
│   ├── 02-架构设计.md
│   ├── 03-API文档.md
│   ├── 04-配置说明.md
│   ├── 05-部署指南.md
│   ├── 06-开发指南.md
│   ├── 07-监控与可观测性指南.md
│   ├── 08-安全指南.md
│   └── 09-高可用性部署指南.md
│
├── scripts/                       # 脚本工具
├── tests/                         # 测试
├── .env.example                   # 环境变量示例
├── docker-compose.yml             # Docker Compose 配置
├── docker-compose.ha.yml          # 高可用配置
├── pyproject.toml                 # Python 项目配置
└── README.md                      # 项目文档
```

---

## 技术栈

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.8+ | 主要开发语言 |
| FastAPI | 0.68+ | Web 框架 |
| SQLAlchemy | 1.4+ | ORM |
| PyMySQL | 1.0+ | MySQL 驱动 |
| Redis | 4.0+ | 缓存和消息队列 |
| Celery | 5.3+ | 分布式任务队列 |
| Flower | 2.0+ | Celery 监控 |
| Pydantic | 1.8+ | 数据验证 |
| python-jose | 3.3+ | JWT 认证 |

### 基础设施

| 技术 | 版本 | 用途 |
|------|------|------|
| MySQL | 8.0+ | 关系型数据库 |
| Redis | 7+ | 缓存和消息队列 |
| Nginx | latest | 反向代理和负载均衡 |
| Docker | 20.10+ | 容器化 |
| Prometheus | latest | 监控指标收集 |
| Grafana | latest | 监控可视化 |

### AI/ML 服务

| 技术 | 用途 |
|------|------|
| SeedVC | 文本转语音 |
| Azure TTS | 文本转语音 (备选) |
| Flux | AI 图像生成 |
| FFmpeg | 视频处理 |

---

## 硬件配置要求

### 推荐配置（生产环境）

**推荐硬件配置**: 8 × NVIDIA A100 (80GB)

| 组件 | 配置 | 说明 |
|------|------|------|
| **GPU** | 8 × NVIDIA A100 80GB | 总显存 640GB，支持大规模并发推理 |
| **CPU** | 64核+ (AMD EPYC 或 Intel Xeon) | 高主频有利于数据预处理 |
| **内存** | 512GB+ DDR4/DDR5 | 大内存支持多任务并发处理 |
| **存储** | 2TB+ NVMe SSD | 高速存储用于模型加载和缓存 |
| **网络** | 100Gbps+ 内网带宽 | 低延迟网络支持分布式通信 |
| **系统盘** | 500GB+ NVMe SSD | 系统和数据存储 |

### 服务资源分配

**图像生成服务 (Flux)**:
- GPU: 4 × A100 80GB
- 显存需求: 每个 Flux 模型约 20-30GB
- 支持并发: 8-16 个并发生成任务

**语音合成服务 (SeedVC)**:
- GPU: 2 × A100 80GB
- 显存需求: DiT 模型约 10GB, BigVGAN 约 2GB
- 支持并发: 20-30 个并发合成任务

**Worker 服务**:
- GPU: 2 × A100 80GB
- 显存需求: 动态分配给不同任务
- 支持并发: 10-15 个并发处理任务

### 最低配置（开发环境）

| 组件 | 最低配置 | 说明 |
|------|---------|------|
| **GPU** | 1 × NVIDIA RTX 3090/4090 (24GB) | 仅用于开发和测试 |
| **CPU** | 16核+ | |
| **内存** | 128GB+ | |
| **存储** | 500GB+ NVMe SSD | |
| **网络** | 10Gbps+ | |

### 显存占用估算

| 模型/服务 | 单实例显存占用 | 推荐并发数 |
|----------|--------------|-----------|
| Flux.1-dev | ~24GB (bfloat16) | 2-3/80GB A100 |
| SeedVC DiT | ~10GB (FP16) | 6-8/80GB A100 |
| SeedVC BigVGAN | ~2GB | 20+ |
| Whisper | ~2GB | 20+ |
| FunASR | ~4GB | 10+ |
| CAMPPlus | ~500MB | 50+ |

### 性能基准

**图像生成性能** (基于 8 × A100 80GB):
- Flux 1024×1024: ~8秒/张
- Flux 1360×768: ~6秒/张
- 并发吞吐量: ~50-80 张/分钟

**语音合成性能** (基于 SeedVC):
- 10秒音频合成: ~3秒
- 并发吞吐量: ~400-600 音频/分钟

**端到端视频生成**:
- 1分钟视频: 约 5-10 分钟
- 支持 8-16 个视频同时处理

### 云服务推荐

**云服务商**: AWS、阿里云、Google Cloud、Azure

**推荐实例类型**:
- AWS: `p4d.24xlarge` (8 × A100 80GB)
- 阿里云: `ecs.gn7v-c8g1.8xlarge` (8 × A100 80GB)
- Google Cloud: `a2-highgpu-8g` (8 × A100 100GB)
- Azure: `Standard_NC96ads100_v4` (8 × A100 80GB)

### 成本估算

**云服务成本** (按需定价，仅供参考):
- AWS p4d.24xlarge: ~$32/小时 (~$23,000/月)
- 阿里云 ecs.gn7v-c8g1.8xlarge: ~$28/小时 (~$20,000/月)
- Google Cloud a2-highgpu-8g: ~$30/小时 (~$21,600/月)

**优化建议**:
1. 使用 Spot/Preemptible 实例可节省 60-80% 成本
2. 按需扩缩容，非高峰时段减少实例
3. 使用预留实例可获得 30-50% 折扣

---

## 数据模型设计

### 数据库表关系图

```
┌─────────────┐
│    User     │
│  (用户表)    │
└──────┬──────┘
       │ 1:N
       ├──────────────────────────────────────┐
       │                                      │
       ▼                                      ▼
┌─────────────┐                      ┌─────────────┐
│  Language   │                      │    Voice    │
│  (语言表)    │                      │  (音色表)    │
└─────────────┘                      └─────────────┘

       │                                      │
       └──────────────────┬───────────────────┘
                          │ 1:N
                          ▼
                   ┌─────────────┐
                   │    Job      │
                   │  (任务表)    │
                   └──────┬──────┘
                          │
          ┌───────────────┼───────────────┐
          │ 1:N          │ 1:N           │ 1:N
          ▼              ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ JobExecution │  │  JobSplit   │  │   Topic     │
│(执行记录表)   │  │ (分片表)     │  │  (话题表)    │
└─────────────┘  └─────────────┘  └─────────────┘
```

### 核心数据表

#### User (用户表)

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | CHAR(36) | UUID 主键 |
| username | String(255) | 唯一用户名 |
| password | String(255) | 加密密码 |
| created_at | DateTime | 创建时间 |
| last_login_at | DateTime | 最后登录时间 |

#### Language (语言表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String(255) | 语言名称 (唯一) |
| platform | String(255) | 平台名称 |
| language_name | String(255) | 显示名称 |

#### Voice (音色表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String(255) | 音色名称 |
| path | String(255) | 音色文件路径 |

#### Topic (话题表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String(255) | 话题名称 (唯一) |
| prompt_gen_image | Text | 图像生成提示词 |
| prompt_cover_image | Text | 封面图提示词 |
| loraname | String(255) | LoRA 模型名称 |
| loraweight | Integer | LoRA 权重 |

#### Account (账号表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| username | String(255) | 账号用户名 |
| logo | String(255) | Logo 路径 |
| platform | String(255) | 平台 (youtube等) |
| area | String(255) | 地区 |

#### Job (任务表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| runorder | Integer | 执行顺序 |
| title | String(255) | 任务标题 |
| content | Text | 任务内容 (文本) |
| description | Text | 描述信息 |
| publish_title | Text | 发布标题 |
| language_id | Integer | 关联语言 |
| voice_id | Integer | 关联音色 |
| topic_id | Integer | 关联话题 |
| account_id | Integer | 关联账号 |
| speech_speed | Float | 语速 (默认 0.9) |
| is_horizontal | Boolean | 横竖屏 (默认 True) |
| extra | JSON | 额外配置 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| deleted_at | DateTime | 软删除时间 |

#### JobExecution (执行记录表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| job_id | Integer | 关联任务 |
| status | Enum | 执行状态 (PENDING/RUNNING/SUCCESS/FAILED) |
| status_detail | String(500) | 状态详情 |
| result_key | Text | 结果存储键 (JSON) |
| worker_hostname | String(255) | 执行主机名 |
| retry_count | Integer | 重试次数 |
| error_message | Text | 错误信息 |
| started_at | DateTime | 开始时间 |
| finished_at | DateTime | 完成时间 |

#### JobSplit (任务分片表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| job_id | Integer | 关联任务 |
| index | Integer | 分片索引 (用于排序) |
| start | Integer | 开始时间 (毫秒) |
| end | Integer | 结束时间 (毫秒) |
| text | String(255) | 文本内容 |
| prompt | String(255) | 图像生成提示词 |
| images | Text | 图像列表 (JSON) |
| video | String(255) | 视频路径 |
| selected | String(255) | 选中的图像 |

---

## 项目模型详解

本章节详细介绍 BatchVideo 项目中涉及的所有模型及其作用。项目中的模型分为三大类：

1. **数据库模型** - SQLAlchemy ORM 模型，定义数据库表结构
2. **API Schema 模型** - Pydantic 模型，用于 API 请求/响应验证
3. **Pipeline 数据模型** - Pipeline 处理过程中的数据容器

---

### 一、数据库模型

数据库模型定义在 `core/db/models.py` 文件中，使用 SQLAlchemy ORM 框架。

#### 1. User (用户模型)

**文件位置**: `core/db/models.py:39-49`

```python
class User(Base):
    """用户模型"""
    __tablename__ = "users"

    user_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=get_beijing_time)
    last_login_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time, nullable=True)
```

**作用**: 存储用户账户信息

**字段说明**:
- `user_id`: UUID 格式的主键，全局唯一标识符
- `username`: 用户名，唯一索引，用于用户登录
- `password`: 加密后的密码（应该使用 bcrypt 或类似算法）
- `created_at`: 账户创建时间（北京时间）
- `last_login_at`: 最后登录时间，每次登录自动更新

**关系**:
- 一个 User 可以拥有多个 Language
- 一个 User 可以拥有多个 Voice
- 一个 User 可以拥有多个 Topic
- 一个 User 可以拥有多个 Account
- 一个 User 可以创建多个 Job

---

#### 2. Language (语言模型)

**文件位置**: `core/db/models.py:52-70`

```python
class Language(Base):
    """语言模型

    表示支持的语言类型。
    """
    __tablename__ = "languages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)  # 语言名称，唯一索引
    platform = Column(String(255), nullable=True)  # 平台名称
    language_name = Column(String(255), nullable=True)  # 语言显示名称
    created_at = Column(DateTime, default=get_beijing_time)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    user_id = Column(CHAR(36), ForeignKey("users.user_id"), nullable=True)
    user = relationship("User")
```

**作用**: 存储系统支持的 TTS 语言配置

**字段说明**:
- `id`: 自增主键
- `name`: 语言代码（如 "zh-CN", "en-US"），唯一索引
- `platform`: TTS 平台名称（如 "edge", "azure", "seedvc"）
- `language_name`: 语言显示名称（如 "中文", "English"）
- `user_id`: 所属用户 ID（支持用户自定义语言）
- `created_at/updated_at`: 时间戳

**使用场景**: 当用户创建任务时，选择语言决定 TTS 服务的语言参数

---

#### 3. Voice (音色模型)

**文件位置**: `core/db/models.py:72-83`

```python
class Voice(Base):
    """音色模型"""
    __tablename__ = "voices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    path = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=get_beijing_time)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    user_id = Column(CHAR(36), ForeignKey("users.user_id"), nullable=True)
    user = relationship("User")
```

**作用**: 存储 TTS 音色配置

**字段说明**:
- `id`: 自增主键
- `name`: 音色名称（如 "xiaoyun", "xiaoxiao"）
- `path`: 参考音频文件路径，用于音色克隆
- `user_id`: 所属用户 ID（支持用户自定义音色）

**使用场景**: TTS 生成时使用指定的音色进行语音合成

---

#### 4. Topic (话题模型)

**文件位置**: `core/db/models.py:85-102`

```python
class Topic(Base):
    """话题模型"""
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    prompt_gen_image = Column(Text, nullable=True)  # 图像生成提示词
    prompt_cover_image = Column(Text, nullable=True)  # 封面图提示词
    prompt_image_prefix = Column(Text, nullable=True)  # 图像前缀提示词
    prompt_l4 = Column(Text, nullable=True)  # L4 层级提示词
    loraname = Column(String(255), unique=True, index=True, nullable=True, default="")
    loraweight = Column(Integer, default=100, nullable=True)  # LoRA 权重
    extra = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, default=get_beijing_time)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    user_id = Column(CHAR(36), ForeignKey("users.user_id"), nullable=True)
    user = relationship("User")
```

**作用**: 存储话题配置，包括 AI 图像生成的提示词和 LoRA 模型配置

**字段说明**:
- `id`: 自增主键
- `name`: 话题名称（如 "科技", "美食", "旅游"）
- `prompt_gen_image`: AI 图像生成的基础提示词
- `prompt_cover_image`: 封面图生成的专用提示词
- `prompt_image_prefix`: 图像提示词前缀
- `prompt_l4`: L4 层级的提示词
- `loraname`: LoRA 模型名称（用于 AI 图像生成风格化）
- `loraweight`: LoRA 模型权重（0-100）
- `extra`: 额外配置（JSON 格式）

**使用场景**:
- 决定生成视频的视觉风格
- 为每个文本片段生成图像时使用话题的提示词
- 通过 LoRA 模型控制生成图像的艺术风格

---

#### 5. Account (账号模型)

**文件位置**: `core/db/models.py:104-118`

```python
class Account(Base):
    """账号模型"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    logo = Column(String(255), default="")
    platform = Column(String(255), default="youtube")
    area = Column(String(255), default="")
    extra = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, default=get_beijing_time)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    user_id = Column(CHAR(36), ForeignKey("users.user_id"), nullable=True)
    user = relationship("User")
```

**作用**: 存储第三方平台账号信息（如 YouTube 账号）

**字段说明**:
- `id`: 自增主键
- `username`: 账号用户名
- `logo`: Logo 图片路径，用于视频水印
- `platform`: 平台名称（默认 "youtube"）
- `area`: 账号所属地区
- `extra`: 额外配置（JSON 格式），包含字幕背景、转场效果等

**extra 配置示例**:
```python
{
    "subtitle_background": "#578B2E",
    "human_config": {"duration": 120, "end_duration": 120},
    "enable_transition": False,
    "transition_types": ["fade"],
    "human_insertion_mode": "fullscreen",
    "enable_srt_concat_transition": False,
    "srt_concat_transition_types": ["fade"]
}
```

**使用场景**:
- 视频合成时添加账号 Logo 水印
- 根据账号配置应用特定的转场效果
- 发布视频到对应平台

---

#### 6. Job (任务模型)

**文件位置**: `core/db/models.py:120-204`

```python
class Job(Base):
    """任务模型 - 任务配置

    表示一个视频生成任务的配置和定义，不包含执行状态。
    这是任务的"模板"，可以被多次执行。
    """
    __tablename__ = "jobs"

    # 复合索引
    __table_args__ = (
        Index('idx_deleted_runorder_id', 'deleted_at', 'runorder', 'id'),
        Index('idx_user_deleted_id', 'user_id', 'deleted_at', 'id'),
        Index('idx_account_deleted_id', 'account_id', 'deleted_at', 'id'),
        Index('idx_language_deleted_id', 'language_id', 'deleted_at', 'id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    runorder = Column(Integer, default=0, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    language_id = Column(Integer, ForeignKey("languages.id"), nullable=True, index=True)
    language = relationship("Language")
    voice_id = Column(Integer, ForeignKey("voices.id"), nullable=True)
    voice = relationship("Voice")
    description = Column(Text, nullable=False)
    publish_title = Column(Text, nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    topic = relationship("Topic")
    speech_speed = Column(Float, default=0.9, nullable=False)
    created_at = Column(DateTime, default=get_beijing_time, index=True)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    user_id = Column(CHAR(36), ForeignKey("users.user_id"), nullable=True, index=True)
    user = relationship("User")
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    account = relationship("Account")
    is_horizontal = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=False, default={})
    deleted_at = Column(DateTime, nullable=True, index=True)

    # 关系
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")
```

**作用**: 存储视频生成任务的配置信息（任务模板）

**设计理念**: Job 表只存储配置，不存储执行状态。支持多次执行（重试、重新运行）

**字段说明**:
- `id`: 自增主键
- `runorder`: 执行顺序优先级（数字越小越优先）
- `title`: 任务标题
- `content`: 待转换的文本内容
- `description`: 任务描述信息
- `publish_title`: 发布时使用的标题
- `language_id`: 关联语言 ID
- `voice_id`: 关联音色 ID
- `topic_id`: 关联话题 ID
- `account_id`: 关联账号 ID（决定 Logo 和水印）
- `speech_speed`: 语速（0.5-2.0，默认 0.9）
- `is_horizontal`: 是否横屏（True=横屏 1360x768, False=竖屏 768x1360）
- `extra`: 额外配置（JSON 格式）
- `deleted_at`: 软删除时间戳（NULL 表示未删除）

**extra 配置示例**:
```python
{
    "h2v": False,  # 横屏转竖屏
    "index_text": "",  # 集数文字
    "title_text": "",  # 标题文字
    "desc_text": "",  # 描述文字
    "audio": "",  # 音频文件路径
    "enable_digital_human": False  # 是否启用数字人
}
```

**关系**:
- 一个 Job 可以有多个 JobExecution（执行记录）
- 一个 Job 可以有多个 JobSplit（分片）

**向后兼容属性**:
```python
@property
def latest_execution(self):
    """获取最新的执行记录"""

@property
def status(self):
    """向后兼容：获取最新执行状态"""

@property
def status_detail(self):
    """向后兼容：获取最新执行详情"""

@property
def job_result_key(self):
    """向后兼容：获取最新执行结果"""
```

---

#### 7. JobExecution (任务执行记录模型)

**文件位置**: `core/db/models.py:206-290`

```python
class JobExecution(Base):
    """任务执行记录表

    存储每一次任务执行的记录，包括状态、结果、执行时间等。
    """
    __tablename__ = "job_executions"

    __table_args__ = (
        Index('idx_job_status', 'job_id', 'status'),
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_worker_status', 'worker_hostname', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    status = Column(Enum("PENDING", "RUNNING", "SUCCESS", "FAILED", name="job_execution_status"),
                   default="PENDING", index=True, nullable=False)
    status_detail = Column(String(500), default="")
    result_key = Column(Text, nullable=True)
    worker_hostname = Column(String(255), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    execution_metadata = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, default=get_beijing_time, index=True)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)

    job = relationship("Job", back_populates="executions")
```

**作用**: 记录每次任务执行的状态和结果

**设计优势**:
1. **历史追溯**: 可以清楚看到 Job 被执行了多少次，每次成功还是失败
2. **表结构清晰**: Job 表更稳定，JobExecution 表频繁写入
3. **支持重新运行**: 用户可以对已完成或失败的 Job 发起重新运行
4. **性能优化**: 对 Job 表的查询不会被 JobExecution 的频繁写入影响

**字段说明**:
- `id`: 自增主键
- `job_id`: 关联的 Job ID
- `status`: 执行状态（PENDING=待处理, RUNNING=运行中, SUCCESS=成功, FAILED=失败）
- `status_detail`: 状态详情描述
- `result_key`: 结果存储键（JSON 格式，存储 OSS 路径等）
- `worker_hostname`: 执行该任务的 Worker 主机名
- `started_at`: 开始执行时间
- `finished_at`: 完成时间
- `retry_count`: 重试次数
- `error_message`: 错误信息（如果失败）
- `execution_metadata`: 执行元数据（JSON 格式）

**result_key 存储内容示例**:
```python
{
    "audio_oss_key": "jobs/123/audio.mp3",
    "srt_oss_key": "jobs/123/subtitle.srt",
    "combined_video_oss_key": "jobs/123/video_combined.mp4",
    "logoed_video_oss_key": "jobs/123/video_logoed.mp4",
    "cover_oss_key": "jobs/123/cover.jpg"
}
```

**属性方法**:
```python
@property
def duration(self):
    """获取执行时长（秒）"""

@property
def is_successful(self):
    """是否执行成功"""

@property
def is_failed(self):
    """是否执行失败"""

@property
def is_running(self):
    """是否正在执行"""

@property
def is_pending(self):
    """是否待处理"""
```

---

#### 8. JobSplit (任务分片模型)

**文件位置**: `core/db/models.py:292-320`

```python
class JobSplit(Base):
    """任务分片模型

    表示任务的一个分割片段，包含该片段的文本、图像、视频等信息。
    """
    __tablename__ = "job_splits"

    __table_args__ = (
        Index('idx_job_index', 'job_id', 'index'),
    )

    id = Column(Integer, primary_key=True, index=True)
    start = Column(Integer, nullable=False)  # 开始时间（毫秒）
    end = Column(Integer, nullable=False)  # 结束时间（毫秒）
    text = Column(String(255), nullable=False)  # 文本内容
    prompt = Column(String(255), nullable=True)  # 图像生成提示词
    images = Column(Text, nullable=True)  # 存储为JSON字符串
    video = Column(String(255), nullable=True)  # 视频路径
    selected = Column(String(255), nullable=True)  # 选中的图像
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    index = Column(Integer, nullable=False)  # 分割项索引，用于排序
    created_at = Column(DateTime, default=get_beijing_time)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    job = relationship("Job")
```

**作用**: 存储任务分割后的每个片段信息

**字段说明**:
- `id`: 自增主键
- `job_id`: 关联的 Job ID
- `index`: 分片索引（从 0 开始，用于排序）
- `start`: 片段开始时间（毫秒）
- `end`: 片段结束时间（毫秒）
- `text`: 该片段的文本内容
- `prompt`: 该片段的图像生成提示词
- `images`: 生成的图像路径列表（JSON 数组）
- `video`: 该片段的视频路径
- `selected`: 用户选择的图像

**使用场景**:
- 长文本被分割成多个片段
- 每个片段生成对应的图像
- 用户可以选择或替换某个片段的图像
- 支持对每个片段进行微调

---

### 二、API Schema 模型

API Schema 模型定义在 `services/backend/schema/` 目录中，使用 Pydantic 进行请求/响应验证。

#### 1. Job 相关 Schema

**文件位置**: `services/backend/schema/job.py`

##### Job (响应模型)

```python
class Job(BaseModel):
    id: int
    runorder: int = 0
    title: str
    content: str
    language_id: Optional[int] = None
    language: Optional[SchemaLanguage] = None
    voice_id: Optional[int] = 0
    voice: Optional[SchemaVoice] = None
    description: Optional[str] = ""
    publish_title: Optional[str] = ""
    speech_speed: float = 0.9
    topic_id: Optional[int] = None
    topic: Optional[Topic] = None
    job_splits: list[JobSplit] = []
    job_result_key: str = ""
    status: str = "待处理"
    is_horizontal: bool = True
    status_detail: Optional[str] = ""
    cover_base64: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    account_id: int | None = None
    extra: Optional[dict] = {}
```

**作用**: 任务信息的 API 响应模型，包含关联的语言、音色、话题等信息

##### CreateJobRequest (创建任务请求)

```python
class CreateJobRequest(BaseModel):
    title: str
    content: str
    runorder: int = 0
    language_id: Optional[int] = None
    voice_id: Optional[int] = None
    description: str = ""
    publish_title: str = ""
    account_id: int | None = None
    topic_id: Optional[int] = None
    speech_speed: float = 0.9
    is_horizontal: bool = True
    extra: Optional[dict] = {}
```

**作用**: 创建任务的 API 请求验证模型

##### JobExtra (任务额外配置)

```python
class JobExtra(BaseModel):
    h2v: bool = False  # 横屏转竖屏
    index_text: str = ""  # 集数文字 上方第一条
    title_text: str = ""  # 标题文字 上方第二条
    desc_text: str = ""  # 描述文字 下方
    audio: str = ""  # 音频文件路径
```

**作用**: 定义任务额外的可选配置项

---

#### 2. Account 相关 Schema

**文件位置**: `services/backend/schema/account.py`

##### Account (账号响应模型)

```python
class Account(BaseModel):
    id: int
    username: str
    logo: str = ""
    platform: str = "youtube"
    area: str = ""
    created_at: str = ""
    updated_at: str = ""
    extra: Optional[dict] = {}
```

**作用**: 账号信息的 API 响应模型

##### AccountExtra (账号额外配置)

```python
class AccountExtra(BaseModel):
    subtitle_background: str = "#578B2E"
    human_config: Optional[dict] = {"duration": 120, "end_duration": 120}
    enable_transition: bool = False
    transition_types: list[str] = ["fade"]
    human_insertion_mode: str = "fullscreen"
    enable_srt_concat_transition: bool = False
    srt_concat_transition_types: list[str] = ["fade"]
```

**作用**: 定义账号的额外配置，包括：
- `subtitle_background`: 字幕背景颜色
- `human_config`: 数字人配置（时长、结束时长）
- `enable_transition`: 是否启用转场效果
- `transition_types`: 转场类型列表（淡入淡出等）
- `human_insertion_mode`: 数字人插入模式
- `enable_srt_concat_transition`: 字幕拼接转场
- `srt_concat_transition_types`: 字幕拼接转场类型

---

#### 3. User 相关 Schema

**文件位置**: `services/backend/schema/account.py`

##### User (用户响应模型)

```python
class User(BaseModel):
    user_id: str
    username: str
    created_at: datetime
    last_login_at: datetime
```

##### UserCreate (创建用户请求)

```python
class UserCreate(BaseModel):
    username: str
    password: str
```

##### UserLogin (用户登录请求)

```python
class UserLogin(BaseModel):
    username: str
    password: str
```

##### Token (令牌响应)

```python
class Token(BaseModel):
    access_token: str
    token_type: str
```

**作用**: 用户认证相关的 API 模型

---

#### 4. Language 相关 Schema

**文件位置**: `services/backend/schema/language.py`

```python
class Language(BaseModel):
    id: int
    name: str
    platform: Optional[str] = None
    language_name: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

class CreateLanguageRequest(BaseModel):
    name: str
    platform: Optional[str] = None
    language_name: Optional[str] = None

class ListLanguageResponse(BaseModel):
    total: int
    items: list[Language]
```

---

#### 5. Voice 相关 Schema

**文件位置**: `services/backend/schema/voice.py`

```python
class Voice(BaseModel):
    id: int
    name: str
    path: str

class CreateVoiceRequest(BaseModel):
    name: str
    path: str

class ListVoiceResponse(BaseModel):
    total: int
    items: list[Voice]
```

---

#### 6. Topic 相关 Schema

**文件位置**: `services/backend/schema/topic.py`

```python
class Topic(BaseModel):
    id: int
    name: str
    prompt_gen_image: Optional[str] = None
    prompt_cover_image: Optional[str] = None
    prompt_image_prefix: Optional[str] = None
    prompt_l4: Optional[str] = None
    loraname: str = ""
    loraweight: int = 100
    extra: Optional[dict] = {}
    created_at: str
    updated_at: str

class CreateTopicRequest(BaseModel):
    name: str
    prompt_gen_image: Optional[str] = None
    prompt_cover_image: Optional[str] = None
    prompt_image_prefix: Optional[str] = None
    prompt_l4: Optional[str] = None
    loraname: str = ""
    loraweight: int = 100
    extra: Optional[dict] = {}
```

---

#### 7. JobSplit 相关 Schema

**文件位置**: `services/backend/schema/job_split.py`

```python
class JobSplit(BaseModel):
    job_id: int
    index: int
    start: int
    end: int
    text: str
    prompt: str = ""
    video: str = ""
    images: list[str] = []
    selected: str = ""

class ListJobSplitResponse(BaseModel):
    total: int
    items: list[JobSplit]

class UpdateJobSplitRequest(BaseModel):
    images: list[str] = []
    selected: str = ""
    prompt: str = ""
```

**作用**: 任务分片的 API 模型，支持查询和更新分片信息

---

### 三、Pipeline 数据模型

Pipeline 数据模型定义在 `services/worker/pipeline/` 目录中，用于 Pipeline 执行过程中的数据传递。

#### 1. PipelineData (Pipeline 数据容器)

**文件位置**: `services/worker/pipeline/data.py:14-103`

```python
@dataclass
class PipelineData:
    """Pipeline 纯数据容器

    只负责数据存储，不包含业务逻辑。
    """
    # 基础信息
    job_id: int
    title: str = ""
    content: str = ""
    user_id: Optional[str] = None
    workspace_dir: Optional[Path] = None

    # 配置信息
    language_name: str = ""
    language_platform: str = "edge"
    speech_speed: float = 0.9
    is_horizontal: bool = True
    reference_audio_path: Optional[str] = None
    logopath: Optional[str] = None
    topic_prompts: Optional[Dict[str, Any]] = None
    loras: Optional[List[Dict[str, Any]]] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    account: Optional[Any] = None

    # 步骤中间结果
    audio_path: Optional[str] = None
    srt_path: Optional[str] = None
    splits: List[Dict[str, Any]] = field(default_factory=list)
    image_paths: List[str] = field(default_factory=list)
    selected_images: List[str] = field(default_factory=list)
    combined_video: Optional[str] = None
    human_video_path: Optional[str] = None
    final_video_path: Optional[str] = None

    # 上传结果
    upload_results: Dict[str, str] = field(default_factory=dict)
```

**作用**: 纯数据容器，存储 Pipeline 执行过程中的所有数据

**字段分类**:
- **基础信息**: job_id, title, content, user_id, workspace_dir
- **配置信息**: 语言、音色、语速、横竖屏、话题提示词、LoRA 配置等
- **步骤中间结果**: audio_path, srt_path, splits, image_paths, combined_video 等
- **上传结果**: upload_results (存储 OSS 路径)

**设计原则**:
- 遵循单一职责原则，只负责数据存储
- 不包含业务逻辑
- 所有字段都是可变的，允许在 Pipeline 执行过程中更新

---

#### 2. StepResultData (步骤结果数据)

**文件位置**: `services/worker/pipeline/data.py:105-123`

```python
@dataclass
class StepResultData:
    """步骤结果数据

    用于在函数式模式中传递步骤结果。
    """
    step_name: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=get_beijing_time)

    def get(self, key: str, default: Any = None) -> Any:
        """获取数据值"""

    def set(self, key: str, value: Any) -> None:
        """设置数据值"""
```

**作用**: 在函数式 Pipeline 模式中，存储每个步骤的执行结果

**使用场景**:
```python
# 函数式模式
results = pipeline.execute_functional()

# 获取 TTS 步骤结果
tts_result = results.get("TTSGeneration")
audio_path = tts_result.get("audio_path")
duration = tts_result.get("duration")
```

---

#### 3. StepExecutionRecord (步骤执行记录)

**文件位置**: `services/worker/pipeline/state_manager.py:16-31`

```python
@dataclass
class StepExecutionRecord:
    """步骤执行记录"""
    step_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "RUNNING"  # RUNNING, COMPLETED, FAILED
    error: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """获取执行时长（秒）"""
```

**作用**: 记录单个步骤的执行状态和时间信息

---

#### 4. PipelineStateManager (Pipeline 状态管理器)

**文件位置**: `services/worker/pipeline/state_manager.py:33-198`

```python
class PipelineStateManager:
    """Pipeline 状态管理器

    职责：
    - 记录步骤执行状态
    - 跟踪执行进度
    - 计算执行时间
    """

    def __init__(self, job_id: int):
        self.job_id = job_id
        self.started_at: datetime = get_beijing_time()
        self.executed_steps: List[str] = []
        self.step_records: dict[str, StepExecutionRecord] = {}

    def mark_step_started(self, step_name: str) -> None
    def mark_step_completed(self, step_name: str) -> None
    def mark_step_failed(self, step_name: str, error: str) -> None
    def get_step_status(self, step_name: str) -> Optional[str]
    def get_step_duration(self, step_name: str) -> Optional[float]
    def get_total_duration(self) -> float
    def get_failed_step(self) -> Optional[str]
    def get_step_summary(self) -> dict
```

**作用**: 管理 Pipeline 执行状态，不负责数据存储或业务逻辑

**职责**:
- 记录每个步骤的开始、完成、失败状态
- 计算步骤执行时长
- 提供步骤执行摘要

---

#### 5. PipelineContext (Pipeline 上下文)

**文件位置**: `services/worker/pipeline/context.py:34-451`

```python
class PipelineContext:
    """Pipeline 上下文 (重构版)

    使用组合模式，将职责分离到专门的类：
    - data: PipelineData - 数据存储
    - state_manager: PipelineStateManager - 状态跟踪
    - status_updater: JobStatusUpdater - 数据库更新
    """

    def __init__(
        self,
        job_id: int,
        db: Session,
        job: Optional[Job] = None,
        execution: Optional['JobExecution'] = None,
        workspace_dir: Optional[Path] = None,
        user_id: Optional[str] = None,
    ):
        self.job_id = job_id
        self.db = db
        self.job = job
        self.execution = execution

        # 组合专门的组件
        self._data = PipelineData(job_id=job_id, workspace_dir=workspace_dir, user_id=user_id)
        self._state_manager = PipelineStateManager(job_id)
        self._status_updater = JobStatusUpdater(db, job_id) if execution else None
```

**作用**: Pipeline 执行的上下文对象，组合数据、状态、数据库更新功能

**设计模式**: 组合模式
- `_data`: 数据存储组件
- `_state_manager`: 状态管理组件
- `_status_updater`: 数据库状态更新组件

**向后兼容属性**:
```python
# 数据访问属性
@property
def title(self) -> str
@property
def content(self) -> str
@property
def audio_path(self) -> Optional[str]
@property
def combined_video(self) -> Optional[str]
# ... 更多属性

# 状态访问属性
@property
def executed_steps(self) -> list
@property
def failed_step_name(self) -> Optional[str]
@property
def error_message(self) -> Optional[str]
```

**类方法工厂**:
```python
@classmethod
def from_job(cls, job: Job, db: Session, execution: Optional['JobExecution'] = None) -> "PipelineContext":
    """从任务对象创建上下文"""
```

**核心方法**:
```python
def mark_step_started(self, step_name: str) -> None
def mark_step_completed(self, step_name: str) -> None
def mark_step_failed(self, step_name: str, error: str) -> None
def update_job_status(self, status: Union[str, ExecutionStatus], status_detail: str = "") -> None
def get_duration(self) -> float
def to_dict(self) -> Dict[str, Any]
```

---

### 四、模型关系总结

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           模型关系架构图                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                        数据库模型 (SQLAlchemy)                             │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│  │  │   User   │──│ Language │  │  Voice   │  │  Topic   │               │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘               │  │
│  │       │             │             │             │                       │  │
│  │       └─────────────┴─────────────┴─────────────┼─────────────┐         │  │
│  │                                             │             │         │  │
│  │                                        ┌──────▼──────┐  │         │  │
│  │                                        │    Job      │  │         │  │
│  │                                        │  (任务配置)   │  │         │  │
│  │                                        └──────┬──────┘  │         │  │
│  │                                               │         │         │  │
│  │       ┌────────────────────────────────────────┼─────────┼─────────┐│  │
│  │       │                                        │         │         ││  │
│  │  ┌────▼─────────┐  ┌──────────────┐  ┌────────▼─────┐ ┌▼────────┐│  │
│  │  │JobExecution  │  │  JobSplit    │  │   Account    │ │  User   ││  │
│  │  │(执行记录)     │  │  (任务分片)   │  │   (账号)     │ │ (用户)   ││  │
│  │  └───────────────┘  └──────────────┘  └──────────────┘ └─────────┘│  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                      API Schema 模型                                │  │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐               │  │
│  │  │ CreateJobRequest│ │ ListJobResponse│ │ TokenResponse  │               │  │
│  │  │  CreateVoiceReq │ │  CreateAccount │ │  UserResponse  │               │  │
│  │  │ CreateTopicReq │ │  CreateLanguage│ │ AccountExtra   │               │  │
│  │  └───────────────┘  └───────────────┘  └───────────────┘               │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                    Pipeline 数据模型                                      │  │
│  │  ┌──────────────────┐  ┌─────────────────┐  ┌──────────────────┐        │  │
│  │  │  PipelineData    │  │StepResultData   │  │PipelineContext  │        │  │
│  │  │ (纯数据容器)      │  │(步骤结果)        │  │(组合上下文)      │        │  │
│  │  └──────────────────┘  └─────────────────┘  └──────────────────┘        │  │
│  │  ┌──────────────────────────────────────────────────────────────┐       │  │
│  │  │          PipelineStateManager (状态管理器)                    │       │  │
│  │  └──────────────────────────────────────────────────────────────┘       │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### 五、模型使用场景

#### 场景1: 创建新的视频生成任务

```
用户输入 (CreateJobRequest)
        ↓
API 验证
        ↓
创建 Job 记录 (数据库模型)
        ↓
创建 JobExecution 记录 (数据库模型)
        ↓
创建 PipelineContext (Pipeline模型)
        ↓
执行 Pipeline
```

#### 场景2: 查询任务状态

```
用户请求 (GET /api/jobs/{id})
        ↓
查询 Job 记录
        ↓
关联查询 JobExecution (最新执行状态)
        ↓
转换为 API Schema (Job Response)
        ↓
返回给用户
```

#### 场景3: Pipeline 执行

```
PipelineContext 组合:
├── PipelineData (数据)
│   ├── job_id, title, content
│   ├── audio_path, srt_path
│   ├── image_paths, combined_video
│   └── upload_results
│
├── PipelineStateManager (状态)
│   ├── executed_steps
│   ├── step_records
│   └── get_step_summary()
│
└── JobStatusUpdater (数据库更新)
    └── update_execution_status()
```

---

## AI 模型与技术详解

本章节详细介绍 BatchVideo 项目中使用的所有 AI 模型和技术，包括它们的作用、应用场景和技术细节。

---

### 一、图像生成模型

#### 1. Flux (Flux.1-dev)

**技术类型**: 文生图扩散模型 (Text-to-Image Diffusion Model)

**文件位置**: `services/image_gen/flux_server/flux.py`

**作用**: 根据文本提示词生成高质量图像

**技术特点**:
- 基于 **Diffusers** 库实现
- 使用 **FluxPipeline** 进行图像生成
- 支持 **LoRA** 模型进行风格化微调
- 使用 bfloat16 精度进行推理
- 支持 CPU offload 优化显存使用
- 支持 VAE tiling 处理大分辨率图像
- 使用 torch.compile 优化推理速度

**关键代码**:
```python
from diffusers import FluxPipeline

# 加载 Flux 模型
pipe = FluxPipeline.from_pretrained(
    dev_path,
    torch_dtype=torch.bfloat16
)

# 优化配置
pipe.enable_model_cpu_offload(device=f"cuda:{deviceid}")
pipe.enable_vae_tiling()
pipe.transformer = torch.compile(
    pipe.transformer,
    mode="reduce-overhead"
)
```

**生成参数**:
- `width/height`: 图像分辨率 (默认 1024x1024, 支持 1360x768 横屏, 768x1360 竖屏)
- `num_inference_steps`: 推理步数 (默认 30，范围 20-50)
- `cfg_scale`: 提示词相关度 (默认 3.5)
- `seed`: 随机种子 (-1 表示随机)

**应用场景**:
- 为视频每个片段生成对应图像
- 生成视频封面图
- 生成数字人角色形象

---

#### 2. Diffusers

**技术类型**: Hugging Face 扩散模型库

**作用**: 提供标准化的扩散模型接口

**在项目中的应用**:
```python
from diffusers import FluxPipeline

# Flux 模型
pipe = FluxPipeline.from_pretrained(model_path)

# 模型优化
pipe.enable_model_cpu_offload()      # CPU 卸载
pipe.enable_vae_tiling()              # VAE 分块
pipe.enable_attention_slicing()       # 注意力切片
```

**优势**:
- 统一的 API 接口
- 内置优化功能
- 支持多种扩散模型
- 活跃的社区支持

---

#### 3. LoRA (Low-Rank Adaptation)

**技术类型**: 模型微调技术

**作用**: 在不修改主模型的情况下，为图像添加特定风格

**工作原理**:
- 在扩散模型的注意力层中添加低秩矩阵
- 训练时只更新 LoRA 参数，冻结主模型
- 推理时将 LoRA 权重合并到主模型

**在项目中的应用**:
```python
# LoRA 配置
loras = [
    {
        "name": "anime_style",      # LoRA 模型名称
        "weight": 0.8               # 权重 (0.0-1.0)
    }
]

# 生成时应用 LoRA
pipe.load_lora_weights(lora_name)
pipe.set_adapters(["default"], adapter_weights=[lora_weight])
```

**存储位置**: `services/image_gen/flux_server/loras/`

**支持的 LoRA 类型**:
- 风格化 LoRA (动漫、写实、油画等)
- 角色 LoRA (特定人物形象)
- 概念 LoRA (场景、物体)

**数据库配置**:
```python
# Topic 表中的 LoRA 配置
class Topic(Base):
    loraname = Column(String(255))   # LoRA 模型名称
    loraweight = Column(Integer)     # LoRA 权重 (0-100)
```

---

### 二、语音相关模型

#### 4. SeedVC (语音克隆)

**技术类型**: 语音克隆与合成模型

**文件位置**: `services/tts/seedvc_server/seedvc_run.py`

**作用**: 根据参考音频克隆音色，生成目标语音

**核心组件**:

| 组件 | 作用 | 模型文件 |
|------|------|----------|
| DiT (Diffusion Transformer) | 核心生成模型 | DiT_seed_v2_uvit_whisper_small_wavenet_bigvgan_pruned.pth |
| Whisper | 语音内容编码器 | whisper-small |
| BigVGAN | 神经声码器 | bigvgan_v2_22khz_80band_256x |
| CAMPPlus | 说话人嵌入模型 | campplus_cn_common.bin |

**工作流程**:
```
参考音频 → CAMPPlus → 说话人嵌入
                               ↓
文本 → Whisper → 语义特征 → DiT → Mel频谱 → BigVGAN → 音频
```

**关键代码**:
```python
# 加载模型
model = build_model(model_params, stage="DiT")
campplus_model = CAMPPlus(feat_dim=80, embedding_size=192)
bigvgan_model = bigvgan.BigVGAN.from_pretrained(bigvgan_model_path)

# 语音合成
audio = model.inference(
    text=text,
    reference_audio=reference_audio,
    speaker_embedding=campplus_model.encode(reference_audio)
)
```

**配置文件**: `models/config_dit_mel_seed_uvit_whisper_small_wavenet.yml`

---

#### 5. Whisper (OpenAI)

**技术类型**: 自动语音识别模型

**作用**: 将音频转换为文本，用于内容编码

**在项目中的位置**: SeedVC 内部使用

**模型**: `whisper-small` (约 244MB)

**优势**:
- 多语言支持
- 高识别准确率
- 鲁棒性强

**应用场景**:
- 作为 SeedVC 的语音内容编码器
- 提取音频的语义特征

---

#### 6. BigVGAN

**技术类型**: 神经声码器 (Neural Vocoder)

**作用**: 将 Mel 频谱转换为音频波形

**特点**:
- 22kHz 采样率
- 80 频带
- 高质量音频合成
- 快速推理速度

**模型路径**: `models/bigvgan_v2_22khz_80band_256x/`

---

#### 7. CAMPPlus

**技术类型**: 说话人识别/嵌入模型

**作用**: 提取说话人特征向量

**参数**:
- `feat_dim`: 80 (特征维度)
- `embedding_size`: 192 (嵌入向量大小)

**应用场景**:
- 语音克隆时的音色提取
- 说话人相似度计算

---

### 三、语音识别模型

#### 8. FunASR (ASR)

**技术类型**: 自动语音识别

**文件位置**: `services/tts/azure_tts_server/services/asr_service.py`

**作用**: 将音频转换为带时间戳的文本

**核心模型**:

| 模型 | 作用 | 模型名称 |
|------|------|----------|
| ASR 模型 | 语音识别 | speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn |
| VAD 模型 | 语音活动检测 | speech_fsmn_vad_zh-cn-16k-common-pytorch |
| 标点模型 | 添加标点符号 | punc_ct-transformer_cn-en-common-vocab471067-large |
| 说话人模型 | 说话人分离 | speech_campplus_sv_zh-cn_16k-common |

**关键代码**:
```python
from funasr import AutoModel

# 加载 ASR 模型
model = AutoModel(
    model="iic/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn",
    vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    punc_model="iic/punc_ct-transformer_cn-en-common-vocab471067-large",
    spk_model="iic/speech_campplus_sv_zh-cn_16k-common",
    device="cuda:0"
)

# 转录音频
result = model.generate(
    input=audio_path,
    sentence_timestamp=True,
    return_raw_text=True,
    is_final=True,
)
```

**输出格式**:
```python
SentenceInfo(
    text="识别的文本内容",
    start=1000,      # 开始时间 (毫秒)
    end=5000,        # 结束时间 (毫秒)
    spk_id=0         # 说话人 ID
)
```

**应用场景**:
- 音频转字幕
- 语音内容分析
- 字幕时间轴生成

---

### 四、大语言模型

#### 9. LLM (Large Language Models)

**文件位置**: `services/worker/utils/util.py`

**作用**: 生成图像描述文本、总结内容等

**支持的模型**:

| 模型 | 用途 | 特点 |
|------|------|------|
| deepseek-r1 | 推理、总结 | 深度推理能力强 |
| deepseek-v3 | 通用生成 | 性价比高 |
| gemini-2.5-flash | 快速生成 | 速度快，适合实时场景 |
| gpt-4o | 高质量生成 | 质量最高 |

**关键代码**:
```python
from openai import OpenAI

client = OpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_API_BASE
)

# 调用 LLM
response = client.chat.completions.create(
    model="deepseek-v3",
    messages=[{"role": "user", "content": prompt}],
    stream=False,
    max_tokens=200000
)

result = response.choices[0].message.content
```

**应用场景**:

1. **生成图像描述**: 从文本内容生成用于图像生成的英文提示词
```python
prompt = f"""
{text_content}

根据文章内容，为每个片段生成英文图像描述。
要求：30-50词，详细描述画面内容。
"""
image_prompt = chat_with_llm(prompt, model="deepseek-v3")
```

2. **生成角色描述**: 为数字人生成角色形象描述
```python
prompt = f"""
{content}

根据文章内容，总结出老人的特征，设定一个老人形象，
用一段英文(30-40词)来描述老人的正面全身。
"""
character_desc = chat_with_llm(prompt, model="gemini-2.5-flash")
```

3. **内容总结**: 生成视频标题、描述等

**配置环境变量**:
```env
LLM_API_KEY=your_api_key
LLM_API_BASE=https://api.deepseek.com/v1
```

---

### 五、OCR 模型

#### 10. OCR (Optical Character Recognition)

**文件位置**: `services/worker/utils/util.py`

**作用**: 检测生成图像中是否包含文字

**实现方式**: 调用外部 OCR 服务

**关键代码**:
```python
def ocr_image(image_path: str) -> Dict[str, Any]:
    """OCR图片识别"""
    ocr_url = f"{settings.OCR_SERVICE_URL}/ocr/"

    with open(image_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(ocr_url, files=files)
        return response.json()
```

**在图像生成中的应用**:
```python
# 检查生成的图像是否包含文字
result = ocr_image(filename)
ocr_result = result.get("ocr_result", [])

# 如果文字过多，重新生成
text_length = sum(len(x[-1][0]) for x in ocr_result[0] if x)
if len(text) > 10:
    # 重新生成图像
```

**作用**: 确保生成的图像不包含多余文字，保持画面纯净

---

### 六、技术架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          AI 模型技术架构                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                        图像生成流程                                        │  │
│  │  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │  │
│  │  │ 文本内容      │ ──> │  LLM         │ ──> │ 图像提示词    │            │  │
│  │  └──────────────┘     │ deepseek/v3  │     └──────┬───────┘            │  │
│  │                       └──────────────┘              │                      │  │
│  │                                                    │                      │  │
│  │                       ┌──────────────┐             ▼                      │  │
│  │  ┌──────────────┐     │  LoRA        │ <──────────┐                     │  │
│  │  │ Flux Pipeline │ ──>│ 风格模型      │             │                     │  │
│  │  │ Diffusers    │     └──────────────┘             │                     │  │
│  │  └──────┬───────┘                                  │                     │  │
│  │         │                                          │                     │  │
│  │         ▼                                          ▼                     │  │
│  │  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │  │
│  │  │ 生成图像      │ ──> │  OCR检测     │ ──> │ 质量验证      │            │  │
│  │  └──────────────┘     └──────────────┘     └──────────────┘            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                        语音生成流程                                        │  │
│  │  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │  │
│  │  │ 文本内容      │ ──> │  Whisper     │ ──> │ 语义特征     │            │  │
│  │  └──────────────┘     │ 内容编码      │     └──────┬───────┘            │  │
│  │                       └──────────────┘              │                      │  │
│  │  ┌──────────────┐              │                   │                     │  │
│  │  │ 参考音频      │ ──> ──────────> │  CAMPPlus ──> │ 说话人特征           │  │
│  │  └──────────────┘              │                   │                     │  │
│  │                                  │                   ▼                     │  │
│  │                                  └────────────────> │                     │  │
│  │                                                     │                     │  │
│  │                                  ┌─────────────────┤                     │  │
│  │                                  ▼                 ▼                     │  │
│  │                       ┌──────────────────────────────┐                │  │
│  │                       │          SeedVC DiT          │                │  │
│  │                       │      (Diffusion Transformer)  │                │  │
│  │                       └──────────────┬───────────────┘                │  │
│  │                                      │                               │  │
│  │                                      ▼                               │  │
│  │                       ┌──────────────────────────────┐                │  │
│  │                       │          BigVGAN Vocoder      │                │  │
│  │                       └──────────────┬───────────────┘                │  │
│  │                                      │                               │  │
│  │                                      ▼                               │  │
│  │                       ┌──────────────────────────────┐                │  │
│  │                       │        合成音频               │                │  │
│  │                       └──────────────────────────────┘                │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                        语音识别流程                                        │  │
│  │  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │  │
│  │  │ 音频文件      │ ──> │   FunASR     │ ──> │ 带时间戳文本  │            │  │
│  │  └──────────────┘     │  Paraformer   │     └──────────────┘            │  │
│  │                       │  VAD + PUNC   │                                   │  │
│  │                       │  说话人分离   │                                   │  │
│  │                       └──────────────┘                                   │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### 七、模型配置与优化

#### 模型路径配置

**Flux 模型**:
```python
# services/image_gen/flux_server/config/settings.py
FLUX_MODEL_PATH = "black-forest-labs/FLUX.1-dev"
LORA_BASE_PATH = "./loras/"
FLUX_DEVICE_ID = "0"
```

**SeedVC 模型**:
```python
# services/tts/seedvc_server/seedvc_run.py
DEFAULT_MODEL_PATHS = {
    'dit_checkpoint': 'models/DiT_seed_v2_uvit_whisper_small_wavenet_bigvgan_pruned.pth',
    'dit_config': 'models/config_dit_mel_seed_uvit_whisper_small_wavenet.yml',
    'campplus_checkpoint': 'models/campplus_cn_common.bin',
    'bigvgan_model': 'models/bigvgan_v2_22khz_80band_256x',
    'whisper_model': 'models/whisper-small',
}
```

**ASR 模型**:
```python
# services/tts/azure_tts_server/config/settings.py
asr_model_paths = {
    "model": "iic/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn",
    "vad_model": "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "punc_model": "iic/punc_ct-transformer_cn-en-common-vocab471067-large",
    "spk_model": "iic/speech_campplus_sv_zh-cn_16k-common",
}
```

#### 性能优化

**Flux 优化**:
```python
# 1. CPU Offload - 显存优化
pipe.enable_model_cpu_offload(device=f"cuda:{device_id}")

# 2. VAE Tiling - 大图像处理
pipe.enable_vae_tiling()

# 3. Torch Compile - 推理加速
pipe.transformer = torch.compile(
    pipe.transformer,
    mode="reduce-overhead"
)

# 4. TF32 - Ampere GPU 加速
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
```

**SeedVC 优化**:
```python
# CFM Cache - 条件流匹配缓存
model.cfm.estimator.setup_caches(
    max_batch_size=1,
    max_seq_length=8192
)

# FP16 推理
fp16 = True
```

---

### 八、模型使用总结

| 模型类型 | 模型名称 | 主要功能 | 文件位置 |
|---------|---------|---------|---------|
| 图像生成 | Flux.1-dev | 文生图 | `services/image_gen/flux_server/` |
| 模型微调 | LoRA | 风格化 | `services/image_gen/flux_server/loras/` |
| 框架库 | Diffusers | 扩散模型接口 | Hugging Face |
| 语音克隆 | SeedVC | 音色克隆+合成 | `services/tts/seedvc_server/` |
| 语音编码 | Whisper | 音频→语义特征 | SeedVC 内部 |
| 声码器 | BigVGAN | Mel频谱→音频 | SeedVC 内部 |
| 说话人嵌入 | CAMPPlus | 音色特征提取 | SeedVC 内部 |
| 语音识别 | FunASR | 音频→文本 | `services/tts/azure_tts_server/` |
| 大语言模型 | DeepSeek/Gemini | 文本生成/理解 | `services/worker/utils/` |
| 文字识别 | OCR | 图像文字检测 | 外部服务 |

---

## 完整代码逻辑流程

本章节详细展示从用户输入文本到最终生成视频的完整代码执行流程，包括每个阶段的代码实现细节。

### 总体流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          完整代码执行流程                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  阶段1: 用户输入处理         │
│  ├─ 请求验证                    │
│  ├─ 文本清理                    │
│  └─ 参数校验                    │
│                                                                             │
│  阶段2: 任务创建              │
│  ├─ JobService.create_job()     │
│  ├─ 数据库记录创建               │
│  └─ Celery 任务分发              │
│                                                                             │
│  阶段3: Celery 任务分发        │
│  ├─ process_video_job.delay()   │
│  └─ Redis 队列存储               │
│                                                                             │
│  阶段4: Worker 接收任务          │
│  ├─ Celery Worker 消费          │
│  ├─ JobExecution 创建           │
│  └─ Pipeline 上下文初始化        │
│                                                                             │
│  阶段5: Pipeline 构建           │
│  ├─ PipelineBuilder.build()     │
│  └─ 步骤组装                     │
│                                                                             │
│  阶段6-12: Pipeline 步骤执行     │
│  ├─ TTS 生成                    │
│  ├─ 字幕生成                     │
│  ├─ 文本分割                     │
│  ├─ 图像生成                     │
│  ├─ 视频合成                     │
│  ├─ 后处理                       │
│  └─ 文件上传                     │
│                                                                             │
│  阶段13: 结果返回               │
│  ├─ 状态更新                     │
│  └─ URL 生成                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 阶段1: 用户输入处理

当用户通过前端界面提交视频生成请求时，后端 API 首先接收并验证输入。

#### 1.1 API 端点接收请求

**文件位置**: `services/backend/api/job.py`

```python
@router.post("", response_model=JobCreateResponse)
async def create_job(
    job_data: JobCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    创建新的视频生成任务

    请求体包含:
    - title: 任务标题
    - content: 待转换的文本内容
    - language_id: 语言ID
    - voice_id: 音色ID
    - topic_id: 话题ID
    - account_id: 账号ID
    - speech_speed: 语速 (0.5-2.0)
    - is_horizontal: 是否横屏
    """
```

#### 1.2 用户认证验证

**文件位置**: `services/backend/api/job.py:254-266`

```python
async def create_job(
    job_data: JobCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    # 1. 从请求头获取用户信息
    user_id = getattr(request.state, "user_id", None)

    # 2. 验证用户身份
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 3. 检查用户是否存在
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
```

#### 1.3 文本清理和验证

**文件位置**: `services/backend/api/utils.py`

```python
def sanitize_text(text: str) -> str:
    """
    清理文本内容，移除控制字符和标记内容

    1. 移除标记内容 (#@#...#@#)
    2. 移除控制字符
    3. 限制文本长度
    """
    if not text:
        return text

    # 移除标记内容
    pattern = r'#@#.*?#@#'
    text = re.sub(pattern, '', text, flags=re.DOTALL)

    # 移除控制字符（保留换行和制表符）
    text = ''.join(char for char in text
                   if char == '\n' or char == '\t' or char.isprintable())

    return text.strip()


def validate_job_request(job_data: JobCreate) -> None:
    """
    验证任务请求参数

    检查:
    - 标题长度 (1-255字符)
    - 内容长度 (1-10000字符)
    - 语速范围 (0.5-2.0)
    - 语言、音色、话题是否有效
    """
    if not job_data.title or len(job_data.title) > 255:
        raise ValueError("Invalid title length")

    if not job_data.content or len(job_data.content) > 10000:
        raise ValueError("Invalid content length")

    if job_data.speech_speed < 0.5 or job_data.speech_speed > 2.0:
        raise ValueError("Speech speed must be between 0.5 and 2.0")
```

---

### 阶段2: 任务创建 (JobService)

验证通过后，后端创建 Job 记录并分发 Celery 任务。

#### 2.1 JobService.create_job() 实现

**文件位置**: `services/backend/service/job.py`

```python
def create_job(
    db: Session,
    user_id: str,
    title: str,
    content: str,
    description: Optional[str] = None,
    publish_title: Optional[str] = None,
    language_id: Optional[int] = None,
    voice_id: Optional[int] = None,
    topic_id: Optional[int] = None,
    account_id: Optional[int] = None,
    speech_speed: float = 0.9,
    is_horizontal: bool = True,
    extra: Optional[Dict] = None
) -> Job:
    """
    创建新的视频生成任务

    步骤:
    1. 验证关联实体存在性
    2. 创建 Job 记录
    3. 分发 Celery 任务
    4. 返回创建的任务
    """

    # 1. 验证语言存在
    if language_id:
        language = db.query(Language).filter(
            Language.id == language_id
        ).first()
        if not language:
            raise ValueError(f"Language {language_id} not found")

    # 2. 验证音色存在
    if voice_id:
        voice = db.query(Voice).filter(
            Voice.id == voice_id
        ).first()
        if not voice:
            raise ValueError(f"Voice {voice_id} not found")

    # 3. 验证话题存在
    if topic_id:
        topic = db.query(Topic).filter(
            Topic.id == topic_id
        ).first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")

    # 4. 验证账号存在
    if account_id:
        account = db.query(Account).filter(
            Account.id == account_id
        ).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")

    # 5. 清理文本内容
    cleaned_content = sanitize_text(content)

    # 6. 创建 Job 记录
    job = Job(
        runorder=0,  # 可根据业务需求调整
        title=title,
        content=cleaned_content,
        description=description,
        publish_title=publish_title,
        language_id=language_id,
        voice_id=voice_id,
        topic_id=topic_id,
        account_id=account_id,
        speech_speed=speech_speed,
        is_horizontal=is_horizontal,
        extra=extra or {}
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(f"Created job {job.id} for user {user_id}")

    return job
```

#### 2.2 Celery 任务分发

**文件位置**: `services/backend/api/job.py:320-336`

```python
from services.worker.tasks import process_video_job

# 创建任务后立即分发
try:
    # 使用 .delay() 异步分发任务
    task_result = process_video_job.delay(job.id)

    logger.info(f"Dispatched job {job.id} to Celery. Task ID: {task_result.id}")

except Exception as e:
    logger.error(f"Failed to dispatch job {job.id}: {e}")
    # 即使分发失败，任务已创建，可通过状态查询重试
```

---

### 阶段3: Celery 任务队列

任务被发送到 Redis 作为消息队列，等待 Worker 处理。

#### 3.1 Celery 配置

**文件位置**: `core/config/celery_config.py`

```python
from celery import Celery

# 创建 Celery 应用
celery_app = Celery('BatchVideo')

# Broker 配置 (Redis)
celery_app.conf.broker_url = 'redis://localhost:6379/0'

# Backend 配置 (存储结果)
celery_app.conf.result_backend = 'redis://localhost:6379/0'

# 任务序列化
celery_app.conf.task_serializer = 'json'
celery_app.conf.accept_content = ['json']
celery_app.conf.result_serializer = 'json'

# 时区设置
celery_app.conf.timezone = 'Asia/Shanghai'

# 任务路由
celery_app.conf.task_routes = {
    'services.worker.tasks.process_video_job': {'queue': 'video_tasks'},
    'services.worker.tasks.reset_stuck_jobs': {'queue': 'maintenance'},
}

# 超时配置
celery_app.conf.task_time_limit = 3600  # 1小时硬限制
celery_app.conf.task_soft_time_limit = 3300  # 55分钟软限制
```

#### 3.2 任务消息存储

当 `process_video_job.delay(job_id)` 被调用时:

```python
# 存储在 Redis 中的任务消息结构
task_message = {
    "task": "services.worker.tasks.process_video_job",
    "id": "uuid-task-id",
    "args": [job_id],  # 位置参数
    "kwargs": {},      # 关键字参数
    "retries": 0,
    "eta": None,       # 预定执行时间
}
```

---

### 阶段4: Worker 接收任务

Celery Worker 从队列中获取任务并开始处理。

#### 4.1 Celery 任务定义

**文件位置**: `services/worker/tasks.py:217-273`

```python
from celery import shared_task
from celery.utils.log import get_task_logger
from services.worker.job_processing.job_executor import JobExecutor

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name='services.worker.tasks.process_video_job',
    base=DatabaseTask,  # 自定义基类，管理数据库会话
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=3300,  # 55分钟软限制
    time_limit=3600,  # 1小时硬限制
)
def process_video_job(self, job_id: int) -> Dict[str, Any]:
    """
    处理视频生成任务

    Args:
        job_id: 任务ID

    Returns:
        包含执行结果的字典
    """
    db = self.db  # 从 DatabaseTask 获取数据库会话

    logger.info(f"Processing job {job_id} on worker {socket.gethostname()}")

    # 1. 查询任务配置
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found")
        return {"status": "error", "message": "Job not found"}

    # 2. 检查任务是否已删除
    if job.deleted_at is not None:
        logger.warning(f"Job {job_id} is deleted, skipping")
        return {"status": "skipped", "message": "Job is deleted"}

    # 3. 创建 JobExecution 记录
    execution = JobExecution(
        job_id=job.id,
        status=ExecutionStatus.PENDING,
        worker_hostname=socket.gethostname(),
        retry_count=0,
        started_at=get_beijing_time()
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    try:
        # 4. 检查是否有正在运行的执行
        running_execution = db.query(JobExecution).filter(
            JobExecution.job_id == job_id,
            JobExecution.status == ExecutionStatus.RUNNING,
            JobExecution.id != execution.id
        ).first()

        if running_execution:
            logger.warning(f"Job {job_id} already running on {running_execution.worker_hostname}")
            execution.status = ExecutionStatus.SKIPPED
            execution.status_detail = "Another execution is already running"
            execution.finished_at = get_beijing_time()
            db.commit()
            return {"status": "skipped"}

        # 5. 更新状态为运行中
        execution.status = ExecutionStatus.RUNNING
        execution.status_detail = "Pipeline execution started"
        db.commit()

        # 6. 执行视频生成流程
        executor = JobExecutor(db, job, execution)
        result = executor.execute()

        # 7. 更新执行状态
        if result.get("success"):
            execution.status = ExecutionStatus.SUCCESS
            execution.status_detail = "Job completed successfully"
            execution.result_key = json.dumps(result.get("result_key", {}))
        else:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = result.get("error", "Unknown error")

        execution.finished_at = get_beijing_time()
        db.commit()

        logger.info(f"Job {job_id} completed with status: {execution.status}")
        return {"status": execution.status, "result": result}

    except SoftTimeLimitExceeded:
        # 软超时处理
        logger.error(f"Job {job_id} exceeded soft time limit")
        execution.status = ExecutionStatus.FAILED
        execution.error_message = "Task timeout (soft limit exceeded)"
        execution.finished_at = get_beijing_time()
        db.commit()
        return {"status": "timeout"}

    except Exception as e:
        # 异常处理和重试
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)

        execution.retry_count += 1
        execution.error_message = str(e)

        # 检查是否需要重试
        if execution.retry_count < self.max_retries:
            execution.status = ExecutionStatus.PENDING
            execution.status_detail = f"Retry {execution.retry_count}/{self.max_retries}"
            db.commit()

            # 指数退避重试
            countdown = 60 * (2 ** execution.retry_count)
            raise self.retry(exc=e, countdown=countdown)

        execution.status = ExecutionStatus.FAILED
        execution.finished_at = get_beijing_time()
        db.commit()

        return {"status": "failed", "error": str(e)}
```

#### 4.2 DatabaseTask 基类

**文件位置**: `services/worker/tasks.py:40-90`

```python
from celery import Task

class DatabaseTask(Task):
    """
    Celery 任务基类，管理数据库会话
    """
    _db = None

    @property
    def db(self) -> Session:
        """获取或创建数据库会话"""
        if self._db is None:
            from core.db.session import get_db_factory
            db_factory = get_db_factory()
            self._db = db_factory()
        return self._db

    def after_return(self, *args, **kwargs):
        """任务完成后关闭数据库会话"""
        if self._db is not None:
            self._db.close()
            self._db = None
```

---

### 阶段5: Pipeline 构建

JobExecutor 创建 Pipeline 上下文并构建处理流程。

#### 5.1 JobExecutor 实现

**文件位置**: `services/worker/job_processing/job_executor.py`

```python
from services.worker.pipeline import PipelineBuilder, PipelineContext
from services.worker.pipeline.context import ContextConfig
import logging

logger = logging.getLogger(__name__)


class JobExecutor:
    """
    任务执行器，负责协调 Pipeline 的执行

    职责:
    1. 创建 Pipeline 上下文
    2. 构建 Pipeline
    3. 执行 Pipeline
    4. 处理执行结果
    """

    def __init__(self, db: Session, job: Job, execution: JobExecution):
        self.db = db
        self.job = job
        self.execution = execution

    def execute(self) -> Dict[str, Any]:
        """
        执行视频生成流程

        Returns:
            执行结果字典
        """
        try:
            # 1. 加载关联数据
            language = self.job.language
            voice = self.job.voice
            topic = self.job.topic
            account = self.job.account

            # 2. 创建上下文配置
            config = ContextConfig(
                job_id=self.job.id,
                user_id=str(self.job.user_id) if hasattr(self.job, 'user_id') else None,
                title=self.job.title,
                content=self.job.content,
                description=self.job.description,
                publish_title=self.job.publish_title,
                speech_speed=self.job.speech_speed,
                is_horizontal=self.job.is_horizontal,
                language_name=language.name if language else "zh-CN",
                reference_audio_path=voice.path if voice else None,
                topic_prompts={
                    "prompt_gen_image": topic.prompt_gen_image if topic else "",
                    "prompt_cover_image": topic.prompt_cover_image if topic else "",
                },
                loras={
                    "loraname": topic.loraname if topic else None,
                    "loraweight": topic.loraweight if topic else None,
                } if topic else {},
                logo_path=account.logo if account else None,
                extra=self.job.extra or {}
            )

            # 3. 创建 Pipeline 上下文
            context = PipelineContext(config, self.db)
            context.initialize_working_directory()

            logger.info(f"Initialized context for job {self.job.id} at {context.working_dir}")

            # 4. 构建 Pipeline
            pipeline = PipelineBuilder.build_standard_pipeline(
                context=context,
                functional_mode=False  # 使用传统模式
            )

            # 5. 执行 Pipeline
            logger.info(f"Starting pipeline execution for job {self.job.id}")
            pipeline.execute()

            # 6. 收集结果
            result = self._collect_results(context)

            # 7. 清理临时文件（可选）
            # context.cleanup()

            return {
                "success": True,
                "result_key": result
            }

        except Exception as e:
            logger.error(f"Pipeline execution failed for job {self.job.id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _collect_results(self, context: PipelineContext) -> Dict[str, str]:
        """
        收集执行结果

        Returns:
            OSS key 字典
        """
        from services.worker.services.oss_service import OssManager

        oss_manager = OssManager()

        result = {}

        # 上传音频
        if context.audio_path:
            audio_key = oss_manager.upload_file(
                context.audio_path,
                f"jobs/{self.job.id}/audio.mp3"
            )
            result["audio_oss_key"] = audio_key

        # 上传字幕
        if context.srt_path:
            srt_key = oss_manager.upload_file(
                context.srt_path,
                f"jobs/{self.job.id}/subtitle.srt"
            )
            result["srt_oss_key"] = srt_key

        # 上传合成视频
        if context.combined_video:
            video_key = oss_manager.upload_file(
                context.combined_video,
                f"jobs/{self.job.id}/video_combined.mp4"
            )
            result["combined_video_oss_key"] = video_key

        # 上传带Logo视频
        if context.logoed_video:
            logoed_key = oss_manager.upload_file(
                context.logoed_video,
                f"jobs/{self.job.id}/video_logoed.mp4"
            )
            result["logoed_video_oss_key"] = logoed_key

        # 上传封面图
        if context.cover_image_path:
            cover_key = oss_manager.upload_file(
                context.cover_image_path,
                f"jobs/{self.job.id}/cover.jpg"
            )
            result["cover_oss_key"] = cover_key

        return result
```

#### 5.2 PipelineBuilder 实现

**文件位置**: `services/worker/pipeline/pipeline.py`

```python
from typing import List, TYPE_CHECKING
from services.worker.pipeline.steps import (
    TTSGenerationStep,
    SubtitleGenerationStep,
    TextSplitStep,
    ImageGenerationStep,
    VideoCompositionStep,
    DigitalHumanStep,
    PostProcessingStep,
    UploadStep
)

if TYPE_CHECKING:
    from services.worker.pipeline.context import PipelineContext


class PipelineBuilder:
    """
    Pipeline 构建器

    负责组装视频生成的各个步骤
    """

    @staticmethod
    def build_standard_pipeline(
        context: 'PipelineContext',
        functional_mode: bool = False
    ) -> 'Pipeline':
        """
        构建标准视频生成 Pipeline

        步骤顺序:
        1. TTS 生成
        2. 字幕生成
        3. 文本分割
        4. 图像生成
        5. 视频合成
        6. 数字人合成 (可选)
        7. 后处理
        8. 文件上传

        Args:
            context: Pipeline 上下文
            functional_mode: 是否使用函数式模式

        Returns:
            配置好的 Pipeline 实例
        """
        steps: List[PipelineStep] = [
            # 阶段1: 音频生成
            TTSGenerationStep(
                name="TTSGeneration",
                description="生成语音音频",
                context=context
            ),

            # 阶段2: 字幕生成
            SubtitleGenerationStep(
                name="SubtitleGeneration",
                description="生成SRT字幕",
                context=context
            ),

            # 阶段3: 文本分割
            TextSplitStep(
                name="TextSplit",
                description="分割文本为片段",
                context=context
            ),

            # 阶段4: 图像生成
            ImageGenerationStep(
                name="ImageGeneration",
                description="生成AI图像",
                context=context,
                max_retries=30,
                retry_delay=5
            ),

            # 阶段5: 视频合成
            VideoCompositionStep(
                name="VideoComposition",
                description="合成视频",
                context=context
            ),

            # 阶段6: 数字人合成 (条件执行)
            DigitalHumanStep(
                name="DigitalHuman",
                description="数字人视频合成",
                context=context,
                enabled=self._should_enable_digital_human(context)
            ),

            # 阶段7: 后处理
            PostProcessingStep(
                name="PostProcessing",
                description="视频后处理",
                context=context
            ),

            # 阶段8: 文件上传
            UploadStep(
                name="Upload",
                description="上传文件到OSS",
                context=context
            ),
        ]

        return Pipeline(
            steps=steps,
            context=context,
            functional_mode=functional_mode
        )

    @staticmethod
    def _should_enable_digital_human(context: 'PipelineContext') -> bool:
        """判断是否启用数字人步骤"""
        extra = context.extra or {}
        return extra.get("enable_digital_human", False)
```

#### 5.3 Pipeline 类实现

**文件位置**: `services/worker/pipeline/pipeline.py`

```python
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Pipeline:
    """
    视频生成 Pipeline

    负责按顺序执行各个处理步骤
    """

    def __init__(
        self,
        steps: List['PipelineStep'],
        context: 'PipelineContext',
        functional_mode: bool = False
    ):
        self.steps = steps
        self.context = context
        self.functional_mode = functional_mode

    def execute(self) -> None:
        """
        执行 Pipeline（传统模式）

        在传统模式下，步骤结果存储在 context 中，
        通过 context 属性访问中间结果。
        """
        self.context.started_at = datetime.now()

        for step in self.steps:
            # 检查步骤是否启用
            if hasattr(step, 'enabled') and not step.enabled:
                logger.info(f"Skipping disabled step: {step.name}")
                continue

            # 开始执行步骤
            logger.info(f"Executing step: {step.name}")
            step_context = self.context.create_step_context(step.name)
            step_context.status = StepStatus.RUNNING
            step_context.started_at = datetime.now()

            try:
                # 执行步骤
                step.execute()

                # 标记步骤完成
                step_context.status = StepStatus.COMPLETED
                step_context.finished_at = datetime.now()

                logger.info(f"Step {step.name} completed successfully")

            except Exception as e:
                # 标记步骤失败
                step_context.status = StepStatus.FAILED
                step_context.error_message = str(e)
                step_context.finished_at = datetime.now()

                logger.error(f"Step {step.name} failed: {e}", exc_info=True)

                # 根据配置决定是否继续
                if getattr(step, 'continue_on_error', False):
                    logger.warning(f"Step {step.name} failed, continuing...")
                    continue
                else:
                    raise

        self.context.finished_at = datetime.now()

    def execute_functional(self) -> Dict[str, Any]:
        """
        执行 Pipeline（函数式模式）

        在函数式模式下，每个步骤返回结果对象，
        通过结果字典访问中间结果。
        """
        results = {}
        self.context.started_at = datetime.now()

        for step in self.steps:
            if hasattr(step, 'enabled') and not step.enabled:
                continue

            logger.info(f"Executing step: {step.name}")
            step_context = self.context.create_step_context(step.name)
            step_context.status = StepStatus.RUNNING
            step_context.started_at = datetime.now()

            try:
                # 执行步骤并获取结果
                result = step.execute_functional()
                results[step.name] = result

                step_context.status = StepStatus.COMPLETED
                step_context.finished_at = datetime.now()

            except Exception as e:
                step_context.status = StepStatus.FAILED
                step_context.error_message = str(e)
                step_context.finished_at = datetime.now()

                if not getattr(step, 'continue_on_error', False):
                    raise

        self.context.finished_at = datetime.now()
        return results
```

---

### 阶段6: TTS 生成

第一个 Pipeline 步骤，将文本转换为语音。

#### 6.1 TTSGenerationStep 实现

**文件位置**: `services/worker/pipeline/steps/tts_generation_step.py`

```python
import os
import logging
from typing import Optional
from services.worker.pipeline.steps.base import PipelineStep
from services.worker.services.tts_service import TTSService

logger = logging.getLogger(__name__)


class TTSGenerationStep(PipelineStep):
    """
    TTS 生成步骤

    职责:
    1. 调用 TTS 服务生成音频
    2. 保存音频文件
    3. 提取音频元数据
    """

    def __init__(self, name: str, description: str, context: 'PipelineContext'):
        super().__init__(name, description, context)
        self.tts_service = TTSService()

    def execute(self) -> None:
        """执行 TTS 生成"""
        try:
            # 1. 准备输出路径
            output_path = os.path.join(
                self.context.working_dir,
                "audio.mp3"
            )

            # 2. 准备 TTS 参数
            tts_params = {
                "text": self.context.content,
                "language": self.context.language_name,
                "reference_audio": self.context.reference_audio_path,
                "speed": self.context.speech_speed,
            }

            logger.info(f"Generating TTS for job {self.context.job_id}")

            # 3. 调用 TTS 服务
            audio_path, duration = self.tts_service.generate_speech(
                output_path=output_path,
                **tts_params
            )

            # 4. 存储结果到 context
            self.context.audio_path = audio_path
            self.context.audio_duration = duration

            logger.info(f"TTS generated: {audio_path}, duration: {duration:.2f}s")

        except Exception as e:
            logger.error(f"TTS generation failed: {e}", exc_info=True)
            raise

    def execute_functional(self) -> 'TTSResult':
        """执行 TTS 生成（函数式模式）"""
        self.execute()
        return TTSResult(
            audio_path=self.context.audio_path,
            duration=self.context.audio_duration
        )
```

#### 6.2 TTSService 实现

**文件位置**: `services/worker/services/tts_service.py`

```python
import os
import requests
import logging
from typing import Tuple, Optional
from core.config.constants import TTSEndpoints

logger = logging.getLogger(__name__)


class TTSService:
    """
    TTS 服务客户端

    支持:
    - SeedVC TTS
    - Azure TTS
    """

    def __init__(self):
        self.seedvc_endpoint = TTSEndpoints.SEEDVC_URL
        self.azure_endpoint = TTSEndpoints.AZURE_TTS_URL

    def generate_speech(
        self,
        text: str,
        language: str,
        output_path: str,
        reference_audio: Optional[str] = None,
        speed: float = 1.0,
        provider: str = "seedvc"
    ) -> Tuple[str, float]:
        """
        生成语音

        Args:
            text: 待转换文本
            language: 语言代码
            output_path: 输出文件路径
            reference_audio: 参考音频路径（用于音色克隆）
            speed: 语速
            provider: TTS 提供商 (seedvc/azure)

        Returns:
            (音频路径, 时长秒数)
        """
        if provider == "seedvc":
            return self._generate_with_seedvc(
                text, language, output_path, reference_audio, speed
            )
        elif provider == "azure":
            return self._generate_with_azure(
                text, language, output_path, speed
            )
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")

    def _generate_with_seedvc(
        self,
        text: str,
        language: str,
        output_path: str,
        reference_audio: Optional[str],
        speed: float
    ) -> Tuple[str, float]:
        """使用 SeedVC 生成语音"""
        try:
            # 准备请求数据
            files = {}
            data = {
                "text": text,
                "language": language,
                "speed": str(speed),
            }

            # 添加参考音频（音色）
            if reference_audio and os.path.exists(reference_audio):
                files["reference_audio"] = open(reference_audio, "rb")

            # 发送请求
            response = requests.post(
                f"{self.seedvc_endpoint}/tts",
                data=data,
                files=files,
                timeout=300  # 5分钟超时
            )

            if response.status_code != 200:
                raise Exception(f"SeedVC TTS failed: {response.text}")

            # 保存音频文件
            with open(output_path, "wb") as f:
                f.write(response.content)

            # 获取时长
            duration = self._get_audio_duration(output_path)

            logger.info(f"SeedVC TTS generated: {output_path}")
            return output_path, duration

        finally:
            if "reference_audio" in files:
                files["reference_audio"].close()

    def _generate_with_azure(
        self,
        text: str,
        language: str,
        output_path: str,
        speed: float
    ) -> Tuple[str, float]:
        """使用 Azure TTS 生成语音"""
        try:
            # 准备请求数据
            data = {
                "text": text,
                "language": language,
                "speed": str(speed),
            }

            # 发送请求
            response = requests.post(
                f"{self.azure_endpoint}/tts",
                json=data,
                timeout=300
            )

            if response.status_code != 200:
                raise Exception(f"Azure TTS failed: {response.text}")

            # 保存音频文件
            with open(output_path, "wb") as f:
                f.write(response.content)

            # 获取时长
            duration = self._get_audio_duration(output_path)

            logger.info(f"Azure TTS generated: {output_path}")
            return output_path, duration

        except Exception as e:
            logger.error(f"Azure TTS error: {e}")
            raise

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        from pydub import AudioSegment

        audio = AudioSegment.from_mp3(audio_path)
        return len(audio) / 1000.0  # 转换为秒
```

---

### 阶段7: 字幕生成

根据音频时长生成 SRT 格式字幕。

#### 7.1 SubtitleGenerationStep 实现

**文件位置**: `services/worker/pipeline/steps/subtitle_generation_step.py`

```python
import os
import logging
from services.worker.pipeline.steps.base import PipelineStep
from services.worker.services.subtitle_service import SubtitleService

logger = logging.getLogger(__name__)


class SubtitleGenerationStep(PipelineStep):
    """
    字幕生成步骤

    职责:
    1. 根据音频时长分割文本
    2. 计算时间戳
    3. 生成 SRT 格式字幕
    """

    def __init__(self, name: str, description: str, context: 'PipelineContext'):
        super().__init__(name, description, context)
        self.subtitle_service = SubtitleService()

    def execute(self) -> None:
        """执行字幕生成"""
        try:
            # 1. 准备输出路径
            srt_path = os.path.join(
                self.context.working_dir,
                "subtitle.srt"
            )

            # 2. 获取音频时长
            duration = self.context.audio_duration

            # 3. 生成字幕
            segments = self.subtitle_service.generate_subtitle(
                text=self.context.content,
                duration=duration,
                output_path=srt_path
            )

            # 4. 存储结果
            self.context.srt_path = srt_path
            self.context.subtitle_segments = segments

            logger.info(f"Subtitle generated: {srt_path}, segments: {len(segments)}")

        except Exception as e:
            logger.error(f"Subtitle generation failed: {e}", exc_info=True)
            raise
```

#### 7.2 SubtitleService 实现

**文件位置**: `services/worker/services/subtitle_service.py`

```python
import os
import logging
from typing import List, Dict
from services.worker.utils.text_utils import split_text_by_duration

logger = logging.getLogger(__name__)


class SubtitleService:
    """
    字幕生成服务

    职责:
    1. 智能分割文本
    2. 计算时间戳
    3. 生成 SRT 格式
    """

    def generate_subtitle(
        self,
        text: str,
        duration: float,
        output_path: str,
        words_per_second: float = 3.0
    ) -> List[Dict]:
        """
        生成 SRT 字幕

        Args:
            text: 原始文本
            duration: 音频时长（秒）
            output_path: 输出文件路径
            words_per_second: 每秒字数（用于分割）

        Returns:
            字幕片段列表
        """
        # 1. 分割文本
        segments = split_text_by_duration(
            text=text,
            duration=duration,
            words_per_second=words_per_second
        )

        # 2. 生成 SRT 内容
        srt_content = self._generate_srt_content(segments, duration)

        # 3. 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)

        logger.info(f"SRT subtitle generated: {output_path}")
        return segments

    def _generate_srt_content(self, segments: List[Dict], total_duration: float) -> str:
        """生成 SRT 格式内容"""
        srt_lines = []

        # 计算每个片段的时长
        segment_duration = total_duration / len(segments)

        for i, segment in enumerate(segments, 1):
            # 计算时间戳
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration

            # 格式化时间戳 (HH:MM:SS,mmm)
            start_str = self._format_timestamp(start_time)
            end_str = self._format_timestamp(end_time)

            # 添加 SRT 行
            srt_lines.append(str(i))
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(segment['text'])
            srt_lines.append("")  # 空行分隔

        return '\n'.join(srt_lines)

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳为 SRT 格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
```

---

### 阶段8: 文本分割

将文本分割为适合视频的片段，每个片段对应一个图像。

#### 8.1 TextSplitStep 实现

**文件位置**: `services/worker/pipeline/steps/text_split_step.py`

```python
import os
import logging
import json
from typing import List, Dict
from services.worker.pipeline.steps.base import PipelineStep

logger = logging.getLogger(__name__)


class TextSplitStep(PipelineStep):
    """
    文本分割步骤

    职责:
    1. 解析 SRT 字幕
    2. 提取文本片段
    3. 为每个片段生成图像提示词
    """

    def __init__(self, name: str, description: str, context: 'PipelineContext'):
        super().__init__(name, description, context)

    def execute(self) -> None:
        """执行文本分割"""
        try:
            # 1. 解析 SRT 字幕
            splits = self._parse_srt(self.context.srt_path)

            # 2. 为每个片段生成图像提示词
            for split in splits:
                split['prompt'] = self._generate_prompt(split['text'])

            # 3. 保存分割信息
            splits_path = os.path.join(
                self.context.working_dir,
                "splits.json"
            )
            with open(splits_path, 'w', encoding='utf-8') as f:
                json.dump(splits, f, ensure_ascii=False, indent=2)

            # 4. 存储结果
            self.context.splits = splits

            logger.info(f"Text split into {len(splits)} segments")

        except Exception as e:
            logger.error(f"Text split failed: {e}", exc_info=True)
            raise

    def _parse_srt(self, srt_path: str) -> List[Dict]:
        """解析 SRT 字幕文件"""
        splits = []

        with open(srt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 跳过空行和序号行
            if not line or line.isdigit():
                i += 1
                continue

            # 解析时间戳行
            if '-->' in line:
                time_range = line
                # 解析开始和结束时间
                start_str, end_str = time_range.split('-->')
                start_ms = self._parse_time_to_ms(start_str.strip())
                end_ms = self._parse_time_to_ms(end_str.strip())

                # 读取文本内容
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1

                text = ' '.join(text_lines)

                splits.append({
                    'start': start_ms,
                    'end': end_ms,
                    'text': text,
                    'prompt': ''
                })

            i += 1

        return splits

    def _parse_time_to_ms(self, time_str: str) -> int:
        """解析 SRT 时间戳为毫秒"""
        # 格式: HH:MM:SS,mmm
        time_part, ms_part = time_str.split(',')
        h, m, s = time_part.split(':')

        total_ms = (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms_part)
        return total_ms

    def _generate_prompt(self, text: str) -> str:
        """为文本片段生成图像提示词"""
        # 组合话题提示词和文本内容
        topic_prompt = self.context.topic_prompts.get('prompt_gen_image', '')

        # 简化文本（去除标点符号）
        clean_text = text[:100]  # 限制长度

        # 组合提示词
        prompt = f"{topic_prompt} {clean_text}".strip()

        return prompt
```

---

### 阶段9: 图像生成

为每个文本片段生成对应的 AI 图像。

#### 9.1 ImageGenerationStep 实现

**文件位置**: `services/worker/pipeline/steps/image_generation_step.py`

```python
import os
import logging
from typing import List
from services.worker.pipeline.steps.base import PipelineStep
from services.worker.services.image_service import ImageService

logger = logging.getLogger(__name__)


class ImageGenerationStep(PipelineStep):
    """
    图像生成步骤

    职责:
    1. 为每个文本片段生成图像
    2. 支持批量生成
    3. 重试机制
    """

    def __init__(
        self,
        name: str,
        description: str,
        context: 'PipelineContext',
        max_retries: int = 30,
        retry_delay: int = 5
    ):
        super().__init__(name, description, context)
        self.image_service = ImageService()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def execute(self) -> None:
        """执行图像生成"""
        try:
            splits = self.context.splits
            image_paths = []

            # 1. 为每个片段生成图像
            for i, split in enumerate(splits):
                logger.info(f"Generating image {i+1}/{len(splits)}")

                output_path = os.path.join(
                    self.context.working_dir,
                    f"image_{i:03d}.jpg"
                )

                # 准备生成参数
                prompt = split['prompt']
                lora_name = self.context.loras.get('loraname')
                lora_weight = self.context.loras.get('loraweight', 50)

                # 带重试的生成
                image_path = self._generate_with_retry(
                    prompt=prompt,
                    output_path=output_path,
                    lora_name=lora_name,
                    lora_weight=lora_weight
                )

                image_paths.append(image_path)
                split['image_path'] = image_path

            # 2. 存储结果
            self.context.image_paths = image_paths

            logger.info(f"Generated {len(image_paths)} images")

        except Exception as e:
            logger.error(f"Image generation failed: {e}", exc_info=True)
            raise

    def _generate_with_retry(
        self,
        prompt: str,
        output_path: str,
        lora_name: str = None,
        lora_weight: int = 50
    ) -> str:
        """带重试的图像生成"""
        import time

        for attempt in range(self.max_retries):
            try:
                return self.image_service.generate_image(
                    prompt=prompt,
                    output_path=output_path,
                    lora_name=lora_name,
                    lora_weight=lora_weight
                )
            except Exception as e:
                logger.warning(f"Image generation attempt {attempt+1} failed: {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
```

#### 9.2 ImageService 实现

**文件位置**: `services/worker/services/image_service.py`

```python
import os
import logging
import requests
from typing import Optional
from core.config.constants import ImageGenEndpoints

logger = logging.getLogger(__name__)


class ImageService:
    """
    图像生成服务客户端

    使用 Flux AI 模型生成图像
    """

    def __init__(self):
        self.endpoint = ImageGenEndpoints.FLUX_URL

    def generate_image(
        self,
        prompt: str,
        output_path: str,
        lora_name: Optional[str] = None,
        lora_weight: int = 50,
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 28
    ) -> str:
        """
        生成 AI 图像

        Args:
            prompt: 图像生成提示词
            output_path: 输出文件路径
            lora_name: LoRA 模型名称
            lora_weight: LoRA 权重
            width: 图像宽度
            height: 图像高度
            num_inference_steps: 推理步数

        Returns:
            生成的图像路径
        """
        try:
            # 准备请求数据
            payload = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_inference_steps": num_inference_steps,
            }

            # 添加 LoRA 配置
            if lora_name:
                payload["lora_name"] = lora_name
                payload["lora_weight"] = lora_weight

            logger.info(f"Generating image with prompt: {prompt[:50]}...")

            # 发送请求
            response = requests.post(
                f"{self.endpoint}/generate",
                json=payload,
                timeout=300  # 5分钟超时
            )

            if response.status_code != 200:
                raise Exception(f"Image generation failed: {response.text}")

            # 保存图像
            with open(output_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"Image saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Image generation error: {e}")
            raise
```

---

### 阶段10: 视频合成

将音频和图像合成为视频。

#### 10.1 VideoCompositionStep 实现

**文件位置**: `services/worker/pipeline/steps/video_composition_step.py`

```python
import os
import logging
from services.worker.pipeline.steps.base import PipelineStep
from services.worker.services.video_service import VideoService

logger = logging.getLogger(__name__)


class VideoCompositionStep(PipelineStep):
    """
    视频合成步骤

    职责:
    1. 使用 FFmpeg 合成视频
    2. 支持横竖屏切换
    3. 添加转场效果
    """

    def __init__(self, name: str, description: str, context: 'PipelineContext'):
        super().__init__(name, description, context)
        self.video_service = VideoService()

    def execute(self) -> None:
        """执行视频合成"""
        try:
            # 1. 准备输出路径
            output_path = os.path.join(
                self.context.working_dir,
                "video_combined.mp4"
            )

            # 2. 确定分辨率
            if self.context.is_horizontal:
                width, height = 1360, 768  # 横屏
            else:
                width, height = 768, 1360  # 竖屏

            # 3. 合成视频
            video_path = self.video_service.compose_video(
                audio_path=self.context.audio_path,
                image_paths=self.context.image_paths,
                splits=self.context.splits,
                output_path=output_path,
                width=width,
                height=height
            )

            # 4. 存储结果
            self.context.combined_video = video_path

            logger.info(f"Video composed: {video_path}")

        except Exception as e:
            logger.error(f"Video composition failed: {e}", exc_info=True)
            raise
```

#### 10.2 VideoService 实现

**文件位置**: `services/worker/services/video_service.py`

```python
import os
import logging
import subprocess
from typing import List, Dict
import ffmpeg

logger = logging.getLogger(__name__)


class VideoService:
    """
    视频处理服务

    使用 FFmpeg 进行视频合成
    """

    def compose_video(
        self,
        audio_path: str,
        image_paths: List[str],
        splits: List[Dict],
        output_path: str,
        width: int,
        height: int,
        transition_duration: float = 1.0
    ) -> str:
        """
        合成视频

        Args:
            audio_path: 音频文件路径
            image_paths: 图像路径列表
            splits: 分割信息（包含时间戳）
            output_path: 输出视频路径
            width: 视频宽度
            height: 视频高度
            transition_duration: 转场时长

        Returns:
            合成的视频路径
        """
        try:
            logger.info(f"Composing video with {len(image_paths)} images")

            # 1. 创建临时目录
            temp_dir = os.path.dirname(output_path)
            resized_dir = os.path.join(temp_dir, "resized")
            os.makedirs(resized_dir, exist_ok=True)

            # 2. 调整图像尺寸
            resized_paths = []
            for i, img_path in enumerate(image_paths):
                resized_path = os.path.join(resized_dir, f"resized_{i:03d}.jpg")
                self._resize_image(img_path, resized_path, width, height)
                resized_paths.append(resized_path)

            # 3. 计算每个图像的显示时长
            audio_duration = self._get_audio_duration(audio_path)
            segment_duration = audio_duration / len(resized_paths)

            # 4. 构建 FFmpeg 复杂滤镜
            filter_complex = self._build_filter_complex(
                resized_paths,
                segment_duration,
                width,
                height,
                transition_duration
            )

            # 5. 执行 FFmpeg 命令
            cmd = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
            ]

            # 添加输入图像
            for path in resized_paths:
                cmd.extend(['-loop', '1', '-i', path])

            # 添加音频
            cmd.extend(['-i', audio_path])

            # 添加滤镜
            cmd.extend(['-filter_complex', filter_complex])

            # 映射输出
            cmd.extend([
                '-map', f'[{len(resized_paths)}:v]',  # 视频流
                '-map', f'{len(resized_paths)}:a',     # 音频流
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-shortest',
                '-pix_fmt', 'yuv420p',
                output_path
            ])

            # 执行命令
            logger.info(f"Running FFmpeg command")
            subprocess.run(cmd, check=True, capture_output=True)

            logger.info(f"Video composed successfully: {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise

    def _resize_image(self, input_path: str, output_path: str, width: int, height: int):
        """调整图像尺寸"""
        (
            ffmpeg
            .input(input_path)
            .filter('scale', width, height, force_original_aspect_ratio='decrease')
            .filter('pad', width, height, '(ow-iw)/2', '(oh-ih)/2')
            .output(output_path, format='image2', vframes=1)
            .overwrite_output()
            .run(quiet=True)
        )

    def _build_filter_complex(
        self,
        image_paths: List[str],
        duration: float,
        width: int,
        height: int,
        transition: float
    ) -> str:
        """构建 FFmpeg 复杂滤镜"""
        filters = []

        # 为每个输入添加时长和淡入淡出效果
        for i, path in enumerate(image_paths):
            # 设置时长
            filters.append(f"[{i}:v]setpts=PTS-STARTPTS,scale={width}:{height}[v{i}]")

        # 叠加所有视频
        current = "[v0]"
        for i in range(1, len(image_paths)):
            next_input = f"[v{i}]"
            output = f"ov{i}" if i < len(image_paths) - 1 else "outv"

            # 计算开始时间
            start_time = i * (duration - transition)

            filters.append(
                f"{current}{next_input}overlay=x=0:y=0:enable='between(t,{start_time},{duration})'[{output}]"
            )
            current = f"[{output}]"

        return ";".join(filters)

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        probe = ffmpeg.probe(audio_path)
        return float(probe['streams'][0]['duration'])
```

---

### 阶段11: 后处理和上传

视频后处理（添加 Logo、水印）和上传到 OSS。

#### 11.1 PostProcessingStep 实现

**文件位置**: `services/worker/pipeline/steps/post_processing_step.py`

```python
import os
import logging
from services.worker.pipeline.steps.base import PipelineStep
from services.worker.services.video_service import VideoService

logger = logging.getLogger(__name__)


class PostProcessingStep(PipelineStep):
    """
    后处理步骤

    职责:
    1. 添加 Logo 和水印
    2. 视频压缩
    """

    def __init__(self, name: str, description: str, context: 'PipelineContext'):
        super().__init__(name, description, context)
        self.video_service = VideoService()

    def execute(self) -> None:
        """执行后处理"""
        try:
            input_video = self.context.combined_video
            logo_path = self.context.logo_path

            # 如果没有 Logo，跳过
            if not logo_path or not os.path.exists(logo_path):
                logger.info("No logo provided, skipping post-processing")
                self.context.logoed_video = input_video
                return

            # 准备输出路径
            output_path = os.path.join(
                self.context.working_dir,
                "video_logoed.mp4"
            )

            # 添加 Logo
            logoed_video = self.video_service.add_logo(
                input_video=input_video,
                logo_path=logo_path,
                output_path=output_path,
                position='bottom-right'
            )

            # 存储结果
            self.context.logoed_video = logoed_video

            logger.info(f"Post-processing completed: {logoed_video}")

        except Exception as e:
            logger.error(f"Post-processing failed: {e}", exc_info=True)
            # 不中断流程，使用原始视频
            self.context.logoed_video = self.context.combined_video
```

#### 11.2 UploadStep 实现

**文件位置**: `services/worker/pipeline/steps/upload_step.py`

```python
import os
import logging
from services.worker.pipeline.steps.base import PipelineStep
from services.worker.services.oss_service import OssManager

logger = logging.getLogger(__name__)


class UploadStep(PipelineStep):
    """
    上传步骤

    职责:
    1. 上传所有生成的文件到 OSS
    2. 生成签名 URL
    """

    def __init__(self, name: str, description: str, context: 'PipelineContext'):
        super().__init__(name, description, context)
        self.oss_manager = OssManager()

    def execute(self) -> None:
        """执行文件上传"""
        try:
            upload_results = {}

            # 1. 上传音频
            if self.context.audio_path and os.path.exists(self.context.audio_path):
                audio_key = self.oss_manager.upload_file(
                    self.context.audio_path,
                    f"jobs/{self.context.job_id}/audio.mp3"
                )
                upload_results["audio_oss_key"] = audio_key
                logger.info(f"Audio uploaded: {audio_key}")

            # 2. 上传字幕
            if self.context.srt_path and os.path.exists(self.context.srt_path):
                srt_key = self.oss_manager.upload_file(
                    self.context.srt_path,
                    f"jobs/{self.context.job_id}/subtitle.srt"
                )
                upload_results["srt_oss_key"] = srt_key
                logger.info(f"Subtitle uploaded: {srt_key}")

            # 3. 上传合成视频
            if self.context.combined_video and os.path.exists(self.context.combined_video):
                video_key = self.oss_manager.upload_file(
                    self.context.combined_video,
                    f"jobs/{self.context.job_id}/video_combined.mp4"
                )
                upload_results["combined_video_oss_key"] = video_key
                logger.info(f"Combined video uploaded: {video_key}")

            # 4. 上传带 Logo 视频
            if self.context.logoed_video and os.path.exists(self.context.logoed_video):
                logoed_key = self.oss_manager.upload_file(
                    self.context.logoed_video,
                    f"jobs/{self.context.job_id}/video_logoed.mp4"
                )
                upload_results["logoed_video_oss_key"] = logoed_key
                logger.info(f"Logoed video uploaded: {logoed_key}")

            # 5. 生成封面图
            if self.context.logoed_video:
                cover_path = os.path.join(
                    self.context.working_dir,
                    "cover.jpg"
                )
                self._generate_cover(self.context.logoed_video, cover_path)

                cover_key = self.oss_manager.upload_file(
                    cover_path,
                    f"jobs/{self.context.job_id}/cover.jpg"
                )
                upload_results["cover_oss_key"] = cover_key
                self.context.cover_image_path = cover_path
                logger.info(f"Cover uploaded: {cover_key}")

            # 6. 存储上传结果
            self.context.upload_results = upload_results

        except Exception as e:
            logger.error(f"Upload failed: {e}", exc_info=True)
            raise

    def _generate_cover(self, video_path: str, output_path: str):
        """从视频生成封面图"""
        import subprocess

        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', '00:00:01',  # 第1秒
            '-vframes', '1',
            '-q:v', '2',
            output_path
        ]

        subprocess.run(cmd, check=True, capture_output=True)
```

#### 11.3 OssManager 实现

**文件位置**: `services/worker/services/oss_service.py`

```python
import os
import logging
import oss2
from core.config.constants import OSSConfig

logger = logging.getLogger(__name__)


class OssManager:
    """
    OSS 文件管理器

    支持阿里云 OSS
    """

    def __init__(self):
        # 创建 Auth 实例
        auth = oss2.Auth(
            OSSConfig.ACCESS_KEY_ID,
            OSSConfig.ACCESS_KEY_SECRET
        )

        # 创建 Bucket 实例
        self.bucket = oss2.Bucket(
            auth,
            OSSConfig.ENDPOINT,
            OSSConfig.BUCKET_NAME
        )

    def upload_file(self, local_path: str, oss_key: str) -> str:
        """
        上传文件到 OSS

        Args:
            local_path: 本地文件路径
            oss_key: OSS 存储键

        Returns:
            OSS 键
        """
        try:
            # 上传文件
            result = self.bucket.put_object_from_file(oss_key, local_path)

            if result.status != 200:
                raise Exception(f"OSS upload failed: {result.status}")

            logger.info(f"Uploaded {local_path} to {oss_key}")
            return oss_key

        except Exception as e:
            logger.error(f"OSS upload error: {e}")
            raise

    def get_sign_url(self, oss_key: str, expiration: int = 3600) -> str:
        """
        生成签名 URL

        Args:
            oss_key: OSS 存储键
            expiration: 过期时间（秒）

        Returns:
            签名 URL
        """
        url = self.bucket.sign_url('GET', oss_key, expiration)
        return url

    def delete_file(self, oss_key: str) -> bool:
        """删除文件"""
        try:
            result = self.bucket.delete_object(oss_key)
            return result.status == 200
        except Exception as e:
            logger.error(f"OSS delete error: {e}")
            return False
```

---

### 阶段12: 结果返回

任务完成后，更新数据库状态并返回结果给用户。

#### 12.1 更新执行状态

**文件位置**: `services/worker/tasks.py:265-273`

```python
# 在 process_video_job 任务中

# 7. 更新执行状态
if result.get("success"):
    execution.status = ExecutionStatus.SUCCESS
    execution.status_detail = "Job completed successfully"
    execution.result_key = json.dumps(result.get("result_key", {}))
else:
    execution.status = ExecutionStatus.FAILED
    execution.error_message = result.get("error", "Unknown error")

execution.finished_at = get_beijing_time()
db.commit()
```

#### 12.2 用户查询结果

**文件位置**: `services/backend/api/job.py:440-492`

```python
@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    获取任务详情

    返回:
    - 任务基本信息
    - 执行状态
    - 结果文件 URL
    """
    user_id = getattr(request.state, "user_id", None)

    # 1. 查询任务
    job = JobService.get_job_with_topic(db, job_id, user_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # 2. 获取最新执行状态
    execution = job.latest_execution

    # 3. 解析结果键
    job_result_key = safe_json_loads(job.job_result_key) or {}

    # 4. 构建响应
    response_data = {
        "id": job.id,
        "title": job.title,
        "content": job.content,
        "status": execution.status if execution else "PENDING",
        "status_detail": execution.status_detail if execution else "",
        "language": {
            "id": job.language.id,
            "name": job.language.name,
            "language_name": job.language.language_name
        } if job.language else None,
        "voice": {
            "id": job.voice.id,
            "name": job.voice.name,
            "path": job.voice.path
        } if job.voice else None,
        "topic": {
            "id": job.topic.id,
            "name": job.topic.name
        } if job.topic else None,
        "is_horizontal": job.is_horizontal,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }

    # 5. 添加签名 URL（如果完成）
    if execution and execution.status == ExecutionStatus.SUCCESS:
        oss_manager = OssManager()

        if "combined_video_oss_key" in job_result_key:
            video_url = oss_manager.get_sign_url(
                job_result_key["combined_video_oss_key"],
                expiration=3600
            )
            response_data["video_url"] = video_url

        if "cover_oss_key" in job_result_key:
            cover_url = oss_manager.get_sign_url(
                job_result_key["cover_oss_key"],
                expiration=3600
            )
            response_data["cover_url"] = cover_url

    return response_data
```

---

### 完整流程时序图

```
用户                    后端 API              Celery              Worker                  外部服务
 │                        │                      │                   │                        │
 │ POST /api/jobs         │                      │                   │                        │
 │───────────────────────>│                      │                   │                        │
 │                        │                      │                   │                        │
 │                        │ 验证用户身份          │                   │                        │
 │                        │ 清理和验证文本        │                   │                        │
 │                        │                      │                   │                        │
 │                        │ 创建 Job 记录        │                   │                        │
 │                        │─────────────────────>│                   │                        │
 │                        │                      │                   │                        │
 │                        │ process_video_job    │                   │                        │
 │                        │ .delay(job_id)       │                   │                        │
 │                        │─────────────────────>│                   │                        │
 │                        │                      │                   │                        │
 │                        │                      │ 任务入队           │                        │
 │                        │                      │                   │                        │
 │  返回 job_id           │                      │                   │                        │
 │<───────────────────────│                      │                   │                        │
 │                        │                      │                   │                        │
 │                        │                      │ ───────────────────────────────────────>   │
 │                        │                      │ Worker 消费任务    │                        │
 │                        │                      │                   │                        │
 │                        │                      │                   │ 创建 JobExecution       │
 │                        │                      │                   │                        │
 │                        │                      │                   │ 构建 Pipeline          │
 │                        │                      │                   │                        │
 │                        │                      │                   │ ──────────────────────────────────────────>
 │                        │                      │                   │ TTS 生成               │
 │                        │                      │                   │<──────────────────────────────────────────
 │                        │                      │                   │                        │
 │                        │                      │                   │ 生成字幕               │
 │                        │                      │                   │                        │
 │                        │                      │                   │ 分割文本               │
 │                        │                      │                   │                        │
 │                        │                      │                   │ ──────────────────────────────────────────>
 │                        │                      │                   │ 图像生成               │
 │                        │                      │                   │<──────────────────────────────────────────
 │                        │                      │                   │                        │
 │                        │                      │                   │ ──────────────────────────────────────────>
 │                        │                      │                   │ 视频合成               │
 │                        │                      │                   │<──────────────────────────────────────────
 │                        │                      │                   │                        │
 │                        │                      │                   │ 后处理                 │
 │                        │                      │                   │                        │
 │                        │                      │                   │ 上传 OSS               │
 │                        │                      │                   │                        │
 │                        │                      │                   │ 更新状态为 SUCCESS     │
 │                        │                      │                   │                        │
 │                        │                      │                   │                        │
 │ 轮询 GET /api/jobs/{id}                       │                   │                        │
 │───────────────────────>│                      │                   │                        │
 │                        │                      │                   │                        │
 │                        │ 查询 Job 和 Execution │                   │                        │
 │                        │─────────────────────>│                   │                        │
 │                        │                      │                   │                        │
 │  返回状态和 URL         │                      │                   │                        │
 │<───────────────────────│                      │                   │                        │
 │                        │                      │                   │                        │
 │ 下载视频文件            │                      │                   │                        │
 │─────────────────────────────────────────────────────────────────────────────────────────>│
 │                        │                      │                   │                        │
 │<───────────────────────│                      │                   │                        │
```

---

### 关键代码位置总结

| 功能模块 | 文件位置 | 关键函数/类 |
|---------|---------|-----------|
| API 接收 | `services/backend/api/job.py` | `create_job()` |
| 文本验证 | `services/backend/api/utils.py` | `sanitize_text()`, `validate_job_request()` |
| 任务创建 | `services/backend/service/job.py` | `JobService.create_job()` |
| Celery 任务 | `services/worker/tasks.py` | `process_video_job()` |
| 任务执行器 | `services/worker/job_processing/job_executor.py` | `JobExecutor.execute()` |
| Pipeline 构建 | `services/worker/pipeline/pipeline.py` | `PipelineBuilder.build_standard_pipeline()` |
| Pipeline 执行 | `services/worker/pipeline/pipeline.py` | `Pipeline.execute()` |
| TTS 生成 | `services/worker/pipeline/steps/tts_generation_step.py` | `TTSGenerationStep.execute()` |
| 字幕生成 | `services/worker/pipeline/steps/subtitle_generation_step.py` | `SubtitleGenerationStep.execute()` |
| 文本分割 | `services/worker/pipeline/steps/text_split_step.py` | `TextSplitStep.execute()` |
| 图像生成 | `services/worker/pipeline/steps/image_generation_step.py` | `ImageGenerationStep.execute()` |
| 视频合成 | `services/worker/pipeline/steps/video_composition_step.py` | `VideoCompositionStep.execute()` |
| 后处理 | `services/worker/pipeline/steps/post_processing_step.py` | `PostProcessingStep.execute()` |
| 文件上传 | `services/worker/pipeline/steps/upload_step.py` | `UploadStep.execute()` |
| 结果查询 | `services/backend/api/job.py` | `get_job()` |

---

## 业务流程详解

### 1. 任务创建流程

```
用户填写任务信息 (标题、内容、语言/音色、话题、横竖屏)
        ↓
后端 API 接收请求 (POST /api/jobs)
        ↓
1. 用户认证验证 (验证 JWT Token)
        ↓
2. 请求验证和清理
   - validate_job_request()
   - sanitize_text() 移除控制字符
   - 移除标记内容 (#@#...#@#)
   - 限制文本长度
        ↓
3. 创建 Job 记录
   - JobService.create_job()
   - 关联 language, voice, topic
   - 初始化状态为 "待处理"
        ↓
4. 通过 Celery 分发任务
   - process_video_job.delay(job_id)
   - 任务进入 Celery 队列
        ↓
5. 返回任务 ID 给用户
```

**关键代码位置**：`services/backend/api/job.py:254-336`

### 2. 任务执行流程

```
Celery Worker 接收任务
        ↓
1. 创建数据库会话
        ↓
2. 创建 JobExecution 记录
   - status = "PENDING"
   - worker_hostname = socket.gethostname()
   - retry_count = 0
        ↓
3. 查询 Job 配置
   - 加载 job, language, voice, topic
   - 检查 deleted_at == None
        ↓
4. 检查是否有正在运行的执行
        ↓
5. 更新状态为 "RUNNING"
        ↓
6. 创建 Pipeline 上下文
   - context = PipelineContext.from_job(job, db)
   - 创建工作目录
   - 加载任务配置
        ↓
7. 构建 Pipeline
   - pipeline = PipelineBuilder.build_standard_pipeline()
   - 按顺序添加步骤
        ↓
8. 执行 Pipeline
   - TTS 生成 → 字幕生成 → 文本分割
   - 图像生成 → 视频合成 → 数字人合成
   - 后处理 → 文件上传
        ↓
9. 收集和上传结果
   - 上传到 OSS
   - 生成签名 URL
        ↓
10. 更新执行状态
    - execution.status = "SUCCESS" / "FAILED"
    - execution.result_key = JSON 结果
    - execution.finished_at = get_beijing_time()
```

**关键代码位置**：
- 任务执行入口：`services/worker/tasks.py:217-273`
- Pipeline 构建：`services/worker/pipeline/pipeline.py`
- 任务执行器：`services/worker/job_processing/job_executor.py`

### 3. 状态查询流程

```
用户轮询任务状态 (GET /api/jobs/{job_id})
        ↓
1. 用户认证验证
        ↓
2. 查询任务
   - JobService.get_job_with_topic(job_id, user_id)
   - 关联查询 language, voice, topic
        ↓
3. 获取最新执行状态
   - job.latest_execution (Property)
   - 或者 job.status (向后兼容)
        ↓
4. 解析结果键
   - job_result_key = safe_json_loads(job.job_result_key)
   - 提取 OSS key
        ↓
5. 获取封面图片 (可选)
        ↓
6. 转换为响应模型并返回
```

**关键代码位置**：`services/backend/api/job.py:440-492`

### 4. 文件下载流程

```
用户获取签名 URL (GET /api/jobs/{job_id}/desc)
        ↓
1. 查询任务
        ↓
2. 解析结果键
   - 提取所有 OSS key
        ↓
3. 生成签名 URL
   - OssManager.get_sign_url(oss_key, expiration=3600)
   - 为每个文件生成临时访问链接
        ↓
4. 构建描述文本
   - 包含完整视频、不带Logo视频、字幕、音频的链接
        ↓
5. 返回描述和内容
        ↓
6. 用户点击下载
        ↓
OSS 验证签名并返回文件流
```

**关键代码位置**：`services/backend/api/job.py:411-438`

---

## API 接口文档

### 任务管理 API

#### 创建任务

```http
POST /api/jobs
Content-Type: application/json
Authorization: Bearer <token>

{
  "title": "测试视频",
  "content": "这是测试内容...",
  "description": "这是一个测试视频的描述",
  "publish_title": "发布的标题",
  "language_id": 1,
  "voice_id": 1,
  "topic_id": 1,
  "account_id": 1,
  "speech_speed": 0.9,
  "is_horizontal": true
}

Response:
{
  "id": 123
}
```

#### 任务列表

```http
GET /api/jobs?page=1&page_size=10&status=&account_id=&language_id=
Authorization: Bearer <token>

Response:
{
  "total": 100,
  "items": [
    {
      "id": 123,
      "title": "测试视频",
      "status": "已完成",
      "status_detail": "任务执行成功",
      "language_id": 1,
      "voice_id": 1,
      "topic_id": 1,
      "is_horizontal": true,
      "created_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-01T12:30:00"
    }
  ]
}
```

#### 获取任务详情

```http
GET /api/jobs/{job_id}
Authorization: Bearer <token>

Response:
{
  "id": 123,
  "title": "测试视频",
  "status": "已完成",
  "language": {
    "id": 1,
    "name": "zh-CN",
    "language_name": "中文"
  },
  "voice": {
    "id": 1,
    "name": "xiaoyun",
    "path": "/path/to/voice.mp3"
  },
  "topic": {
    "id": 1,
    "name": "科技",
    "prompt_gen_image": "..."
  },
  "cover_base64": "data:image/jpeg;base64,...",
  "is_horizontal": true
}
```

#### 获取任务描述和签名URL

```http
GET /api/jobs/{job_id}/desc
Authorization: Bearer <token>

Response:
{
  "description": "#@#\n完整视频地址：https://oss.example.com/video.mp4?signature=...\n...",
  "content": "这是测试内容..."
}
```

#### 更新任务

```http
PUT /api/jobs/{job_id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "id": 123,
  "title": "更新后的标题",
  "status": "待处理",
  "language_id": 2
}

Response:
{
  "id": 123,
  "title": "更新后的标题",
  ...
}
```

#### 删除任务

```http
DELETE /api/jobs/{job_id}
Authorization: Bearer <token>

Response:
{
  "id": 123
}
```

#### 导出任务视频

```http
POST /api/jobs/export/{job_id}
Authorization: Bearer <token>

Response:
{
  "export_url": "https://oss.example.com/export/video.zip",
  "expires_at": "2024-01-01T13:00:00"
}
```

#### 提升任务优先级

```http
POST /api/jobs/{job_id}/increase_priority
Authorization: Bearer <token>

Response:
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

### 健康检查 API

```http
# 基本健康检查
GET /health

Response:
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00"
}

# 详细健康检查
GET /health/extended

Response:
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 5
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1
    },
    "oss": {
      "status": "healthy",
      "latency_ms": 50
    }
  }
}

# 就绪检查
GET /ready

Response:
{
  "ready": true
}

# 监控指标
GET /metrics

Response:
# Prometheus 文本格式的指标
```

---

## Pipeline 处理系统

### Pipeline 架构

```
Pipeline 上下文
├── 数据容器
│   ├── job_id, user_id
│   ├── title, content
│   ├── speech_speed, is_horizontal
│   ├── topic_prompts, loras
│   └── 步骤中间结果
│       ├── audio_path, srt_path
│       ├── splits, image_paths
│       ├── combined_video, human_video_path
│       ├── final_video_path
│       └── upload_results
│
├── 状态管理器
│   ├── executed_steps: List[str]
│   ├── step_records: Dict[str, StepRecord]
│   ├── started_at, finished_at
│   └── error_message
│
└── 状态更新器
    ├── update_execution_status()
    ├── update_step_status()
    └── mark_step_completed/failed()
```

### Pipeline 执行模式

#### 传统模式（向后兼容）

```python
from services.worker.pipeline import PipelineBuilder, PipelineContext

# 创建上下文
context = PipelineContext.from_job(job, db)

# 构建 Pipeline
pipeline = PipelineBuilder.build_standard_pipeline(context)

# 执行（传统模式）
pipeline.execute()

# 访问结果（通过 context）
audio_path = context.audio_path
video_path = context.combined_video
```

#### 函数式模式（推荐）

```python
from services.worker.pipeline import PipelineBuilder, PipelineContext

# 创建上下文
context = PipelineContext.from_job(job, db)

# 构建 Pipeline（函数式模式）
pipeline = PipelineBuilder.build_standard_pipeline(context, functional_mode=True)

# 执行（函数式模式）
results = pipeline.execute_functional()

# 访问结果（通过结果对象）
tts_result = results.get("TTSGeneration")
audio_path = tts_result.audio_path
duration = tts_result.duration
```

### 步骤详解

#### TTSGenerationStep

**职责**：将文本转换为语音音频

**输入**：
- `context.content`: 待转换的文本
- `context.language_name`: 语言名称
- `context.reference_audio_path`: 参考音频路径（音色）
- `context.speech_speed`: 语速

**处理流程**：
1. 准备 TTS 参数
2. 调用 TTS 服务 (SeedVC / Azure TTS)
3. 保存音频文件到工作目录
4. 提取音频元数据

**输出**：
- `audio_path`: 音频文件路径
- `duration`: 音频时长（秒）

#### SubtitleGenerationStep

**职责**：根据音频生成 SRT 字幕

**输入**：
- `context.audio_path`: 音频文件路径
- `context.content`: 原始文本

**处理流程**：
1. 获取音频时长
2. 按时长分割文本
3. 计算每个片段的时间戳
4. 生成 SRT 格式字幕

**输出**：
- `srt_path`: SRT 字幕文件路径
- `segments`: 字幕片段列表

#### TextSplitStep

**职责**：将文本分割为适合视频的片段

**输入**：
- `context.srt_path`: SRT 字幕文件路径
- `context.content`: 原始文本

**处理流程**：
1. 解析 SRT 字幕
2. 根据字幕片段分割文本
3. 为每个片段生成图像提示词

**输出**：
- `splits`: 分割项列表
  - 每项包含：`start`, `end`, `text`, `prompt`

#### ImageGenerationStep

**职责**：为每个文本片段生成图像

**输入**：
- `context.splits`: 分割项列表
- `context.topic_prompts`: 话题提示词

**处理流程**：
1. 遍历分割项
2. 组合提示词（话题提示词 + 文本内容）
3. 调用 Flux AI 图像生成服务
4. 带重试机制（最多30次）

**输出**：
- `image_paths`: 生成的图像路径列表
- `selected_images`: 选中的图像列表

#### VideoCompositionStep

**职责**：将音频和图像合成为视频

**输入**：
- `context.audio_path`: 音频文件路径
- `context.image_paths`: 图像路径列表
- `context.is_horizontal`: 横竖屏设置

**处理流程**：
1. 根据横竖屏设置视频分辨率
   - 横屏：1360x768
   - 竖屏：768x1360
2. 使用 FFmpeg 合成视频
3. 添加转场效果

**输出**：
- `video_path`: 合成的视频路径
- `duration`: 视频时长

#### DigitalHumanStep

**职责**：生成数字人视频（可选）

**输入**：
- `context.audio_path`: 音频文件路径
- `context.human_path`: 数字人模型路径

**处理流程**：
1. 准备数字人参数
2. 调用数字人服务
3. 语音同步和表情控制

**输出**：
- `human_video_path`: 数字人视频路径

#### PostProcessingStep

**职责**：视频后处理

**输入**：
- `context.combined_video`: 合成视频路径
- `context.logopath`: Logo 路径

**处理流程**：
1. 添加 Logo 和水印
2. 视频压缩（调整 CRF 值）

**输出**：
- `final_video_path`: 最终视频路径

#### UploadStep

**职责**：上传文件到 OSS

**输入**：
- 所有生成的文件路径

**处理流程**：
1. 准备上传文件列表
2. 上传到 OSS
3. 生成签名 URL

**输出**：
- `upload_results`: 上传结果字典
  - `audio_oss_key`
  - `srt_oss_key`
  - `combined_video_oss_key`
  - `logoed_video_oss_key`
  - `cover_oss_key`

---

## Celery 任务队列

### Celery 配置

```python
# Broker 配置
broker_url = "redis://localhost:6379/0"

# Backend 配置
result_backend = "redis://localhost:6379/0"

# 任务限制
task_time_limit = 3600  # 1小时硬限制
task_soft_time_limit = 3300  # 55分钟软限制

# 重试配置
task_autoretry_for = (Exception,)
task_retry_kwargs = {"max_retries": 3, "countdown": 60}
```

### Celery Beat 定时任务

```python
celery_beat_schedule = {
    "reset-stuck-jobs-every-hour": {
        "task": "services.worker.tasks.reset_stuck_jobs",
        "schedule": crontab(minute=0),  # 每小时执行
    },
    "cleanup-old-jobs-daily": {
        "task": "services.worker.tasks.cleanup_old_jobs",
        "schedule": crontab(hour=2, minute=0),  # 每天凌晨2点
    },
    "check-job-health-every-5-minutes": {
        "task": "services.worker.tasks.check_job_health",
        "schedule": crontab(minute="*/5"),  # 每5分钟
    },
}
```

### 任务定义

#### 核心任务：process_video_job

```python
@shared_task(
    bind=True,
    name='services.worker.tasks.process_video_job',
    base=DatabaseTask,  # 支持数据库会话
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=3300,  # 55分钟软限制
    time_limit=3600,  # 1小时硬限制
)
def process_video_job(self, job_id: int) -> Dict[str, Any]:
    """处理视频生成任务

    这是核心任务，负责:
    1. 从数据库获取任务信息
    2. 创建 JobExecution 记录
    3. 执行视频生成流水线
    4. 更新执行状态
    """
```

**任务特性**：
- **数据库会话管理**：继承 `DatabaseTask`，自动管理数据库会话
- **超时控制**：软限制55分钟，硬限制60分钟
- **自动重试**：失败后自动重试，最多3次
- **重试延迟**：指数退避（60秒, 120秒, 240秒）

#### 维护任务

##### reset_stuck_jobs

重置状态为"处理中"但超过1小时未更新的任务

##### cleanup_old_jobs

清理30天前的已完成/失败任务

##### check_job_health

统计各状态任务数量，用于监控

### Worker 启动

```bash
# 启动 Worker
celery -A services.worker.tasks worker \
    --loglevel=info \
    --concurrency=4 \
    --queue=video_tasks,maintenance

# 启动 Beat (定时任务调度器)
celery -A services.worker.tasks beat \
    --loglevel=info

# 启动 Flower (监控界面)
celery -A services.worker.tasks flower \
    --port=5555
```

### Flower 监控

访问 Flower 监控界面：`http://localhost:5555`

---

## 监控与可观测性

### Prometheus 指标

系统自动收集以下指标：

#### HTTP 请求指标

```python
http_requests_total{method, endpoint, status}
http_request_duration_seconds{method, endpoint, status}
http_request_size_bytes{method, endpoint}
http_response_size_bytes{method, endpoint}
```

#### 任务指标

```python
jobs_total{status}  # PENDING, RUNNING, SUCCESS, FAILED
job_duration_seconds{status}
job_retries_total{job_id}
```

#### 系统指标

```python
system_cpu_usage_percent
system_memory_usage_percent
system_disk_usage_percent{path}
```

### Grafana 仪表板

#### 系统概览仪表板

- 请求量趋势图
- 错误率趋势图
- 响应时间分布图
- 任务执行状态图
- 系统资源使用率

#### 任务监控仪表板

- 任务队列长度
- 任务执行速率
- 任务成功率
- 任务失败原因
- 任务执行时长

### 健康检查端点

```
GET /health              # 基本健康检查
GET /ready               # 就绪检查
GET /health/live         # 存活检查
GET /health/extended     # 详细健康检查
GET /health/metrics      # 监控指标
```

---

## 安全功能

### API 限流

系统支持多种限流算法：

#### 令牌桶算法

```python
from core.security import TokenBucketLimiter

limiter = TokenBucketLimiter(
    rate=10,      # 每秒10个令牌
    capacity=100  # 桶容量100
)

await limiter.check_rate_limit(request)
```

#### 滑动窗口

```python
from core.security import SlidingWindowLimiter

limiter = SlidingWindowLimiter(
    requests_per_minute=100,
    requests_per_hour=1000,
    burst_size=20
)
```

### 熔断器

```python
from core.security import with_circuit_breaker

@with_circuit_breaker("database_service")
async def call_database():
    # 数据库调用
    pass
```

### 输入验证

```python
from core.security import validate_xss, sanitize_html

# XSS 检测
if validate_xss(user_input):
    raise ValueError("XSS detected")

# HTML 清理
clean_html = sanitize_html(user_input)
```

### 数据加密

```python
from core.security import encrypt_data, decrypt_data

# 加密
ciphertext = encrypt_data("sensitive_data")

# 解密
decrypted = decrypt_data(ciphertext)
```

---

## 高可用性部署

### 高可用架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Nginx LB   │───▶│ Backend-1   │    │   Master    │
│   (主)      │    │   (主)      │    │   MySQL     │
└─────────────┘    └─────────────┘    └──────┬──────┘
       │                                    │
       │                                    │ 复制
       ▼                                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Backend-2   │    │   Slave     │    │ Redis Master│
│   (备)      │    │   MySQL     │    └──────┬──────┘
└─────────────┘    └─────────────┘           │
                                          复制
       ┌─────────────┐                      │
       │ Backend-3   │                      ▼
       │   (备)      │              ┌─────────────┐
       └─────────────┘              │Redis Slave  │
                                   └─────────────┘
```

### 部署命令

```bash
# 使用高可用配置启动
docker-compose -f docker-compose.ha.yml up -d

# 扩容服务
docker-compose -f docker-compose.ha.yml up -d --scale backend=5

# 查看状态
docker-compose -f docker-compose.ha.yml ps
```

---

## 开发指南

### 环境设置

```bash
# 创建虚拟环境
conda create -n BatchVideo python=3.8
conda activate BatchVideo

# 安装依赖
pip install -e ".[dev]"

# 初始化数据库
alembic upgrade head

# 启动开发服务器
# Backend
uvicorn services.backend.api_main:app --reload

# Worker
celery -A services.worker.tasks worker --loglevel=debug
```

### 代码规范

```bash
# 代码格式化
black core/ services/

# 导入排序
isort core/ services/

# 类型检查
mypy core/

# 代码检查
flake8 core/ services/
```

### 测试

```bash
# 运行测试
pytest tests/

# 测试覆盖率
pytest --cov=core --cov=services tests/

# 生成报告
pytest --cov-report=html tests/
```

---

## 部署指南

### Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 生产环境部署

```bash
# 使用高可用配置
docker-compose -f docker-compose.ha.yml up -d

# 配置 Nginx
cp deploy/nginx/sites-available/BatchVideo /etc/nginx/sites-available/
ln -s /etc/nginx/sites-available/BatchVideo /etc/nginx/sites-enabled/
nginx -t
nginx -s reload

# 配置 SSL
certbot --nginx -d yourdomain.com
```

---

## 故障排查

### 常见问题

#### 任务卡住

```bash
# 检查任务状态
curl http://localhost:8006/health

# 重置卡住的任务
curl -X POST http://localhost:8006/api/jobs/reset-stuck
```

#### Worker 无响应

```bash
# 查看 Worker 日志
docker-compose logs worker

# 重启 Worker
docker-compose restart worker
```

#### 数据库连接失败

```bash
# 检查数据库状态
docker-compose exec mysql mysql -uroot -ppassword -e "STATUS"

# 检查连接池
curl http://localhost:8006/health/db
```

---

## 贡献指南

1. Fork 仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 许可证

本项目采用 **MIT License** 开源许可证。

### 许可证详情

```
MIT License

Copyright (c) 2024 BatchVideo Development Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 许可证说明

MIT License 是一种非常宽松的开源许可证，允许：

- **商业使用** - 您可以将此软件用于商业目的
- **修改** - 您可以修改此软件
- **分发** - 您可以分发此软件
- **私用** - 您可以私有使用此软件而不披露源代码
- **再许可** - 您可以在您的项目中包含此软件并使用不同的许可证

**条件**：
- 必须在所有副本或实质性部分中包含版权声明和许可声明
- 软件按"原样"提供，不提供任何形式的明示或暗示保证

### 第三方依赖

本项目使用了以下第三方库和模型，它们可能有各自的许可证：

| 组件 | 许可证 |
|------|--------|
| FastAPI | MIT |
| SQLAlchemy | MIT |
| Celery | BSD-3-Clause |
| Redis | BSD-3-Clause |
| Diffusers (Hugging Face) | Apache-2.0 |
| Flux.1-dev | Apache-2.0 |
| FunASR | MIT |
| OpenAI Whisper | MIT |
| PyTorch | BSD-style |

完整依赖列表请查看 `pyproject.toml` 文件。

### 依赖模型说明

本项目使用的 AI 模型（如 Flux、Whisper、FunASR 等）遵循各自的许可证：

- **Flux.1-dev**: 使用 Apache-2.0 许可证，允许商业使用
- **Whisper**: 使用 MIT 许可证
- **FunASR**: 使用 MIT 许可证

请确保在使用这些模型时遵守其各自的许可证条款。

---

## 联系方式

- **作者**: 宫凡VanGong
- **GitHub**: [VanGongwanxiaowan/batch-video](https://github.com/VanGongwanxiaowan/batch-video)
- **邮箱**: gongfan1213@163.com
