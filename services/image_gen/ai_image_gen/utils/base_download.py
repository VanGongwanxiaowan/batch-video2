import logging
import os

from huggingface_hub import snapshot_download

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("ai_image_gen.base_download")

# --- 配置 ---
BASE_DOWNLOAD_DIR = f"{MODEL_CACHE_DIR}"
PROXY_HTTP = "http://127.0.0.1:10809"
PROXY_HTTPS = "http://127.0.0.1:10809"

# Hugging Face 模型 ID
SD15_MODEL_ID = "runwayml/stable-diffusion-v1-5"
SDXL_MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"
# 如果还需要 SDXL VAE，可以加上
SDXL_VAE_MODEL_ID = "stabilityai/sdxl-vae"

# --- 设置代理环境变量 ---
logger.info(f"Setting HTTP_PROXY to {PROXY_HTTP}")
os.environ["HTTP_PROXY"] = PROXY_HTTP
logger.info(f"Setting HTTPS_PROXY to {PROXY_HTTPS}")
os.environ["HTTPS_PROXY"] = PROXY_HTTPS

# 可选：如果你不需要代理访问本地或特定内网地址
# os.environ["NO_PROXY"] = "localhost,127.0.0.1"


def download_model(model_id: str, sub_dir: str):
    """
    下载 Hugging Face 模型到指定子目录
    """
    local_dir = os.path.join(BASE_DOWNLOAD_DIR, sub_dir)
    os.makedirs(local_dir, exist_ok=True) # 确保目录存在

    logger.info(f"Attempting to download model: '{model_id}' to '{local_dir}'")
    try:
        # 使用 snapshot_download 下载整个仓库
        # local_dir_use_symlinks=False 确保所有文件都被复制而不是创建软链接
        # allow_patterns 可以用来过滤下载的文件，例如只下载 .safetensors 和 .json 文件
        snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
            # 过滤不需要的大文件，例如训练日志、示例图片等
            # 对于Diffusers模型，通常需要 .safetensors/.bin, .json 文件
            allow_patterns=["*.safetensors", "*.bin", "*.json", "*.txt"]
        )
        logger.info(f"Successfully downloaded '{model_id}' to '{local_dir}'")
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（模型下载错误等）
        logger.error(f"[download_model] Failed to download '{model_id}': {e}", exc_info=True)
        # 清理可能下载不完整的文件，避免下次重试时出现问题
        # 如果下载失败，确保不会留下损坏的文件
        if os.path.exists(local_dir):
            import shutil
            try:
                shutil.rmtree(local_dir)
                logger.warning(f"[download_model] Cleaned up incomplete download directory: {local_dir}")
            except (OSError, PermissionError) as cleanup_error:
                logger.warning(f"[download_model] Failed to cleanup incomplete download directory: {cleanup_error}")


if __name__ == "__main__":
    logger.info("Starting model download process...")

    # 下载 SD1.5 模型
    download_model(SD15_MODEL_ID, "stable-diffusion-v1-5")

    # 下载 SDXL base 模型
    download_model(SDXL_MODEL_ID, "stable-diffusion-xl-base-1.0")

    # 下载 SDXL VAE (可选，但强烈推荐，因为SDXL base模型默认不带VAE)
    download_model(SDXL_VAE_MODEL_ID, "sdxl-vae")

    logger.info("Model download process completed (check logs for success/failure).")