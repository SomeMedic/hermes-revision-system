import json
from typing import Dict, List


class Tree:
    def __init__(self, entries: Dict[str, str] = None):
        """
        entries: словарь, где ключ - путь к файлу, значение - хеш содержимого
        """
        self.entries = entries or {}
    
    def add_entry(self, path: str, hash_value: str) -> None:
        """Добавляет файл в дерево"""
        self.entries[path] = hash_value
    
    def get_entry(self, path: str) -> str:
        """Возвращает хеш файла по пути"""
        return self.entries.get(path)
    
    def to_dict(self) -> Dict[str, str]:
        """Преобразует дерево в словарь"""
        return self.entries
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Tree':
        """Создает объект дерева из словаря"""
        return cls(entries=data)
    
    def serialize(self) -> bytes:
        """Сериализует дерево в bytes"""
        return json.dumps(self.to_dict()).encode()
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'Tree':
        """Десериализует дерево из bytes"""
        return cls.from_dict(json.loads(data.decode())) 