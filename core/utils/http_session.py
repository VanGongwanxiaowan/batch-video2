"""HTTP Session 管理器

提供全局共享的 requests.Session，带有连接池和重试配置。
避免每次请求都创建新的 TCP 连接，显著提升性能。
"""
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.logging_config import setup_logging

logger = setup_logging("core.utils.http_session")


class _HTTPSessionManager:
    """HTTP Session 管理器

    提供共享的 requests.Session，带有：
    - 连接池配置
    - 自动重试机制
    - 连接复用
    """

    def __init__(self):
        self._session: Optional[requests.Session] = None
        self._initialized = False

    def _create_session(self, pool_connections: int = 10, pool_maxsize: int = 20) -> requests.Session:
        """创建配置好的 Session

        Args:
            pool_connections: 连接池数量
            pool_maxsize: 每个池的最大连接数

        Returns:
            配置好的 requests.Session
        """
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=3,  # 最大重试次数
            backoff_factor=0.5,  # 重试延迟因子: 0.5, 1, 2, 4秒
            status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的HTTP状态码
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )

        # 配置连接池适配器
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        logger.debug(
            f"[HTTPSessionManager] Session 已创建 "
            f"(pool_connections={pool_connections}, pool_maxsize={pool_maxsize})"
        )
        return session

    def get_session(
        self,
        pool_connections: int = 10,
        pool_maxsize: int = 20
    ) -> requests.Session:
        """获取共享的 HTTP Session

        如果尚未初始化，则创建新的 Session。

        Args:
            pool_connections: 连接池数量
            pool_maxsize: 每个池的最大连接数

        Returns:
            配置好的 requests.Session 实例
        """
        if not self._initialized:
            self._session = self._create_session(pool_connections, pool_maxsize)
            self._initialized = True

        return self._session

    def close(self) -> None:
        """关闭 Session（通常在应用关闭时调用）"""
        if self._session:
            self._session.close()
            self._initialized = False
            logger.debug("[HTTPSessionManager] Session 已关闭")


# 全局单例
_http_session_manager = _HTTPSessionManager()


def get_http_session(
    pool_connections: int = 10,
    pool_maxsize: int = 20
) -> requests.Session:
    """获取共享的 HTTP Session

    Args:
        pool_connections: 连接池数量（默认 10）
        pool_maxsize: 每个池的最大连接数（默认 20）

    Returns:
        配置好连接池的 requests.Session

    Example:
        >>> from core.utils.http_session import get_http_session
        >>> session = get_http_session()
        >>> response = session.post("http://example.com/api", data={"key": "value"})
    """
    return _http_session_manager.get_session(pool_connections, pool_maxsize)


def close_http_session() -> None:
    """关闭共享的 HTTP Session

    通常在应用关闭时调用。
    """
    _http_session_manager.close()


__all__ = [
    "get_http_session",
    "close_http_session",
]
