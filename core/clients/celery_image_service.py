"""基于 Celery 的图像生成服务

实现 IImageGenerationService 接口，使用 Celery 任务执行并行图像生成。

代码重构说明：
- 使用 core.config.video_config 中的统一 VideoResolution
- 替换硬编码的 1360x768 默认分辨率
"""
import time
from typing import Any, Dict, List

from celery import group

from core.interfaces.service_interfaces import IImageGenerationService, ImageGenerationResult
from core.logging_config import setup_logging
# 使用统一的视频配置
from core.config.video_config import get_dimensions

logger = setup_logging("core.clients.celery_image_service")

# 默认分辨率（使用统一配置）
DEFAULT_WIDTH, DEFAULT_HEIGHT = get_dimensions(is_horizontal=True)


class CeleryImageService(IImageGenerationService):
    """基于 Celery 的图像生成服务

    使用 Celery group 实现并行图像生成。
    适用于 Worker 环境，利用 Celery 集群进行分布式处理。
    """

    def __init__(self, task_timeout: int = 3600):
        """初始化 Celery 图像服务

        Args:
            task_timeout: Celery 任务超时时间（秒）
        """
        from services.worker.tasks.image_tasks import generate_single_image_task

        self.task = generate_single_image_task
        self.task_timeout = task_timeout

    def generate_single_image(
        self,
        prompt: str,
        output_path: str,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        num_inference_steps: int = 30,
        lora_name: str = None,
        lora_weight: float = 1.2,
        **kwargs,
    ) -> ImageGenerationResult:
        """生成单张图像

        注意：虽然此服务支持批量生成，但单张图像生成仍会通过 Celery 执行。
        如果只是生成单张图像，建议直接使用 ImageClient 以减少网络开销。

        Args:
            prompt: 图像生成提示词
            output_path: 输出文件路径
            width: 图像宽度
            height: 图像高度
            num_inference_steps: 推理步数
            lora_name: LoRA 模型名称
            lora_weight: LoRA 权重
            **kwargs: 其他参数（支持 topic_prefix）

        Returns:
            ImageGenerationResult: 生成结果
        """
        start_time = time.time()

        try:
            # 构建任务参数
            task_params = {
                "prompt": prompt,
                "output_path": output_path,
                "width": width,
                "height": height,
                "num_inference_steps": num_inference_steps,
                "lora_name": lora_name,
                "lora_weight": lora_weight,
                "topic_prefix": kwargs.get("topic_prefix", ""),
            }

            # 通过 Celery 执行任务
            result = self.task.apply_async(
                kwargs=task_params,
            )

            # 等待任务完成
            task_result = result.get(timeout=self.task_timeout)

            generation_time = time.time() - start_time

            if task_result['status'] == 'success':
                logger.info(
                    f"[CeleryImageService] 单张图像生成成功: {output_path}, "
                    f"耗时={generation_time:.2f}秒"
                )
                return ImageGenerationResult(
                    output_path=output_path,
                    status="success",
                    generation_time=generation_time,
                )
            else:
                return ImageGenerationResult(
                    output_path=output_path,
                    status="failed",
                    error_message=task_result.get('error', '未知错误'),
                    generation_time=generation_time,
                )

        except Exception as e:
            logger.error(f"[CeleryImageService] 单张图像生成失败: {e}")
            return ImageGenerationResult(
                output_path=output_path,
                status="failed",
                error_message=str(e),
                generation_time=time.time() - start_time,
            )

    def generate_batch(
        self,
        generation_params: List[Dict[str, Any]],
        job_id: int,
    ) -> List[ImageGenerationResult]:
        """批量生成图像（使用 Celery group 并行执行）

        Args:
            generation_params: 生成参数列表
            job_id: 任务 ID

        Returns:
            List[ImageGenerationResult]: 生成结果列表
        """
        start_time = time.time()

        logger.info(
            f"[CeleryImageService] 开始批量生成 "
            f"(job_id={job_id}, 数量={len(generation_params)})"
        )

        # 构建任务参数
        task_params_list = []
        for params in generation_params:
            task_params = {
                "prompt": params.get("prompt", ""),
                "output_path": params.get("output_path", ""),
                "width": params.get("width", DEFAULT_WIDTH),
                "height": params.get("height", DEFAULT_HEIGHT),
                "num_inference_steps": params.get("num_inference_steps", 30),
                "lora_name": params.get("lora_name"),
                "lora_weight": params.get("lora_weight", 1.2),
                "topic_prefix": params.get("topic_prefix", ""),
            }
            task_params_list.append(task_params)

        # 创建 Celery group
        task_group = group(
            self.task.s(**task_params)
            for task_params in task_params_list
        )

        group_result = task_group.apply_async()

        try:
            # 等待所有任务完成
            task_results = group_result.get(timeout=self.task_timeout)

            total_time = time.time() - start_time

            # 转换为 ImageGenerationResult
            results = []
            success_count = 0
            failed_count = 0

            for task_result in task_results:
                if task_result['status'] == 'success':
                    success_count += 1
                    results.append(ImageGenerationResult(
                        output_path=task_result['output_path'],
                        status="success",
                        generation_time=task_result.get('generation_time', 0),
                    ))
                else:
                    failed_count += 1
                    results.append(ImageGenerationResult(
                        output_path=task_result['output_path'],
                        status="failed",
                        error_message=task_result.get('error', '未知错误'),
                        generation_time=task_result.get('generation_time', 0),
                    ))

            logger.info(
                f"[CeleryImageService] 批量生成完成 "
                f"(job_id={job_id}, 成功={success_count}/{len(task_results)}, "
                f"失败={failed_count}, 总耗时={total_time:.2f}秒)"
            )

            return results

        except Exception as exc:
            logger.error(f"[CeleryImageService] 批量生成失败: {exc}")

            # 创建失败结果
            total_time = time.time() - start_time
            return [
                ImageGenerationResult(
                    output_path=params.get("output_path", ""),
                    status="failed",
                    error_message=str(exc),
                    generation_time=total_time,
                )
                for params in generation_params
            ]


__all__ = ["CeleryImageService"]
