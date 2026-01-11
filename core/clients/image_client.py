"""图像生成服务客户端

实现 IImageGenerationService 接口，提供 AI 图像生成功能。

代码重构说明：
- 使用 core.config.video_config 中的统一 VideoResolution
- 替换硬编码的 1360x768 默认分辨率
- 使用共享事件循环优化性能
"""
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.exceptions import ServiceTimeoutException
from core.interfaces.service_interfaces import IImageGenerationService, ImageGenerationResult
from core.logging_config import setup_logging
from core.utils import run_async
from core.utils.exception_handler import handle_service_exceptions
# 使用统一的视频配置
from core.config.video_config import get_dimensions

from .base_client import BaseServiceClient

logger = setup_logging("core.clients.image_client")

# 默认分辨率（使用统一配置）
DEFAULT_WIDTH, DEFAULT_HEIGHT = get_dimensions(is_horizontal=True)


class ImageClient(BaseServiceClient, IImageGenerationService):
    """图像生成服务客户端

    实现 IImageGenerationService 接口，提供同步和异步的图像生成功能。

    支持两种服务模式:
    1. 同步 HTTP 模式 (flux_server): 直接返回图像二进制数据
    2. 异步 Kafka 模式 (ai_image_gen): 提交任务后轮询获取结果

    推荐使用同步 HTTP 模式，更简单高效。
    """

    # ========================================================================
    # IImageGenerationService 接口实现
    # ========================================================================

    def generate_single_image(
        self,
        prompt: str,
        output_path: str,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        num_inference_steps: int = 30,
        lora_name: Optional[str] = None,
        lora_weight: float = 1.2,
        **kwargs,
    ) -> ImageGenerationResult:
        """生成单张图像（实现 IImageGenerationService 接口）

        Args:
            prompt: 图像生成提示词
            output_path: 输出文件路径
            width: 图像宽度
            height: 图像高度
            num_inference_steps: 推理步数
            lora_name: LoRA 模型名称
            lora_weight: LoRA 权重
            **kwargs: 其他参数

        Returns:
            ImageGenerationResult: 生成结果
        """
        import time

        start_time = time.time()

        try:
            # 确保输出目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 调用底层同步方法获取图像二进制数据
            image_bytes = self.generate_image_sync(
                prompt=prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                lora_name=lora_name,
                lora_step=int(lora_weight * 100) if lora_name else 120,
            )

            # 保存图像
            if isinstance(image_bytes, bytes):
                with open(output_path, 'wb') as f:
                    f.write(image_bytes)

                generation_time = time.time() - start_time

                logger.info(
                    f"[generate_single_image] 图像生成成功: {output_path}, "
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
                    error_message=f"不支持的响应类型: {type(image_bytes)}"
                )

        except Exception as e:
            logger.error(f"[generate_single_image] 图像生成失败: {e}")
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
        """批量生成图像（实现 IImageGenerationService 接口）

        Args:
            generation_params: 生成参数列表，每个参数包含:
                - prompt: 提示词
                - output_path: 输出路径
                - width: 宽度
                - height: 高度
                - num_inference_steps: 推理步数
                - lora_name: LoRA 名称
                - lora_weight: LoRA 权重
            job_id: 任务 ID

        Returns:
            List[ImageGenerationResult]: 生成结果列表
        """
        results = []

        for params in generation_params:
            result = self.generate_single_image(
                prompt=params.get("prompt", ""),
                output_path=params.get("output_path", ""),
                width=params.get("width", DEFAULT_WIDTH),
                height=params.get("height", DEFAULT_HEIGHT),
                num_inference_steps=params.get("num_inference_steps", 30),
                lora_name=params.get("lora_name"),
                lora_weight=params.get("lora_weight", 1.2),
            )
            results.append(result)

        return results

    # ========================================================================
    # 原有方法（向后兼容）
    # ========================================================================

    @handle_service_exceptions("IMAGE_GEN", "generate_image")
    async def generate_image(
        self,
        prompt: str,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        num_inference_steps: int = 30,
        lora_name: Optional[str] = None,
        lora_step: int = 120,
        **kwargs,
    ) -> bytes:
        """
        生成单张图像（同步 HTTP 模式）

        Args:
            prompt: 提示词
            width: 图像宽度
            height: 图像高度
            num_inference_steps: 推理步数
            lora_name: LoRA模型名称
            lora_step: LoRA步数
            **kwargs: 其他参数

        Returns:
            bytes: 图像二进制数据

        Raises:
            Exception: 图像生成失败时抛出
        """
        endpoint = "/generate_image/"
        data = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps,
        }
        if lora_name:
            data["loras"] = [{"name": lora_name, "weight": lora_step / 100}]
        data.update(kwargs)

        # 直接发起请求，处理二进制响应
        try:
            response = await self.client.request("POST", endpoint, json=data)
            response.raise_for_status()

            # 检查响应类型
            content_type = response.headers.get("content-type", "")

            if "image" in content_type:
                # 图像二进制数据（flux_server 模式）
                logger.debug(
                    f"[generate_image] 图像生成成功 "
                    f"(prompt={prompt[:50]}..., size={len(response.content)} bytes)"
                )
                return response.content

            elif "application/json" in content_type:
                # JSON 响应（可能是错误信息）
                json_data = response.json()
                if "error" in json_data:
                    raise ValueError(f"图像生成失败: {json_data['error']}")
                # 如果 JSON 中包含 base64 编码的图像
                if "image" in json_data:
                    import base64
                    return base64.b64decode(json_data["image"])
                # 其他情况，返回原始数据
                return json_data
            else:
                # 未知类型，尝试作为字节处理
                logger.warning(
                    f"[generate_image] 未知响应类型: {content_type}, "
                    f"尝试作为字节处理"
                )
                return response.content

        except Exception as exc:
            logger.error(
                f"[generate_image] 图像生成失败: {exc}, "
                f"prompt={prompt[:50]}..."
            )
            raise

    @handle_service_exceptions("IMAGE_GEN", "submit_generation_task")
    async def submit_generation_task(
        self,
        topic: str,
        model_name: str,
        prompt: str,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        loras: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        提交图像生成任务(Kafka方式 - 已废弃)

        .. deprecated::
            此方法用于 Kafka 异步模式，现已废弃。
            请使用 generate_image() 方法进行同步 HTTP 调用。

        Args:
            topic: Kafka主题
            model_name: 模型名称
            prompt: 提示词
            width: 图像宽度
            height: 图像高度
            loras: LoRA配置列表
            **kwargs: 其他参数

        Returns:
            任务提交结果
        """
        logger.warning(
            "[submit_generation_task] Kafka 模式已废弃，"
            "请使用 generate_image() 方法"
        )
        endpoint = "/generate_image"
        data = {
            "topic": topic,
            "model_name": model_name,
            "prompt": prompt,
            "width": width,
            "height": height,
            "loras": loras or [],
        }
        data.update(kwargs)

        return await self._request("POST", endpoint, json=data)

    def generate_image_sync(
        self,
        prompt: str,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        num_inference_steps: int = 30,
        lora_name: Optional[str] = None,
        lora_step: int = 120,
        **kwargs,
    ) -> bytes:
        """
        同步生成图像（便捷方法）

        在非异步上下文中使用，内部使用共享事件循环处理异步调用。

        Args:
            prompt: 提示词
            width: 图像宽度
            height: 图像高度
            num_inference_steps: 推理步数
            lora_name: LoRA模型名称
            lora_step: LoRA步数
            **kwargs: 其他参数

        Returns:
            bytes: 图像二进制数据
        """
        async def _generate():
            return await self.generate_image(
                prompt=prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                lora_name=lora_name,
                lora_step=lora_step,
                **kwargs,
            )

        # 使用共享事件循环（性能优化：避免频繁创建/销毁）
        return run_async(_generate, timeout=300)

    @handle_service_exceptions("IMAGE_GEN", "check_task_status")
    async def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        检查任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态
        """
        endpoint = f"/check_status/{task_id}"
        return await self._request("GET", endpoint)

    async def get_image(
        self, task_id: str, max_wait_time: int = 600
    ) -> Optional[bytes]:
        """
        获取生成的图像(轮询方式)

        Args:
            task_id: 任务ID
            max_wait_time: 最大等待时间(秒)

        Returns:
            图像字节数据

        Raises:
            ServiceTimeoutException: 超时异常
        """
        from core.logging_config import setup_logging
        logger = setup_logging("core.clients.image_client")
        
        endpoint = f"/get_image/{task_id}"
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                response = await self.client.get(endpoint)
                if response.status_code == 200:
                    return response.content
                elif response.status_code in (400, 404):
                    # 任务未完成或未找到,继续等待
                    await asyncio.sleep(1)
                else:
                    response.raise_for_status()
            except (SystemExit, KeyboardInterrupt):
                raise
            except Exception as e:
                logger.warning(f"[get_image] Get image attempt failed: {e}")
                await asyncio.sleep(1)

        raise ServiceTimeoutException("IMAGE_GEN", timeout=max_wait_time)

    @handle_service_exceptions("IMAGE_GEN", "get_image_and_save", raise_service_exception=False)
    async def get_image_and_save(
        self, task_id: str, filepath: str, max_wait_time: int = 600
    ) -> bool:
        """
        获取生成的图像并保存

        Args:
            task_id: 任务ID
            filepath: 保存路径
            max_wait_time: 最大等待时间(秒)

        Returns:
            是否成功
        """
        from core.logging_config import setup_logging
        logger = setup_logging("core.clients.image_client")
        
        image_data = await self.get_image(task_id, max_wait_time)
        if image_data:
            with open(filepath, "wb") as f:
                f.write(image_data)
            logger.info(f"Image saved to {filepath}")
            return True
        return False

