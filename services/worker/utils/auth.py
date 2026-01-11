import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from db.models import User
from db.session import get_db
from fastapi import APIRouter, Body, Depends, File, HTTPException, Path, Query, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None

# 从环境变量或配置文件中获取密钥
SECRET_KEY = settings.ACCESS_SECRET

ALGORITHM = "HS256"
# 从配置获取JWT过期时间，默认7天（而不是2年）
from config import settings

ACCESS_TOKEN_EXPIRE_MINUTES = getattr(settings, 'JWT_ACCESS_TOKEN_EXPIRE_MINUTES', 60 * 24 * 7)  # 7天

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # print("SECRET_KEY", SECRET_KEY)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_uuid")
        if not user_id:
            user_id = payload.get("user_id")
        # print(payload)
        if username is None or user_id is None:
            raise credentials_exception
        token_data = TokenData(username=username, user_id=user_id)
    except JWTError as e:
        raise credentials_exception
    user = db.query(User).filter(User.user_id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    return user