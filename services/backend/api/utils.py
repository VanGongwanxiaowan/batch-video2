import asyncio
import base64
import os
import random
import shutil
import tempfile
import uuid
from datetime import timedelta
from io import BytesIO
from typing import Dict, List, Optional

import httpx
from db.models import User
from db.session import get_db
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from ossutils import OssManager
from passlib.context import CryptContext
from schema.account import TokenData
from schema.utils import (
    AIImageModelName,
    AiImageRequest,
    AiImageResponse,
    DrawTextRequest,
    DrawTextResponse,
    FluxDrawImageRequest,
    FluxDrawImageResponse,
)
from sqlalchemy.orm import Session
from worker.clients import ai_image_client
from worker.clients.flux_client import generate_image
from worker.utils.cover_draw_text import draw_text_for_api

from config import settings
from core.config.constants import APIConfig
from core.logging_config import setup_logging

logger = setup_logging("backend.api.utils", log_to_file=False)

# 从环境变量或配置文件中获取密钥
SECRET_KEY = settings.ACCESS_SECRET
HUMAN_VIDEO_DIR = settings.assets_path

ALGORITHM = "HS256"
# 从配置获取JWT过期时间，默认7天（而不是2年）
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌
    
    Args:
        data: 要编码到令牌中的数据字典
        expires_delta: 可选的过期时间增量
        
    Returns:
        str: 编码后的JWT令牌字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    从JWT令牌中获取当前登录用户
    
    Args:
        token: JWT访问令牌（通过OAuth2依赖注入）
        db: 数据库会话对象
        
    Returns:
        User: 当前登录的用户对象
        
    Raises:
        HTTPException: 401 如果令牌无效、过期或用户不存在
        
    Note:
        - 使用OAuth2PasswordBearer进行令牌提取
        - 支持user_uuid和user_id两种字段名
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_uuid")
        if not user_id:
            user_id = payload.get("user_id")
        if username is None or user_id is None:
            raise credentials_exception
        token_data = TokenData(username=username, user_id=user_id)
    except JWTError as e:
        raise credentials_exception
    user = db.query(User).filter(User.user_id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    return user


utils_router = APIRouter()

@utils_router.post("/upload", summary="上传图片文件")
def upload_logo(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    typ: str = Query("logo", description="上传类型，logo或cover")
) -> Dict[str, str]:
    """上传图片文件到OSS
    
    Args:
        file: 上传的文件
        db: 数据库会话
        typ: 上传类型，logo或cover
        
    Returns:
        包含uploadkey和url的字典
        
    Raises:
        HTTPException: 如果上传失败
    """
    try:
        # 验证文件类型
        file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        if file_ext not in APIConfig.ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {file_ext}，允许的类型: {', '.join(APIConfig.ALLOWED_IMAGE_EXTENSIONS)}"
            )
        
        # 验证文件大小（限制为10MB）
        file.file.seek(0, 2)  # 移动到文件末尾
        file_size = file.file.tell()
        file.file.seek(0)  # 重置到开头
        
        if file_size > APIConfig.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件大小超过限制: {file_size} bytes，最大允许: {APIConfig.MAX_FILE_SIZE} bytes"
            )
        
        uploadkey = f"stored/{f"{typ}_" if typ else ''}{uuid.uuid4().hex}{file_ext}"
        oss_util = OssManager()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp:
            temp_path = temp.name
            try:
                shutil.copyfileobj(file.file, temp)
                temp.flush()
                oss_util.upload(temp_path, uploadkey)
                logger.info(f"File uploaded successfully: {uploadkey}")
            finally:
                # 确保临时文件被删除
                if os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except OSError as e:
                        logger.warning(f"Failed to delete temporary file: {temp_path}, error: {e}")
        
        return {"uploadkey": uploadkey, "url": oss_util.get_sign_url(uploadkey)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传失败"
        )


@utils_router.post("/upload_human_video", summary="上传数字人视频")
def upload_human_video(file: UploadFile = File(...), account_name: str = Form(...)) -> Dict[str, str]:
    """上传数字人视频文件
    
    Args:
        file: 上传的视频文件
        account_name: 账号名称
        
    Returns:
        包含成功消息的字典
        
    Raises:
        HTTPException: 如果上传失败
    """
    try:
        # 验证账号名称（防止路径遍历）
        if not account_name or '/' in account_name or '\\' in account_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的账号名称"
            )
        
        # 验证文件扩展名
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名不能为空"
            )
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {file_extension}，允许的类型: {', '.join(allowed_extensions)}"
            )
        
        human_video_dir = HUMAN_VIDEO_DIR
        if not os.path.exists(human_video_dir):
            os.makedirs(human_video_dir, exist_ok=True)
        
        video_path = os.path.join(human_video_dir, f"{account_name}{file_extension}")
        
        # 验证路径安全（防止路径遍历）
        real_path = os.path.realpath(video_path)
        real_dir = os.path.realpath(human_video_dir)
        if not real_path.startswith(real_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件路径"
            )
        
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Human video uploaded successfully: {video_path}")
        return {"message": "Human video uploaded successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Human video upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="视频上传失败"
        )


@utils_router.get("/preview_human_video", summary="预览数字人视频")
def preview_human_video(account_name: str = Query(..., description="账号名称")) -> FileResponse:
    """预览数字人视频文件
    
    Args:
        account_name: 账号名称
        
    Returns:
        FileResponse: 视频文件响应
        
    Raises:
        HTTPException: 如果视频文件不存在
    """
    try:
        # 验证账号名称（防止路径遍历）
        if not account_name or '/' in account_name or '\\' in account_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的账号名称"
            )
        
        human_video_dir = HUMAN_VIDEO_DIR
        
        # Find the video file with any extension
        video_path = None
        allowed_extensions = [".mp4", ".mov", ".avi", ".mkv"]
        for ext in allowed_extensions:
            path = os.path.join(human_video_dir, f"{account_name}{ext}")
            # 验证路径安全
            real_path = os.path.realpath(path)
            real_dir = os.path.realpath(human_video_dir)
            if real_path.startswith(real_dir) and os.path.exists(path):
                video_path = path
                break
                
        if not video_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Video not found"
            )
            
        return FileResponse(video_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview human video failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="预览视频失败"
        )


@utils_router.get("/files", summary="获取文件链接")
def get_file_url(uploadkey: str = Query(..., description="上传的文件key")) -> Dict[str, str]:
    oss_util = OssManager()
    url = oss_util.get_sign_url(uploadkey)
    return {"url": url}


@utils_router.post("/drawtext", summary="封面绘制")
def draw_text_on_image(
    request: DrawTextRequest = Body(..., description="绘制文本请求"),
) -> DrawTextResponse:
    response = draw_text_for_api(request)
    return DrawTextResponse(
        output_image=response,
    )


@utils_router.get("/loras")
def list_loras() -> List[str]:
    return [
        "中国老人人像-realistic,full view",
        "国风绘本插图画风加强-guofeng",
        "乡村悬疑风格画风-hyh",
        "精炼小说民间悬疑画风",
        "历史人物小说推文场景插画",
        "淘气小孩童年回忆-pl",
        "农村小孩旧时光-rural_children",
    ]

@utils_router.post("/flux", summary="绘图")
def flux_draw_image(request: FluxDrawImageRequest) -> FluxDrawImageResponse:
    # PIL Image
    image = generate_image(
        prompt=request.prompt,
        num_inference_steps=30,
        width=request.width,
        height=request.height,
        lora_name=request.loraname,
        lora_step=request.lorastep,
    )
    # get base64 from pil image
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue())
    return FluxDrawImageResponse(
        outputimage=img_str
    )

@utils_router.post("/aiimage", summary="在线绘图")
async def aiimage(request: AiImageRequest) -> AiImageResponse:
    model_name = request.model
    topic = "online_task"
    prompt = request.prompt
    # if AIImageModelName.is_flux(model_name):
    #     topic = "flux_tasks"
    # elif AIImageModelName.is_sd15(model_name):
    #     topic = "sd15_tasks"
    # elif AIImageModelName.is_sdxl(model_name):
    #     topic = "sdxl_tasks"
    # else:
    #     return AiImageResponse(code=500, outputimage="")
    loras = []
    if request.loraname:
        loras = [{
            "name": request.loraname,
            "weight": request.loraweight / 100
        }]
        prefix = ai_image_client.get_prefix(loras, prompt)
        if prefix:
            prompt = prefix + prompt

    negative_prompt = "blurry, low quality"
    image_params = {"width": request.width, "height": request.height, "steps": 30, "cfg_scale": 3.5, "seed": -1, "batch_size": 1}
    if request.subject_image:
        image_params["subject_image"] = request.subject_image
        image_params["subject_scale"] = request.subject_scale

    data =  {
        "user_id": "test_user_" + str(random.randint(1, 1000)),
        "topic": topic, # Add topic to the request data
        "model_name": model_name,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "image_params": image_params,
        "loras": loras,
        "width": request.width,
        "height": request.height,
    }
    logger.debug(f"Image generation request: model={model_name}, topic={topic}")
    async with httpx.AsyncClient() as client:
        task_id, topic, model_name = await ai_image_client.submit_image_generation_task(client, topic, model_name, data)
        if task_id:
            # await ai_image_client.get_image_and_save(client, task_id, model_name)
            for i in range(APIConfig.IMAGE_GENERATION_MAX_RETRIES):
                await asyncio.sleep(APIConfig.IMAGE_GENERATION_RETRY_INTERVAL)
                status = await ai_image_client.check_task_status(client, task_id)
                if status and status.get("status") == "completed":
                    image_bytes = await ai_image_client.get_image(client, task_id)
                    img_str = base64.b64encode(image_bytes)
                    return AiImageResponse(code=200, outputimage=img_str)
        else:
            logger.error("Image generation task_id is None, request failed")
            return AiImageResponse(code=500, outputimage="")
