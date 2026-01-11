"""
数据库分片支持

提供基于一致性哈希的分片策略，支持动态添加/移除分片节点
"""
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)

# 类型变量
ModelType = TypeVar('ModelType')
ShardKey = Union[int, str]


@dataclass
class ShardNode:
    """分片节点"""
    name: str
    engine: Engine
    weight: int = 1
    is_active: bool = True
    last_heartbeat: Optional[datetime] = None


class ConsistentHashRing:
    """一致性哈希环"""
    
    def __init__(self, nodes: List[ShardNode], replicas: int = 100):
        """
        初始化一致性哈希环
        
        Args:
            nodes: 分片节点列表
            replicas: 每个节点的虚拟节点数，增加可以提高分布均匀性
        """
        self.replicas = replicas
        self.ring: Dict[int, ShardNode] = {}
        self.sorted_keys: List[int] = []
        
        for node in nodes:
            self.add_node(node)
    
    def _hash(self, key: str) -> int:
        """计算键的哈希值"""
        return int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16)
    
    def add_node(self, node: ShardNode) -> None:
        """添加节点到哈希环"""
        if not node.is_active:
            return
            
        for i in range(self.replicas * node.weight):
            key = self._hash(f"{node.name}:{i}")
            self.ring[key] = node
            self.sorted_keys.append(key)
        
        self.sorted_keys.sort()
    
    def remove_node(self, node_name: str) -> None:
        """从哈希环中移除节点"""
        keys_to_remove = [
            key for key, node in self.ring.items() 
            if node.name == node_name
        ]
        
        for key in keys_to_remove:
            del self.ring[key]
            self.sorted_keys.remove(key)
    
    def get_node(self, key: ShardKey) -> Optional[ShardNode]:
        """获取键对应的节点"""
        if not self.ring:
            return None
            
        key_hash = self._hash(str(key))
        
        # 查找第一个大于等于key_hash的节点
        for node_key in self.sorted_keys:
            if node_key >= key_hash:
                return self.ring[node_key]
        
        # 如果没找到，返回环中的第一个节点
        return self.ring[self.sorted_keys[0]]


class ShardingManager:
    """分片管理器"""
    
    def __init__(self, model_class: Type[ModelType]):
        """
        初始化分片管理器
        
        Args:
            model_class: 要分片的模型类
        """
        self.model_class = model_class
        self.shard_nodes: Dict[str, ShardNode] = {}
        self.hash_ring: Optional[ConsistentHashRing] = None
        self.shard_key_attr: Optional[str] = None
    
    def add_shard(self, name: str, db_url: str, weight: int = 1) -> None:
        """
        添加分片节点
        
        Args:
            name: 分片名称
            db_url: 数据库连接URL
            weight: 节点权重，影响数据分布
        """
        if name in self.shard_nodes:
            raise ValueError(f"Shard {name} already exists")
        
        engine = create_engine(db_url)
        node = ShardNode(name=name, engine=engine, weight=weight)
        self.shard_nodes[name] = node
        self._update_hash_ring()
    
    def remove_shard(self, name: str) -> None:
        """移除分片节点"""
        if name not in self.shard_nodes:
            raise ValueError(f"Shard {name} does not exist")
            
        node = self.shard_nodes.pop(name)
        node.engine.dispose()
        self._update_hash_ring()
    
    def set_shard_key(self, attr_name: str) -> None:
        """设置分片键属性"""
        if not hasattr(self.model_class, attr_name):
            raise AttributeError(
                f"Model {self.model_class.__name__} has no attribute '{attr_name}'"
            )
        self.shard_key_attr = attr_name
    
    def get_shard_for_key(self, key: ShardKey) -> Optional[ShardNode]:
        """获取键对应的分片节点"""
        if not self.hash_ring:
            return None
        return self.hash_ring.get_node(key)
    
    def get_session_for_key(self, key: ShardKey) -> Optional[Session]:
        """获取键对应的数据库会话"""
        node = self.get_shard_for_key(key)
        if not node:
            return None
        return Session(node.engine)
    
    def get_all_sessions(self) -> List[Session]:
        """获取所有分片的数据库会话"""
        return [Session(node.engine) for node in self.shard_nodes.values()]
    
    def _update_hash_ring(self) -> None:
        """更新哈希环"""
        active_nodes = [
            node for node in self.shard_nodes.values() 
            if node.is_active
        ]
        self.hash_ring = ConsistentHashRing(active_nodes)
    
    def get_shard_stats(self) -> Dict[str, Any]:
        """获取分片统计信息"""
        stats = {
            "shard_count": len(self.shard_nodes),
            "active_shards": sum(1 for n in self.shard_nodes.values() if n.is_active),
            "shards": []
        }
        
        for name, node in self.shard_nodes.items():
            stats["shards"].append({
                "name": name,
                "weight": node.weight,
                "is_active": node.is_active,
                "last_heartbeat": node.last_heartbeat
            })
            
        return stats


class ShardedDAO:
    """支持分片的数据访问对象"""
    
    def __init__(self, model_class: Type[ModelType], shard_key_attr: str):
        """
        初始化分片DAO
        
        Args:
            model_class: 模型类
            shard_key_attr: 用于分片的属性名
        """
        self.sharding_manager = ShardingManager(model_class)
        self.sharding_manager.set_shard_key(shard_key_attr)
    
    def add_shard(self, name: str, db_url: str, weight: int = 1) -> None:
        """添加分片"""
        self.sharding_manager.add_shard(name, db_url, weight)
    
    def get_shard_for_object(self, obj: ModelType) -> Optional[Session]:
        """获取对象对应的分片会话"""
        if not self.sharding_manager.shard_key_attr:
            raise ValueError("Shard key attribute not set")
            
        key = getattr(obj, self.sharding_manager.shard_key_attr)
        return self.sharding_manager.get_session_for_key(key)
    
    async def save(self, obj: ModelType, commit: bool = True) -> None:
        """保存对象到对应的分片"""
        session = self.get_shard_for_object(obj)
        if not session:
            raise ValueError("No available shard for object")
            
        try:
            session.add(obj)
            if commit:
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save {obj.__class__.__name__}: {e}")
            raise
        finally:
            if commit:
                session.close()
    
    async def get(self, id: ShardKey, shard_key: Optional[ShardKey] = None) -> Optional[ModelType]:
        """
        根据ID和分片键获取对象
        
        Args:
            id: 对象ID
            shard_key: 分片键，如果为None则使用id作为分片键
        """
        key = shard_key or id
        session = self.sharding_manager.get_session_for_key(key)
        if not session:
            return None
            
        try:
            return session.query(self.sharding_manager.model_class).get(id)
        finally:
            session.close()
    
    def query_across_shards(self) -> List[ModelType]:
        """跨分片查询所有数据"""
        results = []
        for session in self.sharding_manager.get_all_sessions():
            try:
                results.extend(session.query(self.sharding_manager.model_class).all())
            finally:
                session.close()
        return results
