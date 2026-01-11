"""
内容处理配置模块
定义文本处理所需的配置常量和数据类
"""
from dataclasses import dataclass

# 重试配置常量
DEFAULT_MAX_RETRIES = 5
DEFAULT_SLEEP_TIME = 30  # 秒

# 文本验证常量
CJK_PERCENTAGE_THRESHOLD = 10.0  # CJK百分比差异阈值
MIN_TEXT_LENGTH_FOR_CJK_CHECK = 10  # 进行CJK检查的最小文本长度

# 文本分割常量
DEFAULT_CHUNK_SIZE = 80  # 默认文本块大小


@dataclass
class TextProcessConfig:
    """文本处理配置数据类
    
    Attributes:
        max_retries: 最大重试次数，默认5
        sleep_time: 重试等待时间（秒），默认30
    """
    max_retries: int = DEFAULT_MAX_RETRIES
    sleep_time: int = DEFAULT_SLEEP_TIME
    
    def validate(self) -> None:
        """验证配置参数
        
        Raises:
            ValueError: 如果参数无效
        """
        if self.max_retries < 1:
            raise ValueError("最大重试次数必须大于0")
        if self.sleep_time < 0:
            raise ValueError("等待时间不能为负数")

