# Utility for downloading models and Lora from Civitai
import logging
import os
from typing import Optional

import requests
from tqdm import tqdm  # For progress bar

from core.logging_config import setup_logging

logger = setup_logging("ai_image_gen.civitai_downloader")

class CivitaiDownloader:
    def __init__(self, download_dir: str = "./model_cache", proxies: Optional[dict] = None):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        self.base_url = "https://civitai.com/api/v1" # Base API URL
        self.proxies = proxies

    def _get_model_info(self, model_id: str) -> Optional[dict]:
        """Fetches model information from Civitai API."""
        url = f"{self.base_url}/models/{model_id}"
        try:
            response = requests.get(url, proxies=self.proxies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching model info for ID {model_id}: {e}")
            return None

    def download_file(self, file_url: str, destination_path: str, file_name: str) -> Optional[str]:
        """Downloads a file with progress bar and handles resume."""
        full_path = os.path.join(destination_path, file_name)
        
        headers = {}
        mode = "wb"
        current_size = 0
        if os.path.exists(full_path):
            current_size = os.path.getsize(full_path)
            headers["Range"] = f"bytes={current_size}-"
            mode = "ab"
            logger.info(f"Resuming download for {file_name} from {current_size} bytes.")

        try:
            response = requests.get(file_url, headers=headers, stream=True, proxies=self.proxies)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0)) + current_size
            if total_size == current_size and mode == "ab":
                logger.info(f"File {file_name} already fully downloaded.")
                return full_path

            with open(full_path, mode) as f:
                with tqdm(
                    total=total_size, initial=current_size, unit="B", unit_scale=True, desc=file_name
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            logger.info(f"Successfully downloaded {file_name} to {full_path}")
            return full_path
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading file {file_name} from {file_url}: {e}")
            if os.path.exists(full_path) and os.path.getsize(full_path) == 0:
                os.remove(full_path) # Clean up empty file on error
            return None

    async def download_model_by_id(self, model_id: str, version_id: Optional[str] = None) -> Optional[str]:
        """Downloads a specific model version from Civitai."""
        model_info = self._get_model_info(model_id)
        if not model_info:
            return None

        target_version = None
        if version_id:
            for version in model_info.get("modelVersions", []):
                if str(version.get("id")) == version_id:
                    target_version = version
                    break
        else:
            # Default to latest version if no version_id specified
            if model_info.get("modelVersions"):
                target_version = model_info["modelVersions"][0] # Assuming latest is first

        if not target_version:
            logger.error(f"Model version {version_id or 'latest'} not found for model ID {model_id}.")
            return None

        files = target_version.get("files", [])
        if not files:
            logger.error(f"No files found for model version {target_version.get('id')}.")
            return None
        
        # Prioritize safetensors if available, otherwise take the first file
        file_to_download = None
        for f in files:
            if f.get("type") == "Model" and f.get("metadata", {}).get("format") == "SafeTensor":
                file_to_download = f
                break
        if not file_to_download:
            file_to_download = files[0] # Fallback to first available file

        download_url = file_to_download.get("downloadUrl")
        file_name = file_to_download.get("name")

        if not download_url or not file_name:
            logger.error(f"Download URL or file name missing for model ID {model_id}, version {target_version.get('id')}.")
            return None

        model_dir = os.path.join(self.download_dir, model_info.get("name").replace(" ", "_"), str(target_version.get("id")))
        os.makedirs(model_dir, exist_ok=True)

        logger.info(f"Starting download of model '{file_name}' from Civitai...")
        return self.download_file(download_url, model_dir, file_name)

    async def download_lora_by_id(self, lora_id: str, version_id: Optional[str] = None) -> Optional[str]:
        """Downloads a specific Lora version from Civitai."""
        # Lora models are also fetched via the /models endpoint
        return await self.download_model_by_id(lora_id, version_id)

if __name__ == "__main__":
    # Example usage (requires an event loop for async methods)
    async def main():
        proxies = {
            "http": "http://127.0.0.1:10809",
            "https": "http://127.0.0.1:10809",
        }
        downloader = CivitaiDownloader(proxies=proxies)
        # Replace with actual Civitai Model ID and Version ID
        # Example SDXL model ID: 101055 (Juggernaut XL)
        # Example Lora ID: 12345 (replace with a real one)
        
        # 使用标准logging，因为这个模块可能被其他地方导入
        import logging
        downloaded_model_path = await downloader.download_model_by_id("376130")
        if downloaded_model_path:
            logging.info(f"Downloaded SDXL model to: {downloaded_model_path}")
        
        # downloaded_lora_path = await downloader.download_lora_by_id("12345")
        # if downloaded_lora_path:
        #     logging.info(f"Downloaded Lora to: {downloaded_lora_path}")

        logging.info("CivitaiDownloader example. Uncomment lines to test downloads.")

    import asyncio
    asyncio.run(main())