from pathlib import Path
from typing import Optional, List, Dict


class Branch:
    def __init__(self, name: str, commit_hash: str):
        self.name = name
        self.commit_hash = commit_hash

    @staticmethod
    def create_branch_file(refs_dir: Path, name: str, commit_hash: str) -> None:
        """Создает файл ветки"""
        branch_file = refs_dir / name
        with open(branch_file, 'w') as f:
            f.write(commit_hash)

    @staticmethod
    def get_branch_commit(refs_dir: Path, name: str) -> Optional[str]:
        """Возвращает хеш коммита, на который указывает ветка"""
        branch_file = refs_dir / name
        if not branch_file.exists():
            return None
        with open(branch_file, 'r') as f:
            return f.read().strip()

    @staticmethod
    def list_branches(refs_dir: Path) -> List[str]:
        """Возвращает список всех веток"""
        return [f.name for f in refs_dir.iterdir() if f.is_file()]

    @staticmethod
    def delete_branch(refs_dir: Path, name: str) -> None:
        """Удаляет ветку"""
        branch_file = refs_dir / name
        if branch_file.exists():
            branch_file.unlink()

    @staticmethod
    def get_current_branch(head_file: Path, refs_dir: Path) -> Optional[str]:
        """Возвращает имя текущей ветки"""
        if not head_file.exists():
            return None
            
        with open(head_file, 'r') as f:
            head_content = f.read().strip()
            
        # Проверяем все ветки
        for branch_name in Branch.list_branches(refs_dir):
            if Branch.get_branch_commit(refs_dir, branch_name) == head_content:
                return branch_name
                
        return None 