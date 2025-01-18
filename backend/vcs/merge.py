from typing import List, Dict, Optional
from pathlib import Path
import difflib
import os

from .core import VCSRepository
from .diff import DiffTool

class MergeTool:
    def __init__(self, vcs_repo: VCSRepository):
        self.vcs = vcs_repo
        self.diff_tool = DiffTool(vcs_repo)
        
    def merge_branches(self, source_branch: str, target_branch: str, message: str = None) -> bool:
        """
        Слияние веток с автоматическим разрешением конфликтов где возможно
        """
        if not message:
            message = f"Merge branch '{source_branch}' into '{target_branch}'"
            
        # Получаем последние коммиты обеих веток
        source_commit = self.vcs.get_branch_head(source_branch)
        target_commit = self.vcs.get_branch_head(target_branch)
        
        # Находим общий базовый коммит
        base_commit = self.find_merge_base(source_commit, target_commit)
        
        # Получаем изменения в обеих ветках относительно базового коммита
        source_changes = self.diff_tool.get_changes(base_commit, source_commit)
        target_changes = self.diff_tool.get_changes(base_commit, target_commit)
        
        # Определяем конфликты
        conflicts = self.detect_conflicts(source_changes, target_changes)
        
        if conflicts:
            return self.handle_conflicts(conflicts, source_branch, target_branch)
        
        # Если конфликтов нет, выполняем автоматическое слияние
        return self.auto_merge(source_changes, target_changes, message)
    
    def find_merge_base(self, commit1: str, commit2: str) -> str:
        """
        Находит общий базовый коммит для двух веток
        """
        # Получаем историю коммитов для обеих веток
        history1 = self.vcs.get_commit_history(commit1)
        history2 = self.vcs.get_commit_history(commit2)
        
        # Находим первый общий коммит
        for commit in history1:
            if commit in history2:
                return commit
                
        return None
    
    def detect_conflicts(self, source_changes: Dict, target_changes: Dict) -> List[Dict]:
        """
        Определяет конфликты между изменениями в ветках
        """
        conflicts = []
        
        for file_path in set(source_changes.keys()) & set(target_changes.keys()):
            if source_changes[file_path] != target_changes[file_path]:
                conflicts.append({
                    'file': file_path,
                    'source_changes': source_changes[file_path],
                    'target_changes': target_changes[file_path]
                })
                
        return conflicts
    
    def handle_conflicts(self, conflicts: List[Dict], source_branch: str, target_branch: str) -> bool:
        """
        Обработка конфликтов с созданием конфликтных маркеров в файлах
        """
        for conflict in conflicts:
            file_path = conflict['file']
            with open(file_path, 'w') as f:
                f.write(f"<<<<<<< {target_branch}\n")
                f.write(conflict['target_changes'])
                f.write(f"=======\n")
                f.write(conflict['source_changes'])
                f.write(f">>>>>>> {source_branch}\n")
                
        return False
    
    def auto_merge(self, source_changes: Dict, target_changes: Dict, message: str) -> bool:
        """
        Выполняет автоматическое слияние изменений
        """
        # Применяем изменения из обеих веток
        all_changes = {**target_changes, **source_changes}
        
        for file_path, content in all_changes.items():
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
                
        # Создаем коммит слияния
        self.vcs.commit(message)
        return True 