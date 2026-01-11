"""音频处理工具."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from core.exceptions import FileNotFoundException, ServiceException
from core.logging_config import setup_logging

logger = setup_logging("audio_utils", log_to_file=True)


class AudioProcessor:
    """音频处理工具类."""

    @staticmethod
    def merge_wav_files(wav_files: list[str], output_file: str) -> str:
        """
        合并多个 WAV 文件.

        Args:
            wav_files: WAV 文件路径列表
            output_file: 输出文件路径

        Returns:
            输出文件路径

        Raises:
            subprocess.CalledProcessError: 如果合并失败
            FileNotFoundError: 如果输入文件不存在
        """
        if not wav_files:
            raise ValueError("WAV 文件列表不能为空")

        # 检查所有输入文件是否存在
        for wav_file in wav_files:
            if not os.path.exists(wav_file):
                raise FileNotFoundException(wav_file)

        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建文件列表
        filelist_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".txt"
            ) as f:
                filelist_path = f.name
                for wav_file in wav_files:
                    # 使用绝对路径避免相对路径问题
                    abs_path = os.path.abspath(wav_file)
                    f.write(f"file '{abs_path}'\n")

            # 使用 ffmpeg 合并文件
            merge_command = [
                "ffmpeg",
                "-y",  # 覆盖输出文件
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                filelist_path,
                "-c",
                "copy",
                output_file,
            ]

            logger.debug(f"开始合并 {len(wav_files)} 个 WAV 文件...")
            result = subprocess.run(
                merge_command,
                check=True,
                capture_output=True,
                text=True,
            )

            logger.info(f"WAV 文件合并成功: {output_file}")
            return output_file

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if isinstance(e.stderr, str) else (e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e))
            logger.error(f"合并 WAV 文件失败: {error_msg}")
            raise ServiceException(
                f"合并 WAV 文件失败: {error_msg}",
                service_name="audio_processor"
            ) from e
        finally:
            # 清理临时文件
            if filelist_path and os.path.exists(filelist_path):
                try:
                    os.remove(filelist_path)
                except OSError as e:
                    logger.warning(f"无法删除临时文件列表: {e}")

    @staticmethod
    def convert_wav_to_mp3(wav_file: str, mp3_file: str) -> str:
        """
        将 WAV 文件转换为 MP3 文件.

        Args:
            wav_file: WAV 文件路径
            mp3_file: MP3 输出文件路径

        Returns:
            MP3 文件路径

        Raises:
            FileNotFoundError: 如果 WAV 文件不存在
            subprocess.CalledProcessError: 如果转换失败
        """
        if not os.path.exists(wav_file):
            raise FileNotFoundException(wav_file)

        # 确保输出目录存在
        output_path = Path(mp3_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 使用 ffmpeg 转换
            convert_command = [
                "ffmpeg",
                "-y",  # 覆盖输出文件
                "-i",
                wav_file,
                "-vn",  # 无视频
                "-acodec",
                "libmp3lame",
                "-q:a",
                "2",  # VBR 质量 (2 是较好的质量, 0-9)
                mp3_file,
            ]

            logger.debug(f"开始转换 WAV 到 MP3: {wav_file} -> {mp3_file}")
            result = subprocess.run(
                convert_command,
                check=True,
                capture_output=True,
                text=True,
            )

            logger.info(f"WAV 转 MP3 成功: {mp3_file}")
            return mp3_file

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if isinstance(e.stderr, str) else (e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e))
            logger.error(f"转换 WAV 到 MP3 失败: {error_msg}")
            raise ServiceException(
                f"转换 WAV 到 MP3 失败: {error_msg}",
                service_name="audio_processor"
            ) from e

    @staticmethod
    def cleanup_files(file_paths: list[str]) -> None:
        """
        清理文件列表.

        Args:
            file_paths: 要清理的文件路径列表
        """
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"已删除临时文件: {file_path}")
                except OSError as e:
                    logger.warning(f"无法删除文件 {file_path}: {e}")

