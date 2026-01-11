"""Flux图像生成服务客户端"""
from typing import Any, Dict, Optional

from core.utils.exception_handler import handle_service_exceptions

from .base_client import BaseServiceClient


class FluxClient(BaseServiceClient):
    """Flux图像生成服务客户端"""

    @handle_service_exceptions("FLUX", "generate_image")
    async def generate_image(
        self,
        prompt: str,
        width: int = 1360,
        height: int = 768,
        num_inference_steps: int = 30,
        lora_name: Optional[str] = None,
        lora_step: int = 120,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        生成单张图像

        Args:
            prompt: 提示词
            width: 图像宽度
            height: 图像高度
            num_inference_steps: 推理步数
            lora_name: LoRA模型名称
            lora_step: LoRA步数
            **kwargs: 其他参数

        Returns:
            生成结果
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

        return await self._request("POST", endpoint, json=data)

