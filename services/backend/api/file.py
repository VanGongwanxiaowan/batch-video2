import uuid
from typing import Any, Dict

from db.session import get_db
from fastapi import APIRouter, Body, Depends, File, UploadFile
from sqlalchemy.orm import Session

file_router = APIRouter()

@file_router.post("/upload", summary="上传文件")
def upload_file(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    uploadkey = uuid.uuid4().hex
    suffix = file.name.split('.')[-1]
    