"""数字人路径管理器

统一管理数字人合成过程中的所有临时文件路径。
"""

from dataclasses import dataclass


@dataclass
class HumanPathManager:
    """数字人路径管理器，统一管理所有临时文件路径"""
    
    origin_video_path: str
    
    def __post_init__(self) -> None:
        """初始化所有路径"""
        base = self.origin_video_path.replace(".mp4", "")
        
        # 基础路径
        self.short_audio = f"{base}_short.mp3"
        self.short_audio_end = f"{base}_short_end.mp3"
        self.human_video_final = f"{base}_human_final.mp4"
        self.human_video_end_final = f"{base}_human_end_final.mp4"
        self.output = f"{base}_human_generate.mp4"
        self.human_generate_end = f"{base}_human_generate_end.mp4"
        self.origin_cut_video = f"{base}_cut.mp4"
        self.origin_cut_end_video = f"{base}_cut_end.mp4"
        self.human_replaced_video = f"{base}_human_replaced.mp4"
        self.temp_video = f"{base}_temp.mp4"
        
        # 角标模式专用路径
        self.short_audio_intro = f"{base}_short_intro.mp3"
        self.human_generate_intro = f"{base}_human_generate_intro.mp4"
        self.human_video_intro_final = f"{base}_human_intro_final.mp4"
        self.short_audio_outro = f"{base}_short_outro.mp3"
        self.human_generate_outro = f"{base}_human_generate_outro.mp4"
        self.human_video_outro_final = f"{base}_human_outro_final.mp4"
        self.main_video_part1 = f"{base}_main_part1.mp4"
        self.main_video_part2 = f"{base}_main_part2.mp4"
        self.main_video_part3 = f"{base}_main_part3.mp4"
        self.part1_with_human = f"{base}_part1_with_human.mp4"
        self.part3_with_human = f"{base}_part3_with_human.mp4"
        self.xfade_temp = f"{base}_xfade_temp.mp4"

