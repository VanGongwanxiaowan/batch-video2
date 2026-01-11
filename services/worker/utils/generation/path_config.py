"""
路径配置模块
负责视频生成过程中的路径准备和配置管理

代码重构说明：
- 使用 core.config.video_config 中的统一 VideoResolution
- 替换硬编码的 1360x768 分辨率
"""
import os
from typing import Dict

from core.logging_config import setup_logging
# 使用统一的视频配置
from core.config.video_config import get_dimensions

logger = setup_logging("worker.utils.generation.path_config")

# 方块字语言列表
SQUARE_WORDS_LIST = [
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-YunxiNeural",
    "ko-KR-SunHiNeural",
    "ja-JP-NanamiNeural",
    "zh-TW-HsiaoChenNeural",
    "zh-HK-HiuGaaiNeural",
    "th-TH-PremwadeeNeural",
    "lo-LA-KeomanyNeural",
    "my-MM-NilarNeural",
]


class PathConfig:
    """路径配置管理器"""
    
    @staticmethod
    def prepare_paths_and_config(
        title: str,
        user_id: str,
        assertspath: str,
        is_horizontal: bool
    ) -> Dict[str, str]:
        """
        准备所有文件路径和配置
        
        Args:
            title: 视频标题
            user_id: 用户ID
            assertspath: 资源根路径
            is_horizontal: 是否横向视频
            
        Returns:
            包含所有路径的字典
        """
        # 清理标题
        title = title.replace(" ", "_").replace("+", "_")

        # 使用统一的视频配置获取分辨率
        width, height = get_dimensions(is_horizontal=is_horizontal)

        # 构建资源路径
        assrtpath = os.path.abspath(os.path.join(assertspath, title))
        user_id = user_id.replace("-", "")
        if user_id:
            assrtpath = os.path.join(assertspath, user_id, title)
        
        # 确保目录存在
        os.makedirs(assrtpath, exist_ok=True)
        
        return {
            "assrtpath": assrtpath,
            "width": width,
            "height": height,
            "tts_audio": os.path.join(assrtpath, "tts.mp3"),
            "seedvc_audio": os.path.join(assrtpath, "seedvc.wav"),
            "seedvc_mp3_audio": os.path.join(assrtpath, "seedvc.mp3"),
            "datajson_path": os.path.join(assrtpath, "data.json"),
            "srtpath": os.path.join(assrtpath, "data.srt"),
            "logoed_video": os.path.join(assrtpath, "logoed.mp4"),
            "subtitled_video": os.path.join(assrtpath, "subtitled.mp4"),
            "h2v_video": os.path.join(assrtpath, "h2v.mp4"),
        }
    
    @staticmethod
    def is_square_language(language: str) -> bool:
        """
        判断是否为方块字语言
        
        Args:
            language: 语言代码
            
        Returns:
            是否为方块字语言
        """
        return language in SQUARE_WORDS_LIST

