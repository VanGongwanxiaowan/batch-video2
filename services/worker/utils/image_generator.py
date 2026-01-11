"""图像生成模块"""
import concurrent.futures
import json
import os
import random
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple

from clients import ai_image_client
from utils.image_embedding_tool import ImageEmbeddingTool
from utils.util import ocr_image
from worker.config import settings

from core.logging_config import setup_logging

logger = setup_logging("worker.utils.image_generator")

HUMAN_CONFIG_PATH = settings.human_config_path


def _generate_single_image(
    index: str,
    imageprompt: str,
    width: int,
    height: int,
    basepath: str,
    is_actor: str,
    loras: List[Dict[str, Any]],
) -> Tuple[str, str]:
    """
    生成单张图像
    
    Args:
        index: 图像索引
        imageprompt: 图像提示词
        width: 图像宽度
        height: 图像高度
        basepath: 基础路径
        is_actor: 是否为actor图像
        loras: LoRA配置列表
        
    Returns:
        (index, task_id) 元组
    """
    datajsonpath = os.path.join(basepath, "data.json")
    datajson = {}
    if os.path.exists(datajsonpath):
        with open(datajsonpath, "r", encoding="utf-8") as f:
            datajson = json.load(f)
    task_id = datajson.get("actor_task")

    filename = os.path.join(basepath, f"{index}.png")
    model_name = "flux"
    image_params = {
        "width": width,
        "height": height,
        "steps": 30,
        "cfg_scale": 3.5,
        "seed": -1,
        "batch_size": 1,
    }
    
    if task_id and str(is_actor) in ["true", "True"]:
        image_params["subject_image"] = f"{task_id}.png"
        image_params["subject_scale"] = 0.6
        model_name = "insc"

    prefix = ai_image_client.get_prefix(loras)
    
    try:
        for attempt in range(20):  # 最多重试20次
            negative_prompt = "blurry, low quality"
            topic = "flux_tasks"

            data = {
                "user_id": "test_user_" + str(random.randint(1, 1000)),
                "topic": topic,
                "model_name": model_name,
                "prompt": prefix + imageprompt,
                "negative_prompt": negative_prompt,
                "image_params": image_params,
                "loras": loras,
                "width": width,
                "height": height,
            }
            
            logger.debug(f"提交图像生成任务: index={index}, model={model_name}")
            task_id, topic, model_name = ai_image_client.submit_image_generation_tasks_sync(
                topic, model_name, data
            )
            
            if not task_id:
                logger.warning(f"图像生成任务提交失败: index={index}, attempt={attempt + 1}")
                continue
            
            # 等待任务完成
            for i in range(60):
                time.sleep(5)
                status = ai_image_client.check_task_status_sync(task_id)
                if status and status.get("status") == "completed":
                    ai_image_client.get_image_and_save_sync(
                        task_id, topic, model_name, filename
                    )
                    break
                if status and status.get("status") == "failed":
                    raise Exception(
                        f"Image generation failed. Error Message: {status.get('error_message', '')}"
                    )
            
            # 检查OCR结果，如果包含文字则重试
            result = ocr_image(filename)
            ocr_result = result.get("ocr_result", [])
            if not ocr_result or not ocr_result[0]:
                logger.info(f"图像生成成功（无OCR结果）: index={index}")
                return index, task_id
            
            text = ""
            results = [] if not ocr_result[0] else ocr_result[0]
            for x in results:
                if x:
                    text += x[-1][0]
            
            if len(text) < 10:
                logger.info(f"图像生成成功: index={index}")
                return index, task_id
            else:
                logger.warning(f"图像包含文字，重试: index={index}, text_length={len(text)}, attempt={attempt + 1}")
                
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（图像生成错误等）
        logger.error(f"[generate_image] 图像生成失败: index={index}, error={e}", exc_info=True)
    
    return index, task_id


def _match_similar_image(
    imageindex: str,
    prompt_data: Dict[str, Any],
    basepath: str,
    srtdata: Dict[str, Dict[str, Any]],
    topics_config: Dict[str, Any],
    topic_name: str,
) -> None:
    """
    匹配相似图像或视频
    
    Args:
        imageindex: 图像索引
        prompt_data: 提示词数据
        basepath: 基础路径
        srtdata: 字幕数据
        topics_config: 主题配置
        topic_name: 主题名称
    """
    imagepath = os.path.join(basepath, f"{imageindex}.png")
    if os.path.exists(imagepath):
        return

    # 检查是否需要生成视频而不是图像
    _generate = True
    if topic_name in topics_config:
        _generate = topics_config[topic_name].get("generate", True)

    if not _generate:
        # 匹配一段视频
        min_duration = prompt_data.get("duration", 0) + 500
        if str(int(imageindex) + 1) in srtdata:
            next_image_prompt_data = srtdata[str(int(imageindex) + 1)]
            next_start = next_image_prompt_data.get("start", 0)
            start = prompt_data.get("start", 0)
            min_duration = next_start - start

        video_path = os.path.join(basepath, f"{imageindex}.mp4")
        from utils.video_processor import compare_video
        compare_video(int(min_duration) / 1000.0, imagepath, video_path)
        return

    # 使用图像嵌入工具查找相似图片
    logger.info(f"匹配相似图像: index={imageindex}, prompt={prompt_data['prompt'][:50]}...")
    image_embedding_tool = ImageEmbeddingTool()
    results = image_embedding_tool.find_similar_image(
        prompt_data["prompt"], top_k=3
    )
    
    for result in results:
        image_path = result["image_path"]
        if not os.path.exists(image_path):
            continue
        shutil.copy(image_path, imagepath)
        logger.info(f"成功匹配图像: {image_path} -> {imagepath}")
        return


def generate_images_from_srtdata(
    srtdata: Dict[str, Dict[str, Any]],
    basepath: str,
    width: int = 1360,
    height: int = 768,
    loras: Optional[List[Dict[str, Any]]] = None,
    topic_extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    根据字幕数据生成图像
    
    Args:
        srtdata: 字幕数据字典
        basepath: 基础路径
        width: 图像宽度
        height: 图像高度
        loras: LoRA配置列表
        topic_extra: 主题额外配置
        
    Returns:
        更新后的字幕数据字典
    """
    loras = loras or []
    topic_extra = topic_extra or {}
    
    # 加载配置
    with open(HUMAN_CONFIG_PATH, "r", encoding="utf-8") as fp:
        config_json = json.load(fp)
    topics_config = config_json.get("topic", {})
    topic_name = topic_extra.get("topic", "")

    # 准备数据
    values = []
    for key, val in srtdata.items():
        values.append([key, val, val.get("is_actor", "false")])
    values = sorted(values, key=lambda x: str(x[2]))

    # 获取生成参数
    generate_ratio = topic_extra.get("generate_ratio", 100)
    generate_time_minutes = topic_extra.get("generate_time", 0)
    generate_time_ms = generate_time_minutes * 60 * 1000

    logger.info(f"图像生成参数: ratio={generate_ratio}%, time={generate_time_minutes}分钟")

    # 分类需要生成和匹配的图像
    images_to_generate = []
    images_to_match = []

    for key, val in srtdata.items():
        end = val.get("end", 0)
        if (generate_time_minutes == 0 or end < generate_time_ms) and (
            len(images_to_generate) < len(values) * generate_ratio // 100
        ):
            images_to_generate.append([key, val, val.get("is_actor", "false")])
        else:
            images_to_match.append([key, val, val.get("is_actor", "false")])

    # 并行生成图像
    max_workers = min(len(images_to_generate), 8)
    if max_workers > 0:
        logger.info(f"开始生成 {len(images_to_generate)} 张图像，使用 {max_workers} 个工作线程")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for _value in images_to_generate:
                imageindex, prompt_data, is_actor = _value
                imagepath = os.path.join(basepath, f"{imageindex}.png")
                if os.path.exists(imagepath):
                    continue
                
                future = executor.submit(
                    _generate_single_image,
                    imageindex,
                    prompt_data["prompt"],
                    width,
                    height,
                    basepath,
                    is_actor,
                    loras,
                )
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except Exception as e:
                    # 其他异常（图像生成任务错误等）
                    logger.error(f"[_match_similar_image] 图像生成任务失败: {e}", exc_info=True)

    # 匹配相似图像
    logger.info(f"开始匹配 {len(images_to_match)} 张图像")
    for _value in images_to_match:
        imageindex, prompt_data, is_actor = _value
        _match_similar_image(
            imageindex, prompt_data, basepath, srtdata, topics_config, topic_name
        )

    return srtdata


def generate_actor_image(
    basepath: str,
    content: str,
    loras: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    生成Actor图像
    
    Args:
        basepath: 基础路径
        content: 内容文本
        loras: LoRA配置列表
        
    Returns:
        task_id字符串
    """
    loras = loras or []
    data_path = os.path.join(basepath, "data.json")
    actorpath = os.path.join(basepath, "actor.png")
    
    if not os.path.exists(data_path):
        logger.warning(f"数据文件不存在: {data_path}")
        return ""
    
    datajson = {}
    with open(data_path, "r", encoding="utf-8") as f:
        datajson = json.load(f)

    prompt = f"""
{content}

---------
根据文章内容，总结出老人的特征，设定一个老人形象，用一段英文(30 - 40词之内)来描述一下老人的正面全身。 注意：性别绝对不能搞错

直接输出外貌的英文描述：
"""
    from utils.util import chat_with_llm
    imageprompt = chat_with_llm(prompt, model="gemini-2.5-flash")
    prefix = ai_image_client.get_prefix(loras)
    
    try:
        for attempt in range(10):
            negative_prompt = "blurry, low quality"
            topic = "flux_tasks"
            model_name = "flux"
            image_params = {
                "width": 768,
                "height": 1360,
                "steps": 30,
                "cfg_scale": 3.5,
                "seed": -1,
                "batch_size": 1,
            }
            data = {
                "user_id": "test_user_" + str(random.randint(1, 1000)),
                "topic": topic,
                "model_name": model_name,
                "prompt": prefix + imageprompt,
                "negative_prompt": negative_prompt,
                "image_params": image_params,
                "loras": loras,
                "width": 768,
                "height": 1360,
            }
            
            logger.info(f"提交Actor图像生成任务: attempt={attempt + 1}")
            task_id, topic, model_name = ai_image_client.submit_image_generation_tasks_sync(
                topic, model_name, data
            )
            
            if not task_id:
                logger.warning(f"Actor图像生成任务提交失败: attempt={attempt + 1}")
                continue
            
            # 等待任务完成
            for i in range(90):
                time.sleep(5)
                status = ai_image_client.check_task_status_sync(task_id)
                if status and status.get("status") == "completed":
                    ai_image_client.get_image_and_save_sync(
                        task_id, topic, model_name, actorpath
                    )
                    break
                if status and status.get("status") == "failed":
                    raise Exception(
                        f"Image generation failed. Error Message: {status.get('error_message', '')}"
                    )
            
            # 检查OCR结果
            result = ocr_image(actorpath)
            ocr_result = result.get("ocr_result", [])
            if not ocr_result or not ocr_result[0]:
                logger.info("Actor图像生成成功（无OCR结果）")
                break
            
            text = ""
            results = [] if not ocr_result[0] else ocr_result[0]
            for x in results:
                if x:
                    text += x[-1][0]
            
            if len(text) < 10:
                logger.info("Actor图像生成成功")
                break
            else:
                logger.warning(f"Actor图像包含文字，重试: text_length={len(text)}, attempt={attempt + 1}")
                
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（Actor图像生成错误等）
        logger.error(f"[generate_actor_image] Actor图像生成失败: {e}", exc_info=True)
        task_id = ""
    
    # 保存task_id到数据文件
    datajson["actor_task"] = task_id
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(datajson, f, ensure_ascii=False, indent=4)
    
    return task_id

