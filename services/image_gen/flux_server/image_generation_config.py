"""
图像生成配置模块
定义图像生成所需的配置数据类，用于封装函数参数
"""
from dataclasses import dataclass
from typing import Optional

from PIL import Image


@dataclass
class ImageGenerationConfig:
    """图像生成配置数据类
    
    封装 generate_image 函数的所有参数，提供类型安全和默认值支持。
    遵循单一职责原则，将配置参数与业务逻辑分离。
    
    Attributes:
        prompt: 图像生成提示词
        num_inference_steps: 推理步数，默认30
        width: 图像宽度，默认1360
        height: 图像高度，默认768
        lora_name: LoRA模型名称（可选），默认空字符串
        lora_step: LoRA步数，默认120
    """
    prompt: str
    num_inference_steps: int = 30
    width: int = 1360
    height: int = 768
    lora_name: str = ""
    lora_step: int = 120
    
    def validate(self) -> None:
        """验证配置参数
        
        Raises:
            ValueError: 如果参数无效
        """
        if not self.prompt or not self.prompt.strip():
            raise ValueError("提示词不能为空")
        if self.num_inference_steps < 1:
            raise ValueError("推理步数必须大于0")
        if self.width < 1 or self.height < 1:
            raise ValueError("图像尺寸必须大于0")
        if self.lora_step < 0:
            raise ValueError("LoRA步数不能为负数")


@dataclass
class ImageGenerationResult:
    """图像生成结果数据类
    
    封装图像生成的返回结果，包含成功状态、图像对象和错误信息。
    
    Attributes:
        success: 是否成功生成图像
        image: 生成的图像对象（成功时）
        error: 错误信息（失败时）
    """
    success: bool
    image: Optional[Image.Image] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, image: Image.Image) -> "ImageGenerationResult":
        """创建成功结果
        
        Args:
            image: 生成的图像对象
            
        Returns:
            ImageGenerationResult: 成功结果对象
        """
        return cls(success=True, image=image)
    
    @classmethod
    def error_result(cls, error: str) -> "ImageGenerationResult":
        """创建失败结果
        
        Args:
            error: 错误信息
            
        Returns:
            ImageGenerationResult: 失败结果对象
        """
        return cls(success=False, error=error)

