# Handles the actual image generation using Diffusers
import base64
import io
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import torch
from consumer_worker.model_manager import ModelManager
from PIL import Image

from config.settings import get_settings  # Import get_settings
from core.logging_config import setup_logging

logger = setup_logging("ai_image_gen.image_generator")

# 使用安全的路径拼接
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED_IMAGES_DIR = os.path.join(_base_dir, "uploads_images")
os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)

class ImageGenerator:
    def __init__(self, model_manager: ModelManager, output_dir: str = None):
        self.model_manager = model_manager
        # 使用绝对路径，默认使用全局配置的目录
        self.output_dir = os.path.abspath(output_dir) if output_dir else GENERATED_IMAGES_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(
        self,
        model_name: str,
        prompt: str,
        negative_prompt: Optional[str],
        image_params: Dict[str, Any],
        loras: Optional[List[Dict[str, Any]]] = None
    ) -> str: # Returns image URL/path
        # Get model path from settings based on model_name
        settings = get_settings()
        model_config = settings.MODEL_CONFIGS.get(model_name.upper())
        if not model_config:
            raise ValueError(f"Model configuration for '{model_name}' not found in settings.")
        
        model_path_or_url = model_config.get("path")
        if not model_path_or_url:
            raise ValueError(f"Model path for '{model_name}' not found in model configuration.")
        
        # If loras are not provided in the task, try to get default lora from config
  
        pipeline = self.model_manager.get_loaded_pipeline()
        # if not pipeline or self.model_manager.get_loaded_model_name() != model_name:
        #     logger.warning(f"Model '{model_name}' not loaded or incorrect model loaded. Attempting to load from {model_path_or_url}...")
        self.model_manager.load_model_and_loras(model_path_or_url, model_name, loras)
        pipeline = self.model_manager.get_loaded_pipeline()
        if not pipeline:
            raise RuntimeError(f"Failed to load model {model_name} for image generation.")

        logger.info(f"Generating image for prompt: '{prompt}' with model '{model_name}'")

        try:
            gen_args = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": image_params.get("width"),
                "height": image_params.get("height"),
                "num_inference_steps": image_params.get("steps"),
                "guidance_scale": image_params.get("cfg_scale"),
                "num_images_per_prompt": image_params.get("batch_size", 1),
            }
            logger.debug(f"Image generation parameters: {image_params}")
            if image_params.get("seed") != -1:
                gen_args["generator"] = torch.Generator("cuda").manual_seed(image_params.get("seed"))

            if image_params.get("subject_image"):
                image_path = image_params.get("subject_image", "")
                subject_image = None
                # 安全检查：防止路径遍历攻击
                if image_path:
                    # 规范化路径并检查是否在允许的目录内
                    image_full_path = os.path.abspath(os.path.join(GENERATED_IMAGES_DIR, image_path))
                    allowed_dir = os.path.abspath(GENERATED_IMAGES_DIR)
                    if image_full_path.startswith(allowed_dir) and os.path.exists(image_full_path):
                        try:
                            subject_image = Image.open(image_full_path).convert('RGB')
                        except (SystemExit, KeyboardInterrupt):
                            # 系统退出异常，不捕获，直接抛出
                            raise
                        except (OSError, IOError, ValueError) as e:
                            # 图像文件IO错误或格式错误
                            logger.warning(f"[generate] Failed to load subject image from {image_full_path}: {e}")
                            subject_image = None
                        except Exception as e:
                            # 其他异常
                            logger.warning(f"[generate] Failed to load subject image from {image_full_path}: {e}")
                            subject_image = None
                    else:
                        logger.warning(f"Subject image path {image_path} is outside allowed directory or does not exist")
                subject_scale = image_params.get("subject_scale", 0.9)
                gen_args["subject_image"] = subject_image
                gen_args["subject_scale"] = subject_scale

            # Call the pipeline
            output = pipeline(**gen_args)
            images = output.images

            image_urls = []
            for i, img in enumerate(images):
                file_name = f"{uuid.uuid4()}.png"
                # 使用安全的路径拼接
                file_path = os.path.join(self.output_dir, file_name)
                # 确保路径在允许的目录内（额外安全检查）
                file_path = os.path.abspath(file_path)
                if not file_path.startswith(os.path.abspath(self.output_dir)):
                    raise ValueError(f"Generated file path {file_path} is outside output directory")
                
                try:
                    img.save(file_path)
                    image_urls.append(file_path)
                    logger.debug(f"Saved image {i+1}/{len(images)} to {file_path}")
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except (OSError, PermissionError, IOError) as e:
                    # 文件系统错误
                    logger.error(f"[generate] 文件系统错误，保存图像失败 {i+1} to {file_path}: {e}", exc_info=True)
                    raise
                except Exception as e:
                    # 其他异常（图像保存错误等）
                    logger.error(f"[generate] Failed to save image {i+1} to {file_path}: {e}", exc_info=True)
                    raise

            logger.info(f"Generated {len(images)} image(s). Paths: {image_urls}")
            return image_urls[0] if image_urls else None  # Return the first image URL for simplicity

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（图像生成错误等）
            logger.error(f"[generate] Error during image generation: {e}", exc_info=True)
            raise