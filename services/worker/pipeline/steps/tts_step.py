"""TTS 语音合成步骤

将文本转换为语音，并生成对应的字幕文件。

支持两种执行模式：
1. 传统模式（向后兼容）：execute() 返回 PipelineContext
2. 函数式模式（推荐）：_execute_functional() 返回 TTSResult

依赖倒置原则改进：
- 依赖 ITTSService 抽象接口而非具体实现
- 支持依赖注入，便于测试和替换实现
"""
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from config import settings
from core.interfaces.service_interfaces import ITTSService
from core.logging_config import setup_logging

from .base import BaseStep
from ..context import PipelineContext

if TYPE_CHECKING:
    from ..results import TTSResult

logger = setup_logging("worker.pipeline.steps.tts")


class TTSGenerationStep(BaseStep):
    """TTS 语音合成步骤

    功能:
    1. 调用 TTS 服务生成语音
    2. 生成 SRT 字幕文件
    3. 保存音频和字幕文件到工作目录

    输入 (context/kwargs):
    - content: 要合成的文本
    - language_name: 语言名称
    - language_platform: TTS 平台
    - speech_speed: 语速
    - reference_audio_path: 参考音频（可选）
    - workspace_dir: 工作目录

    输出 (TTSResult):
    - audio_path: 音频文件路径
    - srt_path: 字幕文件路径
    - duration: 音频时长（秒）

    依赖注入:
    - 通过 __init__ 接收 ITTSService 实例
    - 如果未提供，使用默认的 TTSClient

    注意:
    - 此步骤不包含应用层重试逻辑
    - 重试由 Celery 任务级重试机制处理 (process_video_job)
    - 如果 TTS 服务调用失败，整个 Pipeline 会失败并由 Celery 重试
    - 这是正确的架构，因为:
      1. Worker 崩溃时重试不会丢失
      2. 支持跨 Worker 重试
      3. 网络中断时 Celery 可以等待后重试
      4. 不会阻塞 Worker 进程
    """

    name = "TTSGeneration"
    description = "文本转语音和字幕生成"

    # 启用函数式模式
    _functional_mode = True

    def __init__(self, tts_service: Optional[ITTSService] = None):
        """初始化 TTS 步骤

        Args:
            tts_service: TTS 服务实例（可选）
                        如果不提供，将创建默认的 TTSClient
        """
        if tts_service is None:
            from core.clients.tts_client import TTSClient
            tts_service = TTSClient(base_url=settings.TTS_SERVER_URL)

        self.tts_service = tts_service

    def validate(self, context: PipelineContext) -> None:
        """验证输入数据"""
        if not context.content:
            raise ValueError("文本内容不能为空")

        if not context.language_name:
            raise ValueError("语言名称不能为空")

        if not context.workspace_dir:
            raise ValueError("工作目录未设置")

    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行 TTS 合成（传统模式）

        此方法保持向后兼容，内部调用函数式模式。
        """
        from ..results import StepResult

        # 调用函数式实现
        result = self._execute_functional(context)

        # 将结果合并到 context
        context.audio_path = result.data.get("audio_path")
        context.srt_path = result.data.get("srt_path")

        return context

    def _execute_functional(
        self,
        context: PipelineContext,
        **kwargs
    ) -> "TTSResult":
        """执行 TTS 合成（函数式模式）

        Args:
            context: Pipeline 上下文
            **kwargs: 额外参数（可以从 context 读取）

        Returns:
            TTSResult: 包含 audio_path, srt_path, duration 的结果
        """
        from ..results import TTSResult

        # 准备输出路径
        workspace = Path(context.workspace_dir)
        output_base = workspace / "audio"
        output_base.mkdir(parents=True, exist_ok=True)

        audio_path = str(output_base / "speech.wav")
        srt_path = str(output_base / "subtitle.srt")

        logger.info(
            f"[{self.name}] 开始 TTS 合成 "
            f"(job_id={context.job_id}, language={context.language_name}, "
            f"platform={context.language_platform})"
        )

        # 调用 TTS 服务 (通过依赖注入的接口)
        try:
            result = self.tts_service.synthesize(
                text=context.content,
                language=context.language_name,
                output_path=audio_path,
                subtitle_output_path=srt_path,
                volume=50,
                speech_rate=context.speech_speed,
            )

            if not result.success:
                raise RuntimeError(f"TTS 合成失败: {result.error_message}")

            # 验证文件是否生成
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"音频文件未生成: {audio_path}")

            if result.srt_path and not os.path.exists(result.srt_path):
                raise FileNotFoundError(f"字幕文件未生成: {result.srt_path}")

            logger.info(
                f"[{self.name}] TTS 合成成功 "
                f"(job_id={context.job_id}, audio={audio_path}, srt={srt_path})"
            )

        except Exception as exc:
            logger.error(
                f"[{self.name}] TTS 合成失败 "
                f"(job_id={context.job_id}, error={exc})"
            )
            raise

        # 返回函数式结果
        return TTSResult(
            step_name=self.name,
            audio_path=audio_path,
            srt_path=result.srt_path,
            duration=result.duration
        )

    def post_process(
        self,
        context: PipelineContext,
        result: Optional["TTSResult"] = None
    ) -> None:
        """后处理

        Args:
            context: Pipeline 上下文
            result: TTS 结果（函数式模式下可用）
        """
        # 记录文件大小
        audio_path = None
        if result:
            audio_path = result.audio_path
        elif hasattr(context, 'audio_path'):
            audio_path = context.audio_path

        if audio_path and os.path.exists(audio_path):
            size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            logger.debug(
                f"[{self.name}] 音频文件大小: {size_mb:.2f} MB "
                f"(job_id={context.job_id})"
            )

    def _context_to_result(self, context: PipelineContext) -> "TTSResult":
        """将 PipelineContext 转换为 TTSResult

        Args:
            context: Pipeline 上下文

        Returns:
            TTSResult
        """
        from ..results import TTSResult

        audio_path = getattr(context, 'audio_path', None)
        srt_path = getattr(context, 'srt_path', None)
        duration = 0.0

        if audio_path and os.path.exists(audio_path):
            duration = self._get_audio_duration(audio_path)

        return TTSResult(
            step_name=self.name,
            audio_path=audio_path,
            srt_path=srt_path,
            duration=duration
        )

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长

        Args:
            audio_path: 音频文件路径

        Returns:
            float: 音频时长（秒）
        """
        try:
            import librosa
            duration = librosa.get_duration(filename=audio_path)
            logger.debug(
                f"[{self.name}] 音频时长: {duration:.2f}秒 "
                f"(audio_path={audio_path})"
            )
            return duration
        except ImportError:
            logger.warning(
                f"[{self.name}] librosa 未安装，无法获取音频时长 "
                f"(audio_path={audio_path})"
            )
            return 0.0
        except Exception as exc:
            logger.error(
                f"[{self.name}] 获取音频时长失败 "
                f"(audio_path={audio_path}, error={exc})"
            )
            return 0.0


class EdgeTTSSubtitleStep(BaseStep):
    """EdgeTTS 字幕生成步骤（备用方案）

    当主 TTS 服务失败时，可以使用此步骤直接调用 EdgeTTS。

    支持两种执行模式：
    1. 传统模式：execute() 返回 PipelineContext
    2. 函数式模式：_execute_functional() 返回 TTSResult
    """

    name = "EdgeTTSSubtitle"
    description = "使用 EdgeTTS 生成语音和字幕"

    # 启用函数式模式
    _functional_mode = True

    def validate(self, context: PipelineContext) -> None:
        """验证输入"""
        if not context.content:
            raise ValueError("文本内容不能为空")

        if not context.workspace_dir:
            raise ValueError("工作目录未设置")

    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行 EdgeTTS 合成（传统模式）

        此方法保持向后兼容。
        """
        from ..results import TTSResult

        # 调用函数式实现
        result = self._execute_functional(context)

        # 将结果合并到 context
        context.audio_path = result.data.get("audio_path")
        context.srt_path = result.data.get("srt_path")

        return context

    def _execute_functional(
        self,
        context: PipelineContext,
        **kwargs
    ) -> "TTSResult":
        """执行 EdgeTTS 合成（函数式模式）

        Args:
            context: Pipeline 上下文
            **kwargs: 额外参数

        Returns:
            TTSResult
        """
        from clients.tts_seedvc_client import VoiceSynthesisClient, edge_lang_voice_map
        from ..results import TTSResult

        workspace = Path(context.workspace_dir)
        output_base = workspace / "audio"
        output_base.mkdir(parents=True, exist_ok=True)

        audio_path = str(output_base / "speech_edge.wav")
        srt_path = str(output_base / "subtitle_edge.srt")

        # 获取语音映射
        voice_name = edge_lang_voice_map.get(
            context.language_name,
            edge_lang_voice_map.get("中文", "zh-CN-XiaoxiaoNeural")
        )

        logger.info(
            f"[{self.name}] 使用 EdgeTTS 合成 "
            f"(job_id={context.job_id}, voice={voice_name})"
        )

        # 调用 EdgeTTS
        client = VoiceSynthesisClient(base_url=settings.TTS_SERVER_URL)

        # 准备 SRT 输出路径
        output_dir = str(output_base)

        success = client.synthesize_voice(
            text=context.content,
            voice=voice_name,
            output_file=audio_path,
            volume=50,
            speech_rate=int((context.speech_speed - 1.0) * 100),  # 转换为 EdgeTTS 格式
            tts_type="edge",
        )

        if not success:
            raise RuntimeError("EdgeTTS 合成失败")

        # 生成字幕（从音频时间戳）
        self._generate_simple_srt(context, srt_path)

        # 计算时长
        duration = self._get_audio_duration(audio_path)

        # 返回结果
        return TTSResult(
            step_name=self.name,
            audio_path=audio_path,
            srt_path=srt_path,
            duration=duration
        )

    def _generate_simple_srt(self, context: PipelineContext, srt_path: str) -> None:
        """生成简单字幕文件

        这是一个简化实现，实际应该解析 TTS 返回的时间戳。

        Args:
            context: Pipeline 上下文
            srt_path: SRT 文件路径
        """
        # 按句子分割文本
        sentences = [s.strip() for s in context.content.split("。") if s.strip()]

        with open(srt_path, "w", encoding="utf-8") as f:
            for i, sentence in enumerate(sentences, 1):
                # 简单假设每个句子 5 秒
                start_time = i * 5
                end_time = (i + 1) * 5

                f.write(f"{i}\n")
                f.write(f"{self._format_srt_time(start_time)} --> {self._format_srt_time(end_time)}\n")
                f.write(f"{sentence}。\n")
                f.write("\n")

    def _format_srt_time(self, seconds: int) -> str:
        """格式化 SRT 时间

        Args:
            seconds: 秒数

        Returns:
            str: SRT 时间格式 (00:00:00,000)
        """
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d},000"

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长

        Args:
            audio_path: 音频文件路径

        Returns:
            float: 音频时长（秒）
        """
        try:
            import librosa
            duration = librosa.get_duration(filename=audio_path)
            return duration
        except (ImportError, Exception):
            return 0.0

    def _context_to_result(self, context: PipelineContext) -> "TTSResult":
        """将 PipelineContext 转换为 TTSResult

        Args:
            context: Pipeline 上下文

        Returns:
            TTSResult
        """
        from ..results import TTSResult

        audio_path = getattr(context, 'audio_path', None)
        srt_path = getattr(context, 'srt_path', None)
        duration = 0.0

        if audio_path:
            duration = self._get_audio_duration(audio_path)

        return TTSResult(
            step_name=self.name,
            audio_path=audio_path,
            srt_path=srt_path,
            duration=duration
        )


__all__ = [
    "TTSGenerationStep",
    "EdgeTTSSubtitleStep",
]
