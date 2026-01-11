import base64
import os
import tempfile
from typing import Any, List, Optional, Tuple

import cv2
import numpy as np
from opencc import OpenCC
from PIL import Image, ImageDraw, ImageFont
from worker.config import settings

from core.logging_config import setup_logging

# 初始化日志记录器
logger = setup_logging("worker.utils.cover_draw_text", log_to_file=False)

# 字体映射表
FONT_MAP = {
    "en-AU-NatashaNeural": "arialbd.ttf",
    "zh-CN-XiaoxiaoNeural": "USMCCyuanjiantecu.otf",
    "zh-CN-YunxiNeural": "USMCCyuanjiantecu.otf",
    "pt-BR-FranciscaNeural": "arialbd.ttf",
    "pt-PT-RaquelNeural": "arialbd.ttf",
    "af-ZA-WillemNeural": "arialbd.ttf",
    "am-ET-MekdesNeural": "Tera",
    "ar-AE-FatimaNeural": "AdobeArabic-Bold_0.otf",
    "az-AZ-BanuNeural": "arialbd.ttf",
    "bg-BG-KalinaNeural": "arialbd.ttf",
    "bn-BD-NabanitaNeural": "Vrinda",
    "bs-BA-VesnaNeural": "arialbd.ttf",
    "ca-ES-JoanaNeural": "arialbd.ttf",
    "cs-CZ-VlastaNeural": "arialbd.ttf",
    "cy-GB-NiaNeural": "arialbd.ttf",
    "da-DK-ChristelNeural": "arialbd.ttf",
    "de-AT-IngridNeural": "arialbd.ttf",
    "el-GR-AthinaNeural": "arialbd.ttf",
    "es-AR-ElenaNeural": "arialbd.ttf",
    "et-EE-AnuNeural": "arialbd.ttf",
    "fa-IR-DilaraNeural": "arialbd.ttf",
    "fi-FI-NooraNeural": "arialbd.ttf",
    "fil-PH-BlessicaNeural": "arialbd.ttf",
    "fr-BE-CharlineNeural": "arialbd.ttf",
    "ga-IE-OrlaNeural": "arialbd.ttf",
    "gl-ES-SabelaNeural": "arialbd.ttf",
    "gu-IN-DhwaniNeural": "arialbd.ttf",
    "he-IL-HilaNeural": "AdobeHebrew-Bold.otf",
    "hi-IN-SwaraNeural": "arialbd.ttf",
    "hr-HR-GabrijelaNeural": "arialbd.ttf",
    "hu-HU-NoemiNeural": "arialbd.ttf",
    "id-ID-GadisNeural": "arialbd.ttf",
    "is-IS-GudrunNeural": "arialbd.ttf",
    "it-IT-ElsaNeural": "arialbd.ttf",
    "iu-Cans-CA-SiqiniqNeural": "arialbd.ttf",
    "ja-JP-NanamiNeural": "msgothic.ttc",
    "jv-ID-SitiNeural": "arialbd.ttf",
    "ka-GE-EkaNeural": "arialbd.ttf",
    "kk-KZ-AigulNeural": "arialbd.ttf",
    "km-KH-SreymomNeural": "arialbd.ttf",
    "kn-IN-SapnaNeural": "arialbd.ttf",
    "ko-KR-SunHiNeural": "malgunbd.ttf",
    "lo-LA-KeomanyNeural": "arialbd.ttf",
    "lt-LT-OnaNeural": "arialbd.ttf",
    "lv-LV-EveritaNeural": "arialbd.ttf",
    "mk-MK-MarijaNeural": "arialbd.ttf",
    "ml-IN-SobhanaNeural": "arialbd.ttf",
    "mn-MN-YesuiNeural": "arialbd.ttf",
    "mr-IN-AarohiNeural": "arialbd.ttf",
    "ms-MY-YasminNeural": "arialbd.ttf",
    "mt-MT-GraceNeural": "arialbd.ttf",
    "my-MM-NilarNeural": "Myanmar 3Version 1.358",
    "nb-NO-PernilleNeural": "arialbd.ttf",
    "ne-NP-HemkalaNeural": "arialbd.ttf",
    "nl-BE-DenaNeural": "arialbd.ttf",
    "pl-PL-ZofiaNeural": "arialbd.ttf",
    "ps-AF-LatifaNeural": "arialbd.ttf",
    "ro-RO-AlinaNeural": "arialbd.ttf",
    "ru-RU-SvetlanaNeural": "arialbd.ttf",
    "si-LK-ThiliniNeural": "arialbd.ttf",
    "sk-SK-ViktoriaNeural": "arialbd.ttf",
    "sl-SI-PetraNeural": "arialbd.ttf",
    "so-SO-UbaxNeural": "arialbd.ttf",
    "sq-AL-AnilaNeural": "arialbd.ttf",
    "sr-RS-SophieNeural": "arialbd.ttf",
    "su-ID-TutiNeural": "arialbd.ttf",
    "sv-SE-SofieNeural": "arialbd.ttf",
    "sw-KE-ZuriNeural": "arialbd.ttf",
    "ta-IN-PallaviNeural": "arialbd.ttf",
    "te-IN-ShrutiNeural": "arialbd.ttf",
    "th-TH-PremwadeeNeural": "arialbd.ttf",
    "tr-TR-EmelNeural": "arialbd.ttf",
    "uk-UA-PolinaNeural": "arialbd.ttf",
    "ur-IN-GulNeural": "arialbd.ttf",
    "uz-UZ-MadinaNeural": "arialbd.ttf",
    "vi-VN-HoaiMyNeural": "arialbd.ttf",
    "zh-HK-HiuGaaiNeural": "腾祥嘉丽大黑繁.ttf",
    "zh-TW-HsiaoChenNeural": "腾祥嘉丽大黑繁.ttf",
    "zu-ZA-ThandoNeural": "arialbd.ttf",
}


def draw_text(
    texts: List[str], 
    input_image: str, 
    output_image: str, 
    font_path: str
) -> None:
    # 加载图片
    img = cv2.imread(input_image)
    img_pil = Image.fromarray(img)

    width, height = img_pil.size  # 获取图片的实际尺寸

    # 字体设置
    font_large = ImageFont.truetype(font_path, 95)
    font_small = ImageFont.truetype(font_path, 80)

    # 颜色定义
    WHITE = (255, 255, 255)
    RED = (0, 0, 255)
    YELLOW = (0, 255, 255)
    BLACK = (0, 0, 0)

    lines = []

    # 四行文字 白黄黄红
    if len(texts) < 5:
        for index, text in enumerate(texts):
            if index == 0:
                lines.append((text, WHITE))
            if 1 <= index <= 2:
                lines.append((text, YELLOW))
            if 3 <= index <= 5:
                lines.append((text, RED))
    else:
        for index, text in enumerate(texts):
            if 0 <= index <= 1:
                lines.append((text, WHITE))
            if 2 <= index <= 3:
                lines.append((text, YELLOW))
            if 4 <= index <= 5:
                lines.append((text, RED))

    draw = ImageDraw.Draw(img_pil)

    # 调整行高计算，避免除以零
    if len(lines) > 0:
        line_height = height // len(lines)
    else:
        line_height = 0  # 如果没有文本行，则行高为0

    # 描边宽度（像素）
    stroke_width = 3

    for i, (text, fill_color) in enumerate(lines):
        y = i * line_height + 10
        x = 10
        # 根据文本长度选择字体大小
        if len(text) > 15:
            font_to_use = font_small
        else:
            font_to_use = font_large

        # 描边：先画黑色边框
        draw.text(
            (x, y),
            text,
            font=font_to_use,
            fill=fill_color,
            stroke_width=stroke_width,
            stroke_fill=BLACK,
        )

    # 转回 OpenCV 并保存
    img = np.array(img_pil)
    cv2.imwrite(output_image, img)


import base64
import tempfile


def draw_text_for_api(params: Any) -> str:

    input_base64 = params.input_image
    # 解码 base64 图片
    img_pil = None
    input_image_data = base64.b64decode(input_base64)
    input_image = None
    output_image = None
    try:
        input_image = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        texts = []
        BLACK = (0, 0, 0)
        with open(input_image, "wb") as f:
            f.write(input_image_data)
            img = cv2.imread(f.name)
            img_pil = Image.fromarray(img)
            for text in params.texts:
                font = FONT_MAP.get(params.language, "USMCCyuanjiantecu.otf")
                logger.debug(f"使用字体: {font}")
                if params.usetraditional:
                    font = "思源黑体-Bold.otf"
                    t2s = OpenCC("s2tw")
                    text.text = t2s.convert(text.text)  # 转换为简体中文
                font_path = os.path.join(str(settings.font_dir), font)
                font_config = ImageFont.truetype(font_path, text.size)
                color = text.color
                if isinstance(color, list) and len(color) == 3:
                    # 如果颜色是RGB列表，转换为元组
                    color = tuple(color)
                elif isinstance(color, str):
                    color = tuple(eval(color))
                    # 如果颜色是字符串，直接使用
                texts.append((text.text, color, font_config))
            width, height = img_pil.size  # 获取图片的实际尺寸
            if len(texts) > 0:
                line_height = height // len(texts)
            else:
                line_height = 0  # 如果没有文本行，则行高为0
            draw = ImageDraw.Draw(img_pil)
            for i, (text, fill_color, font_to_use) in enumerate(texts):
                y = i * line_height + 10
                x = 10
                # 描边：先画黑色边框
                stroke_width = 3
                draw.text(
                    (x, y),
                    text,
                    font=font_to_use,
                    fill=fill_color,
                    stroke_width=stroke_width,
                    stroke_fill=BLACK,
                )

            # 转回 OpenCV 并保存
            img = np.array(img_pil)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                output_image = temp_file.name
                # 保存处理后的图片
                logger.debug(f"保存处理后的图片到: {output_image}")
                cv2.imwrite(output_image, img)
                # 获取base64编码
                with open(output_image, "rb") as f:
                    base64_image = base64.b64encode(f.read()).decode("utf-8")
        return base64_image
    finally:
        # 清理临时文件
        for temp_file_path in [input_image, output_image]:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"已清理临时文件: {temp_file_path}")
                except OSError as e:
                    logger.warning(f"无法删除临时文件 {temp_file_path}: {e}")


def get_first_frame_from_video(video_path: str, output_image_path: str) -> bool:
    """
    从视频中提取第一帧并保存为图片。
    
    Args:
        video_path: 视频文件路径
        output_image_path: 输出图片路径
        
    Returns:
        bool: 成功返回True，失败返回False
    """
    vidcap = cv2.VideoCapture(video_path)
    success, image = vidcap.read()
    if success:
        cv2.imwrite(output_image_path, image)
        logger.info(f"成功从 {video_path} 提取第一帧并保存到 {output_image_path}")
        return True
    else:
        logger.warning(f"无法从 {video_path} 提取第一帧。")
        return False


def replace_video_cover_with_text(
    video_path: str, 
    input_image_path: str, 
    language: str, 
    text: str
) -> Optional[str]:
    """
    基于输入的视频路径、图片路径、语种和文本，将视频的首页换成 draw_text 后的图片。
    实际上是提取视频第一帧，在其上绘制文本，然后保存为新的图片。
    
    Args:
        video_path: 视频文件路径
        input_image_path: 输入图片路径
        language: 语言代码
        text: 要绘制的文本
        
    Returns:
        Optional[str]: 成功返回新视频路径，失败返回None或False
    """
    # 1. 从视频中提取第一帧
    output_image_path = (
        input_image_path + "drow_text.png"
    )  # 临时文件，用于保存提取的第一帧
    # 2. 根据语种选择合适的字体
    font_filename = FONT_MAP.get(language, "Arial")  # 默认使用Arial
    # 字体路径在 utils/ttfs 下，需要构建完整路径
    font_base_dir = os.path.join(os.path.dirname(__file__), "ttfs")
    font_path = os.path.join(font_base_dir, font_filename)

    # 检查字体文件是否存在
    if not os.path.exists(font_path):
        logger.error(f"字体文件 {font_path} 不存在，无法继续处理。")
        raise FileNotFoundError(f"字体文件 {font_path} 不存在")
    texts = text.split("\\n")

    logger.debug(f"准备绘制的文本内容: {texts}")
    draw_text(texts, input_image_path, output_image_path, font_path)
    logger.info(f"成功在 {input_image_path} 上绘制文本并保存到 {output_image_path}")
    new_video_path = set_video_cover_image(video_path, output_image_path)
    if not new_video_path:
        logger.warning(f"无法将 {video_path} 的第一帧替换为 {output_image_path}。")
        return False

    return new_video_path


import os
import subprocess
import traceback


def set_video_cover_image(video_path: str, image_path: str) -> Optional[str]:
    """
    将视频文件的封面图替换为指定的图片。
    这会将图片嵌入到视频文件中，作为其"附加图片"或"封面艺术"，
    以便播放器或文件管理器显示。

    Args:
        video_path: 原始视频文件的路径
        image_path: 用作封面图的图片文件的路径

    Returns:
        str: 新生成视频文件的路径，如果操作失败则返回 None。
    """
    logger.info(f"正在尝试将视频 {video_path} 的封面图设置为图片 {image_path}...")

    # Determine the output video path
    # It's usually better to output to a new file and then replace/rename
    # or specify a distinct name to avoid issues with overwriting
    output_video_path = f"{os.path.splitext(video_path)[0]}_with_cover.mp4"

    # Determine the MIME type for the attached image
    image_extension = os.path.splitext(image_path)[1].lower()
    if image_extension in (".jpg", ".jpeg"):
        mimetype = "image/jpeg"
    elif image_extension == ".png":
        mimetype = "image/png"
    else:
        logger.warning(f"不支持的图片格式 {image_extension}。封面图可能无法正常显示。")
        mimetype = "application/octet-stream"  # Fallback

    command = [
        "ffmpeg",
        "-y",  # 添加这个参数表示默认覆盖输出文件
        "-i",
        video_path,  # 第一个输入：原始视频
        "-i",
        image_path,  # 第二个输入：图片
        "-map",
        "0",  # 映射第一个输入的所有流
        "-map",
        "1",  # 映射第二个输入
        "-c",
        "copy",  # 复制所有流（默认）
        "-c:v:1",
        "png",  # 特别指定第二个视频流（图片）的编码格式为PNG
        "-disposition:v:1",
        "attached_pic",  # 将第二个视频流标记为附加图片
        output_video_path,
    ]
    logger.debug(f"FFmpeg command: {' '.join(command)}")
    try:
        # Execute the FFmpeg command
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.debug(f"FFmpeg output (stdout): {result.stdout}")
        if result.stderr:
            logger.debug(f"FFmpeg output (stderr): {result.stderr}")
        logger.info(f"视频封面图已成功设置为：{output_video_path}")
        return output_video_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg command failed with error code {e.returncode}")
        logger.error(f"FFmpeg stdout: {e.stdout}")
        logger.error(f"FFmpeg stderr: {e.stderr}")
        return None
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（FFmpeg处理错误等）
        logger.exception(f"[set_video_cover] 设置视频封面图时发生异常: {e}")
        return None


if __name__ == "__main__":
    # 示例用法
    # 假设有一个视频文件 'test_video.mp4' 和一个输出图片路径 'output_cover.png'
    # 并且字体文件已放在 settings.font_dir 对应目录

    dummy_video_path = "./sample_videos/combined.mp4"
    video_input_path = dummy_video_path  # 替换为你的视频文件路径
    input_image_file = "./sample_videos/0.png"
    language_to_use = "ja-JP-NanamiNeural"
    text_to_draw = "息子が冷たく問う：「母さん、お金を取ったのか？」\\n5万元が消え、親子の絆が砕け散る\\n彼女は潔白を証明するため警察に通報！\\n晩年は自力でこそ、自信が持てる\\n孫の世話で金をなくし、逆に疑われる"
    logger.info(f"开始处理视频封面：{video_input_path}")
    success = replace_video_cover_with_text(
        video_input_path, input_image_file, language_to_use, text_to_draw
    )
    logger.info(f"处理结果: {success}")
