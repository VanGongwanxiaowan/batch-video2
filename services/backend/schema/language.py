from typing import Optional

from pydantic import BaseModel


class Language(BaseModel):
    id: int
    name: str
    platform: Optional[str] = None
    language_name: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

class CreateLanguageRequest(BaseModel):
    name: str
    platform: Optional[str] = None
    language_name: Optional[str] = None

class CreateLanguageResponse(BaseModel):
    id: int

class UpdateLanguageRequest(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None
    language_name: Optional[str] = None

class UpdateLanguageResponse(BaseModel):
    id: int

class GetLanguageResponse(Language):
    pass

class ListLanguageResponse(BaseModel):
    total: int
    items: list[Language]

class DeleteLanguageResponse(BaseModel):
    id: int