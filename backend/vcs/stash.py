import json
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StashEntry:
    index: int
    message: str
    tree_hash: str
    parent_commit: str
    timestamp: float
    author: str

    def to_dict(self) -> Dict:
        return {
            "index": self.index,
            "message": self.message,
            "tree": self.tree_hash,
            "parent": self.parent_commit,
            "timestamp": self.timestamp,
            "author": self.author
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'StashEntry':
        return cls(
            index=data["index"],
            message=data["message"],
            tree_hash=data["tree"],
            parent_commit=data["parent"],
            timestamp=data["timestamp"],
            author=data["author"]
        )

    def serialize(self) -> bytes:
        return json.dumps(self.to_dict()).encode()

    @classmethod
    def deserialize(cls, data: bytes) -> 'StashEntry':
        return cls.from_dict(json.loads(data.decode()))


class StashManager:
    def __init__(self, vcs_dir: Path):
        self.stash_dir = vcs_dir / "stash"
        self.stash_dir.mkdir(parents=True, exist_ok=True)
        self.stash_index_file = self.stash_dir / "index"
        self._ensure_index()

    def _ensure_index(self) -> None:
        """Создает файл индекса если он не существует"""
        if not self.stash_index_file.exists():
            with open(self.stash_index_file, 'w') as f:
                json.dump([], f)

    def _load_index(self) -> List[str]:
        """Загружает список хешей stash записей"""
        with open(self.stash_index_file, 'r') as f:
            return json.load(f)

    def _save_index(self, index: List[str]) -> None:
        """Сохраняет список хешей stash записей"""
        with open(self.stash_index_file, 'w') as f:
            json.dump(index, f)

    def _get_entry_path(self, hash_value: str) -> Path:
        """Возвращает путь к файлу stash записи"""
        return self.stash_dir / hash_value

    def save(self, message: str, tree_hash: str, parent_commit: str, author: str) -> StashEntry:
        """Создает новую stash запись"""
        # Загружаем текущий индекс
        index = self._load_index()
        
        # Создаем новую запись
        entry = StashEntry(
            index=len(index),
            message=message,
            tree_hash=tree_hash,
            parent_commit=parent_commit,
            timestamp=datetime.now().timestamp(),
            author=author
        )
        
        # Сериализуем запись и сохраняем её
        data = entry.serialize()
        entry_hash = hex(hash(data))[2:]  # Используем простой хеш для примера
        
        with open(self._get_entry_path(entry_hash), 'wb') as f:
            f.write(data)
            
        # Обновляем индекс
        index.append(entry_hash)
        self._save_index(index)
        
        return entry

    def get_entry(self, index: int) -> Optional[StashEntry]:
        """Возвращает stash запись по индексу"""
        entries = self._load_index()
        if 0 <= index < len(entries):
            entry_hash = entries[index]
            path = self._get_entry_path(entry_hash)
            
            if path.exists():
                with open(path, 'rb') as f:
                    return StashEntry.deserialize(f.read())
        
        return None

    def drop(self, index: int) -> None:
        """Удаляет stash запись"""
        entries = self._load_index()
        if 0 <= index < len(entries):
            entry_hash = entries.pop(index)
            self._save_index(entries)
            
            # Удаляем файл записи
            path = self._get_entry_path(entry_hash)
            if path.exists():
                path.unlink()
            
            # Обновляем индексы оставшихся записей
            for i, hash_value in enumerate(entries):
                path = self._get_entry_path(hash_value)
                if path.exists():
                    with open(path, 'rb') as f:
                        entry = StashEntry.deserialize(f.read())
                    entry.index = i
                    with open(path, 'wb') as f:
                        f.write(entry.serialize())

    def clear(self) -> None:
        """Удаляет все stash записи"""
        entries = self._load_index()
        for entry_hash in entries:
            path = self._get_entry_path(entry_hash)
            if path.exists():
                path.unlink()
        self._save_index([])

    def list_entries(self) -> List[StashEntry]:
        """Возвращает список всех stash записей"""
        entries = []
        for entry_hash in self._load_index():
            path = self._get_entry_path(entry_hash)
            if path.exists():
                with open(path, 'rb') as f:
                    entries.append(StashEntry.deserialize(f.read()))
        return entries 