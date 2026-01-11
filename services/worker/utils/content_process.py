"""内容处理工具模块。

提供文本处理功能，包括：
- 文本分段
- LLM文本处理
- 多线程并行处理
"""
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple

from utils.util import chat_with_llm

from core.exceptions import ValidationException
from core.logging_config import setup_logging

from .content_process_config import (
    CJK_PERCENTAGE_THRESHOLD,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_SLEEP_TIME,
    MIN_TEXT_LENGTH_FOR_CJK_CHECK,
    TextProcessConfig,
)

# 配置日志记录器
logger = setup_logging("worker.utils.content_process", log_to_file=False)

def remove_punctuation(text: str) -> str:
    """Removes punctuation from a string."""
    # This regex matches common English and Chinese punctuation
    punctuation_pattern = r'[!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~。，！？、；：“”‘’（）【】《》—]'
    return re.sub(punctuation_pattern, '', text)

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def split_content(content: str, chunk_size: int = 100) -> List[str]:
    """
    Splits the content into chunks based on punctuation or newlines,
    aiming for a maximum chunk size, interpreting chunk_size as words
    for Latin-based languages and characters for character-based languages.
    """
    # Heuristic to detect language type: check for CJK character proportion
    # CJK Unified Ideographs range: U+4E00 to U+9FFF
    cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ff\u30a0-\u30ff\uff00-\uffef]')
    cjk_chars = len(cjk_pattern.findall(content))
    total_chars = len(content)
    # Consider it character-based if CJK characters make up more than 50% of the content
    is_character_based = (cjk_chars / total_chars > 0.5) if total_chars > 0 else False

    delimiters = r'([.!?。！？\n,，])'
    parts = re.split(delimiters, content)

    chunks = []
    current_chunk = ""
    for i, part in enumerate(parts):
        current_chunk += part

        if is_character_based:
            # Count characters for character-based languages
            current_chunk_length = len(current_chunk)
        else:
            # Count words for Latin-based languages
            current_chunk_length = len(current_chunk.split()) # Simple word count by splitting on spaces

        # Adjust the condition based on the calculated length
        if (re.match(delimiters, part) and current_chunk_length > chunk_size * 0.5) or \
           current_chunk_length >= chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = ""

    if current_chunk:
        chunks.append(current_chunk.strip())

    return [chunk for chunk in chunks if chunk]






def calculate_cjk_percentage(text: str) -> float:
    """Calculates the percentage of CJK characters in a string."""
    cjk_pattern = re.compile(r'[\u4E00-\u9FFF]')
    cjk_chars = len(cjk_pattern.findall(text))
    total_chars = len(text)
    return (cjk_chars / total_chars) * 100 if total_chars > 0 else 0.0

def _calculate_text_metrics(text: str) -> Dict[str, float]:
    """一次性计算所有文本指标
    
    Args:
        text: 文本内容
        
    Returns:
        包含CJK百分比的字典
    """
    return {
        "cjk_percentage": calculate_cjk_percentage(text),
    }


def _validate_text_similarity(
    clean_chunk_content: str,
    clean_res_content: str,
    chunk_content: str
) -> None:
    """验证文本相似度和语种一致性
    
    Args:
        clean_chunk_content: 清理后的原始文本
        clean_res_content: 清理后的响应文本
        chunk_content: 原始文本块（用于错误信息）
        
    Raises:
        ValidationException: 如果验证失败
    """
    if not clean_chunk_content:
        if not clean_res_content:
            return  # 两者都为空，视为匹配
        else:
            raise ValidationException("清理后的原始文本为空，但响应文本不为空")
    
    # 计算文本指标（避免重复计算）
    chunk_metrics = _calculate_text_metrics(clean_chunk_content)
    res_metrics = _calculate_text_metrics(clean_res_content)
    
    chunk_cjk_percentage = chunk_metrics["cjk_percentage"]
    res_cjk_percentage = res_metrics["cjk_percentage"]
    
    # 记录CJK百分比用于调试
    logger.debug(
        f"CJK percentage - chunk: {chunk_cjk_percentage:.2f}%, "
        f"response: {res_cjk_percentage:.2f}%"
    )
    
    # 检查CJK百分比差异
    cjk_diff = res_cjk_percentage - chunk_cjk_percentage
    if cjk_diff > CJK_PERCENTAGE_THRESHOLD:
        raise ValidationException(
            f"语种不对: CJK百分比差异过大 ({cjk_diff:.2f}%) "
            f"{clean_chunk_content[:50]}... --> {clean_res_content[:50]}..."
        )
    
    # 检查响应CJK百分比是否过低
    if (len(clean_chunk_content) > MIN_TEXT_LENGTH_FOR_CJK_CHECK and 
        res_cjk_percentage < chunk_cjk_percentage - CJK_PERCENTAGE_THRESHOLD):
        raise ValidationException(
            f"CJK百分比不匹配: 响应CJK ({res_cjk_percentage:.2f}%) "
            f"比原始CJK ({chunk_cjk_percentage:.2f}%) 低超过 {CJK_PERCENTAGE_THRESHOLD}%"
        )


def _call_llm_with_retry(
    prompt: str,
    config: TextProcessConfig,
    chunk_content: str
) -> str:
    """调用LLM并处理重试逻辑
    
    Args:
        prompt: LLM提示词
        config: 文本处理配置
        chunk_content: 文本块内容（用于日志）
        
    Returns:
        LLM响应内容
        
    Raises:
        ValidationException: 如果验证失败
        Exception: 如果所有重试都失败
    """
    for attempt in range(config.max_retries):
        try:
            res_content = chat_with_llm(prompt, 'gemini-2.5-flash')
            res_content = res_content.replace('`', '')
            return res_content
            
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（LLM请求错误等）
            logger.warning(
                f"Attempt {attempt + 1}/{config.max_retries} failed for chunk: "
                f"'{chunk_content[:30]}...' - {e}",
                exc_info=True
            )
            if attempt < config.max_retries - 1:
                logger.info(f"Retrying in {config.sleep_time} seconds...")
                time.sleep(config.sleep_time)
            else:
                logger.error(
                    f"All {config.max_retries} attempts failed for chunk: "
                    f"'{chunk_content[:30]}...'. Giving up."
                )
                raise  # 重新抛出最后的异常
    
    return ""  # Should not be reached if an exception is raised or success occurs


def text_process_chunk(
    chunk_content: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    sleep_time: int = DEFAULT_SLEEP_TIME
) -> str:
    """
    处理单个文本块，使用LLM将其转换为口语化文本。
    
    此函数已重构，提取了辅助函数，提高了代码可维护性。
    
    Args:
        chunk_content: 文本块内容
        max_retries: 最大重试次数，默认5
        sleep_time: 重试等待时间（秒），默认30
        
    Returns:
        处理后的文本内容
        
    Raises:
        ValidationException: 如果文本验证失败
        Exception: 如果LLM调用失败
    """
    # 创建配置对象
    config = TextProcessConfig(max_retries=max_retries, sleep_time=sleep_time)
    config.validate()
    
    # 构建提示词
    prompt = f'''稿件内容：```{chunk_content}```
上面是一个文本稿件，我现在需要请将以上稿件转化为口语化的朗读用稿件，句子之间用逗号分隔，
你只要返回稿件内容，保持稿件的语种，不要其他字符，不要解释
'''
    
    try:
        # 调用LLM（带重试）
        res_content = _call_llm_with_retry(prompt, config, chunk_content)
        
        # 清理响应内容
        res_content = res_content.replace('`', '')
        
        # 计算编辑距离和相似度
        clean_chunk_content = remove_punctuation(chunk_content)
        clean_res_content = remove_punctuation(res_content)
        
        # 验证文本相似度和语种一致性
        _validate_text_similarity(clean_chunk_content, clean_res_content, chunk_content)
        
        return res_content
        
    except ValidationException:
        # 验证错误，直接抛出
        raise
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（LLM请求错误等）
        logger.error(
            f"处理文本块失败: '{chunk_content[:30]}...' - {e}",
            exc_info=True
        )
        raise


def _process_chunks_parallel(
    content_chunks: List[str],
    max_workers: int = 15
) -> List[str]:
    """并行处理文本块
    
    Args:
        content_chunks: 文本块列表
        max_workers: 最大工作线程数，默认15
        
    Returns:
        处理后的文本块列表（保持顺序）
    """
    processed_chunks_ordered = [None] * len(content_chunks)

    def process_chunk_and_store(index: int, chunk: str) -> None:
        """处理单个文本块并存储结果。

        Args:
            index: 块索引
            chunk: 文本块内容
        """
        try:
            processed_chunks_ordered[index] = text_process_chunk(chunk)
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（文本处理错误等）
            logger.error(
                f"Critical error processing chunk {index}: {e}",
                exc_info=True
            )
            processed_chunks_ordered[index] = f"[ERROR PROCESSING CHUNK {index}]"

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_chunk_and_store, i, chunk)
                   for i, chunk in enumerate(content_chunks)]
        
        for future in futures:
            future.result()

    return processed_chunks_ordered


def _merge_results(processed_chunks: List[str]) -> str:
    """合并处理后的文本块
    
    Args:
        processed_chunks: 处理后的文本块列表
        
    Returns:
        合并后的完整文本
    """
    return "".join(processed_chunks)


def process_long_text_multithreaded(long_content: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """
    分割长文本，并行处理各个块，然后重新合并。
    
    此函数已重构，提取了辅助函数，提高了代码可维护性。
    
    Args:
        long_content: 长文本内容
        chunk_size: 文本块大小，默认80
        
    Returns:
        处理后的完整文本
    """
    # 分割文本
    content_chunks = split_content(long_content, chunk_size=chunk_size)
    logger.debug(f"Split content into {len(content_chunks)} chunks")
    
    # 并行处理
    processed_chunks = _process_chunks_parallel(content_chunks)
    
    # 合并结果
    return _merge_results(processed_chunks)


# --- Example Usage ---
if __name__ == "__main__":
    long_chinese_content = """これは非常に長い中国語のテキストで、セグメントに分割する必要があります。セグメント化の基準は、句読点、たとえば読点、句点、疑問符、感嘆符などです。同時に、改行も良い区切り点です。\n内容が非常に長くても、各小セグメントの長さを適切に保ち、約百文字程度にする必要があります。これにより、マルチスレッド並列処理を効果的に利用し、全体的な効率を向上させることができます。処理された小セグメントは、その後、完全な朗読用原稿にマージされます。これは、私たちのセグメンテーションロジックがさまざまな状況を正しく処理できるかを確認するためのテストです。これはテストの2番目の文です。
これはテストの3番目の文です。これはテストの4番目の文です。
これはテストの5番目の文で、特殊な記号が含まれている可能性があります！例えば@#$。
最後の文です。
"""
    
    logger.info("--- Processing Chinese Content with Retries ---")
    processed_chinese_text = process_long_text_multithreaded(long_chinese_content)
    logger.info(f"\nProcessed Chinese Text:\n{processed_chinese_text}")
    logger.info("-" * 30)