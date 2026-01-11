# Main entry point for running different components of the service
import argparse
import asyncio  # Import asyncio for async operations
import logging
import os

from dotenv import load_dotenv
from utils.civitai_downloader import CivitaiDownloader  # Import CivitaiDownloader

from config.settings import get_settings  # Import get_settings

# Load environment variables from .env file
load_dotenv()

# Configure logging
from core.logging_config import setup_logging

logger = setup_logging("ai_image_gen.main")

def run_api_service():
    """Runs the FastAPI application."""
    logger.info("Starting API Service...")
    # Ensure uvicorn is installed: pip install uvicorn
    import uvicorn

    # Set the app path relative to the project root
    uvicorn.run("api_service.main:app", host="0.0.0.0", port=8000, reload=True)

async def run_consumer_worker():
    """Runs a Kafka consumer worker instance."""
    logger.info("Starting Consumer Worker...")
    from consumer_worker.worker import ConsumerWorker
    worker = ConsumerWorker()
    await worker.start()

def run_external_scheduler():
    """Runs the external task scheduler for monitoring."""
    logger.info("Starting External Task Scheduler...")
    from task_scheduler.scheduler import ExternalTaskScheduler
    scheduler = ExternalTaskScheduler()
    scheduler.start_monitoring_loop()

def initialize_database():
    """Initializes the database tables."""
    logger.info("Initializing Database...")
    from data_management.database import init_db
    init_db()
    logger.info("Database initialization complete.")

async def download_sdxl_model():
    """Downloads the SDXL base model using CivitaiDownloader."""
    logger.info("Starting SDXL Model Download...")
    settings = get_settings()
    downloader = CivitaiDownloader(download_dir=settings.MODEL_CACHE_DIR)
    
    # Juggernaut XL v8 - Civitai Model ID: 133005
    # This is a common SDXL base model. You can find other model IDs on Civitai.
    model_id = "133005"
    
    try:
        downloaded_path = await downloader.download_model_by_id(model_id)
        if downloaded_path:
            logger.info(f"Successfully downloaded SDXL model (ID: {model_id}) to: {downloaded_path}")
        else:
            logger.error(f"Failed to download SDXL model (ID: {model_id}). Check logs for details.")
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（模型下载错误等）
        logger.error(f"[download_sdxl] An error occurred during SDXL model download: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run components of the AI Image Generation Service.")
    parser.add_argument("component", type=str, choices=["api", "worker", "scheduler", "init_db", "download_sdxl"],
                        help="Specify which component to run: 'api', 'worker', 'scheduler', 'init_db', or 'download_sdxl'.")

    args = parser.parse_args()

    if args.component == "api":
        run_api_service()
    elif args.component == "worker":
        asyncio.run(run_consumer_worker())
    elif args.component == "scheduler":
        run_external_scheduler()
    elif args.component == "init_db":
        initialize_database()
    elif args.component == "download_sdxl":
        asyncio.run(download_sdxl_model())
    else:
        logger.error("Invalid component specified.")