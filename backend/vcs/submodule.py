import json
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class Submodule:
    name: str
    path: str
    url: str
    commit: str

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "path": self.path,
            "url": self.url,
            "commit": self.commit
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Submodule':
        return cls(
            name=data["name"],
            path=data["path"],
            url=data["url"],
            commit=data["commit"]
        )


class SubmoduleManager:
    def __init__(self, vcs_dir: Path):
        self.vcs_dir = vcs_dir
        self.config_file = vcs_dir / "config"
        self._ensure_config()

    def _ensure_config(self) -> None:
        """Создает файл конфигурации если он не существует"""
        if not self.config_file.exists():
            self._save_config({})

    def _load_config(self) -> Dict[str, Dict]:
        """Загружает конфигурацию подмодулей"""
        if not self.config_file.exists():
            return {}
        with open(self.config_file, 'r') as f:
            config = json.load(f)
            return config.get("submodules", {})

    def _save_config(self, config: Dict[str, Dict]) -> None:
        """Сохраняет конфигурацию подмодулей"""
        full_config = {"submodules": config}
        with open(self.config_file, 'w') as f:
            json.dump(full_config, f, indent=2)

    def add_submodule(self, name: str, path: str, url: str, commit: str) -> Submodule:
        """Добавляет новый подмодуль"""
        config = self._load_config()
        
        if name in config:
            raise Exception(f"Подмодуль {name} уже существует")
            
        submodule = Submodule(name, path, url, commit)
        config[name] = submodule.to_dict()
        self._save_config(config)
        
        return submodule

    def remove_submodule(self, name: str) -> None:
        """Удаляет подмодуль"""
        config = self._load_config()
        if name not in config:
            raise Exception(f"Подмодуль {name} не найден")
            
        del config[name]
        self._save_config(config)

    def get_submodule(self, name: str) -> Optional[Submodule]:
        """Возвращает информацию о подмодуле"""
        config = self._load_config()
        if name not in config:
            return None
            
        return Submodule.from_dict(config[name])

    def list_submodules(self) -> List[Submodule]:
        """Возвращает список всех подмодулей"""
        config = self._load_config()
        return [Submodule.from_dict(data) for data in config.values()]

    def update_submodule(self, name: str, commit: str) -> None:
        """Обновляет коммит подмодуля"""
        config = self._load_config()
        if name not in config:
            raise Exception(f"Подмодуль {name} не найден")
            
        config[name]["commit"] = commit
        self._save_config(config) 