"""默认步骤工厂实现

实现 IStepFactory 接口，提供创建默认 Pipeline 步骤的功能。
"""
from typing import Any, Dict, List, Optional

from core.interfaces.service_interfaces import (
    ITTSService,
    IImageGenerationService,
    IFileStorageService,
)
from core.interfaces.step_factory import IStepFactory
from core.logging_config import setup_logging

logger = setup_logging("worker.pipeline.factory")


class DefaultStepFactory(IStepFactory):
    """默认步骤工厂

    实现标准的 Pipeline 步骤创建逻辑。
    支持依赖注入，便于测试和自定义。
    """

    # 步骤创建映射
    STEP_CREATORS = {
        "content_split": "_create_content_split_step_impl",
        "tts": "_create_tts_step_impl",
        "image_generation": "_create_image_generation_step_impl",
        "video_composition": "_create_video_composition_step_impl",
        "digital_human": "_create_digital_human_step_impl",
        "upload": "_create_upload_step_impl",
        "subtitle": "_create_subtitle_step_impl",
        "postprocess": "_create_postprocess_step_impl",
    }

    # 默认步骤执行顺序
    DEFAULT_STEP_ORDER = [
        "content_split",
        "tts",
        "image_generation",
        "video_composition",
        "digital_human",
        "postprocess",
        "upload",
    ]

    def __init__(self, services: Optional[Dict[str, Any]] = None):
        """初始化工厂

        Args:
            services: 服务实例字典（可选）
        """
        self._services = services or {}

    def create_content_split_step(self) -> Any:
        """创建内容分割步骤"""
        from services.worker.pipeline.steps import TextSplitStep
        return TextSplitStep()

    def create_tts_step(
        self,
        tts_service: Optional[ITTSService] = None
    ) -> Any:
        """创建 TTS 语音合成步骤

        Args:
            tts_service: TTS 服务实例（可选）

        Returns:
            TTSGenerationStep: TTS 步骤实例
        """
        from services.worker.pipeline.steps import TTSGenerationStep
        return TTSGenerationStep(tts_service=tts_service)

    def create_image_generation_step(
        self,
        image_service: Optional[IImageGenerationService] = None
    ) -> Any:
        """创建图像生成步骤

        Args:
            image_service: 图像生成服务实例（可选）

        Returns:
            ImageGenerationStep: 图像生成步骤实例
        """
        from services.worker.pipeline.steps import ImageGenerationStep
        return ImageGenerationStep(image_service=image_service)

    def create_video_composition_step(self) -> Any:
        """创建视频合成步骤

        Returns:
            VideoCompositionStep: 视频合成步骤实例
        """
        from services.worker.pipeline.steps import VideoCompositionStep
        return VideoCompositionStep()

    def create_digital_human_step(self) -> Any:
        """创建数字人步骤

        Returns:
            DigitalHumanStep: 数字人步骤实例
        """
        from services.worker.pipeline.steps import DigitalHumanStep
        return DigitalHumanStep()

    def create_upload_step(
        self,
        storage_service: Optional[IFileStorageService] = None
    ) -> Any:
        """创建文件上传步骤

        Args:
            storage_service: 存储服务实例（可选）

        Returns:
            UploadStep: 上传步骤实例
        """
        from services.worker.pipeline.steps import UploadStep
        return UploadStep(storage_service=storage_service)

    def create_all_steps(
        self,
        services: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """创建所有步骤

        Args:
            services: 服务实例字典（可选）

        Returns:
            List[BaseStep]: 所有步骤的列表（按默认顺序）
        """
        services = services or {}
        steps = []

        # 按默认顺序创建步骤
        for step_name in self.DEFAULT_STEP_ORDER:
            step = self._create_step_by_name(step_name, services)
            if step:
                steps.append(step)

        logger.debug(f"[DefaultStepFactory] 创建了 {len(steps)} 个步骤")
        return steps

    def create_pipeline_from_config(
        self,
        config: Dict[str, Any],
        services: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """根据配置创建 Pipeline 步骤

        Args:
            config: Pipeline 配置字典
            services: 服务实例字典

        Returns:
            List[BaseStep]: 配置的步骤列表
        """
        services = services or {}

        # 获取要创建的步骤列表
        step_names = config.get("steps", [])
        step_order = config.get("step_order")

        # 如果没有指定步骤，使用默认步骤
        if not step_names:
            logger.info(
                "[DefaultStepFactory] 未指定步骤，使用默认步骤配置"
            )
            return self.create_all_steps(services)

        # 如果指定了顺序，按顺序创建
        if step_order:
            ordered_steps = []
            for step_name in step_order:
                if step_name in step_names:
                    step = self._create_step_by_name(step_name, services)
                    if step:
                        ordered_steps.append(step)
            return ordered_steps

        # 否则按指定顺序创建
        steps = []
        for step_name in step_names:
            step = self._create_step_by_name(step_name, services)
            if step:
                steps.append(step)

        logger.debug(
            f"[DefaultStepFactory] 根据配置创建了 {len(steps)} 个步骤"
        )
        return steps

    # ========================================================================
    # 私有辅助方法
    # ========================================================================

    def _create_step_by_name(
        self,
        step_name: str,
        services: Dict[str, Any]
    ) -> Optional[Any]:
        """根据步骤名称创建步骤

        Args:
            step_name: 步骤名称
            services: 服务实例字典

        Returns:
            Optional[BaseStep]: 步骤实例，如果步骤不支持则返回 None
        """
        creator_name = self.STEP_CREATORS.get(step_name)
        if not creator_name:
            logger.warning(
                f"[DefaultStepFactory] 未知步骤类型: {step_name}"
            )
            return None

        # 获取创建方法
        creator = getattr(self, creator_name, None)
        if not creator:
            logger.warning(
                f"[DefaultStepFactory] 步骤创建方法未实现: {creator_name}"
            )
            return None

        # 调用创建方法，传入相应的服务
        return self._call_creator(creator, step_name, services)

    def _call_creator(
        self,
        creator: callable,
        step_name: str,
        services: Dict[str, Any]
    ) -> Any:
        """调用步骤创建方法，传入相应的服务

        Args:
            creator: 创建方法
            step_name: 步骤名称
            services: 服务实例字典

        Returns:
            步骤实例
        """
        # 根据步骤类型注入相应的服务
        service_map = {
            "tts": services.get("tts_service"),
            "image_generation": services.get("image_service"),
            "upload": services.get("storage_service"),
        }

        service_arg = service_map.get(step_name)

        if service_arg is not None:
            return creator(service_arg)
        else:
            return creator()

    # ========================================================================
    # 内部实现方法（支持通过 STEP_CREATORS 映射调用）
    # ========================================================================

    def _create_content_split_step_impl(self) -> Any:
        """内容分割步骤内部实现"""
        return self.create_content_split_step()

    def _create_tts_step_impl(
        self,
        tts_service: Optional[ITTSService] = None
    ) -> Any:
        """TTS 步骤内部实现"""
        return self.create_tts_step(tts_service)

    def _create_image_generation_step_impl(
        self,
        image_service: Optional[IImageGenerationService] = None
    ) -> Any:
        """图像生成步骤内部实现"""
        return self.create_image_generation_step(image_service)

    def _create_video_composition_step_impl(self) -> Any:
        """视频合成步骤内部实现"""
        return self.create_video_composition_step()

    def _create_digital_human_step_impl(self) -> Any:
        """数字人步骤内部实现"""
        return self.create_digital_human_step()

    def _create_upload_step_impl(
        self,
        storage_service: Optional[IFileStorageService] = None
    ) -> Any:
        """上传步骤内部实现"""
        return self.create_upload_step(storage_service)

    def _create_subtitle_step_impl(self) -> Any:
        """字幕步骤内部实现"""
        from services.worker.pipeline.steps import SubtitleGenerationStep
        return SubtitleGenerationStep()

    def _create_postprocess_step_impl(self) -> Any:
        """后处理步骤内部实现"""
        from services.worker.pipeline.steps import PostProcessingStep
        return PostProcessingStep()


__all__ = ["DefaultStepFactory"]
