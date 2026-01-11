import os
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config import settings
from core.logging_config import setup_logging
# 使用共享 HTTP Session
from core.utils.http_session import get_http_session

# 配置日志
logger = setup_logging("worker.clients.azure_tts_client", log_to_file=False)

lang_voice_map = {
    "老人女音-中英双语": "zh-CN-XiaoqiuNeural",
    "年轻人女音-中英双语": "zh-CN-XiaomoNeural",
    "成年浑厚男音-中英双语": "zh-CN-YunzeNeural",
    "成年标准男音-中英双语": "zh-CN-YunfengNeural",
    "儿童男音-中英双语": "zh-CN-YunxiaNeural",
    "年轻男音-中英双语": "zh-CN-YunjieNeural",
}


class VoiceSynthesisClient:
    def __init__(self, base_url: Optional[str] = None) -> None:
        """初始化Azure TTS客户端

        使用共享 HTTP Session 优化性能。

        Args:
            base_url: 服务基础URL，如果为None则使用配置中的URL
        """
        if base_url is None:
            base_url = settings.AZURE_TTS_SERVER_URL
        self.base_url = base_url.rstrip('/')
        # 使用共享的 HTTP Session（带连接池）
        self._session = get_http_session()

    def synthesize_voice(
        self,
        audio_text: str,
        audio_output_path: Optional[str] = None,
        subtitle_output_path: Optional[str] = None,
        voice: str = "zh-CN-XiaoqiuNeural",
        volume: int = 50,
        speech_rate: float = 1.0,
    ) -> bool:
        """
        Send a request to the voice synthesis API

        使用共享 Session，自动复用 TCP 连接。

        Args:
            text: Text to synthesize
            audio_file_path: Path to reference audio file for voice cloning
            voice: Voice model to use (default: "beth_ecmix")
            volume: Volume level (0-100)
            speech_rate: Speech rate adjustment
            pitch_rate: Pitch rate adjustment
            output_file: Path to save the output file (if None, won't save)

        Returns:
            bool: True if successful, False otherwise
        """
        url = f"{self.base_url}/asr_service"

        try:
            data = {
                'text': audio_text,
                'voice': voice,
                'volume': volume,
                'speech_rate': speech_rate,
                'audio_text': audio_text,
                'audio_output_path': audio_output_path,
                'subtitle_output_path': subtitle_output_path,
            }

            # 使用共享 Session（连接池自动复用 + 自动重试）
            # Session 配置了自动重试，这里减少手动重试次数
            for attempt in range(2):
                try:
                    self._session.post(url, data=data, timeout=1800)
                    return True
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except Exception as request_e:
                    # 网络请求错误（Session 已配置自动重试）
                    if attempt == 0:  # 仅在第一次失败时记录警告
                        logger.warning(f"[synthesize_voice] 请求失败，尝试重试: {str(request_e)}")
            return False  # 所有重试都失败

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他未预期的异常
            logger.exception(f"[synthesize_voice] 发生未知异常: {str(e)}")
            return False

client = VoiceSynthesisClient()

if __name__ == '__main__':
    # Example usage (requires a dummy source_audio.wav file)
    # Create a dummy source_audio.wav file for testing if needed
    # Example: touch dummy_source_audio.wav
    client = VoiceSynthesisClient('http://127.0.0.1:6016')


    text = 'Mr. Mu'
    source_audio_path = '/tmp/ref_08436c0bee5a493fb48d64cb57d4a9d6.wav'
    tts_audio_path = './test1.wav'
    output_dir = 'tts_audio'
    volume = 50
    speech_rate = 1.1
    tgt_lang = '英语'


    client.synthesize_voice(
        text=text,
        audio_file_path=None,
        voice='en-AU-NatashaNeural',
        output_file='test1.wav',
        volume = volume,
        speech_rate = speech_rate,
        tts_type = 'edge'
    )

    client.synthesize_voice(
        text=text,
        audio_file_path=source_audio_path,
        voice='en-AU-NatashaNeural',
        output_file='test2.wav',
        volume = volume,
        speech_rate = speech_rate,
        tts_type = 'edge'
    )

    # client.synthesize_voice(
    #     text=text,
    #     audio_file_path=source_audio_path,
    #     tts_audio_file_path=tts_audio_path,
    #     voice='en-AU-NatashaNeural',
    #     output_file='test3.wav',
    #     volume = volume,
    #     speech_rate = speech_rate,
    #     tts_type = 'edge'
    # )


    # client.synthesize_voice(
    #     text=text,
    #     audio_file_path=None,
    #     voice='beth_ecmix',
    #     output_file='test3.wav',
    #     volume = volume,
    #     speech_rate = speech_rate,
    #     tts_type = 'aly'
    # )
    # client.synthesize_voice(
    #     text=text,
    #     audio_file_path=source_audio_path,
    #     voice='beth_ecmix',
    #     output_file='test4.wav',
    #     volume = volume,
    #     speech_rate = speech_rate,
    #     tts_type = 'aly'
    # )