"""字幕数据处理模块"""
import json
import os
from typing import Any, Dict

import pysrt

from core.logging_config import setup_logging

logger = setup_logging("worker.utils.srt_processor")


def load_srtdata(srtpath: str) -> Dict[str, Dict[str, Any]]:
    """
    从SRT文件加载字幕数据并进行合并处理
    
    Args:
        srtpath: SRT文件路径
        
    Returns:
        处理后的字幕数据字典
    """
    srts = pysrt.open(srtpath, encoding="utf-8")
    srtdata = {}
    for index, srt in enumerate(srts):
        srtdata[str(index)] = {
            "text": srt.text,
            "start": srt.start.ordinal,
            "end": srt.end.ordinal,
            "duration": srt.duration.ordinal,
            "prompt": "",
        }
    
    # 合并短片段，最多处理3次
    for _ in range(3):
        new_srtdata = []
        index = 0
        for key, values in srtdata.items():
            duration = values["duration"]
            if index == 0:
                new_srtdata.append(values)
            elif duration > 3000 and new_srtdata[-1]["duration"] > 7000:
                new_srtdata.append(values)
            else:
                if new_srtdata[-1]["duration"] > 7000:
                    new_srtdata.append(values)
                else:
                    new_srtdata[-1]["text"] += f",{values['text']}"
                    new_srtdata[-1]["duration"] += duration
                    new_srtdata[-1]["end"] = values["end"]
            index += 1

        # 最后一个片段时间增加0.3秒
        new_srtdata[-1]["duration"] += 300
        new_srtdata[-1]["end"] += 300

        srtdata = {str(key): values for key, values in enumerate(new_srtdata)}
    
    return srtdata


def save_srtdata_to_json(srtdata: Dict[str, Dict[str, Any]], basepath: str) -> str:
    """
    将字幕数据保存到JSON文件
    
    Args:
        srtdata: 字幕数据字典
        basepath: 基础路径
        
    Returns:
        JSON文件路径
    """
    data = {"basepath": basepath, "srtdata": srtdata}
    json_path = os.path.join(basepath, "data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return json_path


def load_srtdata_from_json(json_path: str) -> Dict[str, Dict[str, Any]]:
    """
    从JSON文件加载字幕数据
    
    Args:
        json_path: JSON文件路径
        
    Returns:
        字幕数据字典
    """
    if not os.path.exists(json_path):
        return {}
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("srtdata", {})

