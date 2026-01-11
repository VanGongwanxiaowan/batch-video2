## Worker 服务说明（重构版）

本目录包含批处理视频生成 Worker 服务，当前推荐的官方调用链为：

### 架构说明

Worker 服务使用统一的微服务架构规范：

- **统一配置**: 使用 `core.config.BaseConfig` 和 `PathManager`
- **统一日志**: 使用 `core.logging_config.setup_logging`
- **统一异常**: 使用 `core.exceptions` 中的异常类型
- **统一数据库**: 使用 `core.db` 中的模型和会话管理

- **任务入口**：`worker_main.py` 中的 `_execute_job`  
- **视频流水线**：`pipeline.VideoGenerationPipeline.generate_all`  
- **子服务**：  
  - `services/tts.TTSService`：负责 TTS 与字幕生成  
  - `services/subtitle.SubtitleService`：字幕格式化与繁体转换  
  - `services/image.ImageService`：图片描述与图像生成  
  - `services/video.VideoService`：分镜视频生成、拼接、字幕+音频+Logo 合成  
  - `services/digital_human.DigitalHumanService`：数字人视频生成与合成（内部再调用 `human_pipeline`）

### VideoGenerationPipeline.generate_all 参数概览

- **title**: 文本标题，用于文件命名与部分业务逻辑（含“数字人”会触发数字人流程）  
- **content**: 正文内容，用于 TTS 和画面生成  
- **language / platform**: 语言与 TTS 平台（如 `"zh-CN-XiaoxiaoNeural"` / `"edge"` / `"azure"`）  
- **prompt_gen_images / prompt_prefix / prompt_cover_image**: 图像生成相关提示词  
- **logopath**: 账号 Logo 本地路径（可为空）  
- **reference_audio_path**: 参考音频路径，用于音色克隆（可选）  
- **message**: 描述/文案，用于封面或部分 UI 文案（目前可选）  
- **speech_speed**: 语速（浮点数）  
- **is_horizontal**: 是否横版视频（`True` 横版，`False` 竖版）  
- **loras**: LoRA 配置列表，形如 `[{ "name": str, "weight": float }, ...]`  
- **extra**: 额外控制参数（如 `traditional_subtitle`、`h2v` 等）  
- **topic / account**: 话题与账号对象，用于读取额外配置（如数字人模式、转场效果等）  
- **user_id / job_id**: 用户与任务 ID，用于生成独立工作目录  

旧的 `pipe_line.generate_all` 与 `human_pack*` 系列函数已被标记为 **legacy**，仅保留给历史脚本使用；  
