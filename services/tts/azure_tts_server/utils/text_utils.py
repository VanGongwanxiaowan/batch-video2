"""文本处理工具."""

from textspliter import RecursiveCharacterTextSplitter

from config import get_azure_tts_config
from core.logging_config import setup_logging

logger = setup_logging("text_utils", log_to_file=True)


class TextSplitter:
    """文本分割器."""

    def __init__(self, chunk_size: int | None = None):
        """
        初始化文本分割器.

        Args:
            chunk_size: 分块大小, 如果为 None 则使用配置中的默认值
        """
        config = get_azure_tts_config()
        self.chunk_size = chunk_size or config.DEFAULT_CHUNK_SIZE

        self._splitter = RecursiveCharacterTextSplitter(
            separators=["。", "！", "？", "；", "…", "\n"],
            chunk_size=self.chunk_size,
            chunk_overlap=0,
            keep_separator=False,
        )

        logger.debug(f"文本分割器初始化完成 - chunk_size: {self.chunk_size}")

    def split_text(self, text: str) -> list[str]:
        """
        分割文本.

        Args:
            text: 要分割的文本

        Returns:
            分割后的文本块列表
        """
        try:
            result = self._splitter.split_text(text)
            logger.debug(f"文本分割完成 - 原始长度: {len(text)}, 分块数: {len(result)}")
            return result
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (ValueError, AttributeError) as e:
            # 文本处理错误
            logger.error(f"[split_text] 文本处理错误: {e}", exc_info=True)
            raise RuntimeError(f"分割文本失败: {e}") from e
        except Exception as e:
            # 其他未预期的异常
            logger.exception(f"[split_text] 分割文本时发生错误: {e}")
            raise RuntimeError(f"分割文本失败: {e}") from e

