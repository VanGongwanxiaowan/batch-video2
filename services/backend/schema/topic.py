from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Topic(BaseModel):
    id: int
    name: str
    prompt_gen_image: Optional[str] = None
    prompt_cover_image: Optional[str] = None
    prompt_image_prefix: Optional[str] = None
    prompt_l4: Optional[str] = None
    loraname: str = ""
    loraweight: int = 100
    extra: Optional[dict] = {}
    created_at: str
    updated_at: str

class CreateTopicRequest(BaseModel):
    name: str
    prompt_gen_image: Optional[str] = None
    prompt_cover_image: Optional[str] = None
    prompt_image_prefix: Optional[str] = None
    prompt_l4: Optional[str] = None
    loraname: str = ""
    loraweight: int = 100
    extra: Optional[dict] = {}

class CreateTopicResponse(BaseModel):
    id: int

class UpdateTopicRequest(BaseModel):
    name: Optional[str] = None
    prompt_gen_image: Optional[str] = None
    prompt_cover_image: Optional[str] = None
    prompt_image_prefix: Optional[str] = None
    prompt_l4: Optional[str] = None
    loraname: str = ""
    loraweight: int = 100
    extra: Optional[dict] = {}
    
class UpdateTopicResponse(BaseModel):
    id: int

class GetTopicResponse(Topic):
    pass

class ListTopicResponse(BaseModel):
    total: int
    items: list[Topic]

class DeleteTopicResponse(BaseModel):
    id: int