"""图像描述生成模块（向后兼容包装）

此模块已被重构为模块化结构，位于 utils.image_description 包中。
为了保持向后兼容，此文件保留原有函数接口，但内部调用新的模块化实现。

新模块结构：
- utils.image_description.json_utils: JSON处理工具
- utils.image_description.base_generator: 生成器基类
- utils.image_description.v1_generator: V1生成器（逐行格式）
- utils.image_description.v2_generator: V2生成器（JSON格式）
- utils.image_description.image_description_generator: 主入口

建议新代码直接使用新模块，而不是此兼容包装。
"""
# 从新模块导入所有函数，保持向后兼容
from utils.image_description import (
    generate_descriptions_v1,
    generate_descriptions_v2,
    generate_image_descriptions,
)

# 导出所有函数，保持原有接口
__all__ = [
    "generate_image_descriptions",
    "generate_descriptions_v1",
    "generate_descriptions_v2",
]


def fix_json(text: str) -> str:
    """
    修复JSON格式文本
    
    Args:
        text: 原始文本
        
    Returns:
        修复后的JSON字符串
    """
    text = text.replace("```", "").strip()
    text = text.replace("JSON", "").strip()
    text = text.replace("json", "").strip()
    # 从第一个 { 开始 最后一个 }结束
    text = text[text.find("{") : text.rfind("}") + 1]
    text = repair_json(text)
    try:
        json.loads(text)
        return text
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"调用 LLM 接口返回内容格式错误: {e}")
        return text


def generate_descriptions_v2(
    srtdata: Dict[str, Dict[str, Any]],
    basepath: str,
    model: str,
    baseprompt: str,
    prefix: str,
    prompt_cover_image: str,
) -> Dict[str, Dict[str, Any]]:
    """
    使用v2方法生成图像描述（JSON格式）
    
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
    for attempt in range(5):
        try:
            jsonstr = json.dumps(srtdata, ensure_ascii=False, indent=4)
            prompt = f"""
            {jsonstr}

            {baseprompt}
            """
            logger.info("开始API请求 (v2)")
            result = chat_with_llm(prompt, model)
            logger.debug(f"API返回结果: {result}")
            result = fix_json(result)
            logger.debug(f"修复后的JSON: {result}")
            new_srtdata = json.loads(result)
            
            for key, val in new_srtdata.items():
                srtdata[key]["prompt"] = prefix + val["prompt"]
                srtdata[key]["is_actor"] = val["is_actor"]

            if prompt_cover_image.strip():
                srtdata["0"]["prompt"] = prompt_cover_image
                srtdata["0"]["is_actor"] = True

            return srtdata
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Generate Desc Failed (attempt {attempt + 1}/5)! JSON解析或数据格式错误: {e}")
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他未预期的异常
            logger.warning(f"[generate_descriptions_v2] Generate Desc Failed (attempt {attempt + 1}/5)! 未知错误: {e}")

    raise Exception("Generate Desc Failed after 5 attempts.")


def generate_descriptions_v1(
    srtdata: Dict[str, Dict[str, Any]],
    basepath: str,
    model: str,
    baseprompt: str,
    prefix: str,
    prompt_cover_image: str,
) -> Dict[str, Dict[str, Any]]:
    """
    使用v1方法生成图像描述（逐行格式）
    
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
    def process_batch(unproceed: List[str], prompt_cover_image: str) -> None:
        """处理一批未处理的字幕
        
        Args:
            unproceed: 未处理的字幕列表
            prompt_cover_image: 封面图像提示词
        """
        srtcontent = "\n".join(unproceed)
        prompt = f"""
        {srtcontent}

        {baseprompt}
        """
        logger.info("开始API请求 (v1)")
        res = chat_with_llm(prompt, model=model)
        res = res.strip()
        reslist = res.split("\n")
        
        for resl in reslist:
            if resl.strip().strip(".") == "":
                continue
            ressplit = resl.strip(".").split(".")
            if len(ressplit) < 2:
                continue
            try:
                idx = int(ressplit[0])
                prompt_en = ".".join(ressplit[1:]).strip()
                if not prompt_en:
                    continue
                if prefix:
                    prompt_en = f"{prefix}.{prompt_en}"
                
                if int(idx) in srtdata:
                    if int(idx) == 0 and prompt_cover_image.strip():
                        prompt_en = prompt_cover_image
                    srtdata[int(idx)]["prompt"] = prompt_en
                if str(idx) in srtdata:
                    if int(idx) == 0 and prompt_cover_image.strip():
                        prompt_en = prompt_cover_image
                    srtdata[str(idx)]["prompt"] = prompt_en
            except (ValueError, KeyError, IndexError) as e:
                logger.warning(f"处理描述时出错（数据格式错误）: {e}")
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except Exception as e:
                # 其他未预期的异常
                logger.warning(f"[process_batch] 处理描述时出错（未知错误）: {e}")

    while True:
        unproceed = []
        unproceed_list = []
        for key, value in srtdata.items():
            imagepath = os.path.join(basepath, f"{key}.png")
            if os.path.exists(imagepath):
                continue
            if len(unproceed) >= 50:
                unproceed_list.append(unproceed)
                unproceed = []

            if value["prompt"] == "":
                unproceed.append(f"{key}. {value['text']}")

        if len(unproceed) == 0:
            break
        if len(unproceed) > 0:
            unproceed_list.append(unproceed)
            unproceed = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(
                process_batch, unproceed_list, [prompt_cover_image] * len(unproceed_list)
            )
        
        # 保存中间结果
        from utils.srt_processor import save_srtdata_to_json
        save_srtdata_to_json(srtdata, basepath)
    
    return srtdata


def generate_image_descriptions(
    srtpath: str,
    srtdatapath: str,
    prompt_gen_images: str,
    prompt_prefix: str,
    prompt_cover_image: str,
    model: str = "deepseek-v3",
    topic_extra: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    生成图像描述的主入口函数
    
    Args:
        srtpath: SRT文件路径
        srtdatapath: 数据JSON文件路径
        prompt_gen_images: 图像生成提示词
        prompt_prefix: 提示词前缀
        prompt_cover_image: 封面图像提示词
        model: 使用的模型
        topic_extra: 主题额外配置
        
    Returns:
        包含字幕数据的字典
    """
    from utils.srt_processor import load_srtdata, load_srtdata_from_json, save_srtdata_to_json
    
    basepath = srtpath.replace("/data.srt", "")
    topic_extra = topic_extra or {}
    
    # 加载字幕数据
    if os.path.exists(srtdatapath):
        srtdata = load_srtdata_from_json(srtdatapath)
    else:
        srtdata = load_srtdata(srtpath)
    
    # 保存初始数据
    save_srtdata_to_json(srtdata, basepath)

    # 检查是否需要处理
    need_process = any(value["prompt"] == "" for value in srtdata.values())
    if not need_process:
        return {"basepath": basepath, "srtdata": srtdata}

    # 根据生成类型选择方法
    if topic_extra.get("generate_type", "none") in ["", "none"]:
        srtdata = generate_descriptions_v1(
            srtdata,
            basepath=basepath,
            model=model,
            baseprompt=prompt_gen_images,
            prefix=prompt_prefix,
            prompt_cover_image=prompt_cover_image,
        )
    else:
        srtdata = generate_descriptions_v2(
            srtdata,
            basepath=basepath,
            model=model,
            baseprompt=prompt_gen_images,
            prefix=prompt_prefix,
            prompt_cover_image=prompt_cover_image,
        )
    
    # 保存最终结果
    save_srtdata_to_json(srtdata, basepath)
    return {"basepath": basepath, "srtdata": srtdata}

