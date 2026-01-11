# -*- coding: utf-8 -*-
"""
SeedVC TTS 服务主入口
提供 FastAPI 接口用于语音合成和语音克隆
"""
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

import uvicorn
from aly_tts import AliYunTTS
from edge_tts_serve import EdgeTTS
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from seedvc_run import load_models, seedvc_clone

# 统一日志配置和异常处理
from core.exceptions import (
    BatchShortException,
    ConfigurationException,
    ServiceException,
)
from core.logging_config import setup_logging

logger = setup_logging("tts.seedvc_server")

app = FastAPI(
    title="SeedVC TTS Service",
    description="语音合成和语音克隆服务",
    version="1.0.0"
)

# 全局模型变量
model = None
semantic_fn = None
f0_fn = None
vocoder_fn = None
campplus_model = None
mel_fn = None
mel_fn_args = None
aly_tts = None
edge_tts = None


@app.on_event("startup")
async def startup_event():
    """启动时加载模型和初始化 TTS 服务"""
    global model, semantic_fn, f0_fn, vocoder_fn, campplus_model, mel_fn, mel_fn_args
    global aly_tts, edge_tts
    
    try:
        logger.info("开始加载模型...")
        model, semantic_fn, f0_fn, vocoder_fn, campplus_model, mel_fn, mel_fn_args = load_models()
        logger.info("模型加载完成")
        
        # 初始化 TTS 服务
        ACCESS_KEY_ID = os.getenv('ACCESS_KEY_ID')
        ACCESS_KEY_SECRET = os.getenv('ACCESS_KEY_SECRET')
        APP_KEY = os.getenv('APP_KEY')
        PROXY = os.getenv('PROXY')
        
        # 初始化阿里云 TTS（如果配置了密钥）
        if ACCESS_KEY_ID and ACCESS_KEY_SECRET and APP_KEY:
            logger.info("检测到阿里云 TTS 配置，初始化 AliYunTTS")
            try:
                aly_tts = AliYunTTS(ACCESS_KEY_ID, ACCESS_KEY_SECRET, APP_KEY)
                logger.info("AliYunTTS 初始化成功")
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except (ImportError, AttributeError) as e:
                # 导入错误或属性错误
                logger.warning(f"[startup_event] AliYunTTS 初始化失败: {e}，将仅使用 EdgeTTS")
                aly_tts = None
            except (ValueError, RuntimeError) as e:
                # 配置错误或运行时错误
                logger.warning(f"[startup_event] AliYunTTS 初始化失败: {e}，将仅使用 EdgeTTS")
                aly_tts = None
            except Exception as e:
                # 其他未预期的异常
                logger.warning(f"[startup_event] AliYunTTS 初始化失败: {e}，将仅使用 EdgeTTS")
                aly_tts = None
        else:
            logger.info("未检测到阿里云 TTS 配置，将仅使用 EdgeTTS")
            aly_tts = None
        
        # 初始化 EdgeTTS
        proxy_value = PROXY if PROXY else None
        try:
            edge_tts = EdgeTTS(proxy=proxy_value)
            logger.info("EdgeTTS 初始化成功")
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (ImportError, AttributeError) as e:
            # 导入错误或属性错误
            logger.error(f"[startup_event] EdgeTTS 初始化失败: {e}", exc_info=True)
            edge_tts = None
        except (ValueError, RuntimeError) as e:
            # 配置错误或运行时错误
            logger.error(f"[startup_event] EdgeTTS 初始化失败: {e}", exc_info=True)
            edge_tts = None
        except Exception as e:
            # 其他未预期的异常
            logger.error(f"[startup_event] EdgeTTS 初始化失败: {e}", exc_info=True)
            edge_tts = None
            
        if not aly_tts and not edge_tts:
            logger.warning("所有 TTS 服务初始化失败，语音合成功能将不可用")
            
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（启动错误等）
        logger.error(f"[startup_event] 启动失败: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理资源"""
    logger.info("服务关闭，清理资源...")


def _cleanup_temp_dir(request_id: str):
    """
    清理临时目录
    
    Args:
        request_id: 请求 ID
    """
    temp_dir_path = Path(f"temp/{request_id}")
    try:
        if temp_dir_path.exists():
            shutil.rmtree(temp_dir_path)
            logger.debug(f"已清理临时目录: {temp_dir_path}")
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except (OSError, PermissionError) as e:
        # 文件系统错误
        logger.warning(f"[_cleanup_temp_dir] 清理临时目录失败（文件系统错误） {temp_dir_path}: {e}")
    except Exception as e:
        # 其他异常
        logger.warning(f"[_cleanup_temp_dir] 清理临时目录失败 {temp_dir_path}: {e}", exc_info=True)


@app.post("/synthesize/")
async def synthesize_voice(
    text: str = Form(...),
    voice: str = Form("beth_ecmix"),
    audio_file: Optional[UploadFile] = File(None),
    tts_audio_file: Optional[UploadFile] = File(None),
    volume: int = Form(50),
    speech_rate: float = Form(1.0),
    pitch_rate: int = Form(0),
    tts_type: str = Form('edge'),
    diffusion_steps: int = Form(30),
    length_adjust: float = Form(1.0),
    inference_cfg_rate: float = Form(0.7),
    background_tasks: BackgroundTasks = None
):
    """
    语音合成接口
    
    Args:
        text: 要合成的文本
        voice: 语音模型名称
        audio_file: 参考音频文件（用于语音克隆）
        tts_audio_file: 预生成的 TTS 音频文件（可选）
        volume: 音量 (0-100)
        speech_rate: 语速
        pitch_rate: 音调调整
        tts_type: TTS 类型 ('edge' 或 'aly')
        diffusion_steps: 扩散步数
        length_adjust: 长度调整因子
        inference_cfg_rate: 推理配置率
        background_tasks: 后台任务
        
    Returns:
        FileResponse: 生成的音频文件
        
    Raises:
        HTTPException: 如果处理失败
    """
    request_id = str(uuid.uuid4())
    temp_dir = Path(f"temp/{request_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"处理请求 {request_id}: text='{text[:50]}...', tts_type={tts_type}")
    
    try:
        tgt_voice_path = None
        final_output = temp_dir / "final_output.wav"
        tts_output_file = None
        
        # 保存上传的参考音频文件
        if audio_file:
            tgt_voice_path = temp_dir / "reference.wav"
            try:
                with open(tgt_voice_path, "wb") as buffer:
                    content = await audio_file.read()
                    buffer.write(content)
                logger.debug(f"已保存参考音频: {tgt_voice_path}")
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except (OSError, PermissionError, IOError) as e:
                # 文件系统错误
                logger.error(f"[synthesize_voice] 文件系统错误，保存参考音频失败: {e}", exc_info=True)
                raise HTTPException(status_code=400, detail=f"保存参考音频失败: {e}")
            except Exception as e:
                # 其他异常
                logger.error(f"[synthesize_voice] 保存参考音频失败: {e}", exc_info=True)
                raise HTTPException(status_code=400, detail=f"保存参考音频失败: {e}")
        
        # 处理 TTS 音频文件
        if tts_audio_file:
            tts_output_file = temp_dir / "tts_base.wav"
            try:
                with open(tts_output_file, "wb") as buffer:
                    content = await tts_audio_file.read()
                    buffer.write(content)
                logger.debug(f"已保存预生成 TTS 音频: {tts_output_file}")
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except (OSError, PermissionError, IOError) as e:
                # 文件系统错误
                logger.error(f"[synthesize_voice] 文件系统错误，保存TTS音频失败: {e}", exc_info=True)
                raise HTTPException(status_code=400, detail=f"保存 TTS 音频失败: {e}")
            except Exception as e:
                # 其他异常
                logger.error(f"[synthesize_voice] 保存 TTS 音频失败: {e}", exc_info=True)
                raise HTTPException(status_code=400, detail=f"保存 TTS 音频失败: {e}")
        else:
            # 生成 TTS 输出
            if not text or len(text.strip()) < 1:
                raise HTTPException(status_code=400, detail="文本不能为空")
            
            tts_output_file = temp_dir / "tts_output.wav"
            success = False
            
            try:
                if tts_type == 'aly':
                    if not aly_tts:
                        raise HTTPException(
                            status_code=503,
                            detail="阿里云 TTS 服务未初始化，请检查配置"
                        )
                    logger.debug(f"使用阿里云 TTS 合成语音")
                    success = aly_tts.synthesize_speech(
                        text=text,
                        audio_save_file=str(tts_output_file),
                        voice=voice,
                        format="wav",
                        sample_rate=16000,
                        volume=volume,
                        speech_rate=speech_rate,
                        pitch_rate=pitch_rate,
                        method="GET"
                    )
                else:
                    if not edge_tts:
                        raise HTTPException(
                            status_code=503,
                            detail="EdgeTTS 服务未初始化"
                        )
                    logger.debug(f"使用 EdgeTTS 合成语音")
                    success = edge_tts.synthesize_speech(
                        text=text,
                        audio_save_file=str(tts_output_file),
                        voice=voice,
                        format="wav",
                        sample_rate=16000,
                        volume=volume,
                        speech_rate=speech_rate,
                        pitch_rate=pitch_rate,
                        method="GET"
                    )
                
                if not success:
                    logger.error(f"TTS 合成失败: request_id={request_id}")
                    raise HTTPException(status_code=500, detail="TTS 合成失败")
                
                if not tts_output_file.exists():
                    logger.error(f"TTS 输出文件不存在: {tts_output_file}")
                    raise HTTPException(status_code=500, detail="TTS 输出文件生成失败")
                
                logger.info(f"TTS 合成成功: {tts_output_file}")
                
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except HTTPException:
                raise
            except Exception as e:
                # 其他异常（TTS合成错误等）
                logger.error(f"[synthesize_voice] TTS 合成异常: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"TTS 合成异常: {str(e)}")
        
        # 确定响应文件路径
        response_file_path = tts_output_file
        
        # 如果提供了参考音频，执行语音克隆
        if audio_file and tgt_voice_path and tgt_voice_path.exists():
            logger.info(f"开始语音克隆: request_id={request_id}")
            try:
                if not model:
                    raise HTTPException(
                        status_code=503,
                        detail="模型未加载，请等待服务启动完成"
                    )
                
                seedvc_clone(
                    model,
                    semantic_fn,
                    f0_fn,
                    vocoder_fn,
                    campplus_model,
                    mel_fn,
                    mel_fn_args,
                    str(tts_output_file),
                    str(tgt_voice_path),
                    diffusion_steps=diffusion_steps,
                    length_adjust=length_adjust,
                    inference_cfg_rate=inference_cfg_rate,
                    output=str(final_output)
                )
                
                if not final_output.exists():
                    logger.error(f"语音克隆输出文件不存在: {final_output}")
                    raise HTTPException(status_code=500, detail="语音克隆失败")
                
                response_file_path = final_output
                logger.info(f"语音克隆成功: {final_output}")
                
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except HTTPException:
                raise
            except Exception as e:
                # 其他异常（语音克隆错误等）
                logger.error(f"[synthesize_voice] 语音克隆异常: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"语音克隆异常: {str(e)}")
        
        # 添加后台清理任务
        if background_tasks:
            background_tasks.add_task(_cleanup_temp_dir, request_id)
            logger.debug(f"已添加后台清理任务: {request_id}")
        
        return FileResponse(
            str(response_file_path),
            media_type="audio/wav",
            filename="synthesized_voice.wav"
        )
        
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except HTTPException:
        raise
    except Exception as e:
        # 其他异常（请求处理错误等）
        logger.error(f"[synthesize_voice] 处理请求失败 {request_id}: {e}", exc_info=True)
        # 发生错误时立即清理
        _cleanup_temp_dir(request_id)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "aly_tts_available": aly_tts is not None,
        "edge_tts_available": edge_tts is not None
    }


def _status_for_exception(exc: BatchShortException) -> int:
    """根据异常类型返回对应的HTTP状态码。
    
    Args:
        exc: BatchShortException 异常实例
    
    Returns:
        HTTP状态码
    """
    if isinstance(exc, ConfigurationException):
        return 503
    if isinstance(exc, ServiceException):
        return 502
    return 500


@app.exception_handler(BatchShortException)
async def batchshort_exception_handler(request: Request, exc: BatchShortException) -> JSONResponse:
    """统一处理 BatchShort 异常"""
    status_code = _status_for_exception(exc)
    logger.error(
        f"BatchShortException: {exc.error_code} - {exc.message}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code
        }
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "code": exc.error_code,
            "message": exc.message,
            "success": False
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未预期的异常"""
    logger.exception(
        f"未预期的异常: {type(exc).__name__} - {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
            "success": False
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8007,
        reload=False,
        log_config=None
    )
