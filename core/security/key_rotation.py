"""密钥轮换模块

提供密钥管理和自动轮换功能。
"""
import base64
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.logging_config import get_logger

logger = get_logger(__name__)


class KeyType(str, Enum):
    """密钥类型"""
    JWT = "jwt"
    ENCRYPTION = "encryption"
    API = "api"
    DATABASE = "database"
    OAUTH = "oauth"
    WEBHOOK = "webhook"


@dataclass
class KeyMetadata:
    """密钥元数据"""
    key_id: str
    key_type: KeyType
    version: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    description: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class KeyRotationConfig:
    """密钥轮换配置"""
    # 自动轮换周期
    rotation_period: timedelta = timedelta(days=90)

    # 提前警告时间
    warning_threshold: timedelta = timedelta(days=7)

    # 密钥过期时间
    expiration_period: timedelta = timedelta(days=180)

    # 是否启用自动轮换
    auto_rotation_enabled: bool = False

    # 轮换时保留的历史版本数量
    retain_versions: int = 3


class KeyStorage(ABC):
    """密钥存储抽象基类"""

    @abstractmethod
    async def store_key(
        self,
        key_id: str,
        key_data: bytes,
        metadata: KeyMetadata,
    ) -> None:
        """存储密钥"""
        pass

    @abstractmethod
    async def get_key(
        self,
        key_id: str,
        version: Optional[int] = None,
    ) -> Tuple[bytes, KeyMetadata]:
        """获取密钥"""
        pass

    @abstractmethod
    async def list_keys(
        self,
        key_type: Optional[KeyType] = None,
        active_only: bool = True,
    ) -> List[Tuple[str, KeyMetadata]]:
        """列出密钥"""
        pass

    @abstractmethod
    async def deactivate_key(
        self,
        key_id: str,
        version: Optional[int] = None,
    ) -> None:
        """停用密钥"""
        pass

    @abstractmethod
    async def delete_key(
        self,
        key_id: str,
        version: Optional[int] = None,
    ) -> None:
        """删除密钥"""
        pass


class FileKeyStorage(KeyStorage):
    """文件系统密钥存储

    将密钥存储在加密的文件中。
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Args:
            storage_dir: 密钥存储目录
        """
        self.storage_dir = Path(storage_dir or os.getenv("KEY_STORAGE_DIR", "./keys"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 主加密密钥（从环境变量获取）
        master_key_str = os.getenv("MASTER_KEY", "")
        if not master_key_str:
            logger.warning("MASTER_KEY not set, using insecure storage")
            self.master_key = b" insecure_master_key_change_me "
        else:
            self.master_key = master_key_str.encode()

    def _get_key_path(self, key_id: str, version: int) -> Path:
        """获取密钥文件路径"""
        return self.storage_dir / f"{key_id}_v{version}.key"

    def _encrypt_key_data(self, key_data: bytes) -> bytes:
        """加密密钥数据"""
        from .encryption import AESCipher

        cipher = AESCipher(self.master_key)
        return cipher.encrypt(key_data).encode()

    def _decrypt_key_data(self, encrypted_data: bytes) -> bytes:
        """解密密钥数据"""
        from .encryption import AESCipher

        cipher = AESCipher(self.master_key)
        return cipher.decrypt(encrypted_data.decode()).encode()

    async def store_key(
        self,
        key_id: str,
        key_data: bytes,
        metadata: KeyMetadata,
    ) -> None:
        """存储密钥"""
        key_path = self._get_key_path(key_id, metadata.version)

        # 加密密钥数据
        encrypted_data = self._encrypt_key_data(key_data)

        # 写入文件
        with open(key_path, 'wb') as f:
            f.write(encrypted_data)

        # 存储元数据
        metadata_path = self.storage_dir / f"{key_id}_v{metadata.version}.meta"
        import json
        with open(metadata_path, 'w') as f:
            json.dump({
                "key_id": metadata.key_id,
                "key_type": metadata.key_type.value,
                "version": metadata.version,
                "created_at": metadata.created_at.isoformat(),
                "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None,
                "is_active": metadata.is_active,
                "description": metadata.description,
                "tags": metadata.tags,
            }, f)

        logger.info(f"Key stored: {key_id} v{metadata.version}")

    async def get_key(
        self,
        key_id: str,
        version: Optional[int] = None,
    ) -> Tuple[bytes, KeyMetadata]:
        """获取密钥"""
        import json

        if version is None:
            # 获取最新版本的密钥
            metadata_list = await self.list_keys(KeyType(key_id.split("_")[0]) if "_" in key_id else None)
            if not metadata_list:
                raise KeyError(f"Key not found: {key_id}")

            # 按版本排序，获取最新的
            sorted_metadata = sorted(
                metadata_list,
                key=lambda x: x[1].version,
                reverse=True,
            )
            key_id, metadata = sorted_metadata[0]
            version = metadata.version

        key_path = self._get_key_path(key_id, version)
        metadata_path = self.storage_dir / f"{key_id}_v{version}.meta"

        if not key_path.exists() or not metadata_path.exists():
            raise KeyError(f"Key not found: {key_id} v{version}")

        # 读取并解密密钥
        with open(key_path, 'rb') as f:
            encrypted_data = f.read()

        key_data = self._decrypt_key_data(encrypted_data)

        # 读取元数据
        with open(metadata_path, 'r') as f:
            metadata_dict = json.load(f)

        metadata = KeyMetadata(
            key_id=metadata_dict["key_id"],
            key_type=KeyType(metadata_dict["key_type"]),
            version=metadata_dict["version"],
            created_at=datetime.fromisoformat(metadata_dict["created_at"]),
            expires_at=datetime.fromisoformat(metadata_dict["expires_at"]) if metadata_dict["expires_at"] else None,
            is_active=metadata_dict["is_active"],
            description=metadata_dict["description"],
            tags=metadata_dict["tags"],
        )

        return key_data, metadata

    async def list_keys(
        self,
        key_type: Optional[KeyType] = None,
        active_only: bool = True,
    ) -> List[Tuple[str, KeyMetadata]]:
        """列出密钥"""
        import json

        keys = []

        for meta_file in self.storage_dir.glob("*.meta"):
            try:
                with open(meta_file, 'r') as f:
                    metadata_dict = json.load(f)

                metadata = KeyMetadata(
                    key_id=metadata_dict["key_id"],
                    key_type=KeyType(metadata_dict["key_type"]),
                    version=metadata_dict["version"],
                    created_at=datetime.fromisoformat(metadata_dict["created_at"]),
                    expires_at=datetime.fromisoformat(metadata_dict["expires_at"]) if metadata_dict["expires_at"] else None,
                    is_active=metadata_dict["is_active"],
                    description=metadata_dict["description"],
                    tags=metadata_dict["tags"],
                )

                # 过滤
                if key_type and metadata.key_type != key_type:
                    continue

                if active_only and not metadata.is_active:
                    continue

                keys.append((metadata.key_id, metadata))

            except Exception as e:
                logger.error(f"Failed to read metadata file {meta_file}: {e}")

        return keys

    async def deactivate_key(
        self,
        key_id: str,
        version: Optional[int] = None,
    ) -> None:
        """停用密钥"""
        import json

        if version is None:
            # 停用所有版本
            metadata_list = await self.list_keys()
            for kid, metadata in metadata_list:
                if kid == key_id:
                    metadata.is_active = False
                    metadata_path = self.storage_dir / f"{kid}_v{metadata.version}.meta"
                    with open(metadata_path, 'w') as f:
                        json.dump({
                            "key_id": metadata.key_id,
                            "key_type": metadata.key_type.value,
                            "version": metadata.version,
                            "created_at": metadata.created_at.isoformat(),
                            "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None,
                            "is_active": False,
                            "description": metadata.description,
                            "tags": metadata.tags,
                        }, f)
        else:
            # 停用指定版本
            metadata_path = self.storage_dir / f"{key_id}_v{version}.meta"
            with open(metadata_path, 'r') as f:
                metadata_dict = json.load(f)

            metadata_dict["is_active"] = False

            with open(metadata_path, 'w') as f:
                json.dump(metadata_dict, f)

        logger.info(f"Key deactivated: {key_id}")

    async def delete_key(
        self,
        key_id: str,
        version: Optional[int] = None,
    ) -> None:
        """删除密钥"""
        if version is None:
            # 删除所有版本
            for key_file in self.storage_dir.glob(f"{key_id}_v*.*"):
                key_file.unlink()
        else:
            # 删除指定版本
            key_path = self._get_key_path(key_id, version)
            metadata_path = self.storage_dir / f"{key_id}_v{version}.meta"

            if key_path.exists():
                key_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()

        logger.info(f"Key deleted: {key_id} v{version}")


class KeyManager:
    """密钥管理器

    提供密钥生成、轮换、验证等功能。
    """

    def __init__(
        self,
        storage: Optional[KeyStorage] = None,
        config: Optional[KeyRotationConfig] = None,
    ):
        """
        Args:
            storage: 密钥存储后端
            config: 密钥轮换配置
        """
        self.storage = storage or FileKeyStorage()
        self.config = config or KeyRotationConfig()

    def _generate_key_data(self, key_size: int = 32) -> bytes:
        """生成随机密钥数据"""
        return os.urandom(key_size)

    async def create_key(
        self,
        key_id: str,
        key_type: KeyType,
        key_size: int = 32,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Tuple[bytes, KeyMetadata]:
        """创建新密钥

        Args:
            key_id: 密钥标识符
            key_type: 密钥类型
            key_size: 密钥大小（字节）
            description: 密钥描述
            tags: 标签

        Returns:
            Tuple[bytes, KeyMetadata]: 密钥数据和元数据
        """
        # 检查是否已有活动密钥
        existing_keys = await self.storage.list_keys(key_type)
        if existing_keys:
            latest_version = max(metadata.version for _, metadata in existing_keys)
            new_version = latest_version + 1
        else:
            new_version = 1

        # 生成密钥数据
        key_data = self._generate_key_data(key_size)

        # 创建元数据
        metadata = KeyMetadata(
            key_id=key_id,
            key_type=key_type,
            version=new_version,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + self.config.expiration_period,
            is_active=True,
            description=description,
            tags=tags or {},
        )

        # 存储密钥
        await self.storage.store_key(key_id, key_data, metadata)

        logger.info(
            f"Key created: {key_id} v{new_version}",
            extra={"key_id": key_id, "version": new_version, "key_type": key_type.value}
        )

        return key_data, metadata

    async def rotate_key(
        self,
        key_id: str,
        key_type: KeyType,
    ) -> Tuple[bytes, KeyMetadata]:
        """轮换密钥

        创建新版本密钥并停用旧版本。

        Args:
            key_id: 密钥标识符
            key_type: 密钥类型

        Returns:
            Tuple[bytes, KeyMetadata]: 新密钥数据和元数据
        """
        # 停用旧密钥
        try:
            await self.storage.deactivate_key(key_id)
        except KeyError:
            pass  # 密钥不存在，继续创建

        # 创建新密钥
        return await self.create_key(key_id, key_type)

    async def get_active_key(
        self,
        key_id: str,
        key_type: KeyType,
    ) -> Tuple[bytes, KeyMetadata]:
        """获取活动密钥

        Args:
            key_id: 密钥标识符
            key_type: 密钥类型

        Returns:
            Tuple[bytes, KeyMetadata]: 密钥数据和元数据
        """
        return await self.storage.get_key(key_id)

    async def check_rotation_needed(self) -> List[KeyMetadata]:
        """检查需要轮换的密钥

        Returns:
            List[KeyMetadata]: 需要轮换的密钥元数据列表
        """
        keys_to_rotate = []
        now = datetime.utcnow()

        all_keys = await self.storage.list_keys(active_only=True)

        for key_id, metadata in all_keys:
            # 检查是否即将过期
            if metadata.expires_at:
                time_until_expiration = metadata.expires_at - now

                if time_until_expiration <= self.config.warning_threshold:
                    keys_to_rotate.append(metadata)
                    logger.warning(
                        f"Key needs rotation: {key_id}",
                        extra={
                            "key_id": key_id,
                            "expires_at": metadata.expires_at.isoformat(),
                            "days_until_expiration": time_until_expiration.days,
                        }
                    )

        return keys_to_rotate

    async def auto_rotate_keys(self) -> List[str]:
        """自动轮换密钥

        Returns:
            List[str]: 已轮换的密钥 ID 列表
        """
        rotated_keys = []

        if not self.config.auto_rotation_enabled:
            logger.info("Auto rotation is disabled")
            return rotated_keys

        keys_to_rotate = await self.check_rotation_needed()

        for metadata in keys_to_rotate:
            try:
                await self.rotate_key(metadata.key_id, metadata.key_type)
                rotated_keys.append(metadata.key_id)
            except Exception as e:
                logger.error(
                    f"Failed to rotate key: {metadata.key_id}",
                    exc_info=True,
                    extra={"key_id": metadata.key_id, "error": str(e)}
                )

        return rotated_keys

    async def cleanup_old_keys(self) -> int:
        """清理旧版本的密钥

        保留配置中指定数量的最近版本。

        Returns:
            int: 删除的密钥数量
        """
        deleted_count = 0

        all_keys = await self.storage.list_keys(active_only=False)

        # 按 key_id 分组
        key_groups: Dict[str, List[KeyMetadata]] = {}
        for key_id, metadata in all_keys:
            if key_id not in key_groups:
                key_groups[key_id] = []
            key_groups[key_id].append(metadata)

        # 清理每个密钥的旧版本
        for key_id, metadata_list in key_groups.items():
            # 按版本排序，保留最新的 N 个版本
            metadata_list.sort(key=lambda m: m.version, reverse=True)

            versions_to_delete = metadata_list[self.config.retain_versions:]

            for metadata in versions_to_delete:
                if not metadata.is_active:
                    try:
                        await self.storage.delete_key(key_id, metadata.version)
                        deleted_count += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to delete key: {key_id} v{metadata.version}",
                            exc_info=True
                        )

        logger.info(f"Cleaned up {deleted_count} old key versions")
        return deleted_count


# 全局密钥管理器实例
_global_key_manager: Optional[KeyManager] = None


def get_key_manager(
    storage: Optional[KeyStorage] = None,
    config: Optional[KeyRotationConfig] = None,
) -> KeyManager:
    """获取全局密钥管理器实例

    Args:
        storage: 密钥存储后端
        config: 密钥轮换配置

    Returns:
        KeyManager: 密钥管理器实例
    """
    global _global_key_manager
    if _global_key_manager is None:
        _global_key_manager = KeyManager(storage, config)
    return _global_key_manager


async def rotate_all_keys() -> List[str]:
    """轮换所有需要轮换的密钥

    Returns:
        List[str]: 已轮换的密钥 ID 列表
    """
    manager = get_key_manager()
    return await manager.auto_rotate_keys()
