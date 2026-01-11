from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Account(BaseModel):
    id: int
    username: str
    logo: str = ""
    platform: str = "youtube"
    area: str = ""
    created_at: str = ""
    updated_at: str = ""
    extra: Optional[dict] = {}

class AccountExtra(BaseModel):
    subtitle_background: str = "#578B2E"
    human_config: Optional[dict] = {"duration": 120, "end_duration": 120}
    enable_transition: bool = False
    transition_types: list[str] = ["fade"] # Changed to list for multiple selections
    human_insertion_mode: str = "fullscreen"
    enable_srt_concat_transition: bool = False
    srt_concat_transition_types: list[str] = ["fade"] # Changed to list for multiple selections

class CreateAccountRequest(BaseModel):
    username: str
    logo: str = ""
    area: str = ""
    platform: str = "youtube"
    extra: Optional[AccountExtra] = AccountExtra()

class CreateAccountResponse(BaseModel):
    id: int


class ListAccountRequest(BaseModel):
    page: int = 1
    page_size: int = 10


class ListAccountResponse(BaseModel):
    total: int
    items: list[Account]


class UpdateAccountRequest(BaseModel):
    username: str
    logo: str = ""
    area: str = ""
    extra: Optional[AccountExtra] = AccountExtra()


class UpdateAccountResponse(BaseModel):
    id: int


class DeleteAccountResponse(BaseModel):
    id: int


class GetAccountResponse(BaseModel):
    id: int
    username: str
    logo: str = ""
    area: str = ""
    created_at: str = ""
    updated_at: str = ""
    extra: Optional[dict] = {}


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserLogin(UserBase):
    password: str


class UserSync(BaseModel):
    id: str
    username: str
    password: str

class User(UserBase):
    user_id: str
    created_at: datetime
    last_login_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
