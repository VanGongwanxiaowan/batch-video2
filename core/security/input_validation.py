"""输入验证和清理模块

提供多种安全验证和清理功能，防止 XSS、SQL 注入、路径遍历等攻击。
"""
import html
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.logging_config import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """验证错误异常"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class XSSDetector:
    """XSS 攻击检测器"""

    # 常见的 XSS 攻击模式
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'<style[^>]*>.*?</style>',
        r'<img[^>]*onerror[^>]*>',
        r'<svg[^>]*>.*?</svg>',
        r'fromCharCode',
        r'eval\s*\(',
        r'alert\s*\(',
        r'document\.cookie',
        r'window\.location',
        r'\.innerHTML',
        r'\.outerHTML',
        r'\.insertAdjacentHTML',
    ]

    # 危险的 HTML 标签
    DANGEROUS_TAGS = {
        'script', 'iframe', 'object', 'embed',
        'link', 'meta', 'style', 'svg', 'form',
    }

    # 危险的事件属性
    DANGEROUS_EVENTS = {
        'onload', 'onerror', 'onclick', 'onmouseover',
        'onmouseout', 'onfocus', 'onblur', 'onsubmit',
        'onkeydown', 'onkeyup', 'onkeypress', 'ondblclick',
    }

    @classmethod
    def detect_xss(cls, input_string: str) -> bool:
        """检测输入是否包含 XSS 攻击代码

        Args:
            input_string: 输入字符串

        Returns:
            bool: 如果检测到 XSS 返回 True
        """
        if not input_string:
            return False

        # 转换为小写进行检测
        input_lower = input_string.lower()

        # 检查已知的 XSS 模式
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, input_lower, re.IGNORECASE | re.DOTALL):
                logger.warning(f"XSS pattern detected: {pattern}")
                return True

        # 检查十六进制编码
        if re.search(r'&#x[0-9a-f]+;', input_lower):
            logger.warning("Hex encoded XSS pattern detected")
            return True

        # 检查 URL 编码
        if re.search(r'%[0-9a-f]{2}', input_lower):
            decoded = urllib.parse.unquote(input_lower)
            if cls.detect_xss(decoded):
                return True

        return False

    @classmethod
    def sanitize(cls, input_string: str) -> str:
        """清理输入字符串，移除潜在的 XSS 代码

        Args:
            input_string: 输入字符串

        Returns:
            str: 清理后的字符串
        """
        if not input_string:
            return ""

        # HTML 转义
        sanitized = html.escape(input_string)

        # 移除危险标签
        for tag in cls.DANGEROUS_TAGS:
            # 使用非贪婪匹配移除标签
            sanitized = re.sub(
                fr'<{tag}[^>]*>.*?</{tag}>',
                '',
                sanitized,
                flags=re.IGNORECASE | re.DOTALL
            )
            sanitized = re.sub(
                fr'<{tag}[^>]*/?>',
                '',
                sanitized,
                flags=re.IGNORECASE
            )

        return sanitized


class SQLInjectionDetector:
    """SQL 注入检测器"""

    # 常见的 SQL 注入模式
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bupdate\b.*\bset\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\bexec\b|\bexecute\b)",
        r"(;.*\b(drop|delete|update|insert|select)\b)",
        r"('.*--)",
        r"(/\*.*\*/)",
        r"(\bor\b.*=.*\bor\b)",
        r"(\band\b.*=.*\band\b)",
        r"(1=1|1 = 1)",
        r"(\badmin\b'--)",
        r"(\badmin\b'/*)",
        r"('.*\.*)",
        r"(\bxp_\w+)",
        r"(\bsp_\w+)",
        r"(\binformation_schema\b)",
        r"(\bsys\.columns\b)",
        r"(\bsys\.objects\b)",
        r"(\bsys\.tables\b)",
        r"(concat\s*\()",
        r"(char\s*\()",
        r"(cast\s*\()",
        r"(convert\s*\()",
    ]

    @classmethod
    def detect_sql_injection(cls, input_string: str) -> bool:
        """检测输入是否包含 SQL 注入

        Args:
            input_string: 输入字符串

        Returns:
            bool: 如果检测到 SQL 注入返回 True
        """
        if not input_string:
            return False

        # 转换为小写进行检测
        input_lower = input_string.lower()

        # 检查已知的 SQL 注入模式
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_lower, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected: {pattern}")
                return True

        # 检查多个单引号
        if input_string.count("'") > 1:
            # 检查是否有 SQL 注入特征
            if any(keyword in input_lower for keyword in ['or', 'and', 'union', 'select']):
                logger.warning("Potential SQL injection with multiple quotes")
                return True

        return False

    @classmethod
    def sanitize_sql_identifier(cls, identifier: str) -> str:
        """清理 SQL 标识符

        Args:
            identifier: SQL 标识符

        Returns:
            str: 清理后的标识符
        """
        if not identifier:
            return ""

        # 移除危险字符
        sanitized = re.sub(r'[^\w]', '', identifier)

        # 限制长度
        if len(sanitized) > 64:
            sanitized = sanitized[:64]

        return sanitized


class HTMLSanitizer:
    """HTML 清理器

    使用白名单方式清理 HTML，只保留安全的标签和属性。
    """

    # 允许的 HTML 标签
    ALLOWED_TAGS = {
        'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'div', 'span', 'blockquote', 'code', 'pre',
    }

    # 允许的 HTML 属性
    ALLOWED_ATTRIBUTES = {
        'href': {'a'},
        'title': {'a', 'abbr', 'acronym'},
        'class': set(ALLOWED_TAGS),
        'id': set(ALLOWED_TAGS),
    }

    @classmethod
    def sanitize_html(cls, html_string: str) -> str:
        """清理 HTML 字符串

        Args:
            html_string: HTML 字符串

        Returns:
            str: 清理后的 HTML
        """
        if not html_string:
            return ""

        # 移除危险的标签和属性
        sanitized = cls._remove_dangerous_tags(html_string)
        sanitized = cls._remove_dangerous_attributes(sanitized)
        sanitized = cls._remove_dangerous_protocols(sanitized)

        return sanitized

    @classmethod
    def _remove_dangerous_tags(cls, html_string: str) -> str:
        """移除危险的 HTML 标签"""
        # 构建不允许的标签列表
        dangerous_tags = XSSDetector.DANGEROUS_TAGS - cls.ALLOWED_TAGS

        for tag in dangerous_tags:
            # 移除开始标签
            html_string = re.sub(
                fr'<{tag}[^>]*>',
                '',
                html_string,
                flags=re.IGNORECASE
            )
            # 移除结束标签
            html_string = re.sub(
                fr'</{tag}>',
                '',
                html_string,
                flags=re.IGNORECASE
            )

        return html_string

    @classmethod
    def _remove_dangerous_attributes(cls, html_string: str) -> str:
        """移除危险的 HTML 属性"""
        # 移除事件处理器
        html_string = re.sub(
            r'\s*on\w+\s*=\s*["\'][^"\']*["\']',
            '',
            html_string,
            flags=re.IGNORECASE
        )

        # 移除 style 属性
        html_string = re.sub(
            r'\s*style\s*=\s*["\'][^"\']*["\']',
            '',
            html_string,
            flags=re.IGNORECASE
        )

        return html_string

    @classmethod
    def _remove_dangerous_protocols(cls, html_string: str) -> str:
        """移除危险的 URL 协议"""
        # 移除 javascript: 协议
        html_string = re.sub(
            r'href\s*=\s*["\']\s*javascript:.*?["\']',
            '',
            html_string,
            flags=re.IGNORECASE
        )

        # 移除 data: 协议
        html_string = re.sub(
            r'href\s*=\s*["\']\s*data:.*?["\']',
            '',
            html_string,
            flags=re.IGNORECASE
        )

        return html_string


class PathValidator:
    """路径验证器

    防止路径遍历攻击。
    """

    # 危险的路径模式
    DANGEROUS_PATTERNS = [
        r'\.\./',  # 父目录遍历
        r'\.\./',  # 父目录遍历（Windows 风格）
        r'~',  # 用户目录
        r'\x00',  # 空字节
        r'//',  # 绝对路径尝试
        r'\\\\',  # UNC 路径尝试
    ]

    @classmethod
    def validate_path(cls, file_path: str, base_dir: Optional[str] = None) -> bool:
        """验证路径是否安全

        Args:
            file_path: 要验证的文件路径
            base_dir: 基础目录（用于相对路径验证）

        Returns:
            bool: 如果路径安全返回 True
        """
        if not file_path:
            return False

        # 检查危险模式
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, file_path):
                logger.warning(f"Dangerous path pattern detected: {pattern}")
                return False

        # 如果提供了基础目录，验证路径是否在基础目录内
        if base_dir:
            try:
                base = Path(base_dir).resolve()
                target = (base / file_path).resolve()

                # 检查解析后的路径是否仍在基础目录内
                try:
                    target.relative_to(base)
                except ValueError:
                    logger.warning(f"Path traversal attempt detected: {file_path}")
                    return False

            except (OSError, ValueError) as e:
                logger.error(f"Path validation error: {e}")
                return False

        return True

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """清理文件名

        Args:
            filename: 文件名

        Returns:
            str: 清理后的文件名
        """
        if not filename:
            return "unnamed"

        # 移除路径部分
        filename = os.path.basename(filename)

        # 移除危险字符
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)

        # 限制长度
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255 - len(ext)] + ext

        # 如果文件名为空，使用默认值
        if not filename:
            filename = "unnamed"

        return filename


class InputValidator:
    """输入验证器

    提供多种输入验证功能。
    """

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证电子邮件地址

        Args:
            email: 电子邮件地址

        Returns:
            bool: 如果有效返回 True
        """
        if not email:
            return False

        # 基本的电子邮件格式验证
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> bool:
        """验证 URL

        Args:
            url: URL 字符串
            allowed_schemes: 允许的协议列表

        Returns:
            bool: 如果 URL 安全返回 True
        """
        if not url:
            return False

        try:
            parsed = urllib.parse.urlparse(url)

            # 检查协议
            if allowed_schemes and parsed.scheme not in allowed_schemes:
                return False

            # 检查危险协议
            dangerous_schemes = {'javascript', 'data', 'vbscript'}
            if parsed.scheme in dangerous_schemes:
                return False

            return True

        except Exception:
            return False

    @staticmethod
    def validate_length(
        value: str,
        min_length: int = 0,
        max_length: int = 1000,
    ) -> bool:
        """验证字符串长度

        Args:
            value: 输入字符串
            min_length: 最小长度
            max_length: 最大长度

        Returns:
            bool: 如果长度在范围内返回 True
        """
        if not isinstance(value, str):
            return False

        return min_length <= len(value) <= max_length

    @staticmethod
    def validate_regex(value: str, pattern: str) -> bool:
        """使用正则表达式验证输入

        Args:
            value: 输入字符串
            pattern: 正则表达式模式

        Returns:
            bool: 如果匹配返回 True
        """
        try:
            return re.match(pattern, value) is not None
        except re.error:
            return False


# 便捷函数
def validate_xss(input_string: str) -> bool:
    """检测 XSS 攻击"""
    return XSSDetector.detect_xss(input_string)


def validate_sql_query(input_string: str) -> bool:
    """检测 SQL 注入"""
    return SQLInjectionDetector.detect_sql_injection(input_string)


def sanitize_html(html_string: str) -> str:
    """清理 HTML"""
    return HTMLSanitizer.sanitize_html(html_string)


def validate_email(email: str) -> bool:
    """验证电子邮件"""
    return InputValidator.validate_email(email)


def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> bool:
    """验证 URL"""
    return InputValidator.validate_url(url, allowed_schemes)


def validate_path(file_path: str, base_dir: Optional[str] = None) -> bool:
    """验证路径"""
    return PathValidator.validate_path(file_path, base_dir)
