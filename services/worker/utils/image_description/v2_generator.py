"""V2图像描述生成器

使用JSON格式生成图像描述（新版方法）。
"""
import json
from typing import Any, Dict

from utils.util import chat_with_llm

from core.logging_config import setup_logging

from .base_generator import ImageDescriptionGenerator
from .json_utils import fix_and_validate_json, parse_json_safely

logger = setup_logging("worker.utils.image_description.v2_generator")


class V2ImageDescriptionGenerator(ImageDescriptionGenerator):
    """V2图像描述生成器（JSON格式）。
    
    此生成器使用JSON格式与LLM交互：
    - 输入：完整的字幕数据JSON
    - 输出：包含prompt和is_actor字段的JSON
    """
    
    MAX_RETRIES = 5  # 最大重试次数
    
    def generate(
        self,
        srtdata: Dict[str, Dict[str, Any]],
        basepath: str,
    ) -> Dict[str, Dict[str, Any]]:
        """生成图像描述（JSON格式）。
        
        Args:
            srtdata: 字幕数据字典
            basepath: 基础路径（此方法中未使用，但保留以保持接口一致）
            
        Returns:
            更新后的字幕数据字典
            
        Raises:
            Exception: 如果所有重试都失败
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                result = self._generate_with_retry(srtdata)
                
                # 应用封面图像提示词
                self.apply_cover_image_prompt(srtdata)
                
                return srtdata
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(
                    f"生成描述失败（尝试 {attempt + 1}/{self.MAX_RETRIES}）: "
                    f"JSON解析或数据格式错误: {e}"
                )
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except Exception as e:
                # 其他未预期的异常
                logger.warning(
                    f"[generate] 生成描述失败（尝试 {attempt + 1}/{self.MAX_RETRIES}）: "
                    f"未知错误: {e}"
                )
        
        raise Exception(f"生成描述失败，已重试 {self.MAX_RETRIES} 次")
    
    def _generate_with_retry(
        self,
        srtdata: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """执行一次生成尝试。
        
        Args:
            srtdata: 字幕数据字典（会被修改）
            
        Returns:
            更新后的字幕数据字典
        """
        # 构建提示词
        jsonstr = json.dumps(srtdata, ensure_ascii=False, indent=4)
        prompt = f"""
        {jsonstr}

        {self.baseprompt}
        """
        
        logger.info("开始API请求 (v2)")
        
        # 调用LLM
        result = chat_with_llm(prompt, self.model)
        logger.debug(f"API返回结果: {result}")
        
        # 修复和验证JSON
        fixed_json = fix_and_validate_json(result)
        logger.debug(f"修复后的JSON: {fixed_json}")
        
        # 解析JSON
        new_srtdata = parse_json_safely(fixed_json)
        if new_srtdata is None:
            raise ValueError("无法解析LLM返回的JSON")
        
        # 更新字幕数据
        self._update_srtdata_from_response(srtdata, new_srtdata)
        
        return srtdata
    
    def _update_srtdata_from_response(
        self,
        srtdata: Dict[str, Dict[str, Any]],
        new_srtdata: Dict[str, Dict[str, Any]],
    ) -> None:
        """从LLM响应更新字幕数据。
        
        Args:
            srtdata: 原始字幕数据字典（会被修改）
            new_srtdata: LLM返回的新数据字典
        """
        for key, val in new_srtdata.items():
            if key not in srtdata:
                logger.warning(f"响应中包含未知的键: {key}")
                continue
            
            # 更新prompt和is_actor字段
            if "prompt" in val:
                srtdata[key]["prompt"] = self.prefix + val["prompt"]
            if "is_actor" in val:
                srtdata[key]["is_actor"] = val["is_actor"]

