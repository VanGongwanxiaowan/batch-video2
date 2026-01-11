"""数字人服务"""
from typing import Any, Dict, Optional

from config import settings
from core.logging_config import setup_logging
from core.utils.ffmpeg import get_video_duration as safe_get_video_duration
from services.base import BaseService

from .human_pipeline import (
    human_pack_new,
    human_pack_new_corner,
    human_pack_new_with_transition,
    human_pack_new_with_transition_corner,
)

# TODO: 后续重构目标：
# 1. 将数字人合成实现从 `pipe_line.py` 完全迁移到独立的 service / pipeline 模块（当前已完成迁移）
# 2. 通过 `DigitalHumanService` 对外暴露统一接口，避免直接依赖底层实现细节
# 3. 使用 `core.config.PathManager` 管理所有与数字人相关的路径
logger = setup_logging("worker.digital_human")


class DigitalHumanService(BaseService):
    """数字人服务，负责数字人视频生成和合成"""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """初始化数字人服务
        
        Args:
            config: 配置字典
        """
        super().__init__(config, logger)
        self.human_base_path = str(settings.human_assets_path)
        self.human_generate_url = f"{settings.HUMAN_SERVICE_URL}/human/generate"
    
    def get_video_duration(self, video_path: str) -> float:
        """
        获取视频精确时长（秒）
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频时长（秒）
        """
        return safe_get_video_duration(video_path)
    
    async def generate_digital_human(
        self,
        account_name: str,
        origin_video_path: str,
        audio_path: str,
        jsonpath: str,
        account_extra: Dict[str, Any],
        mode: str = "fullscreen",
        enable_transition: bool = False,
    ) -> Optional[str]:
        """
        生成数字人视频
        
        Args:
            account_name: 账户名称
            origin_video_path: 原始视频路径
            audio_path: 音频路径
            jsonpath: JSON数据文件路径
            account_extra: 账户额外配置
            mode: 数字人插入模式（"fullscreen" 或 "corner"）
            enable_transition: 是否启用转场效果
            
        Returns:
            生成的数字人视频路径，失败返回None
        """
        try:
            if mode == "corner":
                if enable_transition:
                    return human_pack_new_with_transition_corner(
                        account_name, origin_video_path, audio_path, jsonpath, account_extra
                    )
                else:
                    return human_pack_new_corner(
                        account_name, origin_video_path, audio_path, jsonpath, account_extra
                    )
            else:  # fullscreen
                if enable_transition:
                    return human_pack_new_with_transition(
                        account_name, origin_video_path, audio_path, jsonpath, account_extra
                    )
                else:
                    return human_pack_new(
                        account_name, origin_video_path, audio_path, jsonpath, account_extra
                    )
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（数字人视频生成错误等）
            self.logger.error(f"[generate_digital_human] 生成数字人视频失败: {e}", exc_info=True)
            return None
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理数字人视频生成请求
        
        Args:
            data: 包含数字人参数的字典
            
        Returns:
            处理结果字典
        """
        try:
            result = await self.generate_digital_human(
                account_name=data.get("account_name", ""),
                origin_video_path=data.get("origin_video_path", ""),
                audio_path=data.get("audio_path", ""),
                jsonpath=data.get("jsonpath", ""),
                account_extra=data.get("account_extra", {}),
                mode=data.get("mode", "fullscreen"),
                enable_transition=data.get("enable_transition", False),
            )
            
            if result:
                return {
                    "success": True,
                    "video_path": result
                }
            else:
                return {
                    "success": False,
                    "error": "数字人视频生成失败"
                }
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（数字人视频处理错误等）
            return self.handle_error(e)

