"""任务数据准备器

负责从数据库查询和准备任务执行所需的所有数据。
"""

from typing import Any, Dict, Optional

from db.models import Account, Job, Language, Topic, Voice
from sqlalchemy.orm import Session

from core.logging_config import setup_logging

logger = setup_logging("worker.job_processing.data_preparer")


class JobDataPreparer:
    """任务数据准备器
    
    负责准备任务执行所需的所有数据，包括：
    - 语言和平台信息
    - 主题和提示词
    - 账号和Logo信息
    - 音色和参考音频
    - LoRA配置
    """
    
    def __init__(self, file_storage: Any) -> None:
        """
        初始化数据准备器
        
        Args:
            file_storage: 文件存储服务实例（用于下载OSS文件）
        """
        self.file_storage = file_storage
    
    def prepare_job_data(self, db: Session, job: Job) -> Dict[str, Any]:
        """
        准备任务执行所需的所有数据
        
        Args:
            db: 数据库会话
            job: 任务对象
            
        Returns:
            包含所有准备数据的字典
        """
        logger.info(f"[prepare_job_data] 开始准备任务数据 job_id={job.id}")
        
        data = {}
        
        # 准备语言信息
        data['language_name'] = job.language.language_name if job.language else "未知语言"
        data['language_platform'] = job.language.platform if job.language else "edge"
        logger.info(f"[prepare_job_data] 语言信息 job_id={job.id}, language={data['language_name']}, platform={data['language_platform']}")
        
        # 准备主题信息
        topic_prompts = db.query(Topic).filter(Topic.id == job.topic_id).first()
        data['topic_prompts'] = topic_prompts
        data['prompt_gen_images'] = topic_prompts.prompt_gen_image if topic_prompts else ""
        data['prompt_prefix'] = topic_prompts.prompt_image_prefix if topic_prompts else ""
        data['prompt_cover_image'] = topic_prompts.prompt_cover_image if topic_prompts else ""
        logger.info(f"[prepare_job_data] 主题信息 job_id={job.id}, prompt_gen_images长度={len(data['prompt_gen_images'])}")
        
        # 准备账号信息
        account_logo = db.query(Account).filter(Account.id == job.account_id).first()
        data['account'] = account_logo
        
        # 准备LoRA配置
        loraname = topic_prompts.loraname if topic_prompts else None
        loraweight = topic_prompts.loraweight if topic_prompts else 0
        data['loras'] = []
        if loraname:
            data['loras'] = [{"name": loraname, "weight": loraweight / 100}]
            logger.info(f"[prepare_job_data] LoRA配置 job_id={job.id}, loraname={loraname}, loraweight={loraweight}")
        
        # 准备Logo路径
        if account_logo and account_logo.logo:
            logger.info(f"[prepare_job_data] 下载Logo文件 job_id={job.id}, logo_oss_path={account_logo.logo}")
            data['logopath'] = self.file_storage.download_file(account_logo.logo)
            logger.info(f"[prepare_job_data] Logo文件下载成功 job_id={job.id}, local_path={data['logopath']}")
        else:
            data['logopath'] = None
            logger.info(f"[prepare_job_data] 未配置Logo文件 job_id={job.id}")
        
        # 准备参考音频路径
        if job.voice and job.voice.path:
            logger.info(f"[prepare_job_data] 下载参考音频 job_id={job.id}, voice_path={job.voice.path}")
            data['reference_audio_path'] = self.file_storage.download_file(job.voice.path)
            logger.info(f"[prepare_job_data] 参考音频下载成功 job_id={job.id}, local_path={data['reference_audio_path']}")
        else:
            data['reference_audio_path'] = None
            logger.info(f"[prepare_job_data] 未配置参考音频 job_id={job.id}")
        
        # 准备其他任务属性
        data['description'] = job.description
        data['speech_speed'] = job.speech_speed
        data['is_horizontal'] = job.is_horizontal
        
        logger.info(f"[prepare_job_data] 任务数据准备完成 job_id={job.id}")
        return data

