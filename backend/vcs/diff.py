from typing import Dict, List, Optional
from pathlib import Path
import difflib
import os

from .core import VCSRepository
from .diff_calculator import DiffCalculator

class DiffTool:
    def __init__(self, vcs_repo: VCSRepository):
        self.vcs = vcs_repo
        
    def get_changes(self, base_commit: str, target_commit: str) -> Dict[str, str]:
        """
        Получает изменения между двумя коммитами
        
        Args:
            base_commit: Базовый коммит
            target_commit: Целевой коммит
            
        Returns:
            Словарь с изменениями, где ключ - путь к файлу, значение - содержимое файла
        """
        changes = {}
        
        # Получаем списки файлов в обоих коммитах
        base_files = self.vcs.get_commit_files(base_commit) if base_commit else set()
        target_files = self.vcs.get_commit_files(target_commit) if target_commit else set()
        
        # Обрабатываем все файлы
        all_files = base_files | target_files
        
        for file_path in all_files:
            # Получаем содержимое файлов в обоих коммитах
            base_content = self.vcs.get_file_content_from_commit(base_commit, file_path) if base_commit and file_path in base_files else ""
            target_content = self.vcs.get_file_content_from_commit(target_commit, file_path) if target_commit and file_path in target_files else ""
            
            # Если содержимое различается, добавляем в изменения
            if base_content != target_content:
                changes[file_path] = target_content
                
        return changes
        
    def create_patch(self, base_content: str, target_content: str, file_path: str) -> str:
        """
        Создает патч между двумя версиями файла
        """
        return DiffCalculator.compare_files(
            base_content,
            target_content,
            f"a/{file_path}",
            f"b/{file_path}"
        )
        
    def apply_patch(self, content: str, patch: str) -> str:
        """
        Применяет патч к содержимому файла
        """
        return DiffCalculator.apply_patch(content, patch)
        
    def show_diff(self, base_commit: str, target_commit: str) -> List[str]:
        """
        Показывает различия между двумя коммитами
        """
        diffs = []
        changes = self.get_changes(base_commit, target_commit)
        
        for file_path, target_content in changes.items():
            base_content = self.vcs.get_file_content_from_commit(base_commit, file_path) if base_commit else ""
            diff = self.create_patch(base_content, target_content, file_path)
            diffs.append(diff)
            
        return diffs 