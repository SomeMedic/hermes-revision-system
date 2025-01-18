import json
from datetime import datetime
from typing import Dict, Optional, List


class Commit:
    def __init__(self, 
                 tree_hash: str,
                 message: str,
                 author: str,
                 parent: Optional[str] = None,
                 timestamp: Optional[float] = None):
        self.tree_hash = tree_hash
        self.message = message
        self.author = author
        self.parent = parent
        self.timestamp = timestamp or datetime.now().timestamp()
    
    def to_dict(self) -> Dict:
        """Преобразует коммит в словарь"""
        return {
            "tree": self.tree_hash,
            "parent": self.parent,
            "author": self.author,
            "message": self.message,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Commit':
        """Создает объект коммита из словаря"""
        return cls(
            tree_hash=data["tree"],
            parent=data.get("parent"),
            author=data["author"],
            message=data["message"],
            timestamp=data["timestamp"]
        )
    
    def serialize(self) -> bytes:
        """Сериализует коммит в bytes"""
        return json.dumps(self.to_dict()).encode()
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'Commit':
        """Десериализует коммит из bytes"""
        return cls.from_dict(json.loads(data.decode())) 