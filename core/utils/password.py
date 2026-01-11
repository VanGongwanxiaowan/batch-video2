"""密码哈希和验证工具函数。

提供安全的密码哈希和验证功能，使用bcrypt算法。
"""
from typing import Optional

import bcrypt

from core.logging_config import setup_logging

logger = setup_logging("core.utils.password", log_to_file=False)


def hash_password(password: str) -> str:
    """使用bcrypt哈希密码。
    
    Args:
        password: 原始密码字符串
        
    Returns:
        str: 哈希后的密码字符串（base64编码）
        
    Raises:
        ValueError: 如果密码为空或格式无效
        
    Example:
        >>> hashed = hash_password("my_password")
        >>> verify_password("my_password", hashed)
        True
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（密码哈希错误等）
        logger.error(f"[hash_password] Failed to hash password: {e}", exc_info=True)
        raise


def verify_password(password: str, hashed: str) -> bool:
    """验证密码是否匹配哈希值。
    
    Args:
        password: 原始密码字符串
        hashed: 哈希后的密码字符串
        
    Returns:
        bool: 如果密码匹配返回True，否则返回False
        
    Note:
        - 如果哈希格式无效，会记录警告日志并返回False
        - 不会抛出异常，确保安全性（防止时序攻击）
        
    Example:
        >>> hashed = hash_password("my_password")
        >>> verify_password("my_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    if not password or not hashed:
        return False
    
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed.encode('utf-8')
        )
    except (ValueError, TypeError) as e:
        # 处理无效的哈希格式，记录警告但不抛出异常
        logger.warning(
            f"Invalid password hash format during verification: {e}",
            exc_info=True
        )
        return False
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 处理其他意外错误
        logger.error(
            f"[verify_password] Unexpected error during password verification: {e}",
            exc_info=True
        )
        return False

