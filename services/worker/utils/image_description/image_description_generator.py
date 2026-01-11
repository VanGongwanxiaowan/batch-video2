"""图像描述生成主入口模块

提供统一的图像描述生成接口，根据配置自动选择V1或V2生成方式。
保持向后兼容，原有接口保持不变。

模块结构：
    - config: 配置数据类（GeneratorConfig, ImageDescriptionConfig）
    - factory: 生成器工厂（GeneratorFactory）
    - v1_generator: V1生成器实现（逐行格式）
    - v2_generator: V2生成器实现（JSON格式）
    - base_generator: 生成器基类
"""
import os
from typing import Any, Dict, Union

from utils.srt_processor import load_srtdata, load_srtdata_from_json, save_srtdata_to_json

from core.logging_config import setup_logging

from .config import DEFAULT_MODEL, GeneratorConfig, ImageDescriptionConfig
from .factory import GeneratorFactory
from .v1_generator import V1ImageDescriptionGenerator
from .v2_generator import V2ImageDescriptionGenerator

logger = setup_logging("worker.utils.image_description.image_description_generator")


# 向后兼容：保留原有函数接口
def generate_descriptions_v1(
    srtdata: Dict[str, Dict[str, Any]],
    basepath: str,
    model: str,
    baseprompt: str,
    prefix: str,
    prompt_cover_image: str,
) -> Dict[str, Dict[str, Any]]:
    """[向后兼容] 使用V1方法生成图像描述（逐行格式）。
    
    此函数保持原有接口，内部使用新的V1ImageDescriptionGenerator实现。
    
    Args:
        srtdata: 字幕数据字典
        basepath: 基础路径
        model: 使用的模型
        baseprompt: 基础提示词
        prefix: 提示词前缀
        prompt_cover_image: 封面图像提示词
        
    Returns:
        更新后的字幕数据字典
    """
    config = GeneratorConfig(
        model=model,
        baseprompt=baseprompt,
        prefix=prefix,
        prompt_cover_image=prompt_cover_image,
    )
    generator = GeneratorFactory.create(config, generate_type="none")
    return generator.generate(srtdata, basepath)


def generate_descriptions_v2(
    srtdata: Dict[str, Dict[str, Any]],
    basepath: str,
    model: str,
    baseprompt: str,
    prefix: str,
    prompt_cover_image: str,
) -> Dict[str, Dict[str, Any]]:
    """[向后兼容] 使用V2方法生成图像描述（JSON格式）。
    
    此函数保持原有接口，内部使用新的V2ImageDescriptionGenerator实现。
    
    Args:
        srtdata: 字幕数据字典
        basepath: 基础路径
        model: 使用的模型
        baseprompt: 基础提示词
        prefix: 提示词前缀
        prompt_cover_image: 封面图像提示词
        
    Returns:
        更新后的字幕数据字典
        
    Raises:
        Exception: 如果生成失败
    """
    config = GeneratorConfig(
        model=model,
        baseprompt=baseprompt,
        prefix=prefix,
        prompt_cover_image=prompt_cover_image,
    )
    generator = GeneratorFactory.create(config, generate_type="v2")
    return generator.generate(srtdata, basepath)


def generate_image_descriptions(
    srtpath: str,
    srtdatapath: str,
    prompt_gen_images: str,
    prompt_prefix: str,
    prompt_cover_image: str,
    model: str = DEFAULT_MODEL,
    topic_extra: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """生成图像描述的主入口函数。
    
    此函数会根据配置选择使用V1（逐行格式）或V2（JSON格式）生成方式。
    
    Args:
        srtpath: SRT文件路径
        srtdatapath: 数据JSON文件路径
        prompt_gen_images: 图像生成提示词
        prompt_prefix: 提示词前缀
        prompt_cover_image: 封面图像提示词
        model: 使用的LLM模型名称，默认为"deepseek-v3"
        topic_extra: 主题额外配置，用于选择生成方式
            - 如果generate_type为"none"或空字符串，使用V1方式
            - 否则使用V2方式
        
    Returns:
        包含以下键的字典：
            - basepath: 基础路径
            - srtdata: 更新后的字幕数据字典，prompt字段已填充
            
    Raises:
        FileNotFoundError: 如果SRT文件不存在且JSON文件也不存在
        ValueError: 如果配置无效
        
    Example:
        >>> result = generate_image_descriptions(
        ...     srtpath="/path/to/data.srt",
        ...     srtdatapath="/path/to/data.json",
        ...     prompt_gen_images="Generate an image",
        ...     prompt_prefix="A beautiful",
        ...     prompt_cover_image="Cover image",
        ...     model="deepseek-v3",
        ...     topic_extra={"generate_type": "v2"}
        ... )
        >>> print(result["basepath"])
        /path/to
        >>> print(result["srtdata"]["0"]["prompt"])
        Cover image
    """
    # 创建配置对象
    config = ImageDescriptionConfig(
        srtpath=srtpath,
        srtdatapath=srtdatapath,
        prompt_gen_images=prompt_gen_images,
        prompt_prefix=prompt_prefix,
        prompt_cover_image=prompt_cover_image,
        model=model,
        topic_extra=topic_extra or {},
    )
    
    return _generate_with_config(config)


def _generate_with_config(config: ImageDescriptionConfig) -> Dict[str, Any]:
    """使用配置对象生成图像描述（内部实现）。
    
    Args:
        config: 图像描述生成配置
        
    Returns:
        包含basepath和srtdata的字典
        
    Raises:
        FileNotFoundError: 如果SRT文件不存在且JSON文件也不存在
        ValueError: 如果配置无效
    """
    # 计算基础路径
    basepath = _extract_basepath(config.srtpath)
    
    # 加载字幕数据
    srtdata = _load_srtdata(config.srtpath, config.srtdatapath)
    
    # 保存初始数据
    save_srtdata_to_json(srtdata, basepath)
    
    # 检查是否需要处理
    if not _needs_processing(srtdata):
        logger.info("所有字幕已包含提示词，跳过生成")
        return {"basepath": basepath, "srtdata": srtdata}
    
    # 创建生成器并执行
    generator_config = config.to_generator_config()
    generate_type = config.get_generate_type()
    generator = GeneratorFactory.create(generator_config, generate_type)
    
    try:
        srtdata = generator.generate(srtdata, basepath)
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（图像描述生成错误等）
        logger.error(f"[generate_descriptions] 生成图像描述失败: {e}", exc_info=True)
        raise
    
    # 保存最终结果
    save_srtdata_to_json(srtdata, basepath)
    
    return {"basepath": basepath, "srtdata": srtdata}


def _extract_basepath(srtpath: str) -> str:
    """从SRT文件路径提取基础路径。
    
    Args:
        srtpath: SRT文件路径，通常以"/data.srt"结尾
        
    Returns:
        基础路径（不包含文件名）
        
    Example:
        >>> _extract_basepath("/path/to/data.srt")
        '/path/to'
    """
    return srtpath.replace("/data.srt", "")


def _load_srtdata(srtpath: str, srtdatapath: str) -> Dict[str, Dict[str, Any]]:
    """加载字幕数据。
    
    优先从JSON文件加载，如果不存在则从SRT文件加载。
    
    Args:
        srtpath: SRT文件路径
        srtdatapath: 数据JSON文件路径
        
    Returns:
        字幕数据字典
        
    Raises:
        FileNotFoundError: 如果两个文件都不存在
    """
    if os.path.exists(srtdatapath):
        logger.debug(f"从JSON文件加载字幕数据: {srtdatapath}")
        return load_srtdata_from_json(srtdatapath)
    elif os.path.exists(srtpath):
        logger.debug(f"从SRT文件加载字幕数据: {srtpath}")
        return load_srtdata(srtpath)
    else:
        raise FileNotFoundError(
            f"无法找到字幕数据文件。SRT路径: {srtpath}, JSON路径: {srtdatapath}"
        )


def _needs_processing(srtdata: Dict[str, Dict[str, Any]]) -> bool:
    """检查是否需要处理。
    
    检查字幕数据中是否存在空的prompt字段，如果存在则需要处理。
    
    Args:
        srtdata: 字幕数据字典
        
    Returns:
        如果存在空的prompt字段，返回True；否则返回False
    """
    return any(value.get("prompt", "") == "" for value in srtdata.values())

