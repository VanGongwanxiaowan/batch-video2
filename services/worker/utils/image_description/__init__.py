"""图像描述生成模块

提供图像描述生成功能，支持两种生成方式：
- V1: 逐行格式（旧版）
- V2: JSON格式（新版）

主要接口：
    generate_image_descriptions: 主入口函数，根据配置选择生成方式
    generate_descriptions_v1: V1生成器（向后兼容）
    generate_descriptions_v2: V2生成器（向后兼容）
"""
from .image_description_generator import (
    generate_descriptions_v1,
    generate_descriptions_v2,
    generate_image_descriptions,
)

__all__ = [
    "generate_image_descriptions",
    "generate_descriptions_v1",
    "generate_descriptions_v2",
]

