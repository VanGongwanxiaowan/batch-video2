"""步骤输入解析器

负责解析步骤的输入参数，从之前步骤的结果中提取所需数据。

这是从 VideoPipeline 类中提取出来的专门模块，用于处理步骤间的数据传递。
"""
from typing import Any, Dict, TYPE_CHECKING

from core.logging_config import setup_logging

if TYPE_CHECKING:
    from .steps.base import BaseStep
    from .results import StepResult

logger = setup_logging("worker.pipeline.input_resolver")


class StepInputResolver:
    """步骤输入解析器

    从之前步骤的结果中解析当前步骤需要的输入参数。

    这个类实现了步骤间的数据依赖解析，支持：
    - TextSplitStep 需要 srt_path（来自 TTSGeneration）
    - ImageGenerationStep 需要 splits（来自 TextSplit）
    - VideoCompositionStep 需要 image_paths（来自 ImageGeneration）和 audio_path（来自 context）
    - PostProcessingStep 需要 combined_video（来自 VideoComposition）
    - UploadStep 需要 final_video_path（来自 PostProcessing）和 image_paths（来自 ImageGeneration）

    Attributes:
        step_results: 步骤结果字典
    """

    def __init__(self, step_results: Dict[str, "StepResult"]):
        """初始化输入解析器

        Args:
            step_results: 已执行步骤的结果字典
        """
        self.step_results = step_results

    def resolve_inputs(
        self,
        step: "BaseStep",
        context: Any
    ) -> Dict[str, Any]:
        """解析步骤的输入参数

        根据步骤类型，从之前步骤的结果中提取当前步骤需要的输入。

        Args:
            step: 当前步骤
            context: Pipeline 上下文（用于获取不在结果链中的数据，如 audio_path）

        Returns:
            Dict[str, Any]: 输入参数字典
        """
        kwargs = {}

        # 根据步骤类型，从之前的结果中提取数据
        # TextSplitStep 需要 srt_path
        if step.name == "TextSplit":
            tts_result = self.step_results.get("TTSGeneration")
            if tts_result:
                kwargs["srt_path"] = tts_result.data.get("srt_path")

        # ImageGenerationStep 需要 splits
        elif step.name == "ImageGeneration":
            split_result = self.step_results.get("TextSplit")
            if split_result:
                kwargs["splits"] = split_result.data.get("splits")

        # VideoCompositionStep 需要 image_paths 和 audio_path
        elif step.name == "VideoComposition":
            image_result = self.step_results.get("ImageGeneration")
            if image_result:
                kwargs["image_paths"] = image_result.data.get("image_paths")

            # audio_path 通常来自 context
            audio_path = getattr(context, 'audio_path', None)
            if audio_path:
                kwargs["audio_path"] = audio_path

        # PostProcessingStep 需要 combined_video, audio_path, srt_path, logopath
        elif step.name == "PostProcessing":
            video_result = self.step_results.get("VideoComposition")
            if video_result:
                kwargs["combined_video"] = video_result.data.get("video_path")

        # UploadStep 需要 final_video_path, image_paths, audio_path, srt_path
        elif step.name == "Upload":
            postprocess_result = self.step_results.get("PostProcessing")
            if postprocess_result:
                kwargs["final_video_path"] = postprocess_result.data.get("final_video_path")

            image_result = self.step_results.get("ImageGeneration")
            if image_result:
                kwargs["image_paths"] = image_result.data.get("image_paths")

        return kwargs

    def update_results(self, step_name: str, result: "StepResult") -> None:
        """更新步骤结果缓存

        Args:
            step_name: 步骤名称
            result: 步骤结果
        """
        self.step_results[step_name] = result

    def get_result(self, step_name: str) -> "StepResult":
        """获取指定步骤的结果

        Args:
            step_name: 步骤名称

        Returns:
            StepResult: 步骤结果
        """
        return self.step_results.get(step_name)

    def get_all_results(self) -> Dict[str, "StepResult"]:
        """获取所有步骤的结果

        Returns:
            Dict[str, StepResult]: 所有步骤的结果字典
        """
        return self.step_results.copy()


__all__ = [
    "StepInputResolver",
]
