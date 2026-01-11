"""Pipeline 数据容器

包含 Pipeline 执行过程中的所有数据定义。
遵循单一职责原则，只负责数据存储，不包含业务逻辑。
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.db.models import Job, get_beijing_time


@dataclass
class PipelineData:
    """Pipeline 纯数据容器

    只负责数据存储，不包含业务逻辑。
    所有字段都是可变的，允许在 Pipeline 执行过程中更新。

    Attributes:
        job_id: 任务ID
        title: 任务标题
        content: 任务内容
        user_id: 用户ID
        workspace_dir: 工作目录路径

    # 配置信息
        language_name: 语言名称
        language_platform: 语言平台
        speech_speed: 语速
        is_horizontal: 是否横屏
        reference_audio_path: 参考音频路径
        logopath: Logo路径
        topic_prompts: 话题提示词配置
        loras: LoRA配置列表
        extra: 额外配置
        account: 账户信息

    # 步骤中间结果
        audio_path: 音频文件路径
        srt_path: 字幕文件路径
        splits: 文本分镜数据
        image_paths: 图像路径列表
        selected_images: 选择的图像列表
        combined_video: 合成视频路径
        human_video_path: 数字人视频路径
        final_video_path: 最终视频路径

    # 上传结果
        upload_results: 上传结果字典
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

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于日志和调试）

        Returns:
            Dict[str, Any]: 数据字典表示
        """
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "title": self.title,
            "workspace_dir": str(self.workspace_dir) if self.workspace_dir else None,
            "has_audio": self.audio_path is not None,
            "has_subtitle": self.srt_path is not None,
            "has_splits": len(self.splits) > 0,
            "has_images": len(self.image_paths) > 0,
            "has_video": self.combined_video is not None,
            "has_upload_results": len(self.upload_results) > 0,
        }


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
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置数据值"""
        self.data[key] = value


__all__ = [
    "PipelineData",
    "StepResultData",
]
