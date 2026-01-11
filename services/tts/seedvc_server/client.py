"""
SeedVC TTS 客户端
提供与 SeedVC TTS 服务交互的客户端接口
"""
import os
from typing import Optional

import requests

from core.logging_config import setup_logging

logger = setup_logging("tts.seedvc_server.client")

# Edge TTS 语言到语音映射
edge_lang_voice_map = {
    '英语': 'en-AU-NatashaNeural',
    '中文': 'zh-CN-XiaoxiaoNeural',
    '中文-小说类型': "zh-CN-YunxiNeural",
    '葡萄牙语-巴西': 'pt-BR-FranciscaNeural',
    '葡萄牙语-葡萄牙': 'pt-PT-RaquelNeural',
    '南非荷兰语': 'af-ZA-WillemNeural',
    '阿姆哈拉语': 'am-ET-MekdesNeural',
    '阿拉伯语': 'ar-AE-FatimaNeural',
    '阿塞拜疆语': 'az-AZ-BanuNeural',
    '保加利亚语': 'bg-BG-KalinaNeural',
    '孟加拉语': 'bn-BD-NabanitaNeural',
    '波斯尼亚语': 'bs-BA-VesnaNeural',
    '加泰罗尼亚语': 'ca-ES-JoanaNeural',
    '捷克语': 'cs-CZ-VlastaNeural',
    '威尔士语': 'cy-GB-NiaNeural',
    '丹麦语': 'da-DK-ChristelNeural',
    '德语': 'de-AT-IngridNeural',
    '希腊语': 'el-GR-AthinaNeural',
    '西班牙语': 'es-AR-ElenaNeural',
    '爱沙尼亚语': 'et-EE-AnuNeural',
    '波斯语': 'fa-IR-DilaraNeural',
    '芬兰语': 'fi-FI-NooraNeural',
    '菲律宾语': 'fil-PH-BlessicaNeural',
    '法语': 'fr-BE-CharlineNeural',
    '爱尔兰语': 'ga-IE-OrlaNeural',
    '加利西亚语': 'gl-ES-SabelaNeural',
    '古吉拉特语': 'gu-IN-DhwaniNeural',
    '希伯来语': 'he-IL-HilaNeural',
    '印地语': 'hi-IN-SwaraNeural',
    '克罗地亚语': 'hr-HR-GabrijelaNeural',
    '匈牙利语': 'hu-HU-NoemiNeural',
    '印尼语': 'id-ID-GadisNeural',
    '冰岛语': 'is-IS-GudrunNeural',
    '意大利语': 'it-IT-ElsaNeural',
    '因纽特语 (加拿大)': 'iu-Cans-CA-SiqiniqNeural',
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
    '荷兰语': 'nl-BE-DenaNeural',
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
    '斯瓦希里语': 'sw-KE-ZuriNeural',
    '泰米尔语': 'ta-IN-PallaviNeural',
    '泰卢固语': 'te-IN-ShrutiNeural',
    '泰语': 'th-TH-PremwadeeNeural',
    '土耳其语': 'tr-TR-EmelNeural',
    '乌克兰语': 'uk-UA-PolinaNeural',
    '乌尔都语': 'ur-IN-GulNeural',
    '乌兹别克语': 'uz-UZ-MadinaNeural',
    '越南语': 'vi-VN-HoaiMyNeural',
    '粤语 (香港)': 'zh-HK-HiuGaaiNeural',
    '台湾中文': 'zh-TW-HsiaoChenNeural',
    '祖鲁语': 'zu-ZA-ThandoNeural',
}


class VoiceSynthesisClient:
    """语音合成客户端"""
    
    def __init__(self, base_url: str = "http://10.147.20.56:8000"):
        """
        初始化客户端
        
        Args:
            base_url: 服务基础 URL
        """
        self.base_url = base_url.rstrip('/')
        logger.info(f"初始化语音合成客户端: {self.base_url}")
    
    def synthesize_voice(
        self,
        text: str,
        audio_file_path: Optional[str] = None,
        tts_audio_file_path: Optional[str] = None,
        voice: str = "beth_ecmix",
        volume: int = 50,
        speech_rate: float = 1.0,
        pitch_rate: int = 0,
        output_file: Optional[str] = None,
        tts_type: Optional[str] = 'edge',
        diffusion_steps: int = 50,
        length_adjust: float = 1.0,
        inference_cfg_rate: float = 0.7,
    ) -> bool:
        """
        发送语音合成请求
        
        Args:
            text: 要合成的文本
            audio_file_path: 参考音频文件路径（用于语音克隆）
            tts_audio_file_path: 预生成的 TTS 音频文件路径
            voice: 语音模型名称
            volume: 音量 (0-100)
            speech_rate: 语速
            pitch_rate: 音调调整
            output_file: 输出文件路径（如果为 None，则不保存）
            tts_type: TTS 类型 ('edge' 或 'aly')
            diffusion_steps: 扩散步数
            length_adjust: 长度调整因子
            inference_cfg_rate: 推理配置率
            
        Returns:
            bool: 成功返回 True，失败返回 False
        """
        url = f"{self.base_url}/synthesize/"
        
        try:
            files = {}
            file_handles = []  # 跟踪打开的文件句柄
            
            try:
                # 打开参考音频文件
                if audio_file_path:
                    if not os.path.exists(audio_file_path):
                        logger.error(f"参考音频文件不存在: {audio_file_path}")
                        return False
                    audio_file_handle = open(audio_file_path, 'rb')
                    files['audio_file'] = audio_file_handle
                    file_handles.append(audio_file_handle)
                    logger.debug(f"已打开参考音频文件: {audio_file_path}")
                
                # 打开 TTS 音频文件
                if tts_audio_file_path:
                    if not os.path.exists(tts_audio_file_path):
                        logger.error(f"TTS 音频文件不存在: {tts_audio_file_path}")
                        return False
                    tts_audio_file_handle = open(tts_audio_file_path, 'rb')
                    files['tts_audio_file'] = tts_audio_file_handle
                    file_handles.append(tts_audio_file_handle)
                    logger.debug(f"已打开 TTS 音频文件: {tts_audio_file_path}")

                data = {
                    'text': text,
                    'voice': voice,
                    'volume': volume,
                    'speech_rate': speech_rate,
                    'pitch_rate': pitch_rate,
                    'tts_type': tts_type,
                    "diffusion_steps": diffusion_steps,
                    "length_adjust": length_adjust,
                    "inference_cfg_rate": inference_cfg_rate,
                }
                
                logger.debug(f"发送请求到: {url}, text='{text[:50]}...'")
                response = requests.post(url, files=files, data=data, timeout=300)
                
                if response.status_code == 200:
                    if output_file:
                        output_dir = os.path.dirname(output_file)
                        if output_dir and not os.path.exists(output_dir):
                            os.makedirs(output_dir, exist_ok=True)
                        
                        with open(output_file, 'wb') as out_file:
                            out_file.write(response.content)
                        logger.info(f"输出文件已保存: {output_file}")
                    return True
                else:
                    logger.error(f"请求失败: {response.status_code} - {response.text}")
                    return False
                    
            finally:
                # 确保所有文件句柄都被关闭
                for handle in file_handles:
                    try:
                        handle.close()
                    except Exception as e:
                        logger.warning(f"关闭文件句柄失败: {e}")
                        
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {url}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}", exc_info=True)
            return False
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（请求处理错误等）
            logger.error(f"[synthesize_voice] 处理请求时发生错误: {e}", exc_info=True)
            return False


# 默认客户端实例
client = VoiceSynthesisClient()

if __name__ == '__main__':
    # 示例用法
    client = VoiceSynthesisClient('http://127.0.0.1:8007')

    text = 'Mr. Mu'
    source_audio_path = './source_s2.wav'
    output_dir = 'tts_audio'
    volume = 50
    speech_rate = 1.1

    # 示例：仅 TTS（无语音克隆）
    # client.synthesize_voice(
    #     text=text,
    #     audio_file_path=None,
    #     voice='en-AU-NatashaNeural',
    #     output_file='test1.wav',
    #     volume=volume,
    #     speech_rate=speech_rate,
    #     tts_type='edge'
    # )

    # 示例：TTS + 语音克隆
    client.synthesize_voice(
        text=text,
        audio_file_path=source_audio_path,
        voice='en-AU-NatashaNeural',
        output_file='test2.wav',
        volume=volume,
        speech_rate=speech_rate,
        tts_type='edge'
    )
