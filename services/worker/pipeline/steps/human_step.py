"""数字人合成步骤

将音频和视频合成为数字人视频。

支持两种执行模式：
1. 传统模式（向后兼容）：execute() 返回 PipelineContext
2. 函数式模式（推荐）：_execute_functional() 返回 DigitalHumanResult
"""
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from config import settings
from core.config.api import APIEndpoints, SubtitleStyleConfig
from core.config.constants import TimeoutConfig
from core.logging_config import setup_logging

from .base import ConditionalStep
from ..context import PipelineContext

if TYPE_CHECKING:
    from ..results import DigitalHumanResult

logger = setup_logging("worker.pipeline.steps.human")


class DigitalHumanStep(ConditionalStep):
    """数字人合成步骤

    功能:
    1. 调用数字人服务合成视频
    2. 合并原始视频和数字人视频
    3. 可选步骤，根据配置决定是否执行

    输入 (context/kwargs):
    - combined_video: 原始视频
    - audio_path: 音频文件
    - extra.enable_digital_human: 是否启用数字人
    - account: 账户配置

    输出 (DigitalHumanResult):
    - human_video_path: 数字人视频路径（如果生成了）
    - human_duration: 数字人视频时长

    注意:
    - 此步骤不包含应用层重试逻辑
    - 重试由 Celery 任务级重试机制处理 (process_video_job)
    - 数字人合成失败不是致命错误，会返回空结果并继续 Pipeline
    - 这是正确的架构，因为:
      1. Worker 崩溃时重试不会丢失
      2. 支持跨 Worker 重试
      3. 网络中断时 Celery 可以等待后重试
      4. 不会阻塞 Worker 进程
    """

    name = "DigitalHuman"
    description = "数字人视频合成"

    # 启用函数式模式
    _functional_mode = True

    def should_execute(self, context: PipelineContext) -> bool:
        """判断是否应该执行数字人合成

        Args:
            context: Pipeline 上下文

        Returns:
            bool: 是否执行
        """
        # 检查配置
        enable = context.extra.get("enable_digital_human", False)
        if not enable:
            return False

        # 检查是否有账户配置
        if not context.account:
            return False

        # 检查是否有数字人配置
        account_extra = getattr(context.account, "extra", {})
        if not account_extra.get("digital_human_config"):
            return False

        return True

    def validate(self, context: PipelineContext) -> None:
        """验证输入"""
        combined_video = getattr(context, 'combined_video', None)
        if not combined_video:
            raise ValueError("没有可用的视频文件")

        audio_path = getattr(context, 'audio_path', None)
        if not audio_path:
            raise ValueError("没有可用的音频文件")

    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行数字人合成（传统模式）

        此方法保持向后兼容，内部调用函数式模式。
        """
        # 调用函数式实现
        result = self._execute_functional(context)

        # 将结果合并到 context
        human_video_path = result.data.get("human_video_path")
        if human_video_path:
            context.human_video_path = human_video_path
            context.combined_video = human_video_path

        return context

    def _execute_functional(
        self,
        context: PipelineContext,
        **kwargs
    ) -> "DigitalHumanResult":
        """执行数字人合成（函数式模式）

        Args:
            context: Pipeline 上下文
            **kwargs: 额外参数

        Returns:
            DigitalHumanResult: 包含 human_video_path, human_duration 的结果
        """
        from ..results import DigitalHumanResult

        logger.info(
            f"[{self.name}] 开始数字人合成 "
            f"(job_id={context.job_id})"
        )

        # 准备输出路径
        workspace = Path(context.workspace_dir)
        output_dir = workspace / "human"
        output_dir.mkdir(parents=True, exist_ok=True)

        human_video_path = str(output_dir / "human_video.mp4")

        # 调用数字人服务
        try:
            # 这里调用实际的数字人服务
            human_duration = self._call_digital_human_service(
                context,
                human_video_path,
            )

            logger.info(
                f"[{self.name}] 数字人合成完成 "
                f"(job_id={context.job_id}, output={human_video_path})"
            )

            # 返回函数式结果
            return DigitalHumanResult(
                step_name=self.name,
                human_video_path=human_video_path,
                human_duration=human_duration
            )

        except Exception as exc:
            logger.error(
                f"[{self.name}] 数字人合成失败 "
                f"(job_id={context.job_id}, error={exc})"
            )
            # 数字人合成失败不是致命错误，继续使用原视频
            logger.warning(
                f"[{self.name}] 数字人合成失败，将使用原始视频 "
                f"(job_id={context.job_id})"
            )

            # 返回空结果
            return DigitalHumanResult(
                step_name=self.name,
                human_video_path=None,
                human_duration=0.0
            )

    def _call_digital_human_service(
        self,
        context: PipelineContext,
        output_path: str,
    ) -> float:
        """调用数字人服务

        Args:
            context: Pipeline 上下文
            output_path: 输出视频路径

        Returns:
            float: 生成的数字人视频时长
        """
        import requests

        # 获取账户配置
        account_extra = getattr(context.account, "extra", {})
        human_config = account_extra.get("digital_human_config", {})

        # 准备请求数据（使用 API 端点常量）
        url = f"{settings.HUMAN_SERVICE_URL}{APIEndpoints.DIGITAL_HUMAN_GENERATE.full_path}"

        # 上传音频文件或提供 URL
        # 实际实现中需要上传音频到数字人服务
        data = {
            "audio_url": context.audio_path,  # 实际应该是 OSS URL
            "config": human_config,
        }

        # 使用超时常量
        response = requests.post(url, json=data, timeout=TimeoutConfig.DEFAULT_VIDEO_PROCESSING_TIMEOUT)
        response.raise_for_status()

        # 下载生成的视频
        result = response.json()
        video_url = result.get("video_url")

        if video_url:
            # 下载视频到本地
            import subprocess
            subprocess.run(["wget", "-O", output_path, video_url], check=True)

        # 获取视频时长
        duration = self._get_video_duration(output_path)
        return duration

    def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长

        Args:
            video_path: 视频文件路径

        Returns:
            float: 视频时长（秒）
        """
        try:
            import subprocess
            cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as exc:
            logger.warning(f"[{self.name}] 无法获取视频时长: {exc}")
            return 0.0

    def post_process(self, context: PipelineContext, result: Optional["DigitalHumanResult"] = None) -> None:
        """后处理

        Args:
            context: Pipeline 上下文
            result: DigitalHuman 结果
        """
        human_video_path = None
        if result:
            human_video_path = result.data.get("human_video_path")
        elif hasattr(context, 'human_video_path'):
            human_video_path = context.human_video_path

        if human_video_path:
            # 清理原始视频以节省空间
            combined_video = getattr(context, 'combined_video', None)
            if combined_video and combined_video != human_video_path:
                if os.path.exists(combined_video):
                    os.remove(combined_video)
                    logger.debug(
                        f"[{self.name}] 原始视频已删除 "
                        f"(job_id={context.job_id})"
                    )

    def _context_to_result(self, context: PipelineContext) -> "DigitalHumanResult":
        """将 PipelineContext 转换为 DigitalHumanResult

        Args:
            context: Pipeline 上下文

        Returns:
            DigitalHumanResult
        """
        from ..results import DigitalHumanResult

        human_video_path = getattr(context, 'human_video_path', None)
        human_duration = 0.0

        if human_video_path and os.path.exists(human_video_path):
            human_duration = self._get_video_duration(human_video_path)

        return DigitalHumanResult(
            step_name=self.name,
            human_video_path=human_video_path,
            human_duration=human_duration
        )


__all__ = [
    "DigitalHumanStep",
]
