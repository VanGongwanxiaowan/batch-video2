from pydantic import BaseModel


class Voice(BaseModel):
    id: int
    name: str
    path: str
    
class CreateVoiceRequest(BaseModel):
    name: str
    path: str
    
class CreateVoiceResponse(BaseModel):
    id: int
    
class DeleteVoiceResponse(BaseModel):
    id: int

class ListVoiceRequest(BaseModel):
    page: int = 1
    page_size: int = 10

class ListVoiceResponse(BaseModel):
    total: int
    items: list[Voice]
