"""V1图像描述生成器

使用逐行格式生成图像描述（旧版方法）。
"""
import concurrent.futures
import os
from typing import Any, Dict, List

from utils.srt_processor import save_srtdata_to_json
from utils.util import chat_with_llm

from core.logging_config import setup_logging

from .base_generator import ImageDescriptionGenerator

logger = setup_logging("worker.utils.image_description.v1_generator")


class V1ImageDescriptionGenerator(ImageDescriptionGenerator):
    """V1图像描述生成器（逐行格式）。
    
    此生成器使用逐行格式与LLM交互：
    - 输入：多行文本，每行格式为 "索引. 字幕文本"
    - 输出：多行文本，每行格式为 "索引. 生成的提示词"
    """
    
    BATCH_SIZE = 50  # 每批处理的字幕数量
    MAX_WORKERS = 4  # 并发处理的工作线程数
    
    def generate(
        self,
        srtdata: Dict[str, Dict[str, Any]],
        basepath: str,
    ) -> Dict[str, Dict[str, Any]]:
        """生成图像描述（逐行格式）。
        
        Args:
            srtdata: 字幕数据字典
            basepath: 基础路径，用于检查图像文件是否存在
            
        Returns:
            更新后的字幕数据字典
        """
        while True:
            batches = self._collect_unprocessed_batches(srtdata, basepath)
            
            if not batches:
                break
            
            self._process_batches_parallel(batches, srtdata)
            
            # 保存中间结果
            save_srtdata_to_json(srtdata, basepath)
        
        # 应用封面图像提示词
        self.apply_cover_image_prompt(srtdata)
        
        return srtdata
    
    def _collect_unprocessed_batches(
        self,
        srtdata: Dict[str, Dict[str, Any]],
        basepath: str,
    ) -> List[List[str]]:
        """收集未处理的字幕批次。
        
        Args:
            srtdata: 字幕数据字典
            basepath: 基础路径
            
        Returns:
            批次列表，每个批次是一个字符串列表，格式为 ["索引. 字幕文本", ...]
        """
        batches = []
        current_batch = []
        
        for key, value in srtdata.items():
            # 如果图像文件已存在，跳过
            imagepath = os.path.join(basepath, f"{key}.png")
            if os.path.exists(imagepath):
                continue
            
            # 如果提示词已存在，跳过
            if value.get("prompt", ""):
                continue
            
            # 添加到当前批次
            current_batch.append(f"{key}. {value['text']}")
            
            # 如果批次达到大小限制，保存并创建新批次
            if len(current_batch) >= self.BATCH_SIZE:
                batches.append(current_batch)
                current_batch = []
        
        # 添加最后一个批次（如果有）
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _process_batches_parallel(
        self,
        batches: List[List[str]],
        srtdata: Dict[str, Dict[str, Any]],
    ) -> None:
        """并行处理多个批次。
        
        Args:
            batches: 批次列表
            srtdata: 字幕数据字典（会被修改）
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            executor.map(
                lambda batch: self._process_single_batch(batch, srtdata),
                batches,
            )
    
    def _process_single_batch(
        self,
        batch: List[str],
        srtdata: Dict[str, Dict[str, Any]],
    ) -> None:
        """处理单个批次。
        
        Args:
            batch: 批次内容，格式为 ["索引. 字幕文本", ...]
            srtdata: 字幕数据字典（会被修改）
        """
        # 构建提示词
        srtcontent = "\n".join(batch)
        prompt = f"""
        {srtcontent}

        {self.baseprompt}
        """
        
        logger.info("开始API请求 (v1)")
        
        try:
            # 调用LLM
            response = chat_with_llm(prompt, model=self.model)
            response = response.strip()
            
            # 解析响应
            self._parse_and_update_srtdata(response, srtdata)
            
        except Exception as e:
            logger.error(f"处理批次时出错: {e}", exc_info=True)
    
    def _parse_and_update_srtdata(
        self,
        response: str,
        srtdata: Dict[str, Dict[str, Any]],
    ) -> None:
        """解析LLM响应并更新字幕数据。
        
        Args:
            response: LLM响应文本，每行格式为 "索引. 提示词"
            srtdata: 字幕数据字典（会被修改）
        """
        lines = response.split("\n")
        
        for line in lines:
            line = line.strip()
            
            # 跳过空行
            if not line or line == ".":
                continue
            
            # 解析行：格式为 "索引. 提示词"
            parts = line.strip(".").split(".", 1)
            if len(parts) < 2:
                continue
            
            try:
                idx = int(parts[0])
                prompt_en = parts[1].strip()
                
                # 跳过空提示词
                if not prompt_en:
                    continue
                
                # 添加前缀
                if self.prefix:
                    prompt_en = f"{self.prefix}.{prompt_en}"
                
                # 更新字幕数据（支持整数和字符串索引）
                self._update_srtdata_entry(srtdata, idx, prompt_en)
                
            except (ValueError, KeyError, IndexError) as e:
                logger.warning(f"解析描述行时出错（数据格式错误）: {line}, 错误: {e}")
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except Exception as e:
                # 其他未预期的异常
                logger.warning(f"[_parse_and_update_srtdata] 解析描述行时出错（未知错误）: {line}, 错误: {e}")
    
    def _update_srtdata_entry(
        self,
        srtdata: Dict[str, Dict[str, Any]],
        idx: int,
        prompt_en: str,
    ) -> None:
        """更新字幕数据条目。
        
        Args:
            srtdata: 字幕数据字典（会被修改）
            idx: 字幕索引
            prompt_en: 生成的提示词
        """
        # 处理封面图像提示词覆盖
        if idx == 0 and self.prompt_cover_image.strip():
            prompt_en = self.prompt_cover_image
        
        # 更新数据（支持整数和字符串索引）
        if idx in srtdata:
            srtdata[idx]["prompt"] = prompt_en
        elif str(idx) in srtdata:
            srtdata[str(idx)]["prompt"] = prompt_en

