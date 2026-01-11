"""
[LEGACY MODULE] 视频生成流程的各个步骤函数
此模块已被重构为多个专门的模块，位于 utils.generation 包中。

为了保持向后兼容，此文件保留原有函数接口，但内部调用新的模块化实现。

新模块结构：
- utils.generation.path_config: 路径配置
- utils.generation.audio_generator: 音频生成
- utils.generation.subtitle_handler: 字幕处理
- utils.generation.image_generator_steps: 图片生成
- utils.generation.video_generator_steps: 视频生成
- utils.generation.digital_human_handler: 数字人处理
- utils.generation.final_composer: 最终合成
- utils.generation.generation_utils: 工具函数

建议新代码直接使用新模块，而不是此legacy模块。
"""

# 从新模块导入所有函数和常量，保持向后兼容
from utils.generation import (
    SQUARE_WORDS_LIST,
    add_subtitle_and_logo_to_final_video,
    calculate_points,
    convert_subtitle_to_traditional,
    generate_audio_and_subtitle,
    generate_combined_video,
    generate_images,
    prepare_paths_and_config,
    process_digital_human,
    process_h2v_conversion,
)

__all__ = [
    'prepare_paths_and_config',
    'generate_audio_and_subtitle',
    'convert_subtitle_to_traditional',
    'generate_images',
    'generate_combined_video',
    'process_digital_human',
    'add_subtitle_and_logo_to_final_video',
    'process_h2v_conversion',
    'calculate_points',
    'SQUARE_WORDS_LIST',
]

