import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer, util
from worker.config import settings

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("worker.utils.image_embedding_tool", log_to_file=False)

EMBEDDING_MODEL = str(settings.model_cache_dir / "all-MiniLM-L6-v2")
class ImageEmbeddingTool:
    def __init__(
        self, 
        data_file: str = "image_embeddings.json", 
        model_name: str = EMBEDDING_MODEL
    ) -> None:
        """
        初始化图片embedding工具
        
        Args:
            data_file: 数据文件路径
            model_name: 模型名称或路径
        """
        self.data_file = os.path.join(os.path.dirname(__file__), data_file)
        self.model = SentenceTransformer(model_name)
        self.image_data = self._load_data()

    def _load_data(self) -> List[Dict[str, Any]]:
        """加载现有的图片embedding数据
        
        Returns:
            List[Dict[str, Any]]: 图片数据列表，每个元素包含image_path、description和embedding
        """
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 将embedding列表转换为numpy数组
                for item in data:
                    if 'embedding' in item and isinstance(item['embedding'], list):
                        item['embedding'] = np.array(item['embedding'], dtype=np.float32)
                return data
        return []

    def _save_data(self) -> None:
        """保存图片embedding数据到文件"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            # 将numpy数组转换为列表以便json序列化
            serializable_data = []
            for item in self.image_data:
                temp_item = item.copy()
                if 'embedding' in temp_item and isinstance(temp_item['embedding'], np.ndarray):
                    temp_item['embedding'] = temp_item['embedding'].tolist()
                serializable_data.append(temp_item)
            json.dump(serializable_data, f, ensure_ascii=False, indent=4)

    def insert_image_embedding(self, image_path: str, description: str) -> None:
        """
        插入图片和图片描述，并生成描述的embedding数据。
        如果图片路径已存在，则更新其描述和embedding。
        
        Args:
            image_path: 图片路径
            description: 图片描述
        """
        embedding = self.model.encode(description, convert_to_numpy=True)

        # 检查是否已存在该图片路径
        found = False
        for item in self.image_data:
            if item['image_path'] == image_path:
                item['description'] = description
                item['embedding'] = embedding
                found = True
                break
        
        if not found:
            self.image_data.append({
                "image_path": image_path,
                "description": description,
                "embedding": embedding
            })
        
        self._save_data()
        logger.info(f"图片 '{image_path}' 及其描述已插入/更新。")

    def find_similar_image(
        self, 
        query_description: str, 
        top_k: int = 1
    ) -> List[Dict[str, Any]]:
        """
        根据传入的英文描述，匹配最相近的图片。
        返回最相似的图片路径和描述。
        
        Args:
            query_description: 查询描述
            top_k: 返回前k个最相似的图片
            
        Returns:
            List[Dict[str, Any]]: 相似图片列表，每个元素包含image_path、description和similarity
        """
        if not self.image_data:
            logger.warning("没有可用的图片数据进行匹配。")
            return []

        query_embedding = self.model.encode(query_description, convert_to_numpy=True)
        
        # 提取所有存储的embedding
        corpus_embeddings = [item['embedding'] for item in self.image_data]
        
        # 计算余弦相似度
        # util.cos_sim 期望的是张量，这里我们使用numpy手动计算或转换为张量
        # 为了简化，我们假设embedding已经是numpy数组
        similarities = []
        for i, emb in enumerate(corpus_embeddings):
            sim = util.cos_sim(query_embedding, emb).item()
            similarities.append((sim, i))
        
        # 按相似度降序排序
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for sim, idx in similarities[:top_k]:
            results.append({
                "image_path": self.image_data[idx]['image_path'],
                "description": self.image_data[idx]['description'],
                "similarity": sim
            })
        return results

# 示例用法 (可选，用于测试)
if __name__ == "__main__":
    # 注意：首次运行时，SentenceTransformer 会下载模型，需要网络连接
    # 如果没有安装 sentence-transformers，请先安装：pip install sentence-transformers numpy
    
    tool = ImageEmbeddingTool()

    # 示例：批量插入图片embedding（已注释，需要时取消注释并修复）
    # jsonpath = settings.path_manager.base_dir / "ai_image_gen" / "json.json"
    # if os.path.exists(jsonpath):
    #     with open(jsonpath, 'r', encoding='utf-8') as f:
    #         data = json.load(f)
    #     for item in data.values():
    #         image_path = item.get("image_path")
    #         prompt = item.get("prompt", "")
    #         tool.insert_image_embedding(image_path, prompt)


    # 2. 英文描述匹配相近图片
    logger.info("--- 查找相似图片 ---")
    query = "A small animal enjoying itself with a toy."
    similar_images = tool.find_similar_image(query, top_k=2)
    logger.info(f"查询: '{query}'")
    for img in similar_images:
        logger.info(f"  - 图片: {img['image_path']}, 描述: '{img['description']}', 相似度: {img['similarity']:.4f}")

    query = "A scenic view of nature with water and sky."
    similar_images = tool.find_similar_image(query, top_k=1)
    logger.info(f"\n查询: '{query}'")
    for img in similar_images:
        logger.info(f"  - 图片: {img['image_path']}, 描述: '{img['description']}', 相似度: {img['similarity']:.4f}")

    # 检查数据文件是否生成
    logger.info(f"\n数据文件路径: {tool.data_file}")
    if os.path.exists(tool.data_file):
        logger.info("数据文件已成功创建/更新。")
    else:
        logger.warning("数据文件未找到。")