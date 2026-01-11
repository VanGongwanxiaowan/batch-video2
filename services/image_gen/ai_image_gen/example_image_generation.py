import asyncio
import logging
import os

from consumer_worker.image_generator import ImageGenerator
from consumer_worker.model_manager import ModelManager
from utils.civitai_downloader import CivitaiDownloader  # Import CivitaiDownloader

from config.settings import get_settings
from core.logging_config import setup_logging

logger = setup_logging("ai_image_gen.example")

async def main():
    settings = get_settings()
    
    # Ensure output directory exists
    output_dir = settings.GENERATED_IMAGES_DIR
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Generated images will be saved to: {output_dir}")

    # Initialize ModelManager
    # In a real application, you might pass a device (e.g., "cuda" or "cpu")
    model_manager = ModelManager(cache_dir=settings.MODEL_CACHE_DIR)
    image_generator = ImageGenerator(model_manager=model_manager, output_dir=output_dir)
    downloader = CivitaiDownloader(download_dir=settings.MODEL_CACHE_DIR)

    # --- Example 1: Download SDXL model (Juggernaut XL) ---
    # logger.info("\n--- Running Example 1: Downloading SDXL Model (Juggernaut XL) ---")
    # try:
    #     # Juggernaut XL v8 - Civitai Model ID: 133005
    #     # You can find model IDs on Civitai by looking at the URL: civitai.com/models/{model_id}
    #     downloaded_sdxl_path = await downloader.download_model_by_id("133005")
    #     if downloaded_sdxl_path:
    #         logger.info(f"Downloaded SDXL model to: {downloaded_sdxl_path}")
    #     else:
    #         logger.error("Failed to download SDXL model.")
    # except Exception as e:
    #     logger.error(f"Error downloading SDXL model: {e}")

    # --- Example 2: Generate image with SDXL model ---
    # logger.info("\n--- Running Example 2: SDXL Image Generation ---")
    # try:
    #     sdxl_image_path = await image_generator.generate(
    #         model_name="sdxl",
    #         prompt="A futuristic city at sunset, highly detailed, cinematic lighting",
    #         negative_prompt="low quality, blurry, ugly, deformed",
    #         image_params={
    #             "width": 1024,
    #             "height": 1024,
    #             "steps": 30,
    #             "cfg_scale": 7.0,
    #             "seed": 42,
    #             "batch_size": 1
    #         }
    #     )
    #     logger.info(f"SDXL Image generated at: {sdxl_image_path}")
    # except Exception as e:
    #     logger.error(f"Error generating SDXL image: {e}")

    ## --- Example 3: Generate image with SD15 model ---
    logger.info("\n--- Running Example 3: SD15 Image Generation ---")
    try:
        for i in range(3):
            sd15_image_path = await image_generator.generate(
                model_name="sd15",
                prompt="A cozy cabin in a snowy forest, warm light from windows, highly detailed",
                negative_prompt="bad anatomy, deformed, ugly",
                image_params={
                    "width": 512,
                    "height": 512,
                    "steps": 25,
                    "cfg_scale": 7.5,
                    "seed": 123,
                    "batch_size": 1
                },
                loras=[
                    {
                        "path": os.path.join(
                            settings.MODEL_CACHE_DIR,
                            "stable-diffusion-v1-5_loras",
                            "KoalaEngineV2a.safetensors",
                        ),
                        "name": "KoalaEngineV2a",
                        "weight": 0.8,
                    }
                ]
            )
        logger.info(f"SD15 Image generated at: {sd15_image_path}")
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except (OSError, PermissionError, FileNotFoundError) as e:
        # 文件系统错误
        logger.error(f"[example] 文件系统错误，生成SD15图像失败: {e}", exc_info=True)
    except Exception as e:
        # 其他异常（图像生成错误等）
        logger.error(f"[example] Error generating SD15 image: {e}", exc_info=True)

    ##--- Example 4: Generate image with FLUX model and Lora ---
    logger.info("\n--- Running Example 4: FLUX Image Generation with Lora ---")
    try:
        for i in range(3):
            flux_image_path = image_generator.generate(
                model_name="flux",
                prompt="A cyberpunk street scene with neon lights and rain, intricate details",
                negative_prompt="cartoon, anime, low resolution",
                image_params={
                    "width": 1024,
                    "height": 1024,
                    "steps": 5,
                    "cfg_scale": 6.0,
                    "seed": -1, # Random seed
                    "batch_size": 1
                },
                loras=[
                    {
                        "path": os.path.join(
                            settings.MODEL_CACHE_DIR,
                            "flux-1-dev_loras",
                            "古风漫画男主.safetensors",
                        ),
                        "name": "古风漫画男主",
                        "weight": 0.8,
                    }
                ]
            )

            flux_image_path = image_generator.generate(
                model_name="flux",
                prompt="A cyberpunk street scene with neon lights and rain, intricate details",
                negative_prompt="cartoon, anime, low resolution",
                image_params={
                    "width": 1024,
                    "height": 1024,
                    "steps": 5,
                    "cfg_scale": 6.0,
                    "seed": -1, # Random seed
                    "batch_size": 1
                },
                loras=[
                    {
                        "path": os.path.join(
                            settings.MODEL_CACHE_DIR,
                            "flux-1-dev_loras",
                            "古风漫画男主.safetensors",
                        ),
                        "name": "古风漫画男主",
                        "weight": 0.8,
                    }
                    # {"path": os.path.join(settings.MODEL_CACHE_DIR, "flux-1-dev_loras", "异色迷幻手绘插画.safetensors"), "name": "异色迷幻手绘插画", "weight": 0.8}
                ]
            )

        logger.info(f"FLUX Image with Lora generated at: {flux_image_path}")
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except (OSError, PermissionError, FileNotFoundError) as e:
        # 文件系统错误
        logger.error(f"[example] 文件系统错误，生成FLUX图像失败: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
    except Exception as e:
        # 其他异常（图像生成错误等）
        logger.error(f"[example] Error generating FLUX image with Lora: {e}", exc_info=True)
        import traceback
        traceback.print_exc()

    # logger.info("\n--- Running Example 3: SD15 Image Generation ---")
    # try:
    #     for i in range(3):
    #         sd15_image_path = await image_generator.generate(
    #             model_name="sd15",
    #             prompt="A cozy cabin in a snowy forest, warm light from windows, highly detailed",
    #             negative_prompt="bad anatomy, deformed, ugly",
    #             image_params={
    #                 "width": 512,
    #                 "height": 512,
    #                 "steps": 25,
    #                 "cfg_scale": 7.5,
    #                 "seed": 123,
    #                 "batch_size": 1
    #             }
    #         )
    #     logger.info(f"SD15 Image generated at: {sd15_image_path}")
    # except Exception as e:
    #     logger.error(f"Error generating SD15 image: {e}")


    # logger.info("\n--- All examples finished ---")

if __name__ == "__main__":
    # This part requires torch to be installed for the generator
    # If torch is not installed, you might need to mock it or install it.
    try:
        import torch
    except ImportError:
        logger.warning("PyTorch not found. Image generation with specific seeds might fail. Please install torch if needed.")
    
    asyncio.run(main())