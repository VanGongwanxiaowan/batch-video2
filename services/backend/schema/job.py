from typing import Optional

from pydantic import BaseModel
from schema.job_split import JobSplit
from schema.language import Language as SchemaLanguage
from schema.topic import Topic
from schema.voice import Voice as SchemaVoice


class Job(BaseModel):
    id: int
    runorder: int = 0
    title: str
    content: str
    language_id: Optional[int] = None
    language: Optional[SchemaLanguage] = None
    voice_id: Optional[int] = 0
    voice: Optional[SchemaVoice] = None
    description: Optional[str] = ""
    publish_title: Optional[str] = ""
    speech_speed: float = 0.9
    topic_id: Optional[int] = None
    topic: Optional[Topic] = None
    job_splits: list[JobSplit] = []
    job_result_key: str = ""
    status: str = "待处理"
    is_horizontal: bool = True
    status_detail: Optional[str] = ""
    cover_base64: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    account_id: int | None = None
    extra: Optional[dict] = {}


class CreateJobRequest(BaseModel):
    title: str
    content: str
    runorder: int = 0
    language_id: Optional[int] = None
    voice_id: Optional[int] = None
    description: str = ""
    publish_title: str = ""
    status: str = "待处理"
    status_detail: str = ""
    account_id: int | None = None
    topic_id: Optional[int] = None
    speech_speed: float = 0.9
    job_result_key :str = ""
    is_horizontal: bool = True
    extra: Optional[dict] = {}

class CreateJobResponse(BaseModel):
    id: int

class ListJobRequest(BaseModel):
    page: int = 1
    page_size: int = 10
    status: str = "待处理"
    language_id: Optional[int] = None
    
class ListJobResponse(BaseModel):
    total: int
    items: list[Job]


class JobExtra(BaseModel):
    h2v: bool = False # 横屏转竖屏
    index_text: str = "" # 集数文字 上方第一条
    title_text: str = "" # 标题文字 上方第二条
    desc_text: str = "" # 描述文字 下方
    audio: str = ""
