"""文件存储服务客户端

实现 IFileStorageService 接口，提供 OSS 文件存储功能。
"""
import os
from typing import Any, Dict, List, Optional

from core.interfaces.service_interfaces import (
    IFileStorageService,
    FileUploadResult,
    BatchUploadResult,
)
from core.logging_config import setup_logging

logger = setup_logging("core.clients.storage_client")


class StorageClient(IFileStorageService):
    """OSS 文件存储服务客户端

    实现 IFileStorageService 接口，提供 OSS 文件上传、下载功能。
    """

    def __init__(self, settings: Any):
        """初始化存储服务客户端

        Args:
            settings: 配置对象，包含 OSS 配置
        """
        from utils.oss_file_utils import FileStorage

        self._file_storage = FileStorage(settings)
        self.oss_manager = self._file_storage.bucket

    def upload_file(
        self,
        file_path: str,
        key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FileUploadResult:
        """上传单个文件（实现 IFileStorageService 接口）

        Args:
            file_path: 本地文件路径
            key: 存储的 key
            metadata: 元数据（当前不使用，保留用于扩展）

        Returns:
            FileUploadResult: 上传结果
        """
        try:
            if not os.path.exists(file_path):
                return FileUploadResult(
                    success=False,
                    file_key=key,
                    error_message=f"文件不存在: {file_path}"
                )

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 调用 OSS 上传
            result_key = self._file_storage.upload_file(file_path, key)

            logger.info(f"[StorageClient] 文件上传成功: {file_path} -> {result_key}")

            return FileUploadResult(
                success=True,
                file_key=result_key,
                url=None,  # OSS 私有 Bucket 不提供直接 URL
            )

        except Exception as e:
            logger.error(f"[StorageClient] 文件上传失败: {e}")
            return FileUploadResult(
                success=False,
                file_key=key,
                error_message=str(e)
            )

    def upload_batch(
        self,
        files: Dict[str, str],  # 文件类型 -> 文件路径
        prefix: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BatchUploadResult:
        """批量上传文件（实现 IFileStorageService 接口）

        Args:
            files: 文件字典 {文件类型: 文件路径}
            prefix: key 前缀
            metadata: 元数据

        Returns:
            BatchUploadResult: 批量上传结果
        """
        results = {}
        total_size = 0
        success_count = 0
        failed_count = 0

        for file_type, file_path in files.items():
            if not file_path or not os.path.exists(file_path):
                results[file_type] = FileUploadResult(
                    success=False,
                    file_key="",
                    error_message=f"文件不存在: {file_path}"
                )
                failed_count += 1
                continue

            # 构建 key
            key = f"{prefix}/{file_type}"

            # 上传文件
            result = self.upload_file(file_path, key, metadata)
            results[file_type] = result

            if result.success:
                success_count += 1
                total_size += os.path.getsize(file_path)
            else:
                failed_count += 1

        return BatchUploadResult(
            results=results,
            total_size=total_size,
            success_count=success_count,
            failed_count=failed_count,
        )

    def get_download_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> Optional[str]:
        """获取下载 URL（实现 IFileStorageService 接口）

        Args:
            key: 文件 key
            expires_in: 过期时间（秒）

        Returns:
            Optional[str]: 签名 URL
        """
        try:
            return self._file_storage.gen_tmp_url(key, expires_in)
        except Exception as e:
            logger.error(f"[StorageClient] 生成下载 URL 失败: {e}")
            return None

    def delete_file(self, key: str) -> bool:
        """删除文件（实现 IFileStorageService 接口）

        Args:
            key: 文件 key

        Returns:
            bool: 是否删除成功
        """
        try:
            self.oss_manager.delete_object(key)
            logger.info(f"[StorageClient] 文件删除成功: {key}")
            return True
        except Exception as e:
            logger.error(f"[StorageClient] 文件删除失败: {key}, error={e}")
            return False


__all__ = ["StorageClient"]
