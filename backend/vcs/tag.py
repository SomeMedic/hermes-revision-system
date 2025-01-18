import json
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Tag:
    name: str
    commit_hash: str
    message: Optional[str]
    tagger: str
    timestamp: float

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "commit": self.commit_hash,
            "message": self.message,
            "tagger": self.tagger,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Tag':
        return cls(
            name=data["name"],
            commit_hash=data["commit"],
            message=data.get("message"),
            tagger=data["tagger"],
            timestamp=data["timestamp"]
        )

    def serialize(self) -> bytes:
        return json.dumps(self.to_dict()).encode()

    @classmethod
    def deserialize(cls, data: bytes) -> 'Tag':
        return cls.from_dict(json.loads(data.decode()))


class TagManager:
    def __init__(self, vcs_dir: Path):
        self.tags_dir = vcs_dir / "refs" / "tags"
        self.tags_dir.mkdir(parents=True, exist_ok=True)

    def create_tag(self, name: str, commit_hash: str, message: Optional[str], tagger: str) -> Tag:
        """Создает новый тег"""
        if self.get_tag(name) is not None:
            raise Exception(f"Тег {name} уже существует")

        tag = Tag(
            name=name,
            commit_hash=commit_hash,
            message=message,
            tagger=tagger,
            timestamp=datetime.now().timestamp()
        )

        tag_path = self.tags_dir / name
        with open(tag_path, 'wb') as f:
            f.write(tag.serialize())

        return tag

    def get_tag(self, name: str) -> Optional[Tag]:
        """Возвращает тег по имени"""
        tag_path = self.tags_dir / name
        if not tag_path.exists():
            return None

        with open(tag_path, 'rb') as f:
            return Tag.deserialize(f.read())

    def delete_tag(self, name: str) -> None:
        """Удаляет тег"""
        tag_path = self.tags_dir / name
        if tag_path.exists():
            tag_path.unlink()

    def list_tags(self) -> List[Tag]:
        """Возвращает список всех тегов"""
        tags = []
        for tag_path in self.tags_dir.glob('*'):
            if tag_path.is_file():
                with open(tag_path, 'rb') as f:
                    tags.append(Tag.deserialize(f.read()))
        return sorted(tags, key=lambda t: t.timestamp) 