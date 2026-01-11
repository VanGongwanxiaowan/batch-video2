"""文件上传步骤

将生成的文件上传到 OSS 存储。

支持两种执行模式：
1. 传统模式（向后兼容）：execute() 返回 PipelineContext
2. 函数式模式（推荐）：_execute_functional() 返回 UploadResult

依赖倒置原则改进：
- 依赖 IFileStorageService 抽象接口而非具体实现
- 支持依赖注入，便于测试和替换实现
"""
import os
from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING

from config import settings
from core.config.api import OSSStoragePaths
from core.interfaces.service_interfaces import IFileStorageService
from core.logging_config import setup_logging

from .base import BaseStep
from ..context import PipelineContext

if TYPE_CHECKING:
    from ..results import UploadResult

logger = setup_logging("worker.pipeline.steps.upload")


class UploadStep(BaseStep):
    """文件上传步骤

    功能:
    1. 上传最终视频到 OSS
    2. 上传封面图片到 OSS
    3. 上传音频到 OSS
    4. 上传字幕到 OSS
    5. 生成签名 URL

    输入 (context/kwargs):
    - final_video_path: 最终视频路径
    - image_paths: 图像路径列表
    - audio_path: 音频路径
    - srt_path: 字幕路径
    - workspace_dir: 工作目录
    - user_id: 用户 ID
    - job_id: 任务 ID

    输出 (UploadResult):
    - upload_urls: OSS Key 字典
    - upload_status: 上传状态
    - file_sizes: 文件大小字典

    依赖注入:
    - 通过 __init__ 接收 IFileStorageService 实例
    - 如果未提供，使用默认的 StorageClient
    """

    name = "Upload"
    description = "文件上传到 OSS"

    # 启用函数式模式
    _functional_mode = True

    def __init__(self, storage_service: Optional[IFileStorageService] = None):
        """初始化上传步骤

        Args:
            storage_service: 存储服务实例（可选）
                             如果不提供，将创建默认的 StorageClient
        """
        if storage_service is None:
            from core.clients.storage_client import StorageClient
            storage_service = StorageClient(settings)

        self.storage_service = storage_service

    def validate(self, context: PipelineContext) -> None:
        """验证输入"""
        final_video_path = getattr(context, 'final_video_path', None)
        if not final_video_path:
            raise ValueError("没有最终视频文件")

        if not os.path.exists(final_video_path):
            raise FileNotFoundError(f"视频文件不存在: {final_video_path}")

    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行文件上传（传统模式）

        此方法保持向后兼容，内部调用函数式模式。
        """
        # 调用函数式实现
        result = self._execute_functional(context)

        # 将结果合并到 context
        context.upload_results = result.data.get("upload_urls")

        return context

    def _execute_functional(
        self,
        context: PipelineContext,
        **kwargs
    ) -> "UploadResult":
        """执行文件上传（函数式模式）

        Args:
            context: Pipeline 上下文
            **kwargs: 额外参数

        Returns:
            UploadResult: 包含 upload_urls, upload_status, file_sizes 的结果
        """
        from ..results import UploadResult

        logger.info(
            f"[{self.name}] 开始文件上传 "
            f"(job_id={context.job_id})"
        )

        # 准备 OSS 路径（使用配置常量，重命名变量更清晰）
        oss_user_dir = str(context.user_id).replace("-", "") if context.user_id else "default"
        oss_job_dir = str(context.job_id)
        oss_base_prefix = OSSStoragePaths.VIDEO_PREFIX

        # 准备上传文件字典
        files_to_upload = {}
        file_keys = {}

        # 添加最终视频
        video_key = f"{oss_base_prefix}/{oss_user_dir}/{oss_job_dir}/{OSSStoragePaths.VIDEO_FILENAME}"
        files_to_upload["video"] = context.final_video_path
        file_keys["video_oss_key"] = video_key

        # 添加封面（第一张图片）
        image_paths = getattr(context, 'image_paths', [])
        if image_paths:
            cover_key = f"{oss_base_prefix}/{oss_user_dir}/{oss_job_dir}/{OSSStoragePaths.COVER_FILENAME}"
            files_to_upload["cover"] = image_paths[0]
            file_keys["cover_oss_key"] = cover_key

        # 添加音频
        audio_path = getattr(context, 'audio_path', None)
        if audio_path and os.path.exists(audio_path):
            audio_key = f"{oss_base_prefix}/{oss_user_dir}/{oss_job_dir}/{OSSStoragePaths.AUDIO_FILENAME}"
            files_to_upload["audio"] = audio_path
            file_keys["audio_oss_key"] = audio_key

        # 添加字幕
        srt_path = getattr(context, 'srt_path', None)
        if srt_path and os.path.exists(srt_path):
            srt_key = f"{oss_base_prefix}/{oss_user_dir}/{oss_job_dir}/{OSSStoragePaths.SUBTITLE_FILENAME}"
            files_to_upload["subtitle"] = srt_path
            file_keys["srt_oss_key"] = srt_key

        # 使用存储服务批量上传
        prefix = f"{oss_base_prefix}/{oss_user_dir}/{oss_job_dir}"
        batch_result = self.storage_service.upload_batch(
            files=files_to_upload,
            prefix=prefix,
        )

        # 提取上传结果
        upload_urls = {}
        for url_key, file_type in [
            ("video_oss_key", "video"),
            ("cover_oss_key", "cover"),
            ("audio_oss_key", "audio"),
            ("srt_oss_key", "subtitle"),
        ]:
            if file_type in batch_result.results:
                result = batch_result.results[file_type]
                upload_urls[url_key] = result.file_key if result.success else None

        # 计算文件大小
        file_sizes = {}
        for file_type, result in batch_result.results.items():
            if result.success:
                file_path = files_to_upload.get(file_type)
                if file_path and os.path.exists(file_path):
                    file_sizes[result.file_key] = os.path.getsize(file_path)

        upload_status = "success" if batch_result.failed_count == 0 else "partial"

        logger.info(
            f"[{self.name}] 文件上传完成 "
            f"(job_id={context.job_id}, success={batch_result.success_count}, "
            f"failed={batch_result.failed_count})"
        )

        # 返回函数式结果
        return UploadResult(
            step_name=self.name,
            upload_urls=upload_urls,
            upload_status=upload_status,
            file_sizes=file_sizes
        )

    def _context_to_result(self, context: PipelineContext) -> "UploadResult":
        """将 PipelineContext 转换为 UploadResult

        Args:
            context: Pipeline 上下文

        Returns:
            UploadResult
        """
        from ..results import UploadResult

        upload_results = getattr(context, 'upload_results', {})

        return UploadResult(
            step_name=self.name,
            upload_urls=upload_results,
            upload_status="success",
            file_sizes={}
        )


__all__ = [
    "UploadStep",
]
