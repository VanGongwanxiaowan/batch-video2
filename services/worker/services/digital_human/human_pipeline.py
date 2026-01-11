"""数字人合成底层实现（从 pipe_line.py 迁移而来）

注意：
- 这些函数均为同步阻塞实现，主要负责调用外部数字人服务 + ffmpeg 拼接
- 上层应通过 `DigitalHumanService` 或 `VideoGenerationPipeline` 间接调用
- 已重构为使用辅助函数模块，代码更简洁易维护
"""

# 导入重构后的实现
from .human_pipeline_refactored import (
    human_pack_new,
    human_pack_new_corner,
    human_pack_new_with_transition,
    human_pack_new_with_transition_corner,
)

# 保持向后兼容，导出所有函数
__all__ = [
    "human_pack_new",
    "human_pack_new_with_transition",
    "human_pack_new_corner",
    "human_pack_new_with_transition_corner",
]
