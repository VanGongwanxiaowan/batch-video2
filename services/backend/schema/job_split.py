from typing import Optional

from pydantic import BaseModel
from schema.language import Language as SchemaLanguage
from schema.topic import Topic
from schema.voice import Voice as SchemaVoice


class JobSplit(BaseModel):
    job_id: int
    index: int
    start: int
    end: int
    text: str
    prompt: str = ""
    video: str = ""
    images: list[str] = []
    selected: str = ""
    
class ListJobSplitRequest(BaseModel):
    job_id: int

class ListJobSplitResponse(BaseModel):
    total: int
    items: list[JobSplit]

class UpdateJobSplitRequest(BaseModel):
    images: list[str] = []
    selected: str = ""
    prompt: str = ""