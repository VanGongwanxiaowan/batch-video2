"""步骤工厂接口

定义创建 Pipeline 步骤的抽象接口，遵循开放/封闭原则。
通过工厂模式，可以在不修改现有代码的情况下添加新的步骤类型。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.interfaces.service_interfaces import (
    ITTSService,
    IImageGenerationService,
    IFileStorageService,
)


class IStepFactory(ABC):
    """步骤工厂抽象接口

    定义创建 Pipeline 步骤的标准接口。
    任何步骤工厂实现都应该遵循此接口。

    优势:
    1. 遵循开放/封闭原则：对扩展开放，对修改关闭
    2. 可以轻松添加新的步骤类型
    3. 支持配置驱动的步骤创建
    4. 便于进行单元测试
    """

    @abstractmethod
    def create_content_split_step(self) -> Any:
        """创建内容分割步骤

        Returns:
            BaseStep: 内容分割步骤实例
        """
        pass

    @abstractmethod
    def create_tts_step(
        self,
        tts_service: Optional[ITTSService] = None
    ) -> Any:
        """创建 TTS 语音合成步骤

        Args:
            tts_service: TTS 服务实例（可选）

        Returns:
            BaseStep: TTS 步骤实例
        """
        pass

    @abstractmethod
    def create_image_generation_step(
        self,
        image_service: Optional[IImageGenerationService] = None
    ) -> Any:
        """创建图像生成步骤

        Args:
            image_service: 图像生成服务实例（可选）

        Returns:
            BaseStep: 图像生成步骤实例
        """
        pass

    @abstractmethod
    def create_video_composition_step(self) -> Any:
        """创建视频合成步骤

        Returns:
            BaseStep: 视频合成步骤实例
        """
        pass

    @abstractmethod
    def create_digital_human_step(self) -> Any:
        """创建数字人步骤

        Returns:
            BaseStep: 数字人步骤实例
        """
        pass

    @abstractmethod
    def create_upload_step(
        self,
        storage_service: Optional[IFileStorageService] = None
    ) -> Any:
        """创建文件上传步骤

        Args:
            storage_service: 存储服务实例（可选）

        Returns:
            BaseStep: 上传步骤实例
        """
        pass

    @abstractmethod
    def create_all_steps(
        self,
        services: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """创建所有步骤

        Args:
            services: 服务实例字典，可包含:
                - tts_service: ITTSService 实例
                - image_service: IImageGenerationService 实例
                - storage_service: IFileStorageService 实例

        Returns:
            List[BaseStep]: 所有步骤的列表
        """
        pass

    @abstractmethod
    def create_pipeline_from_config(
        self,
        config: Dict[str, Any],
        services: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """根据配置创建 Pipeline 步骤

        Args:
            config: Pipeline 配置字典，包含:
                - steps: 要启用的步骤名称列表
                - step_order: 步骤执行顺序（可选）
            services: 服务实例字典

        Returns:
            List[BaseStep]: 配置的步骤列表

        Example:
            factory.create_pipeline_from_config({
                "steps": ["content_split", "tts", "image_generation"],
                "step_order": None  # 使用默认顺序
            })
        """
        pass


__all__ = ["IStepFactory"]
