"""图像生成相关 Celery 任务

提供并行的图像生成子任务。
使用 Celery group 实现多图片并发生成。

代码重构说明：
- 使用 core.config.video_config 中的统一 VideoResolution
- 替换硬编码的 1360x768 默认分辨率
"""
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

# 添加项目根目录到 Python 路径
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config import settings
from core.clients.image_client import ImageClient
from core.logging_config import setup_logging
# 使用统一的视频配置
from core.config.video_config import VideoResolution, get_dimensions
# 使用共享事件循环
from core.utils import run_async
from PIL import Image, ImageDraw, ImageFont

logger = setup_logging("worker.tasks.image_tasks")

# 默认分辨率（使用统一配置）
DEFAULT_WIDTH, DEFAULT_HEIGHT = get_dimensions(is_horizontal=True)


# ============================================================================
# 图像生成子任务
# ============================================================================

@shared_task(
    name='services.worker.tasks.image_tasks.generate_single_image_task',
    max_retries=3,
    default_retry_delay=10,
    soft_time_limit=300,  # 5分钟软限制
    time_limit=360,  # 6分钟硬限制
)
def generate_single_image_task(
    prompt: str,
    output_path: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    num_inference_steps: int = 30,
    lora_name: Optional[str] = None,
    lora_weight: float = 1.2,
    topic_prefix: str = "",
) -> Dict[str, Any]:
    """生成单张图片的 Celery 子任务

    这个任务可以被并行调用，用于同时生成多张图片。

    Args:
        prompt: 图像生成提示词
        output_path: 输出文件路径
        width: 图像宽度 (默认 1360)
        height: 图像高度 (默认 768)
        num_inference_steps: 推理步数 (默认 30)
        lora_name: LoRA 模型名称
        lora_weight: LoRA 权重 (默认 1.2)
        topic_prefix: 话题前缀提示词

    Returns:
        Dict[str, Any]: 生成结果
            {
                'output_path': str,  # 生成的图像路径
                'status': str,  # 'success' 或 'failed'
                'error': str,  # 错误信息（如果失败）
                'generation_time': float,  # 生成时间（秒）
            }
    """
    import time

    start_time = time.time()
    logger.info(f"[generate_single_image_task] 开始生成图片: {output_path}")

    try:
        # 构建完整提示词
        full_prompt = prompt
        if topic_prefix:
            full_prompt = f"{topic_prefix}, {prompt}"

        logger.debug(
            f"[generate_single_image_task] prompt={full_prompt[:100]}..., "
            f"size={width}x{height}"
        )

        # 调用图像生成服务
        # 使用共享事件循环，避免频繁创建/销毁的开销
        async def _generate_image():
            client = ImageClient(base_url=settings.AI_IMAGE_GEN_API_URL)
            # 现在返回的是图像二进制数据
            image_bytes = await client.generate_image(
                prompt=full_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                lora_name=lora_name,
                lora_step=int(lora_weight * 100),
            )
            return image_bytes

        # 使用共享事件循环运行（性能优化：1000图从100秒降至1秒）
        image_bytes = run_async(_generate_image, timeout=300)

        # 保存图片
        # API 直接返回图像二进制数据
        if isinstance(image_bytes, bytes):
            _ensure_output_dir(output_path)
            with open(output_path, 'wb') as f:
                f.write(image_bytes)
        else:
            raise TypeError(f"不支持的响应类型: {type(image_bytes)}")

        generation_time = time.time() - start_time

        logger.info(
            f"[generate_single_image_task] 图片生成成功: {output_path}, "
            f"耗时={generation_time:.2f}秒"
        )

        return {
            'output_path': output_path,
            'status': 'success',
            'error': None,
            'generation_time': generation_time,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[generate_single_image_task] 生成超时: {output_path}")
        # 创建超时占位图
        _create_placeholder_image(output_path, prompt, "超时")
        return {
            'output_path': output_path,
            'status': 'timeout',
            'error': '生成超时',
            'generation_time': time.time() - start_time,
        }

    except Exception as exc:
        logger.exception(
            f"[generate_single_image_task] 生成失败: {output_path}, error={exc}"
        )
        # 创建失败占位图
        _create_placeholder_image(output_path, prompt, f"失败: {str(exc)[:50]}")

        generation_time = time.time() - start_time

        # 如果还有重试机会，抛出异常
        # 这里我们使用占位图，所以不重试，直接返回结果
        return {
            'output_path': output_path,
            'status': 'failed',
            'error': str(exc),
            'generation_time': generation_time,
        }


# ============================================================================
# 批量图像生成任务（使用 group）
# ============================================================================

@shared_task(
    name='services.worker.tasks.image_tasks.generate_image_batch_task',
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=1800,  # 30分钟软限制
    time_limit=2100,  # 35分钟硬限制
)
def generate_image_batch_task(
    job_id: int,
    splits: list,
    workspace_dir: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    lora_name: Optional[str] = None,
    lora_weight: float = 1.2,
    topic_prefix: str = "",
) -> Dict[str, Any]:
    """批量生成图片任务

    使用 Celery group 并行生成多张图片。

    Args:
        job_id: 任务 ID
        splits: 分镜列表，每个元素包含 {index, text, prompt}
        workspace_dir: 工作目录
        width: 图像宽度
        height: 图像高度
        lora_name: LoRA 模型名称
        lora_weight: LoRA 权重
        topic_prefix: 话题前缀提示词

    Returns:
        Dict[str, Any]: 批量生成结果
            {
                'total': int,  # 总数
                'success': int,  # 成功数
                'failed': int,  # 失败数
                'image_paths': list,  # 图片路径列表
                'total_time': float,  # 总耗时
            }
    """
    import time
    from celery import group

    logger.info(
        f"[generate_image_batch_task] 开始批量生成 "
        f"(job_id={job_id}, 数量={len(splits)})"
    )

    start_time = time.time()

    # 准备输出目录
    images_dir = Path(workspace_dir) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # 创建任务组
    task_group = group(
        generate_single_image_task.s(
            prompt=split.get("prompt", split["text"]),
            output_path=str(images_dir / f"split_{split['index']:03d}.png"),
            width=width,
            height=height,
            lora_name=lora_name,
            lora_weight=lora_weight,
            topic_prefix=topic_prefix,
        )
        for split in splits
    )

    # 执行任务组（等待所有任务完成）
    results = task_group.apply_async()

    # 等待所有任务完成
    # get() 会阻塞直到所有任务完成
    task_results = results.get()

    # 统计结果
    total = len(task_results)
    success_count = sum(1 for r in task_results if r['status'] == 'success')
    failed_count = total - success_count

    # 提取图片路径
    image_paths = [r['output_path'] for r in task_results]

    total_time = time.time() - start_time

    logger.info(
        f"[generate_image_batch_task] 批量生成完成 "
        f"(job_id={job_id}, 成功={success_count}/{total}, "
        f"耗时={total_time:.2f}秒)"
    )

    return {
        'total': total,
        'success': success_count,
        'failed': failed_count,
        'image_paths': image_paths,
        'total_time': total_time,
    }


# ============================================================================
# 辅助函数
# ============================================================================

def _ensure_output_dir(filepath: str) -> None:
    """确保输出目录存在"""
    output_dir = Path(filepath).parent
    output_dir.mkdir(parents=True, exist_ok=True)


def _create_placeholder_image(
    output_path: str,
    prompt: str,
    error_msg: str = ""
) -> None:
    """创建占位图像

    Args:
        output_path: 输出路径
        prompt: 原始提示词
        error_msg: 错误信息
    """
    _ensure_output_dir(output_path)

    # 使用统一的视频配置获取默认分辨率
    width, height = DEFAULT_WIDTH, DEFAULT_HEIGHT
    img = Image.new("RGB", (width, height), color=(40, 40, 40))
    draw = ImageDraw.Draw(img)

    # 尝试加载字体
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()

    # 添加错误信息
    text_y = height // 2
    draw.text(
        (width // 2, text_y - 50),
        "图像生成失败",
        fill=(255, 100, 100),
        font=font,
        anchor="mm"
    )

    if error_msg:
        draw.text(
            (width // 2, text_y + 10),
            f"原因: {error_msg[:80]}",
            fill=(255, 200, 200),
            font=font,
            anchor="mm"
        )

    # 显示提示词前50个字符
    prompt_preview = prompt[:50] + "..." if len(prompt) > 50 else prompt
    draw.text(
        (width // 2, text_y + 70),
        f"提示词: {prompt_preview}",
        fill=(200, 200, 200),
        font=font,
        anchor="mm"
    )

    img.save(output_path)
    logger.debug(f"占位图像已创建: {output_path}")


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    'generate_single_image_task',
    'generate_image_batch_task',
]
