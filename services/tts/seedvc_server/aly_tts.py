# -*- coding: utf-8 -*-
"""
阿里云 TTS 语音合成服务封装
提供基于阿里云语音服务的语音合成功能
"""
import http.client
import json
import urllib.parse
from typing import Optional

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from core.logging_config import setup_logging

logger = setup_logging("tts.seedvc_server.aly_tts")


class AliYunTTS:
    """阿里云 TTS 语音合成客户端"""
    
    def __init__(self, access_key_id: str, access_key_secret: str, app_key: str):
        """
        初始化阿里云 TTS 客户端
        
        Args:
            access_key_id: 阿里云 AccessKey ID
            access_key_secret: 阿里云 AccessKey Secret
            app_key: 阿里云语音服务的 AppKey
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.app_key = app_key
        self.host = 'nls-gateway-cn-shanghai.aliyuncs.com'
        
        try:
            self.acs_client = AcsClient(
                access_key_id,
                access_key_secret,
                'cn-shanghai'
            )
            logger.info("阿里云 TTS 客户端初始化成功")
        except Exception as e:
            logger.error(f"阿里云 TTS 客户端初始化失败: {e}", exc_info=True)
            raise
    
    def synthesize_speech(
        self,
        text: str,
        audio_save_file: str,
        voice: str = "xiaoyun",
        format: str = "wav",
        sample_rate: int = 16000,
        volume: int = 50,
        speech_rate: float = 1.0,
        pitch_rate: int = 0,
        method: str = "GET"
    ) -> bool:
        """
        语音合成主方法
        
        Args:
            text: 要合成的文本
            audio_save_file: 保存音频文件的路径
            voice: 语音模型名称
            format: 音频格式
            sample_rate: 采样率
            volume: 音量 (0-100)
            speech_rate: 语速倍数
            pitch_rate: 音调调整
            method: HTTP 方法 ('GET' 或 'POST')
            
        Returns:
            bool: 成功返回 True，失败返回 False
        """
        logger.info(f"开始阿里云 TTS 合成: text='{text[:min(len(text), 50)]}...', voice={voice}")
        
        try:
            # 获取 Token
            token = self._get_token()
            if not token:
                logger.error("获取 Token 失败")
                return False
            
            # 转换语速格式（阿里云特定格式）
            speech_rate_int = int((1 - 1 / speech_rate) / 0.002) if speech_rate > 0 else 0
            
            # 根据方法选择处理方式
            if method.upper() == "GET":
                return self._process_get_request(
                    token, text, audio_save_file, voice, format,
                    sample_rate, volume, speech_rate_int, pitch_rate
                )
            elif method.upper() == "POST":
                return self._process_post_request(
                    token, text, audio_save_file, voice, format,
                    sample_rate, volume, speech_rate_int, pitch_rate
                )
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}，请使用 GET 或 POST")
                
        except Exception as e:
            logger.error(f"语音合成失败: {e}", exc_info=True)
            return False
    
    def _get_token(self) -> Optional[str]:
        """
        使用 AccessKey 获取 Token
        
        Returns:
            Token 字符串，失败返回 None
        """
        request = CommonRequest()
        request.set_accept_format('json')
        request.set_domain('nls-meta.cn-shanghai.aliyuncs.com')
        request.set_method('POST')
        request.set_protocol_type('https')
        request.set_version('2019-02-28')
        request.set_action_name('CreateToken')
        
        try:
            response = self.acs_client.do_action_with_exception(request)
            response_dict = json.loads(response.decode('utf-8'))
            token = response_dict.get('Token', {}).get('Id')
            
            if token:
                logger.debug("Token 获取成功")
                return token
            else:
                logger.error(f"Token 响应格式错误: {response_dict}")
                return None
                
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（Token获取错误等）
            logger.error(f"[_get_token] 获取 Token 失败: {e}", exc_info=True)
            return None
    
    def _process_get_request(
        self,
        token: str,
        text: str,
        audio_save_file: str,
        voice: str,
        format: str,
        sample_rate: int,
        volume: int,
        speech_rate: int,
        pitch_rate: int
    ) -> bool:
        """
        GET 请求方式处理
        
        Args:
            token: 认证 Token
            text: 要合成的文本
            audio_save_file: 保存音频文件的路径
            voice: 语音模型名称
            format: 音频格式
            sample_rate: 采样率
            volume: 音量
            speech_rate: 语速
            pitch_rate: 音调
            
        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            url = f'/stream/v1/tts?appkey={self.app_key}&token={token}'
            url += f'&text={self._url_encode(text)}'
            url += f'&format={format}'
            url += f'&sample_rate={sample_rate}'
            url += f'&voice={voice}'
            url += f'&volume={volume}'
            url += f'&speech_rate={speech_rate}'
            url += f'&pitch_rate={pitch_rate}'
            
            conn = http.client.HTTPSConnection(self.host)
            conn.request(method='GET', url=url)
            
            return self._handle_response(conn, audio_save_file)
            
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（GET请求处理错误等）
            logger.error(f"[_process_get_request] GET 请求处理失败: {e}", exc_info=True)
            return False
    
    def _process_post_request(
        self,
        token: str,
        text: str,
        audio_save_file: str,
        voice: str,
        format: str,
        sample_rate: int,
        volume: int,
        speech_rate: int,
        pitch_rate: int
    ) -> bool:
        """
        POST 请求方式处理
        
        Args:
            token: 认证 Token
            text: 要合成的文本
            audio_save_file: 保存音频文件的路径
            voice: 语音模型名称
            format: 音频格式
            sample_rate: 采样率
            volume: 音量
            speech_rate: 语速
            pitch_rate: 音调
            
        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            url = '/stream/v1/tts'
            http_headers = {'Content-Type': 'application/json'}
            
            body = {
                'appkey': self.app_key,
                'token': token,
                'text': text,
                'format': format,
                'sample_rate': sample_rate,
                'voice': voice,
                'volume': volume,
                'speech_rate': speech_rate,
                'pitch_rate': pitch_rate
            }
            
            conn = http.client.HTTPSConnection(self.host)
            conn.request(
                method='POST',
                url=url,
                body=json.dumps(body),
                headers=http_headers
            )
            
            return self._handle_response(conn, audio_save_file)
            
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（POST请求处理错误等）
            logger.error(f"[_process_post_request] POST 请求处理失败: {e}", exc_info=True)
            return False
    
    def _handle_response(self, conn: http.client.HTTPConnection, audio_save_file: str) -> bool:
        """
        处理 HTTP 响应
        
        Args:
            conn: HTTP 连接对象
            audio_save_file: 保存音频文件的路径
            
        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            response = conn.getresponse()
            status = response.status
            reason = response.reason
            logger.debug(f'响应状态: {status} {reason}')
            
            content_type = response.getheader('Content-Type', '')
            logger.debug(f'Content-Type: {content_type}')
            
            body = response.read()
            conn.close()
            
            if 'audio/' in content_type:
                try:
                    with open(audio_save_file, mode='wb') as f:
                        f.write(body)
                    logger.info(f'音频文件已保存: {audio_save_file}')
                    return True
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except (OSError, PermissionError, IOError) as e:
                    # 文件系统错误
                    logger.error(f"[_handle_response] 文件系统错误，保存音频文件失败: {e}", exc_info=True)
                    return False
                except Exception as e:
                    # 其他异常
                    logger.error(f"[_handle_response] 保存音频文件失败: {e}", exc_info=True)
                    return False
            else:
                error_msg = body.decode('utf-8', errors='ignore')
                logger.error(f'请求失败: {error_msg}')
                return False
                
        except Exception as e:
            logger.error(f"处理响应失败: {e}", exc_info=True)
            return False
    
    def _url_encode(self, text: str) -> str:
        """
        URL 编码处理
        
        Args:
            text: 要编码的文本
            
        Returns:
            编码后的文本
        """
        text_encoded = urllib.parse.quote_plus(text)
        text_encoded = text_encoded.replace("+", "%20")
        text_encoded = text_encoded.replace("*", "%2A")
        text_encoded = text_encoded.replace("%7E", "~")
        return text_encoded
