"""
FFmpeg核心工具类
提供FFmpeg命令执行和路径验证的基础功能
"""
import subprocess
from pathlib import Path
from typing import List, Optional, Union

from core.exceptions import FileException, ServiceException
from core.logging_config import setup_logging

logger = setup_logging("core.utils.ffmpeg.core")


class FFmpegError(ServiceException):
    """FFmpeg执行错误"""
    pass


class FFmpegCore:
    """FFmpeg核心工具类"""
    
    def __init__(self, timeout: int = 300):
        """
        初始化FFmpeg工具
        
        Args:
            timeout: 命令执行超时时间(秒)
        """
        self.timeout = timeout
        self._check_ffmpeg_available()
    
    def _check_ffmpeg_available(self) -> None:
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=10,
                check=True
            )
            logger.debug("FFmpeg is available")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise ServiceException("FFmpeg is not available or not installed") from e
    
    def get_hwaccel_args(self) -> List[str]:
        """
        获取硬件加速参数
        
        Returns:
            List[str]: FFmpeg硬件加速参数列表
        """
        import platform
        system = platform.system()
        
        if system == 'Darwin':
            # macOS - check for VideoToolbox
            return ['-hwaccel', 'videotoolbox']
        elif system == 'Linux':
            # Linux - check for CUDA
            try:
                # 简单检查是否有 nvidia-smi，或者直接检查 ffmpeg -hwaccels
                result = subprocess.run(
                    ['ffmpeg', '-hwaccels'], 
                    capture_output=True, 
                    text=True,
                    timeout=5
                )
                if 'cuda' in result.stdout:
                    return ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda']
            except Exception:
                pass
                
        return []

    def validate_path(self, path: Union[str, Path], must_exist: bool = False) -> Path:
        """
        验证文件路径
        
        Args:
            path: 文件路径
            must_exist: 是否必须存在
            
        Returns:
            Path: 验证后的路径对象
            
        Raises:
            FileException: 路径验证失败
        """
        path = Path(path)
        
        # 检查路径是否包含危险字符
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'"]
        path_str = str(path)
        for char in dangerous_chars:
            if char in path_str:
                raise FileException(f"Path contains dangerous character: {char}")
        
        if must_exist and not path.exists():
            raise FileException(f"File does not exist: {path}")
        
        return path
    
    def run_command(
        self,
        command: List[str],
        timeout: Optional[int] = None,
        capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """
        安全执行FFmpeg命令
        
        Args:
            command: FFmpeg命令参数列表
            timeout: 超时时间（秒），None使用默认值
            capture_output: 是否捕获输出
            
        Returns:
            subprocess.CompletedProcess: 执行结果
            
        Raises:
            FFmpegError: 执行失败
        """
        if timeout is None:
            timeout = self.timeout
        
        try:
            logger.info(f"Executing FFmpeg command: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=True
            )
            
            logger.debug("FFmpeg command completed successfully")
            return result
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"FFmpeg command timed out after {timeout} seconds"
            logger.error(error_msg)
            raise FFmpegError(error_msg) from e
            
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg command failed with return code {e.returncode}: {e.stderr}"
            logger.error(error_msg)
            raise FFmpegError(error_msg) from e
            
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（FFmpeg执行错误等）
            error_msg = f"Unexpected error executing FFmpeg command: {str(e)}"
            logger.error(error_msg)
            raise FFmpegError(error_msg) from e

    async def run_command_async(
        self,
        command: List[str],
        timeout: Optional[int] = None,
        capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """
        异步执行FFmpeg命令 (Non-blocking)
        
        Args:
            command: FFmpeg命令参数列表
            timeout: 超时时间（秒），None使用默认值
            capture_output: 是否捕获输出
            
        Returns:
            Tuple[int, str, str]: (return_code, stdout, stderr)
            
        Raises:
            FFmpegError: 执行失败
        """
        import asyncio
        if timeout is None:
            timeout = self.timeout
            
        try:
            logger.info(f"Executing Async FFmpeg command: {' '.join(command)}")
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE if capture_output else asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE if capture_output else asyncio.subprocess.DEVNULL
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                stdout_str = stdout.decode() if stdout else ""
                stderr_str = stderr.decode() if stderr else ""
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                raise FFmpegError(f"FFmpeg command timed out after {timeout} seconds")
                
            if process.returncode != 0:
                error_msg = f"FFmpeg command failed with return code {process.returncode}: {stderr_str}"
                logger.error(error_msg)
                raise FFmpegError(error_msg)
                
            logger.debug("Async FFmpeg command completed successfully")
            return process.returncode, stdout_str, stderr_str
            
        except Exception as e:
            if isinstance(e, FFmpegError) or isinstance(e, (SystemExit, KeyboardInterrupt)):
                raise
            error_msg = f"Unexpected error executing Async FFmpeg command: {str(e)}"
            logger.error(error_msg)
            raise FFmpegError(error_msg) from e
