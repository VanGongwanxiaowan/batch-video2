from enum import Enum

from pydantic import BaseModel


class ImageText(BaseModel):
    text: str
    color: list[int] = [255, 255, 255]  # RGB color
    size: int = 20  # Default font size

class DrawTextRequest(BaseModel):
    texts: list[ImageText] = []
    input_image: str  # Path to the input image
    language: str  # Language of the text
    usetraditional: bool = False  # Use traditional Chinese characters if true

class DrawTextResponse(BaseModel):
    output_image: str  # Path to the output image with text drawn

class FluxDrawImageRequest(BaseModel):
    prompt: str = ""
    width: int = 1360
    height: int = 768
    loraname: str = ""
    lorastep: int = 100

class FluxDrawImageResponse(BaseModel):
    outputimage: str  # Path to the output image with text drawn


class AIImageModelName(str, Enum):
    FLUX = "flux"
    SD15 = "sd15"
    SDXL = "SDXL"
    
    @classmethod
    def is_flux(cls, value: str) -> bool:
        return value == cls.FLUX.value
    
    @classmethod
    def is_sd15(cls, value: str) -> bool:
        return value == cls.SD15.value
    
    @classmethod
    def is_sdxl(cls, value: str) -> bool:
        return value == cls.SDXL.value


class AiImageRequest(BaseModel):
    model: str = AIImageModelName.FLUX.value
    prompt: str = ""
    width: int = 1360
    height: int = 768
    loraname: str = ""
    loraweight: int = 100
    subject_image: str = ""
    subject_scale: float = 0.9


class AiImageResponse(BaseModel):
    outputimage: str = ''  # Path to the output image with text drawn
    code: int = 200