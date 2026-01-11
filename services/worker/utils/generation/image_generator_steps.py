"""
图片生成步骤模块
负责图片描述生成和图片生成
"""
from typing import Any, Dict, List

from gushi import actor_generate, desc2image_gushi, srt2desc_gushi

from core.logging_config import setup_logging

logger = setup_logging("worker.utils.generation.image_generator_steps")


class ImageGeneratorSteps:
    """图片生成步骤处理器"""
    
    def generate_images(
        self,
        srtpath: str,
        datajson_path: str,
        assrtpath: str,
        prompt_gen_images: str,
        prompt_prefix: str,
        prompt_cover_image: str,
        width: int,
        height: int,
        loras: List[Dict[str, Any]],
        topic_extra: Dict[str, Any],
        content: str,
        job_id: int = 0,
    ) -> None:
        """
        生成图片描述和图片
        
        Args:
            srtpath: 字幕文件路径
            datajson_path: 数据JSON文件路径
            assrtpath: 资源路径
            prompt_gen_images: 图片生成提示词
            prompt_prefix: 提示词前缀
            prompt_cover_image: 封面图片提示词
            width: 图片宽度
            height: 图片高度
            loras: LoRA配置列表
            topic_extra: 话题额外配置
            content: 文本内容
            job_id: 任务ID
        """
        # 生成图片描述
        logger.info(f"[generate_images] 开始生成图片描述 job_id={job_id}")
        srt2desc_gushi(
            srtpath,
            datajson_path,
            prompt_gen_images,
            prompt_prefix,
            prompt_cover_image,
            "gemini-2.5-flash",
            topic_extra,
        )
        logger.info(f"[generate_images] 图片描述生成完成 job_id={job_id}")
        
        # 生成Actor图像（如果需要）
        if topic_extra.get("generate_type", "none") == "same":
            logger.info(
                f"[generate_images] 生成类型为same，开始生成actor "
                f"job_id={job_id}"
            )
            actor_generate(assrtpath, content, loras)
            logger.info(f"[generate_images] actor生成完成 job_id={job_id}")
        
        # 生成图片
        topic_extra['topic'] = topic_extra.get('topic', '')
        logger.info(f"[generate_images] 开始生成图片 job_id={job_id}")
        desc2image_gushi(assrtpath, width, height, loras, topic_extra)
        logger.info(f"[generate_images] 图片生成完成 job_id={job_id}")


# 创建全局实例
image_generator_steps = ImageGeneratorSteps()

