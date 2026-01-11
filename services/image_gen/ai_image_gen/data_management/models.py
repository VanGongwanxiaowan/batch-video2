"""SQLAlchemy 模型定义

使用统一的 core/db/session.Base 作为基类。
"""
import uuid

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

# 使用统一的 Base，确保所有模型使用同一个声明式基类
from core.db.session import Base


class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    version = Column(String(50))
    civitai_link = Column(String(512))
    local_path = Column(String(512))
    checksum = Column(String(128))
    last_used_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Model(name='{self.name}', version='{self.version}')>"

class Lora(Base):
    __tablename__ = "loras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    version = Column(String(50))
    civitai_link = Column(String(512))
    local_path = Column(String(512))
    checksum = Column(String(128))
    associated_model_type = Column(String(100)) # e.g., "sdxl", "sd15"
    last_used_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Lora(name='{self.name}', associated_model_type='{self.associated_model_type}')>"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4())) # UUID for task ID
    user_id = Column(String(255), nullable=False)
    model_name = Column(String(255), nullable=False)
    topic = Column(String(255), nullable=False) # Add topic field
    loras = Column(JSON) # Store Lora list as JSON
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text)
    image_params = Column(JSON) # Store image generation parameters as JSON
    status = Column(String(50), default="queued", index=True) # queued, processing, completed, failed
    image_url = Column(String(512))
    error_message = Column(Text)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Task(id='{self.id}', status='{self.status}', model='{self.model_name}')>"