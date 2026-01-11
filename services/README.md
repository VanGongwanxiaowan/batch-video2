# Services 目录

本目录包含所有微服务。

## 目录结构

```
services/
├── backend/          # 后端API服务
├── worker/          # 工作进程服务
├── tts/             # TTS服务
│   ├── azure_tts_server/    # 旧版TTS服务
│   └── seedvc_server/       # 新版TTS服务
├── image_gen/       # 图像生成服务
│   ├── ai_image_gen/        # AI图像生成服务
│   └── flux_server/         # Flux服务
└── digital_human/   # 数字人服务(外部)
```

## 迁移说明

服务已从根目录迁移到此目录，以统一管理所有微服务。

## 导入路径更新

迁移后，如果从外部导入服务，需要使用新的路径：

```python
# 旧方式 (已废弃)
from backend_server.api import job

# 新方式 (推荐)
from services.backend.api import job
```

## 向后兼容

为了保持向后兼容，根目录下的服务目录暂时保留，但会逐步迁移。

