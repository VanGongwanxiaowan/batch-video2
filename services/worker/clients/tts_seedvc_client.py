import os
import sys
from pathlib import Path
from typing import Optional

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("worker.clients.tts_seedvc_client", log_to_file=False)


# ============================================================================
# 连接池管理器
# ============================================================================

class _ConnectionPoolManager:
    """HTTP连接池管理器

    提供共享的 requests.Session，带有连接池配置。
    避免每次请求都创建新的TCP连接，显著提升性能。
    """

    def __init__(self):
        self._session: Optional[requests.Session] = None
        self._initialized = False

    def _create_session(self) -> requests.Session:
        """创建配置好的 Session

        配置说明:
        - pool_connections: 连接池数量
        - pool_maxsize: 每个池的最大连接数
        - max_retries: 自动重试次数
        - backoff_factor: 重试退避因子
        """
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=3,  # 最大重试次数
            backoff_factor=0.5,  # 重试延迟因子: 0.5, 1, 2, 4秒
            status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的HTTP状态码
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )

        # 配置连接池适配器
        adapter = HTTPAdapter(
            pool_connections=10,  # 连接池数量
            pool_maxsize=20,  # 每个池的最大连接数
            max_retries=retry_strategy
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        logger.debug("[ConnectionPool] Session 已创建并配置连接池")
        return session

    def get_session(self) -> requests.Session:
        """获取共享的 Session

        Returns:
            配置好的 requests.Session 实例
        """
        if not self._initialized:
            self._session = self._create_session()
            self._initialized = True

        return self._session

    def close(self) -> None:
        """关闭 Session（通常在应用关闭时调用）"""
        if self._session:
            self._session.close()
            self._initialized = False
            logger.debug("[ConnectionPool] Session 已关闭")


# 全局单例
_connection_pool_manager = _ConnectionPoolManager()


def get_http_session() -> requests.Session:
    """获取共享的 HTTP Session

    Returns:
        配置好连接池的 requests.Session

    Example:
        >>> session = get_http_session()
        >>> response = session.post("http://example.com/api", data={"key": "value"})
    """
    return _connection_pool_manager.get_session()

edge_lang_voice_map = {
    '英语': 'en-AU-NatashaNeural', # 英语有多个地区和女性人声，此处随意选择一个
    '中文': 'zh-CN-XiaoxiaoNeural', # 中文有多个地区和女性人声，此处随意选择一个普通话
    '中文-小说类型': "zh-CN-YunxiNeural",
    '葡萄牙语-巴西': 'pt-BR-FranciscaNeural', # 巴西葡萄牙语女性人声
    '葡萄牙语-葡萄牙': 'pt-PT-RaquelNeural', # 欧洲葡萄牙语女性人声
    '南非荷兰语': 'af-ZA-WillemNeural', # 此语言只有男性人声，已备注
    '阿姆哈拉语': 'am-ET-MekdesNeural',
    '阿拉伯语': 'ar-AE-FatimaNeural', # 阿拉伯语有多个地区和女性人声，此处随意选择一个
    '阿塞拜疆语': 'az-AZ-BanuNeural',
    '保加利亚语': 'bg-BG-KalinaNeural',
    '孟加拉语': 'bn-BD-NabanitaNeural', # 孟加拉语有多个地区和女性人声，此处随意选择一个
    '波斯尼亚语': 'bs-BA-VesnaNeural',
    '加泰罗尼亚语': 'ca-ES-JoanaNeural',
    '捷克语': 'cs-CZ-VlastaNeural',
    '威尔士语': 'cy-GB-NiaNeural',
    '丹麦语': 'da-DK-ChristelNeural',
    '德语': 'de-AT-IngridNeural', # 德语有多个地区和女性人声，此处随意选择一个
    '希腊语': 'el-GR-AthinaNeural',
    '西班牙语': 'es-AR-ElenaNeural', # 西班牙语有多个地区和女性人声，此处随意选择一个
    '爱沙尼亚语': 'et-EE-AnuNeural',
    '波斯语': 'fa-IR-DilaraNeural',
    '芬兰语': 'fi-FI-NooraNeural',
    '菲律宾语': 'fil-PH-BlessicaNeural',
    '法语': 'fr-BE-CharlineNeural', # 法语有多个地区和女性人声，此处随意选择一个
    '爱尔兰语': 'ga-IE-OrlaNeural',
    '加利西亚语': 'gl-ES-SabelaNeural',
    '古吉拉特语': 'gu-IN-DhwaniNeural',
    '希伯来语': 'he-IL-HilaNeural',
    '印地语': 'hi-IN-SwaraNeural',
    '克罗地亚语': 'hr-HR-GabrijelaNeural',
    '匈牙利语': 'hu-HU-NoemiNeural',
    '印尼语': 'id-ID-GadisNeural',
    '冰岛语': 'is-IS-GudrunNeural',
    '意大利语': 'it-IT-ElsaNeural', # 意大利语有多个女性人声，此处随意选择一个
    '因纽特语 (加拿大)': 'iu-Cans-CA-SiqiniqNeural', # 因纽特语有不同书写系统和女性人声，此处随意选择一个 Cans 版本
    '日语': 'ja-JP-NanamiNeural',
    '爪哇语': 'jv-ID-SitiNeural',
    '格鲁吉亚语': 'ka-GE-EkaNeural',
    '哈萨克语': 'kk-KZ-AigulNeural',
    '高棉语': 'km-KH-SreymomNeural',
    '卡纳达语': 'kn-IN-SapnaNeural',
    '韩语': 'ko-KR-SunHiNeural',
    '老挝语': 'lo-LA-KeomanyNeural',
    '立陶宛语': 'lt-LT-OnaNeural',
    '拉脱维亚语': 'lv-LV-EveritaNeural',
    '马其顿语': 'mk-MK-MarijaNeural',
    '马拉雅拉姆语': 'ml-IN-SobhanaNeural',
    '蒙古语': 'mn-MN-YesuiNeural',
    '马拉地语': 'mr-IN-AarohiNeural',
    '马来语': 'ms-MY-YasminNeural',
    '马耳他语': 'mt-MT-GraceNeural',
    '缅甸语': 'my-MM-NilarNeural',
    '挪威语': 'nb-NO-PernilleNeural',
    '尼泊尔语': 'ne-NP-HemkalaNeural',
    '荷兰语': 'nl-BE-DenaNeural', # 荷兰语有多个地区和女性人声，此处随意选择一个
    '波兰语': 'pl-PL-ZofiaNeural',
    '普什图语': 'ps-AF-LatifaNeural',
    '罗马尼亚语': 'ro-RO-AlinaNeural',
    '俄语': 'ru-RU-SvetlanaNeural',
    '僧伽罗语': 'si-LK-ThiliniNeural',
    '斯洛伐克语': 'sk-SK-ViktoriaNeural',
    '斯洛文尼亚语': 'sl-SI-PetraNeural',
    '索马里语': 'so-SO-UbaxNeural',
    '阿尔巴尼亚语': 'sq-AL-AnilaNeural',
    '塞尔维亚语': 'sr-RS-SophieNeural',
    '巽他语': 'su-ID-TutiNeural',
    '瑞典语': 'sv-SE-SofieNeural',
    '斯瓦希里语': 'sw-KE-ZuriNeural', # 斯瓦希里语有多个地区和女性人声，此处随意选择一个
    '泰米尔语': 'ta-IN-PallaviNeural', # 泰米尔语有多个地区和女性人声，此处随意选择一个
    '泰卢固语': 'te-IN-ShrutiNeural',
    '泰语': 'th-TH-PremwadeeNeural',
    '土耳其语': 'tr-TR-EmelNeural',
    '乌克兰语': 'uk-UA-PolinaNeural',
    '乌尔都语': 'ur-IN-GulNeural', # 乌尔都语有多个地区和女性人声，此处随意选择一个
    '乌兹别克语': 'uz-UZ-MadinaNeural',
    '越南语': 'vi-VN-HoaiMyNeural',
    '粤语 (香港)': 'zh-HK-HiuGaaiNeural', # 香港粤语女性人声
    '台湾中文': 'zh-TW-HsiaoChenNeural', # 台湾中文女性人声
    '祖鲁语': 'zu-ZA-ThandoNeural',
}


class VoiceSynthesisClient:
    def __init__(self, base_url: str = "http://10.147.20.56:8000") -> None:
        """初始化语音合成客户端

        Args:
            base_url: 服务基础URL
        """
        self.base_url = base_url.rstrip('/')
        # 使用共享的 HTTP Session（带连接池）
        self._session = get_http_session()

    def synthesize_voice(
        self,
        text: str,
        audio_file_path: Optional[str] = None,
        tts_audio_file_path: Optional[str] = None,
        voice: str = "beth_ecmix",
        volume: int = 50,
        speech_rate: int = 0,
        pitch_rate: int = 0,
        output_file: Optional[str] = None,
        tts_type: Optional[str] = 'edge',
        diffusion_steps: int = 50,
        length_adjust: float = 1.0,
        inference_cfg_rate: float = 0.7,
    ) -> bool:
        """
        Send a request to the voice synthesis API

        使用连接池复用 TCP 连接，显著提升性能。

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
        url = f"{self.base_url}/synthesize/"

        # 使用上下文管理器确保文件正确关闭
        file_handles = []
        try:
            files = {}
            if audio_file_path:
                audio_file_pathf = open(audio_file_path, 'rb')
                files['audio_file'] = audio_file_pathf
                file_handles.append(audio_file_pathf)
            if tts_audio_file_path:
                tts_audio_file_pathf = open(tts_audio_file_path, 'rb')
                files['tts_audio_file'] = tts_audio_file_pathf
                file_handles.append(tts_audio_file_pathf)

            data = {
                'text': text,
                'voice': voice,
                'volume': volume,
                'speech_rate': speech_rate,
                'pitch_rate': pitch_rate,
                'tts_type':tts_type,
                "diffusion_steps": diffusion_steps,
                "length_adjust":length_adjust,
                "inference_cfg_rate":inference_cfg_rate,
            }

            # 使用共享 Session（连接池自动复用）
            # Session 配置了自动重试，这里减少手动重试次数
            for attempt in range(2):
                try:
                    response = self._session.post(
                        url,
                        files=files,
                        data=data,
                        timeout=180
                    )
                    if response.status_code == 200:
                        if output_file:
                            with open(output_file, 'wb') as out_file:
                                out_file.write(response.content)
                        return True
                    else:
                        logger.error(f"Error: {response.status_code} - {response.text}")
                        return False
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except requests.exceptions.RequestException as request_e:
                    # 网络请求错误（Session 已配置自动重试）
                    if attempt == 0:  # 仅在第一次失败时记录警告
                        logger.warning(f"[synthesize_voice] 请求失败，尝试重试: {str(request_e)}")
                except Exception as request_e:
                    # 其他未预期的异常
                    logger.exception(f"[synthesize_voice] 请求时发生未知异常: {str(request_e)}")

            # 重试后仍失败
            return False

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他未预期的异常
            logger.exception(f"[synthesize_voice] 发生未知异常: {str(e)}")
            return False
        finally:
            # 确保所有文件句柄都被关闭
            for handle in file_handles:
                try:
                    if not handle.closed:
                        handle.close()
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except (OSError, IOError) as close_e:
                    # 文件IO错误
                    logger.warning(f"[synthesize_voice] 关闭文件句柄失败: {close_e}")
                except Exception as close_e:
                    # 其他异常
                    logger.warning(f"[synthesize_voice] 关闭文件句柄时发生未知异常: {close_e}")

client = VoiceSynthesisClient()

if __name__ == '__main__':
    # Example usage (requires a dummy source_audio.wav file)
    # Create a dummy source_audio.wav file for testing if needed
    # Example: touch dummy_source_audio.wav
    client = VoiceSynthesisClient('http://127.0.0.1:8007')


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