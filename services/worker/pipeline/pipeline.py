"""Video Pipeline 执行器

提供 Pipeline 的组装和执行功能。
使用构建器模式，支持灵活组合各种步骤。

架构支持：
1. 传统模式（向后兼容）：步骤修改 PipelineContext
2. 函数式模式（推荐）：步骤返回 StepResult，结果在步骤间传递

开放/封闭原则改进：
- 使用 IStepFactory 接口创建步骤
- 可以轻松添加新的步骤类型而无需修改现有代码
- 支持配置驱动的 Pipeline 构建

代码重构说明：
- 拆分为多个模块：executor.py, input_resolver.py, result_manager.py
- VideoPipeline 保留步骤管理功能，委托执行给专门组件
- 从 615 行简化为约 200 行
"""
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from core.interfaces.step_factory import IStepFactory
from core.logging_config import setup_logging

# 导入新模块
from .context import PipelineContext
from .executor import PipelineExecutor, PipelineException
from .input_resolver import StepInputResolver
from .result_manager import StepResultManager
from .steps.base import BaseStep

if TYPE_CHECKING:
    from .results import StepResult

logger = setup_logging("worker.pipeline.pipeline")


class VideoPipeline:
    """视频生成 Pipeline

    使用构建器模式组装多个步骤，然后按顺序执行。

    支持两种执行模式：
    1. 传统模式：步骤通过修改 context 传递数据
    2. 函数式模式：步骤返回 StepResult，结果在步骤间显式传递

    传统模式示例:
        ```python
        pipeline = VideoPipeline(context)
        pipeline.add_step(TTSGenerationStep()) \
                .add_step(SubtitleGenerationStep()) \
                .add_step(ImageGenerationStep())
        pipeline.execute()  # 传统模式
        ```

    函数式模式示例:
        ```python
        pipeline = VideoPipeline(context, functional_mode=True)
        pipeline.add_step(TTSGenerationStep()) \
                .add_step(TextSplitStep()) \
                .add_step(ImageGenerationStep())
        results = pipeline.execute_functional()  # 函数式模式
        ```

    代码重构说明：
        - 执行逻辑委托给 PipelineExecutor
        - 输入解析委托给 StepInputResolver
        - 结果管理委托给 StepResultManager
        - VideoPipeline 保留步骤管理和配置功能

    Attributes:
        context: Pipeline 上下文
        steps: 步骤列表
        functional_mode: 是否启用函数式模式
        executor: 执行器
        result_manager: 结果管理器（函数式模式）
    """

    def __init__(
        self,
        context: PipelineContext,
        functional_mode: bool = False
    ):
        """初始化 Pipeline

        Args:
            context: Pipeline 上下文
            functional_mode: 是否启用函数式模式（默认 False 保持向后兼容）
        """
        self.context = context
        self.steps: List[BaseStep] = []
        self.functional_mode = functional_mode

        # 初始化执行器和结果管理器
        self.result_manager = StepResultManager() if functional_mode else None
        self.input_resolver = StepInputResolver({}) if functional_mode else None
        self.executor = PipelineExecutor(
            context,
            self.input_resolver,
            self.result_manager
        )

    def add_step(self, step: BaseStep) -> "VideoPipeline":
        """添加步骤

        Args:
            step: 要添加的步骤

        Returns:
            VideoPipeline: 返回自身，支持链式调用
        """
        self.steps.append(step)
        logger.debug(
            f"[VideoPipeline] 添加步骤: {step.name} "
            f"(job_id={self.context.job_id}, 总步骤数={len(self.steps)})"
        )
        return self

    def add_steps(self, steps: List[BaseStep]) -> "VideoPipeline":
        """批量添加步骤

        Args:
            steps: 要添加的步骤列表

        Returns:
            VideoPipeline: 返回自身，支持链式调用
        """
        for step in steps:
            self.add_step(step)
        return self

    def insert_step(self, index: int, step: BaseStep) -> "VideoPipeline":
        """在指定位置插入步骤

        Args:
            index: 插入位置
            step: 要插入的步骤

        Returns:
            VideoPipeline: 返回自身，支持链式调用
        """
        self.steps.insert(index, step)
        logger.debug(
            f"[VideoPipeline] 插入步骤: {step.name} at index {index} "
            f"(job_id={self.context.job_id})"
        )
        return self

    def remove_step(self, step_name: str) -> "VideoPipeline":
        """移除指定名称的步骤

        Args:
            step_name: 步骤名称

        Returns:
            VideoPipeline: 返回自身，支持链式调用
        """
        self.steps = [s for s in self.steps if s.name != step_name]
        logger.debug(
            f"[VideoPipeline] 移除步骤: {step_name} "
            f"(job_id={self.context.job_id})"
        )
        return self

    def clear_steps(self) -> "VideoPipeline":
        """清空所有步骤

        Returns:
            VideoPipeline: 返回自身，支持链式调用
        """
        self.steps.clear()
        logger.debug(f"[VideoPipeline] 清空所有步骤 (job_id={self.context.job_id})")
        return self

    def get_step_count(self) -> int:
        """获取步骤数量

        Returns:
            int: 步骤总数
        """
        return len(self.steps)

    def execute(self) -> PipelineContext:
        """执行 Pipeline（传统模式）

        按顺序执行所有步骤，如果某个步骤失败则停止执行。
        步骤通过修改 context 传递数据（向后兼容）。

        Returns:
            PipelineContext: 最终的上下文

        Raises:
            PipelineException: Pipeline 执行失败时抛出

        代码重构说明：
            委托给 PipelineExecutor.execute_traditional()
        """
        return self.executor.execute_traditional(self.steps)

    def execute_functional(self) -> Dict[str, "StepResult"]:
        """执行 Pipeline（函数式模式）

        按顺序执行所有步骤，每个步骤返回 StepResult。
        结果在步骤间显式传递，提供更好的类型安全和可测试性。

        Returns:
            Dict[str, StepResult]: 所有步骤的结果字典

        Raises:
            PipelineException: Pipeline 执行失败时抛出

        代码重构说明：
            委托给 PipelineExecutor.execute_functional()
        """
        return self.executor.execute_functional(self.steps)

    def get_step_result(self, step_name: str) -> Optional["StepResult"]:
        """获取指定步骤的结果

        Args:
            step_name: 步骤名称

        Returns:
            Optional[StepResult]: 步骤结果，如果不存在则返回 None

        代码重构说明：
            委托给 StepResultManager
        """
        if self.result_manager is None:
            return None
        return self.result_manager.get(step_name)

    def get_all_results(self) -> Dict[str, "StepResult"]:
        """获取所有步骤的结果

        Returns:
            Dict[str, StepResult]: 所有步骤的结果字典

        代码重构说明：
            委托给 StepResultManager
        """
        if self.result_manager is None:
            return {}
        return self.result_manager.get_all()

    def __repr__(self) -> str:
        """字符串表示"""
        step_names = [s.name for s in self.steps]
        mode = "functional" if self.functional_mode else "context"
        return f"VideoPipeline(job_id={self.context.job_id}, mode={mode}, steps={step_names})"


# ============================================================================
# Pipeline 构建器
# ============================================================================

class PipelineBuilder:
    """Pipeline 构建器

    提供便捷的方法来构建常用的 Pipeline 配置。

    开放/封闭原则改进：
    - 使用 IStepFactory 接口创建步骤
    - 可以轻松扩展支持新的步骤类型
    - 支持配置驱动的 Pipeline 构建

    示例:
        ```python
        # 使用默认工厂构建标准 Pipeline
        pipeline = PipelineBuilder.build_standard_pipeline(context)

        # 使用自定义工厂和配置构建 Pipeline
        factory = CustomStepFactory()
        pipeline = PipelineBuilder.build_from_config(
            context,
            {"steps": ["tts", "image_generation", "upload"]},
            factory
        )
        ```
    """

    @staticmethod
    def build_standard_pipeline(
        context: PipelineContext,
        functional_mode: bool = False,
        factory: Optional[IStepFactory] = None,
        services: Optional[Dict[str, Any]] = None,
    ) -> VideoPipeline:
        """构建标准 Pipeline

        包含所有基本步骤，不包括数字人。

        Args:
            context: Pipeline 上下文
            functional_mode: 是否启用函数式模式
            factory: 步骤工厂（可选，默认使用 DefaultStepFactory）
            services: 服务实例字典（可选）

        Returns:
            VideoPipeline: 构建好的 Pipeline
        """
        if factory is None:
            from .factory import DefaultStepFactory
            factory = DefaultStepFactory(services)

        pipeline = VideoPipeline(context, functional_mode=functional_mode)
        pipeline.add_step(factory.create_content_split_step())
        pipeline.add_step(factory.create_tts_step(services.get("tts_service") if services else None))
        pipeline.add_step(factory.create_image_generation_step(services.get("image_service") if services else None))
        pipeline.add_step(factory.create_video_composition_step())
        pipeline.add_step(factory.create_postprocess_step())
        pipeline.add_step(factory.create_upload_step(services.get("storage_service") if services else None))

        return pipeline

    @staticmethod
    def build_advanced_pipeline(
        context: PipelineContext,
        functional_mode: bool = False,
        factory: Optional[IStepFactory] = None,
        services: Optional[Dict[str, Any]] = None,
    ) -> VideoPipeline:
        """构建高级 Pipeline

        包含所有步骤，包括数字人。

        Args:
            context: Pipeline 上下文
            functional_mode: 是否启用函数式模式
            factory: 步骤工厂（可选，默认使用 DefaultStepFactory）
            services: 服务实例字典（可选）

        Returns:
            VideoPipeline: 构建好的 Pipeline
        """
        if factory is None:
            from .factory import DefaultStepFactory
            factory = DefaultStepFactory(services)

        pipeline = VideoPipeline(context, functional_mode=functional_mode)
        pipeline.add_step(factory.create_content_split_step())
        pipeline.add_step(factory.create_tts_step(services.get("tts_service") if services else None))
        pipeline.add_step(factory.create_image_generation_step(services.get("image_service") if services else None))
        pipeline.add_step(factory.create_video_composition_step())
        pipeline.add_step(factory.create_digital_human_step())
        pipeline.add_step(factory.create_postprocess_step())
        pipeline.add_step(factory.create_upload_step(services.get("storage_service") if services else None))

        return pipeline

    @staticmethod
    def build_simple_pipeline(
        context: PipelineContext,
        functional_mode: bool = False,
        factory: Optional[IStepFactory] = None,
        services: Optional[Dict[str, Any]] = None,
    ) -> VideoPipeline:
        """构建简化 Pipeline

        只包含最核心的步骤，用于快速生成。

        Args:
            context: Pipeline 上下文
            functional_mode: 是否启用函数式模式
            factory: 步骤工厂（可选，默认使用 DefaultStepFactory）
            services: 服务实例字典（可选）

        Returns:
            VideoPipeline: 构建好的 Pipeline
        """
        if factory is None:
            from .factory import DefaultStepFactory
            factory = DefaultStepFactory(services)

        pipeline = VideoPipeline(context, functional_mode=functional_mode)
        pipeline.add_step(factory.create_tts_step(services.get("tts_service") if services else None))
        pipeline.add_step(factory.create_image_generation_step(services.get("image_service") if services else None))
        pipeline.add_step(factory.create_video_composition_step())
        pipeline.add_step(factory.create_upload_step(services.get("storage_service") if services else None))

        return pipeline

    @staticmethod
    def build_from_config(
        context: PipelineContext,
        config: Dict[str, Any],
        factory: Optional[IStepFactory] = None,
        services: Optional[Dict[str, Any]] = None,
        functional_mode: bool = False,
    ) -> VideoPipeline:
        """根据配置构建 Pipeline

        支持配置驱动的 Pipeline 构建，完全遵循开放/封闭原则。

        Args:
            context: Pipeline 上下文
            config: Pipeline 配置字典
                - steps: 要启用的步骤名称列表
                - step_order: 步骤执行顺序（可选）
            factory: 步骤工厂（可选，默认使用 DefaultStepFactory）
            services: 服务实例字典（可选）
            functional_mode: 是否启用函数式模式

        Returns:
            VideoPipeline: 构建好的 Pipeline

        Example:
            ```python
            config = {
                "steps": ["content_split", "tts", "image_generation", "upload"],
                "step_order": None  # 使用默认顺序
            }
            pipeline = PipelineBuilder.build_from_config(context, config)
            ```
        """
        if factory is None:
            from .factory import DefaultStepFactory
            factory = DefaultStepFactory(services)

        steps = factory.create_pipeline_from_config(config, services)
        pipeline = VideoPipeline(context, functional_mode=functional_mode)
        pipeline.add_steps(steps)

        return pipeline

    @staticmethod
    def build_custom_pipeline(
        context: PipelineContext,
        steps: List[BaseStep],
        functional_mode: bool = False
    ) -> VideoPipeline:
        """构建自定义 Pipeline（向后兼容方法）

        Args:
            context: Pipeline 上下文
            steps: 自定义步骤列表
            functional_mode: 是否启用函数式模式

        Returns:
            VideoPipeline: 构建好的 Pipeline
        """
        pipeline = VideoPipeline(context, functional_mode=functional_mode)
        pipeline.add_steps(steps)
        return pipeline


# 导出
__all__ = [
    "VideoPipeline",
    "PipelineBuilder",
    "PipelineException",
]
