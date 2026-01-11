# backend/app/utils/file_storage.py
import os
import tempfile
import time  # Import time for retry delays
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse

import oss2

from core.config.constants import FileConfig, OSSConfig, RetryConfig
from core.logging_config import setup_logging


class FileStorage:
    def __init__(self, settings: Any) -> None:
        """初始化文件存储
        
        Args:
            settings: 配置对象
        """
        self.oss_endpoint = settings.OSS_ENDPOINT
        self.oss_access_key_id = settings.OSS_ACCESS_KEY_ID
        self.oss_access_key_secret = settings.OSS_ACCESS_KEY_SECRET
        self.oss_bucket_name = settings.OSS_BUCKET_NAME
        
        # 初始化日志记录器
        self.logger = setup_logging("worker.utils.oss_file_utils", log_to_file=False)
        
        # 初始化OSS客户端
        self.auth = oss2.Auth(self.oss_access_key_id, self.oss_access_key_secret)
        self.bucket = oss2.Bucket(self.auth, self.oss_endpoint, self.oss_bucket_name)
        self.logger.info(f"FileStorage initialized with OSS Endpoint: {self.oss_endpoint}, Bucket: {self.oss_bucket_name}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除路径遍历字符，防止安全漏洞。
        
        Args:
            filename: 原始文件名
            
        Returns:
            str: 清理后的文件名
            
        Raises:
            ValueError: 如果文件名无效
        """
        if not filename:
            raise ValueError("filename cannot be empty")
        
        # 移除路径分隔符和特殊字符，只保留文件名部分
        filename = os.path.basename(filename)  # 只保留文件名部分
        filename = filename.replace("..", "").replace("/", "").replace("\\", "")
        filename = filename.replace("\x00", "")  # 移除空字符
        
        if not filename:
            raise ValueError("filename is invalid after sanitization")
        
        # 限制文件名长度（避免过长的文件名）
        if len(filename) > FileConfig.MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(filename)
            filename = name[:FileConfig.MAX_FILENAME_LENGTH - len(ext)] + ext
        
        return filename

    def upload_file(self, file_content, filename: str = None) -> tuple[str, str]:
        """
        上传文件到阿里云OSS。
        
        :param file_content: 文件的二进制内容或本地文件路径
        :param filename: 原始文件名，将作为OSS上的key
        :return: (上传后的文件URL, OSS key)
        
        Raises:
            ValueError: 如果filename为空或包含非法字符
        """
        if not filename:
            raise ValueError("filename 不能为空。")
        
        # 清理文件名，防止路径遍历攻击
        filename = self._sanitize_filename(filename)

        # 生成一个唯一的key，例如使用UUID
        unique_id = uuid.uuid4().hex
        # 提取文件名和扩展名
        name, ext = os.path.splitext(filename)
        remote_file_key = f"uploads/{name}_{unique_id}{ext}"
        
        # 使用配置常量
        for attempt in range(RetryConfig.MAX_RETRIES):
            try:
                if isinstance(file_content, str) and os.path.exists(file_content):
                    self.logger.debug(f'上传文件 (尝试 {attempt + 1}/{RetryConfig.MAX_RETRIES})')
                    self.bucket.put_object_from_file(remote_file_key, file_content)
                elif isinstance(file_content, (str, bytes)):
                    self.logger.debug(f'上传二进制文件内容 (尝试 {attempt + 1}/{RetryConfig.MAX_RETRIES})')
                    if isinstance(file_content, str):
                        file_content = file_content.encode('utf-8')
                    self.bucket.put_object(remote_file_key, file_content)
                else:
                    raise TypeError("file_content 必须是文件路径字符串、字符串内容或二进制内容。")            
                self.logger.info(f"文件上传成功: {remote_file_key}")
                return remote_file_key
            except oss2.exceptions.OssError as e:
                self.logger.warning(f"OSS上传文件失败 (尝试 {attempt + 1}/{RetryConfig.MAX_RETRIES}): {e}")
                if attempt < RetryConfig.MAX_RETRIES - 1:
                    # 使用指数退避，但限制最大延迟
                    delay = min(
                        RetryConfig.BASE_DELAY_SECONDS ** attempt,
                        RetryConfig.MAX_DELAY_SECONDS
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"OSS上传文件失败，已达到最大重试次数: {e}")
                    raise # Re-raise the exception after max retries

    def download_file(self, remote_path: str, local_file_path: str = None) -> str:
        """
        从阿里云OSS下载文件。
        :param remote_path: 对象存储中的文件URL或OSS key
        :param local_file_path: 本地保存路径。如果为None，则下载到临时文件。
        :return: 下载后的本地文件路径
        """
        if remote_path.startswith("http://") or remote_path.startswith("https://"):
            parsed_url = urlparse(remote_path)
            oss_key = unquote(parsed_url.path.lstrip('/'))
        else:
            oss_key = remote_path

        if not oss_key:
            raise ValueError("remote_path 格式不正确或为空，无法提取OSS key。")

        if local_file_path is None:
            # 从OSS key中提取文件名作为本地文件名
            filename = os.path.basename(oss_key)
            local_file_path = os.path.join(tempfile.gettempdir(), filename)
        
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

        try:
            self.bucket.get_object_to_file(oss_key, local_file_path)
            self.logger.info(f"文件 '{oss_key}' 已下载到 '{local_file_path}'")
            return local_file_path
        except oss2.exceptions.OssError as e:
            self.logger.error(f"OSS下载文件失败: {e}")
            raise
    
    def gen_tmp_url(self, key: str, expiration: int = OSSConfig.DEFAULT_URL_EXPIRATION) -> str:
        """
        生成OSS文件的临时签名URL。
        
        Args:
            key: OSS文件在Bucket中的key
            expiration: URL的有效期，单位秒，默认使用配置常量（1小时）
                       最大不超过24小时
            
        Returns:
            str: 临时签名URL
            
        Raises:
            oss2.exceptions.OssError: 如果生成URL失败
        """
        # 限制最大过期时间
        if expiration > OSSConfig.MAX_URL_EXPIRATION:
            expiration = OSSConfig.MAX_URL_EXPIRATION
            self.logger.warning(
                f"URL过期时间超过最大值，已限制为{OSSConfig.MAX_URL_EXPIRATION}秒"
            )
        
        try:
            # 生成签名URL，用于私有Bucket的临时访问
            signed_url = self.bucket.sign_url('GET', key, expiration)
            return signed_url
        except oss2.exceptions.OssError as e:
            self.logger.error(f"生成临时URL失败: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    # 模拟 settings
    from config import settings

    file_storage = FileStorage(settings)

    

    # --- 测试 upload_file ---
    test_content = str(settings.assets_path / "ref.wav")
    test_filename = "ref.wav" # 修改测试文件名以避免冲突
    uploaded_key = file_storage.upload_file(test_content, test_filename)
    file_storage.logger.info(f"测试上传结果: {uploaded_key}")
    

    test_content = str(settings.assets_path / "log.png")
    test_filename = "log.png" # 修改测试文件名以避免冲突
    uploaded_key = file_storage.upload_file(test_content, test_filename)
    file_storage.logger.info(f"测试上传结果: {uploaded_key}")
