"""
视频生成配置模块
定义视频生成所需的配置数据类，用于封装函数参数
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VideoGenerationConfig:
    """视频生成配置数据类
    
    封装 generate_all 函数的所有参数，提供类型安全和默认值支持。
    遵循单一职责原则，将配置参数与业务逻辑分离。
    
    Attributes:
        title: 视频标题
        content: 视频内容文本
        language: 语言代码
        prompt_gen_images: 图像生成提示词
        prompt_prefix: 提示词前缀
        prompt_cover_image: 封面图像提示词
        logopath: Logo文件路径
        reference_audio_path: 参考音频路径（用于语音克隆）
        message: 消息内容（已废弃，保留用于向后兼容）
        speech_speed: 语音速度，默认1.0
        is_horizontal: 是否横向视频，默认True
        loras: LoRA模型列表，默认空列表
        extra: 额外配置字典，默认空字典
        topic: 主题对象（可选）
        user_id: 用户ID
        job_id: 任务ID，默认0
        platform: TTS平台，默认"edge"
        account: 账户对象（可选）
    """
    title: str
    content: str
    language: str
    prompt_gen_images: str
    prompt_prefix: str
    prompt_cover_image: str
    logopath: Optional[str] = None
    reference_audio_path: Optional[str] = None
    message: str = ""
    speech_speed: float = 1.0
    is_horizontal: bool = True
    loras: List[Dict[str, Any]] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
    topic: Optional[Any] = None
    user_id: str = ""
    job_id: int = 0
    platform: str = "edge"
    account: Optional[Any] = None
    
    def get_topic_extra(self) -> Dict[str, Any]:
        """获取主题额外配置
        
        Returns:
            主题额外配置字典，如果topic不存在则返回空字典
        """
        if self.topic and hasattr(self.topic, 'extra') and self.topic.extra:
            return self.topic.extra
        return {}
    
    def get_account_extra(self) -> Dict[str, Any]:
        """获取账户额外配置
        
        Returns:
            账户额外配置字典，如果account不存在则返回空字典
        """
        if self.account and hasattr(self.account, 'extra') and self.account.extra:
            return self.account.extra
        return {}
    
    def get_topic_name(self) -> str:
        """获取主题名称
        
        Returns:
            主题名称，如果topic不存在则返回空字符串
        """
        if self.topic and hasattr(self.topic, 'name'):
            return self.topic.name
        return ""
    
    def should_convert_to_traditional(self) -> bool:
        """判断是否需要转换为繁体字幕
        
        Returns:
            如果需要转换，返回True；否则返回False
        """
        return self.extra.get("traditional_subtitle", False)
    
    def get_transition_config(self) -> tuple[bool, List[str]]:
        """获取转场配置
        
        Returns:
            (是否启用转场, 转场类型列表)
        """
        account_extra = self.get_account_extra()
        enable_transition = account_extra.get("enable_transition", False)
        transition_types = account_extra.get("transition_types", ["fade"])
        return enable_transition, transition_types

