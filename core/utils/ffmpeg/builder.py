"""FFmpeg 命令构建器

提供流式接口来构建 FFmpeg 命令，消除重复的命令构建代码。

使用示例:
    from core.utils.ffmpeg.builder import FFmpegCommandBuilder

    command = (FFmpegCommandBuilder()
               .add_input("video.mp4", index=0)
               .add_input("audio.mp3", index=1)
               .add_subtitle_filter("subs.srt", "FontSize=24")
               .map_stream("[subtitled]", 0)
               .map_stream("1:a")
               .set_video_codec("libx264")
               .set_quality(crf=23)
               .set_audio_codec("copy")
               .set_output("output.mp4")
               .build())

    # 或者使用便捷函数
    from core.utils.ffmpeg.builder import build_subtitle_command
    command = build_subtitle_command("video.mp4", "audio.mp3", "subs.srt", "output.mp4", style)
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from core.logging_config import setup_logging

logger = setup_logging("core.utils.ffmpeg.builder")


@dataclass
class FFmpegInput:
    """FFmpeg 输入规范

    Args:
        path: 输入文件路径
        index: 输入索引（0, 1, 2, ...）
        duration: 持续时间限制（秒）
        start_time: 开始时间（秒）
        options: 额外的输入选项
    """
    path: Union[str, Path]
    index: int = 0
    duration: Optional[float] = None
    start_time: Optional[float] = None
    options: Dict[str, str] = field(default_factory=dict)

    def build_args(self) -> List[str]:
        """构建输入参数

        Returns:
            List[str]: FFmpeg 命令参数列表
        """
        args = []

        # 添加开始时间
        if self.start_time is not None:
            args.extend(["-ss", str(self.start_time)])

        # 添加持续时间
        if self.duration is not None:
            args.extend(["-t", str(self.duration)])

        # 添加自定义选项
        for key, value in self.options.items():
            args.extend([f"-{key}", value])

        # 添加输入文件
        args.extend(["-i", str(self.path)])

        return args


@dataclass
class FFmpegFilter:
    """FFmpeg 滤镜规范

    Args:
        filter_string: 滤镜字符串
        input_label: 输入标签（如 "[0:v]"）
        output_label: 输出标签（如 "[subtitled]"）
    """
    filter_string: str
    input_label: Optional[str] = None
    output_label: Optional[str] = None

    def build_string(self) -> str:
        """构建滤镜字符串

        Returns:
            str: filter_complex 兼容的滤镜字符串
        """
        parts = []

        # 添加输入标签
        if self.input_label:
            parts.append(self.input_label)

        # 添加滤镜字符串
        parts.append(self.filter_string)

        # 添加输出标签
        if self.output_label:
            parts.append(self.output_label)

        return "".join(parts)


class FFmpegCommandBuilder:
    """FFmpeg 命令流式构建器

    提供流式接口来构建复杂的 FFmpeg 命令，
    消除重复的命令构建代码。

    示例:
        builder = FFmpegCommandBuilder()
        command = (builder
                   .add_input("video.mp4")
                   .add_input("logo.png")
                   .add_overlay_filter(logo_label="[1:v]", x=10, y=10)
                   .set_output("output.mp4")
                   .build())
    """

    def __init__(self):
        """初始化构建器"""
        self.inputs: List[FFmpegInput] = []
        self.filters: List[FFmpegFilter] = []
        self.maps: List[str] = []
        self.output_options: Dict[str, str] = {}
        self.output_path: Optional[Path] = None
        self.overwrite: bool = True

        # 视频编码选项
        self.video_codec: Optional[str] = None
        self.crf: Optional[int] = None
        self.preset: Optional[str] = None
        self.pix_fmt: Optional[str] = None
        self.fps: Optional[int] = None

        # 音频编码选项
        self.audio_codec: Optional[str] = None
        self.audio_bitrate: Optional[str] = None

    def add_input(
        self,
        path: Union[str, Path],
        index: Optional[int] = None,
        duration: Optional[float] = None,
        start_time: Optional[float] = None,
        **options
    ) -> "FFmpegCommandBuilder":
        """添加输入文件

        Args:
            path: 输入文件路径
            index: 输入索引
            duration: 持续时间限制
            start_time: 开始时间
            **options: 额外的输入选项

        Returns:
            FFmpegCommandBuilder: 返回自身以支持链式调用
        """
        if index is None:
            index = len(self.inputs)

        self.inputs.append(FFmpegInput(
            path=path,
            index=index,
            duration=duration,
            start_time=start_time,
            options=options
        ))
        return self

    def add_subtitle_filter(
        self,
        srt_path: str,
        force_style: str,
        output_label: str = "subtitled"
    ) -> "FFmpegCommandBuilder":
        """添加字幕滤镜

        Args:
            srt_path: SRT 字幕文件路径
            force_style: 字幕样式字符串
            output_label: 输出标签

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        filter_str = f"subtitles='{srt_path}':force_style='{force_style}'"
        self.filters.append(FFmpegFilter(
            filter_string=filter_str,
            input_label=None,
            output_label=f"[{output_label}]"
        ))
        return self

    def add_overlay_filter(
        self,
        overlay_label: str,
        x: int = 10,
        y: int = 10,
        input_label: str = "[0:v]",
        output_label: str = "final"
    ) -> "FFmpegCommandBuilder":
        """添加叠加滤镜（用于 Logo、水印等）

        Args:
            overlay_label: 叠加层标签（如 "[1:v]"）
            x: X 坐标
            y: Y 坐标
            input_label: 主视频标签
            output_label: 输出标签

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        self.filters.append(FFmpegFilter(
            filter_string=f"overlay={x}:{y}",
            input_label=f"{input_label}[{overlay_label}]",
            output_label=f"[{output_label}]"
        ))
        return self

    def add_scale_filter(
        self,
        width: int,
        height: int,
        force_original: bool = True,
        output_label: str = "scaled"
    ) -> "FFmpegCommandBuilder":
        """添加缩放滤镜

        Args:
            width: 目标宽度
            height: 目标高度
            force_original: 是否保持原始纵横比
            output_label: 输出标签

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        if force_original:
            filter_str = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        else:
            filter_str = f"scale={width}:{height}"

        self.filters.append(FFmpegFilter(
            filter_string=filter_str,
            output_label=f"[{output_label}]"
        ))
        return self

    def add_xfade_filter(
        self,
        transition: str,
        duration: float,
        offset: float,
        input1: str,
        input2: str,
        output: str
    ) -> "FFmpegCommandBuilder":
        """添加 xfade 转场滤镜

        Args:
            transition: 转场类型（fade, slide, zoom 等）
            duration: 转场持续时间（秒）
            offset: 转场偏移时间（秒）
            input1: 第一个输入标签
            input2: 第二个输入标签
            output: 输出标签

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        self.filters.append(FFmpegFilter(
            filter_string=f"xfade=transition={transition}:duration={duration}:offset={offset}",
            input_label=f"{input1}[{input2}]",
            output_label=f"[{output}]"
        ))
        return self

    def map_stream(self, stream_spec: str, file_index: Optional[int] = None) -> "FFmpegCommandBuilder":
        """映射流到输出

        Args:
            stream_spec: 流规范（如 "[0:v]", "1:a"）
            file_index: 文件索引

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        if file_index is not None:
            self.maps.extend(["-map", f"{file_index}:{stream_spec}"])
        else:
            self.maps.extend(["-map", stream_spec])
        return self

    def set_video_codec(self, codec: str) -> "FFmpegCommandBuilder":
        """设置视频编解码器

        Args:
            codec: 编解码器名称（如 "libx264"）

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        self.video_codec = codec
        return self

    def set_audio_codec(self, codec: str) -> "FFmpegCommandBuilder":
        """设置音频编解码器

        Args:
            codec: 编解码器名称（如 "aac"）

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        self.audio_codec = codec
        return self

    def set_quality(self, crf: int, preset: str = "veryfast") -> "FFmpegCommandBuilder":
        """设置视频质量

        Args:
            crf: CRF 值（0-51，越低质量越好）
            preset: 编码速度预设

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        self.crf = crf
        self.preset = preset
        return self

    def set_pixel_format(self, pix_fmt: str) -> "FFmpegCommandBuilder":
        """设置像素格式

        Args:
            pix_fmt: 像素格式（如 "yuv420p"）

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        self.pix_fmt = pix_fmt
        return self

    def set_fps(self, fps: int) -> "FFmpegCommandBuilder":
        """设置帧率

        Args:
            fps: 帧率

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        self.fps = fps
        return self

    def set_output(
        self,
        path: Union[str, Path],
        overwrite: bool = True
    ) -> "FFmpegCommandBuilder":
        """设置输出文件

        Args:
            path: 输出文件路径
            overwrite: 是否覆盖已存在的文件

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        self.output_path = Path(path)
        self.overwrite = overwrite
        return self

    def add_option(self, key: str, value: str) -> "FFmpegCommandBuilder":
        """添加通用输出选项

        Args:
            key: 选项键
            value: 选项值

        Returns:
            FFmpegCommandBuilder: 返回自身
        """
        self.output_options[key] = value
        return self

    def build(self) -> List[str]:
        """构建最终的 FFmpeg 命令

        Returns:
            List[str]: FFmpeg 命令参数列表

        Raises:
            ValueError: 如果没有指定输入或输出
        """
        if not self.inputs:
            raise ValueError("No inputs specified")

        if not self.output_path:
            raise ValueError("No output path specified")

        args = ["ffmpeg"]

        # 添加覆盖标志
        if self.overwrite:
            args.append("-y")

        # 添加所有输入
        for inp in self.inputs:
            args.extend(inp.build_args())

        # 添加滤镜
        if self.filters:
            filter_complex = ";".join(f.build_string() for f in self.filters)
            args.extend(["-filter_complex", filter_complex])

        # 添加流映射
        for map_spec in self.maps:
            args.extend(["-map", map_spec])

        # 添加视频编码选项
        if self.video_codec:
            args.extend(["-c:v", self.video_codec])
        if self.crf is not None:
            args.extend(["-crf", str(self.crf)])
        if self.preset:
            args.extend(["-preset", self.preset])
        if self.pix_fmt:
            args.extend(["-pix_fmt", self.pix_fmt])
        if self.fps:
            args.extend(["-r", str(self.fps)])

        # 添加音频编码选项
        if self.audio_codec:
            args.extend(["-c:a", self.audio_codec])
        if self.audio_bitrate:
            args.extend(["-b:a", self.audio_bitrate])

        # 添加自定义选项
        for key, value in self.output_options.items():
            args.extend([f"-{key}", value])

        # 添加输出路径
        args.append(str(self.output_path))

        return args

    def build_and_execute(
        self,
        timeout: int = 300,
        capture_output: bool = True
    ):
        """构建并执行命令

        Args:
            timeout: 超时时间（秒）
            capture_output: 是否捕获输出

        Returns:
            命令执行结果
        """
        from . import run_ffmpeg

        command = self.build()
        return run_ffmpeg(command, timeout=timeout, capture_output=capture_output)


# ============================================================================
# 便捷函数
# ============================================================================

def build_subtitle_command(
    video_path: str,
    audio_path: str,
    srt_path: str,
    output_path: str,
    subtitle_style: str,
    crf: int = 23,
    preset: str = "veryfast",
    timeout: int = 600
) -> List[str]:
    """构建添加字幕的命令

    Args:
        video_path: 视频文件路径
        audio_path: 音频文件路径
        srt_path: SRT 字幕文件路径
        output_path: 输出文件路径
        subtitle_style: 字幕样式字符串
        crf: CRF 质量值
        preset: 编码速度预设
        timeout: 超时时间（秒）

    Returns:
        List[str]: FFmpeg 命令参数列表
    """
    return (FFmpegCommandBuilder()
            .add_input(video_path, index=0)
            .add_input(audio_path, index=1)
            .add_subtitle_filter(srt_path, subtitle_style, output_label="subtitled_video")
            .map_stream("[subtitled_video]")
            .map_stream("1:a")
            .set_video_codec("libx264")
            .set_quality(crf, preset)
            .set_audio_codec("copy")
            .add_option("shortest", "")
            .set_output(output_path)
            .build())


def build_logo_overlay_command(
    video_path: str,
    logo_path: str,
    output_path: str,
    position: Tuple[int, int] = (10, 10)
) -> List[str]:
    """构建添加 Logo 叠加的命令

    Args:
        video_path: 视频文件路径
        logo_path: Logo 图片路径
        output_path: 输出文件路径
        position: Logo 位置 (x, y)

    Returns:
        List[str]: FFmpeg 命令参数列表
    """
    return (FFmpegCommandBuilder()
            .add_input(video_path, index=0)
            .add_input(logo_path, index=1)
            .add_overlay_filter("[1:v]", x=position[0], y=position[1])
            .map_stream("[final]")
            .set_audio_codec("copy")
            .set_output(output_path)
            .build())


def build_subtitle_and_logo_command(
    video_path: str,
    audio_path: str,
    srt_path: str,
    logo_path: str,
    output_path: str,
    subtitle_style: str,
    logo_position: Tuple[int, int] = (30, 10),
    crf: int = 23,
    preset: str = "veryfast"
) -> List[str]:
    """构建同时添加字幕和 Logo 的命令

    Args:
        video_path: 视频文件路径
        audio_path: 音频文件路径
        srt_path: SRT 字幕文件路径
        logo_path: Logo 图片路径
        output_path: 输出文件路径
        subtitle_style: 字幕样式字符串
        logo_position: Logo 位置 (x, y)
        crf: CRF 质量值
        preset: 编码速度预设

    Returns:
        List[str]: FFmpeg 命令参数列表
    """
    return (FFmpegCommandBuilder()
            .add_input(video_path, index=0)
            .add_input(audio_path, index=1)
            .add_input(logo_path, index=2)
            .add_subtitle_filter(srt_path, subtitle_style, output_label="subtitled_video")
            .add_overlay_filter("[2:v]", x=logo_position[0], y=logo_position[1],
                              input_label="[subtitled_video]", output_label="final_video")
            .map_stream("[final_video]")
            .map_stream("1:a")
            .set_video_codec("libx264")
            .set_quality(crf, preset)
            .set_audio_codec("copy")
            .add_option("shortest", "")
            .set_output(output_path)
            .build())


def build_concat_command(
    video_paths: List[str],
    output_path: str,
    method: str = "concat"
) -> List[str]:
    """构建合并视频的命令

    Args:
        video_paths: 视频文件路径列表
        output_path: 输出文件路径
        method: 合并方法 ("concat" 或 "xfade")

    Returns:
        List[str]: FFmpeg 命令参数列表
    """
    if method == "concat":
        # 创建 concat 文件
        import tempfile
        import os

        concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        try:
            for path in video_paths:
                concat_file.write(f"file '{os.path.abspath(path)}'\n")
            concat_file.close()

            return (FFmpegCommandBuilder()
                    .add_input(concat_file.name, options={"f": "concat", "safe": "0"})
                    .add_option("c", "copy")
                    .set_output(output_path)
                    .build())
        finally:
            if os.path.exists(concat_file.name):
                os.unlink(concat_file.name)

    else:
        raise ValueError(f"Unknown concat method: {method}")


def build_scale_command(
    input_path: str,
    output_path: str,
    width: int,
    height: int,
    force_original: bool = True
) -> List[str]:
    """构建缩放视频的命令

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        width: 目标宽度
        height: 目标高度
        force_original: 是否保持原始纵横比

    Returns:
        List[str]: FFmpeg 命令参数列表
    """
    return (FFmpegCommandBuilder()
            .add_input(input_path)
            .add_scale_filter(width, height, force_original)
            .map_stream("[scaled]")
            .set_output(output_path)
            .build())


__all__ = [
    # 类
    "FFmpegCommandBuilder",
    "FFmpegInput",
    "FFmpegFilter",
    # 便捷函数
    "build_subtitle_command",
    "build_logo_overlay_command",
    "build_subtitle_and_logo_command",
    "build_concat_command",
    "build_scale_command",
]
