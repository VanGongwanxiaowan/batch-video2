"""服务客户端基类"""
from abc import ABC
from typing import Any, Dict, Optional

import httpx

from core.logging_config import setup_logging

logger = setup_logging("core.clients.base_client")


class BaseServiceClient(ABC):
    """服务客户端基类"""

    def __init__(self, base_url: str, timeout: int = 300) -> None:
        """
        初始化客户端

        Args:
            base_url: 服务基础URL
            timeout: 请求超时时间(秒)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout
        )

    async def __aenter__(self) -> 'BaseServiceClient':
        """异步上下文管理器入口
        
        Returns:
            BaseServiceClient: 客户端实例
        """
        return self

    async def __aexit__(
        self, 
        exc_type: Optional[type], 
        exc_val: Optional[Exception], 
        exc_tb: Optional[Any]
    ) -> None:
        """异步上下文管理器出口
        
        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪
        """
        await self.client.aclose()

    async def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        统一请求处理

        Args:
            method: HTTP方法
            endpoint: API端点
            **kwargs: 其他请求参数（headers, json, data等）

        Returns:
            响应JSON数据

        Raises:
            httpx.HTTPStatusError: HTTP状态码错误
            httpx.RequestError: 请求错误
            ValueError: JSON解析错误
        """
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP status error in {self.__class__.__name__}: "
                f"{e.response.status_code} - {e.response.text[:200]}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(
                f"Request error in {self.__class__.__name__}: {e}",
                exc_info=True
            )
            raise
        except (ValueError, KeyError) as e:
            logger.error(
                f"Data parsing error in {self.__class__.__name__}: {e}",
                exc_info=True
            )
            raise
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他未预期的异常（作为兜底）
            logger.exception(
                f"Unexpected error in {self.__class__.__name__}: {e}",
                exc_info=True
            )
            raise

    async def close(self) -> None:
        """关闭客户端"""
        await self.client.aclose()

