"""文件上传器

负责将生成的文件上传到OSS并更新任务结果。
"""

import json
import os
from typing import Any, Dict, Optional, Tuple

from db.models import Job

from core.exceptions import ServiceException
from core.logging_config import setup_logging

logger = setup_logging("worker.job_processing.file_uploader")


class FileUploader:
    """文件上传器
    
    负责上传生成的文件到OSS，并更新任务的job_result_key。
    """
    
    def __init__(self, file_storage: Any) -> None:
        """
        初始化文件上传器
        
        Args:
            file_storage: 文件存储服务实例
        """
        self.file_storage = file_storage
    
    def _upload_single_file(
        self,
        job_id: int,
        local_path: Optional[str],
        file_type: str,
        file_name: str,
        job_result_key_data: Dict[str, str],
    ) -> None:
        """
        上传单个文件到OSS（通用方法）
        
        Args:
            job_id: 任务ID
            local_path: 本地文件路径
            file_type: 文件类型（用于生成OSS key前缀，如 "videos", "images"）
            file_name: 文件名（用于生成OSS key）
            job_result_key_data: 结果字典，用于存储上传后的OSS key
        """
        if not local_path or not os.path.exists(local_path):
            logger.debug(f"[_upload_single_file] 文件不存在，跳过上传 job_id={job_id}, file_type={file_type}, file_name={file_name}")
            return
        
        oss_key = f"{file_type}/{job_id}/{file_name}_{os.path.basename(local_path)}"
        logger.info(f"[_upload_single_file] 开始上传文件 job_id={job_id}, local_path={local_path}, oss_key={oss_key}")
        
        try:
            uploaded_key = self.file_storage.upload_file(local_path, oss_key)
            job_result_key_data[f"{file_type}_{file_name}_oss_key"] = uploaded_key
            logger.info(f"[_upload_single_file] 文件上传成功 job_id={job_id}, oss_key={uploaded_key}")
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (OSError, PermissionError, FileNotFoundError) as e:
            # 文件系统错误
            logger.error(f"[_upload_single_file] 文件系统错误 job_id={job_id}, local_path={local_path}, error={e}", exc_info=True)
            raise
        except ServiceException as e:
            # OSS上传服务错误
            logger.error(f"[_upload_single_file] OSS上传失败 job_id={job_id}, oss_key={oss_key}, error={e}", exc_info=True)
            raise
        except Exception as e:
            # 其他异常（OSS上传错误等）
            logger.error(f"[_upload_single_file] 文件上传失败 job_id={job_id}, oss_key={oss_key}, error={e}", exc_info=True)
            raise ServiceException(f"文件上传失败: {e}")
    
    def upload_generated_files(
        self,
        job: Job,
        logoed_video_path: Optional[str],
        subtitled_video_path: Optional[str],
        cover_image_path: Optional[str],
        combined_video: Optional[str],
        srtpath: Optional[str],
        seedvc_mp3_audio: Optional[str],
    ) -> Dict[str, str]:
        """
        上传所有生成的文件到OSS
        
        Args:
            job: 任务对象
            logoed_video_path: Logo视频路径
            subtitled_video_path: 字幕视频路径
            cover_image_path: 封面图片路径
            combined_video: 合并视频路径
            srtpath: 字幕文件路径
            seedvc_mp3_audio: 音频文件路径
            
        Returns:
            包含所有上传文件OSS key的字典
        """
        logger.info(f"[upload_generated_files] 开始上传文件 job_id={job.id}")
        
        # 加载已有的job_result_key或初始化
        if job.job_result_key:
            job_result_key_data = json.loads(job.job_result_key)
            logger.info(f"[upload_generated_files] 加载已有job_result_key job_id={job.id}")
        else:
            job_result_key_data = {}
            logger.info(f"[upload_generated_files] 初始化job_result_key_data job_id={job.id}")
        
        # 定义需要上传的文件列表（文件路径, 文件类型, 文件名, 结果key名称）
        files_to_upload = [
            (logoed_video_path, "videos", "logoed", "logoed_video"),
            (subtitled_video_path, "videos", "subtitled", "subtitled_video"),
            (cover_image_path, "videos", "cover", "cover"),
            (combined_video, "videos", "combined", "combined_video"),
            (srtpath, "videos", "subtitles", "srt"),
            (seedvc_mp3_audio, "videos", "audio", "audio"),
        ]
        
        # 批量上传文件
        for local_path, file_type, file_name, result_key in files_to_upload:
            if local_path:
                self._upload_single_file(
                    job_id=job.id,
                    local_path=local_path,
                    file_type=file_type,
                    file_name=file_name,
                    job_result_key_data=job_result_key_data,
                )
                # 更新结果key名称（如果需要不同的命名）
                if result_key != file_name:
                    old_key = f"{file_type}_{file_name}_oss_key"
                    new_key = f"{result_key}_oss_key"
                    if old_key in job_result_key_data:
                        job_result_key_data[new_key] = job_result_key_data.pop(old_key)
        
        logger.info(f"[upload_generated_files] 文件上传完成 job_id={job.id}")
        return job_result_key_data
    
    def validate_uploaded_files(self, job_result_key_data: Dict[str, str]) -> bool:
        """
        验证上传的文件是否包含必要的文件
        
        Args:
            job_result_key_data: 上传文件的OSS key字典
            
        Returns:
            如果包含必要文件返回True，否则返回False
        """
        has_logoed = bool(job_result_key_data.get("logoed_video_oss_key"))
        has_subtitled = bool(job_result_key_data.get("subtitled_video_oss_key"))
        
        logger.info(
            f"[validate_uploaded_files] 验证上传文件 "
            f"has_logoed={has_logoed}, has_subtitled={has_subtitled}"
        )
        
        return has_logoed and has_subtitled

