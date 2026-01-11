# TTS (Text-to-Speech) Service

文本转语音服务，支持 Azure TTS 和 SeedVC 语音克隆。

## 概述

该服务包含两个子服务：
- **Azure TTS Server**: 基于 Azure Speech Service 的 TTS 服务，支持语音合成和字幕生成
- **SeedVC Server**: 基于 SeedVC 模型的语音克隆服务

### 架构说明

TTS 服务使用统一的微服务架构规范：

- **统一配置**: 使用 `core.config.BaseConfig` 和 `PathManager`
- **统一日志**: 使用 `core.logging_config.setup_logging`
- **统一异常**: 使用 `core.exceptions` 中的异常类型

## Azure TTS Server

### 环境要求

- Python 3.8+
- Azure Speech Service 订阅密钥

### 配置

在 `azure_tts_server/config/settings.py` 中配置：

- `AZURE_SPEECH_KEY`: Azure Speech Service 密钥（必需）
- `AZURE_SPEECH_REGION`: Azure 区域（默认: `eastus`）
- `HOST`: 服务监听地址（默认: `0.0.0.0`）
- `PORT`: 服务端口（默认: `8001`）

### 启动方式

#### 方式一：使用 Docker

```bash
cd services/tts/azure_tts_server
docker-compose up -d
```

#### 方式二：本地开发（Conda 环境）

```bash
# 激活 Conda 环境
conda activate <你的环境名>

# 安装依赖
cd services/tts/azure_tts_server
pip install -r requirements.txt

# 启动服务
python main.py
```

服务将在 `http://localhost:8001` 启动。

### API 端点

#### TTS 语音合成

```bash
POST /api/v1/asr_service
Content-Type: multipart/form-data

audio_output_path: /path/to/output.mp3
audio_text: 要合成的文本内容
subtitle_output_path: /path/to/subtitle.srt (可选)
voice: zh-CN-XiaoqiuNeural
sample_rate: 16000
volume: 50
speech_rate: 1.0
```

#### 健康检查

```bash
GET /api/v1/health
```

### 日志

日志文件位于项目根目录的 `logs/` 目录：
- `logs/azure_tts_server.log`: 主服务日志
- `logs/azure_tts_service.log`: TTS 服务日志
- `logs/subtitle_service.log`: 字幕服务日志
- `logs/asr_service.log`: ASR 服务日志

## SeedVC Server

### 环境要求

- Python 3.8+
- PyTorch (支持 CUDA/MPS/CPU)
- 模型文件（位于 `checkpoints/` 目录）

### 配置

通过环境变量配置：

- `ACCESS_KEY_ID`: 阿里云 TTS Access Key ID（可选）
- `ACCESS_KEY_SECRET`: 阿里云 TTS Access Key Secret（可选）
- `APP_KEY`: 阿里云 TTS App Key（可选）
- `TTSTYPE`: TTS 类型，`aly` 或 `edge`（默认: `edge`）
- `PROXY`: 代理地址（可选）

### 启动方式

#### 方式一：使用 Docker

```bash
cd services/tts/seedvc_server
docker-compose up -d
```

#### 方式二：本地开发（Conda 环境）

```bash
# 激活 Conda 环境
conda activate <你的环境名>

# 安装依赖
cd services/tts/seedvc_server
pip install -r requirements.txt

# 启动服务
python tts_seedvc.py
```

服务将在 `http://localhost:8007` 启动。

### API 端点

#### 语音合成（带语音克隆）

```bash
POST /synthesize/
Content-Type: multipart/form-data

text: 要合成的文本
voice: beth_ecmix (默认)
audio_file: 参考音频文件（用于语音克隆）
tts_audio_file: TTS 基础音频文件（可选）
volume: 50
speech_rate: 1.0
pitch_rate: 0
tts_type: edge (edge 或 aly)
```

### 日志

日志文件位于项目根目录的 `logs/` 目录：
- `logs/tts.seedvc_server.log`: SeedVC 服务日志

## 与 Worker 服务的关系

TTS 服务被 Worker 服务调用，用于：
- 生成视频配音音频
- 生成字幕文件
- 语音克隆（SeedVC）

Worker 服务通过 HTTP 请求调用 TTS 服务的 API 端点。

## 故障排查

### Azure TTS 配置错误

- 检查 `AZURE_SPEECH_KEY` 是否正确配置
- 验证 Azure 订阅是否有效
- 检查网络连接

### SeedVC 模型加载失败

- 确认模型文件位于 `checkpoints/` 目录
- 检查 PyTorch 版本兼容性
- 验证 GPU/CPU 资源

### 音频生成失败

- 查看服务日志文件
- 检查输出路径权限
- 验证音频格式支持

