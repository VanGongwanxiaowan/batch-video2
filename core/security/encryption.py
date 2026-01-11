"""敏感数据加密模块

提供数据加密和解密功能，支持 AES-256-GCM 加密。
"""
import base64
import hashlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class EncryptionConfig:
    """加密配置"""
    algorithm: str = "AES-256-GCM"
    key_size: int = 32  # 256 bits
    nonce_size: int = 12  # 96 bits for GCM
    tag_size: int = 16  # 128 bits
    iterations: int = 100000  # PBKDF2 迭代次数


class DataEncryption(ABC):
    """数据加密抽象基类"""

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """加密数据

        Args:
            plaintext: 明文字符串

        Returns:
            str: 加密后的字符串（Base64 编码）
        """
        pass

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """解密数据

        Args:
            ciphertext: 加密字符串（Base64 编码）

        Returns:
            str: 解密后的明文字符串
        """
        pass


class AESCipher(DataEncryption):
    """AES-GCM 加密器

    使用 AES-256-GCM 进行加密，提供认证加密。
    """

    def __init__(
        self,
        encryption_key: Optional[bytes] = None,
        config: Optional[EncryptionConfig] = None,
    ):
        """
        Args:
            encryption_key: 加密密钥（32 bytes）
            config: 加密配置
        """
        self.config = config or EncryptionConfig()

        # 如果没有提供密钥，从环境变量获取或生成
        if encryption_key is None:
            key_str = os.getenv("ENCRYPTION_KEY", "")
            if key_str:
                # 从字符串派生密钥
                encryption_key = self._derive_key_from_string(key_str)
            else:
                raise ValueError(
                    "Encryption key must be provided or set ENCRYPTION_KEY environment variable"
                )

        # 验证密钥长度
        if len(encryption_key) != self.config.key_size:
            raise ValueError(
                f"Encryption key must be {self.config.key_size} bytes, "
                f"got {len(encryption_key)} bytes"
            )

        self.key = encryption_key

    @staticmethod
    def _derive_key_from_string(password: str, salt: Optional[bytes] = None) -> bytes:
        """从字符串派生密钥

        Args:
            password: 密码字符串
            salt: 盐值（可选）

        Returns:
            bytes: 派生的密钥
        """
        if salt is None:
            salt = b'batchshort_encryption_salt'

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(password.encode())

    def encrypt(self, plaintext: str) -> str:
        """加密数据

        Args:
            plaintext: 明文字符串

        Returns:
            str: Base64 编码的加密数据（nonce + ciphertext + tag）
        """
        try:
            # 生成随机 nonce
            nonce = os.urandom(self.config.nonce_size)

            # 创建 AES-GCM 加密器
            aesgcm = AESGCM(self.key)

            # 加密数据
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

            # 组合 nonce + ciphertext
            combined = nonce + ciphertext

            # Base64 编码
            return base64.b64encode(combined).decode('utf-8')

        except Exception as e:
            logger.error(f"Encryption failed: {e}", exc_info=True)
            raise

    def decrypt(self, ciphertext: str) -> str:
        """解密数据

        Args:
            ciphertext: Base64 编码的加密数据

        Returns:
            str: 解密后的明文字符串
        """
        try:
            # Base64 解码
            combined = base64.b64decode(ciphertext.encode('utf-8'))

            # 提取 nonce 和 ciphertext
            nonce = combined[:self.config.nonce_size]
            actual_ciphertext = combined[self.config.nonce_size:]

            # 创建 AES-GCM 解密器
            aesgcm = AESGCM(self.key)

            # 解密数据
            plaintext = aesgcm.decrypt(nonce, actual_ciphertext, None)

            return plaintext.decode('utf-8')

        except Exception as e:
            logger.error(f"Decryption failed: {e}", exc_info=True)
            raise ValueError("Decryption failed") from e


class FieldLevelEncryption:
    """字段级加密

    用于加密数据库中的敏感字段。
    """

    def __init__(self, cipher: Optional[AESCipher] = None):
        self.cipher = cipher or AESCipher()

    def encrypt_field(self, value: Optional[str]) -> Optional[str]:
        """加密字段值

        Args:
            value: 字段值

        Returns:
            Optional[str]: 加密后的值，如果输入为 None 则返回 None
        """
        if value is None:
            return None
        return self.cipher.encrypt(value)

    def decrypt_field(self, value: Optional[str]) -> Optional[str]:
        """解密字段值

        Args:
            value: 加密的字段值

        Returns:
            Optional[str]: 解密后的值，如果输入为 None 则返回 None
        """
        if value is None:
            return None
        return self.cipher.decrypt(value)


class Hasher:
    """哈希工具

    用于密码哈希和数据完整性校验。
    """

    @staticmethod
    def hash_sha256(data: str) -> str:
        """计算 SHA-256 哈希

        Args:
            data: 输入数据

        Returns:
            str: 十六进制哈希值
        """
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def hash_sha512(data: str) -> str:
        """计算 SHA-512 哈希

        Args:
            data: 输入数据

        Returns:
            str: 十六进制哈希值
        """
        return hashlib.sha512(data.encode()).hexdigest()

    @staticmethod
    def hash_bcrypt(data: str, salt: Optional[str] = None) -> str:
        """计算 bcrypt 哈希

        Args:
            data: 输入数据
            salt: 盐值（可选）

        Returns:
            str: bcrypt 哈希值
        """
        import bcrypt

        if salt is None:
            salt = bcrypt.gensalt()

        return bcrypt.hashpw(data.encode(), salt).decode()

    @staticmethod
    def verify_bcrypt(data: str, hashed: str) -> bool:
        """验证 bcrypt 哈希

        Args:
            data: 原始数据
            hashed: 哈希值

        Returns:
            bool: 是否匹配
        """
        import bcrypt

        try:
            return bcrypt.checkpw(data.encode(), hashed.encode())
        except Exception:
            return False

    @staticmethod
    def create_checksum(data: str, algorithm: str = "sha256") -> str:
        """创建数据校验和

        Args:
            data: 输入数据
            algorithm: 哈希算法

        Returns:
            str: 校验和
        """
        if algorithm == "sha256":
            return Hasher.hash_sha256(data)
        elif algorithm == "sha512":
            return Hasher.hash_sha512(data)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")


class SecureTokenGenerator:
    """安全令牌生成器

    生成用于密码重置、邮箱验证等的安全令牌。
    """

    def __init__(self, secret_key: Optional[str] = None):
        """
        Args:
            secret_key: 用于签名的密钥
        """
        self.secret_key = secret_key or os.getenv("SECRET_KEY", "default-secret-key")

    def generate_token(
        self,
        data: Dict[str, Any],
        expiration: timedelta = timedelta(hours=1),
    ) -> str:
        """生成安全令牌

        Args:
            data: 要编码的数据
            expiration: 过期时间

        Returns:
            str: 安全令牌
        """
        import jwt

        payload = {
            **data,
            "exp": datetime.utcnow() + expiration,
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证安全令牌

        Args:
            token: 安全令牌

        Returns:
            Optional[Dict[str, Any]]: 解码后的数据，如果验证失败返回 None
        """
        import jwt

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None


class SecureRandom:
    """安全随机数生成器"""

    @staticmethod
    def generate_bytes(length: int) -> bytes:
        """生成随机字节

        Args:
            length: 字节长度

        Returns:
            bytes: 随机字节
        """
        return os.urandom(length)

    @staticmethod
    def generate_hex(length: int) -> str:
        """生成随机十六进制字符串

        Args:
            length: 字符串长度

        Returns:
            str: 随机十六进制字符串
        """
        return os.urandom(length // 2).hex()

    @staticmethod
    def generate_url_safe_token(length: int = 32) -> str:
        """生成 URL 安全的随机令牌

        Args:
            length: 令牌长度

        Returns:
            str: URL 安全的随机令牌
        """
        import secrets

        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_password(
        length: int = 16,
        include_uppercase: bool = True,
        include_lowercase: bool = True,
        include_digits: bool = True,
        include_symbols: bool = True,
    ) -> str:
        """生成安全密码

        Args:
            length: 密码长度
            include_uppercase: 是否包含大写字母
            include_lowercase: 是否包含小写字母
            include_digits: 是否包含数字
            include_symbols: 是否包含特殊符号

        Returns:
            str: 生成的密码
        """
        import secrets
        import string

        charset = ""
        if include_uppercase:
            charset += string.ascii_uppercase
        if include_lowercase:
            charset += string.ascii_lowercase
        if include_digits:
            charset += string.digits
        if include_symbols:
            charset += string.punctuation

        if not charset:
            charset = string.ascii_letters + string.digits

        return ''.join(secrets.choice(charset) for _ in range(length))


# 全局加密器实例
_global_cipher: Optional[AESCipher] = None


def get_cipher(encryption_key: Optional[bytes] = None) -> AESCipher:
    """获取全局加密器实例

    Args:
        encryption_key: 加密密钥

    Returns:
        AESCipher: 加密器实例
    """
    global _global_cipher
    if _global_cipher is None:
        _global_cipher = AESCipher(encryption_key)
    return _global_cipher


def encrypt_data(plaintext: str) -> str:
    """加密数据

    Args:
        plaintext: 明文字符串

    Returns:
        str: 加密后的字符串
    """
    cipher = get_cipher()
    return cipher.encrypt(plaintext)


def decrypt_data(ciphertext: str) -> str:
    """解密数据

    Args:
        ciphertext: 加密字符串

    Returns:
        str: 解密后的明文字符串
    """
    cipher = get_cipher()
    return cipher.decrypt(ciphertext)
