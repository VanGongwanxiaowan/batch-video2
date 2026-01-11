# Manages loading, unloading, and caching of Stable Diffusion models and Lora
import logging
import os
import sys
import traceback
from typing import Any, Dict, List, Optional

import torch
from diffusers import AutoPipelineForText2Image, DiffusionPipeline, StableDiffusionPipeline
from transformers import AutoModelForCausalLM, AutoTokenizer

from config.settings import get_settings
from core.logging_config import setup_logging

logger = setup_logging("ai_image_gen.model_manager")

class ModelManager:
    def __init__(self, cache_dir: str = "./model_cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.loaded_pipeline: Optional[DiffusionPipeline] = None
        self.loaded_model_name: Optional[str] = None
        self.loaded_loras: Dict[str, Any] = {} 
        self.settings = get_settings()
        
    def get_lora_id(self, lora_name: str) -> str:
        """
        Extracts the Lora ID from the Lora name.
        Assumes the Lora name is in the format 'name.safetensors'.
        """
        return os.path.splitext(lora_name)[0] if lora_name else ""

    def load_model_and_loras(self, model_path_or_url: str, model_name: str, loras: Optional[List[Dict[str, Any]]] = None):
        """
        Loads a Stable Diffusion model and applies specified Lora(s).
        model_path_or_url can be a local path or a direct download URL.
        """
        device  = "cuda" if torch.cuda.is_available() else "cpu"
        try:

            if self.loaded_model_name == model_name and self._are_loras_loaded(loras):
                logger.info(f"Model '{model_name}' and specified Lora(s) already loaded. Skipping.")
                return self.loaded_pipeline

            logger.info(f"Attempting to load model: {model_name} from {model_path_or_url}")

            # Unload current model if different
            if self.loaded_pipeline and self.loaded_model_name != model_name:
                if self.loaded_pipeline:
                    self.loaded_pipeline.to("cpu") # Move to CPU to free up GPU memory
                del self.loaded_pipeline
                self.loaded_pipeline = None
                self.loaded_model_name = None
                self.loaded_loras = {}
                torch.cuda.empty_cache() # Clear GPU memory

            # Load base model
            if not self.loaded_pipeline:
                final_model_path = model_path_or_url
                if not os.path.exists(model_path_or_url):
                    raise FileNotFoundError(f"Model not found or could not be downloaded from {model_path_or_url}")
                try:
                    if model_name == "sdxl":
                        self.loaded_pipeline = AutoPipelineForText2Image.from_pretrained(
                            final_model_path, torch_dtype=torch.float16, use_safetensors=True,
                            local_files_only=True, # Ensure it looks for local files
                            # The following line is crucial for loading single checkpoint files
                            # It assumes final_model_path points directly to the .safetensors file
                            checkpoint_file=os.path.basename(final_model_path)
                        ).to(device)
                    elif model_name == "sd15":
                        self.loaded_pipeline = StableDiffusionPipeline.from_pretrained(
                            final_model_path, torch_dtype=torch.float16, use_safetensors=False
                        ).to(device)
                    elif model_name == "flux":
                        logger.warning("Flux model loading is a placeholder. Ensure 'flux.py' provides the correct pipeline.")
                        self.loaded_pipeline = DiffusionPipeline.from_pretrained(
                            final_model_path, torch_dtype=torch.float16, use_safetensors=True
                        ).to(device)
                    elif model_name == "insc":
                        from InstantCharacter.pipeline import InstantCharacterFluxPipeline
                        self.loaded_pipeline = InstantCharacterFluxPipeline.from_pretrained(
                            final_model_path, torch_dtype=torch.bfloat16, use_safetensors=True
                        )
                        self.loaded_pipeline.to(device)
                        model_config = self.settings.MODEL_CONFIGS.get("INSC", {})
                        self.loaded_pipeline.init_adapter(
                            image_encoder_path=model_config.get("image_encoder_path"), 
                            image_encoder_2_path=model_config.get("image_encoder_2_path"), 
                            subject_ipadapter_cfg=dict(subject_ip_adapter_path=model_config.get("ip_adapter_path"), nb_token=1024), 
                        )
                    else:
                        # Attempt to load as a generic pipeline if type is unknown, assuming it's a path
                        self.loaded_pipeline = DiffusionPipeline.from_pretrained(
                            final_model_path, torch_dtype=torch.float16, use_safetensors=True
                        ).to(device)

                    self.loaded_model_name = model_name
                    logger.info(f"Successfully loaded base model: {model_name} from {final_model_path}")
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except (OSError, FileNotFoundError) as e:
                    # 文件系统错误或模型文件不存在
                    logger.error(f"[load_model_and_loras] 文件系统错误，加载模型失败 {model_name} from {final_model_path}: {e}", exc_info=True)
                    self.loaded_pipeline = None
                    self.loaded_model_name = None
                    raise
                except Exception as e:
                    # 其他异常（模型加载错误等）
                    logger.error(f"[load_model_and_loras] Failed to load model {model_name} from {final_model_path}: {e}", exc_info=True)
                    self.loaded_pipeline = None
                    self.loaded_model_name = None
                    raise

            logger.info(f"Model {self.loaded_model_name} loaded successfully. Preparing to load Lora(s): {loras}")
            if loras:
                for lora_info in loras:
                    lora_name = lora_info.get("name")
                    if not lora_name:
                        logger.warning("Lora info missing 'name' field, skipping")
                        continue
                    lora_weight = lora_info.get("weight", 1.0)
                    lora_id = self.get_lora_id(lora_name)
                    
                    lora_base_path = self.settings.MODEL_CONFIGS.get(self.loaded_model_name.upper(), {}).get("lora", None)
                    if not lora_base_path:
                        logger.warning(f"No Lora path configured for model '{self.loaded_model_name}'. Skipping Lora loading.")
                        break
                    # 使用安全的路径拼接
                    lora_path = os.path.abspath(os.path.join(lora_base_path, f"{lora_name}.safetensors"))
                    logger.info(f"Preparing to load Lora: {lora_id} with weight {lora_weight} from {lora_path}")
                    if lora_id and lora_path and lora_id not in self.loaded_loras:
                        final_lora_path = lora_path
                        if not os.path.exists(lora_path):
                            raise FileNotFoundError(f"Lora not found ")
                        try:
                            # Load Lora weights. This assumes the pipeline supports load_lora_weights.
                            # The actual method might vary based on the diffusers version and pipeline.
                            if hasattr(self.loaded_pipeline, 'load_lora_weights'):
                                logger.info(f"Loading Lora weights for {lora_id} from {final_lora_path}")
                                self.loaded_pipeline.load_lora_weights(final_lora_path, adapter_name=lora_id)
                                self.loaded_pipeline.set_adapters([lora_id], adapter_weights=[lora_weight])
                                logger.info(f"Successfully loaded Lora: {lora_id} from {final_lora_path} with weight {lora_weight}")
                                self.loaded_loras[lora_id] = lora_weight
                            else:
                                logger.warning(f"Pipeline does not support direct Lora loading via 'load_lora_weights'. Simulating loading Lora: {lora_id} with weight {lora_weight}")
                                self.loaded_loras[lora_id] = lora_weight # Still track it as loaded
                        except (SystemExit, KeyboardInterrupt):
                            # 系统退出异常，不捕获，直接抛出
                            raise
                        except (OSError, FileNotFoundError) as e:
                            # 文件系统错误或Lora文件不存在
                            logger.error(f"[load_model_and_loras] 文件系统错误，加载Lora失败 {lora_id} from {final_lora_path}: {e}", exc_info=True)
                            raise
                        except Exception as e:
                            # 其他异常（Lora加载错误等）
                            logger.error(f"[load_model_and_loras] Failed to load Lora {lora_id} from {final_lora_path}: {e}", exc_info=True)
                            raise
                    elif lora_id in self.loaded_loras and not self.loaded_loras[lora_id] == lora_weight:
                        logger.warning(f"Lora {lora_id} already loaded with different weight {self.loaded_loras.get(lora_id, 'not set')}. Updating to {lora_weight}.")
                        if hasattr(self.loaded_pipeline, 'set_adapters'):
                            self.loaded_pipeline.set_adapters([lora_id], adapter_weights=[lora_weight])
                            self.loaded_loras[lora_id] = lora_weight
                            logger.info(f"Updated Lora {lora_id} weight to {lora_weight}.")
                    else:
                        logger.info(f"Lora {lora_id} already loaded with weight {self.loaded_loras.get(lora_id, 'not set')}. Skipping.")
                    

            # Unload any Lora that are no longer needed
            target_lora_ids = {self.get_lora_id(l.get("name")) for l in (loras or []) if l.get("name")}
            loras_to_unload = [
                lora_id for lora_id in self.loaded_loras.keys()
                if lora_id not in target_lora_ids
            ]
            if loras_to_unload:
                logger.info(f"Unloading Lora(s): {loras_to_unload} that are no longer needed. Currently loaded: {list(self.loaded_loras.keys())}")
                for lora_id in loras_to_unload:
                    try:
                        logger.info(f"Unloading Lora: {lora_id}")
                        if self.loaded_pipeline and hasattr(self.loaded_pipeline, 'delete_adapters'):
                            self.loaded_pipeline.delete_adapters(lora_id)
                        else:
                            logger.warning(f"Pipeline does not support direct Lora unloading. Simulating unloading Lora: {lora_id}")
                        del self.loaded_loras[lora_id]
                    except (SystemExit, KeyboardInterrupt):
                        # 系统退出异常，不捕获，直接抛出
                        raise
                    except Exception as e:
                        # 其他异常（Lora卸载错误等）
                        logger.error(f"[load_model_and_loras] Failed to unload Lora {lora_id}: {e}", exc_info=True)
                logger.info(f"Lora unloading completed. Currently loaded: {list(self.loaded_loras.keys())}")
            torch.cuda.empty_cache()

            return self.loaded_pipeline
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（模型和Lora加载错误等）
            logger.error(f"[load_model_and_loras] Error loading model and Lora(s): {e}", exc_info=True)
            # 清理资源
            self._cleanup_resources()
            raise
                

    def _are_loras_loaded(self, target_loras: Optional[List[Dict[str, Any]]]):
        if not target_loras and not self.loaded_loras:
            return True
        if not target_loras or len(target_loras) != len(self.loaded_loras):
            return False
        all_lora_ids = {self.get_lora_id(lora_info.get("name")) for lora_info in target_loras}
        all_lora_loaded_ids = {name for name in self.loaded_loras.keys()}
        if len(set(all_lora_ids) & set(all_lora_loaded_ids)) != len(all_lora_ids):
            logger.info(f"Loaded Lora IDs: {all_lora_loaded_ids}, Target Lora IDs: {all_lora_ids}")
            return False
        for lora_info in target_loras:
            lora_name = lora_info.get("name")
            lora_id = self.get_lora_id(lora_name)
            lora_weight = lora_info.get("weight", 1.0)
            if lora_id not in self.loaded_loras or self.loaded_loras[lora_id] != lora_weight:
                return False
        
        return True

    def get_loaded_pipeline(self):
        return self.loaded_pipeline

    def get_loaded_model_name(self):
        return self.loaded_model_name
    
    def _cleanup_resources(self):
        """
        清理已加载的模型和 Lora，释放 GPU 内存。
        在错误处理或模型切换时调用。
        """
        try:
            if self.loaded_pipeline:
                self.loaded_pipeline.to("cpu")  # Move to CPU to free up GPU memory
                del self.loaded_pipeline
            self.loaded_pipeline = None
            self.loaded_model_name = None
            self.loaded_loras = {}
            if torch.cuda.is_available():
                torch.cuda.empty_cache()  # Clear GPU memory
            logger.info("Model and Lora resources cleaned up successfully")
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（资源清理错误等）
            logger.error(f"[_cleanup_resources] Failed to cleanup model and Lora resources: {e}", exc_info=True)
    
    def __del__(self):
        """析构函数，确保资源被正确清理"""
        try:
            self._cleanup_resources()
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception:
            # 其他异常（析构函数中的错误，忽略以避免影响程序退出）
            pass