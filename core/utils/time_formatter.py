"""时间格式化工具模块

提供统一的时间格式化功能，消除重复的时间格式化代码。
"""


def format_time_ms_to_srt(ms: int) -> str:
    """
    将毫秒数格式化为SRT时间格式 (HH:MM:SS,mmm)
    
    Args:
        ms: 毫秒数
        
    Returns:
        SRT格式的时间字符串，格式: HH:MM:SS,mmm
        
    Example:
        >>> format_time_ms_to_srt(3661000)
        '01:01:01,000'
        >>> format_time_ms_to_srt(123456)
        '00:02:03,456'
    """
    hours = ms // 3_600_000
    ms %= 3_600_000
    minutes = ms // 60_000
    ms %= 60_000
    seconds = ms // 1_000
    ms %= 1_000
    return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"


def format_time_seconds_to_srt(seconds: float) -> str:
    """
    将秒数格式化为SRT时间格式 (HH:MM:SS,mmm)
    
    Args:
        seconds: 秒数（可以是浮点数）
        
    Returns:
        SRT格式的时间字符串
        
    Example:
        >>> format_time_seconds_to_srt(3661.5)
        '01:01:01,500'
    """
    ms = int(seconds * 1000)
    return format_time_ms_to_srt(ms)

