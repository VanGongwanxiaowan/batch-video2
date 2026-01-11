# Pydantic schemas for API request and response validation
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ImageParams(BaseModel):
    width: int = Field(512, description="Width of the generated image.")
    height: int = Field(512, description="Height of the generated image.")
    steps: int = Field(20, description="Number of diffusion steps.")
    sampler: str = Field("DPM++ 2M Karras", description="Sampler to use.")
    cfg_scale: float = Field(7.0, description="Classifier-free guidance scale.")
    seed: int = Field(-1, description="Random seed for reproducibility. -1 for random.")
    batch_size: int = Field(1, description="Number of images to generate in a batch.")
    subject_image: str = Field('', description="Base64Str to the subject image.")
    subject_scale: float = Field(0.9, description="Subject image scale.")

class ImageGenerationRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user submitting the request.")
    topic: str = Field(..., description="Kafka topic to send the task to (e.g., 'sdxl_tasks', 'sd15_tasks', 'flux_tasks', 'online_task').")
    model_name: str = Field(..., description="Name of the Stable Diffusion model to use (e.g., 'sdxl', 'sd15', 'flux', 'insc').")
    loras: Optional[List[Dict[str, Any]]] = Field(None, description="List of Lora models to apply, with their weights.")
    prompt: str = Field(..., description="Text prompt for image generation.")
    negative_prompt: Optional[str] = Field(None, description="Negative text prompt.")
    image_params: ImageParams = Field(default_factory=ImageParams, description="Image generation parameters.")

class TaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="Unique ID of the submitted task.")
    status: str = Field(..., description="Current status of the task (e.g., 'queued', 'processing', 'completed', 'failed').")
    image_url: Optional[str] = Field(None, description="URL of the generated image, if completed.")
    error_message: Optional[str] = Field(None, description="Error message if the task failed.")