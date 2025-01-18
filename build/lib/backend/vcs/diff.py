from typing import List, Tuple, Optional
from difflib import unified_diff
from dataclasses import dataclass


@dataclass
class FileDiff:
    """Представляет разницу между двумя версиями файла"""
    path: str
    old_hash: Optional[str]
    new_hash: Optional[str]
    diff_text: str
    
    @property
    def is_new(self) -> bool:
        return self.old_hash is None and self.new_hash is not None
    
    @property
    def is_deleted(self) -> bool:
        return self.old_hash is not None and self.new_hash is None
    
    @property
    def is_modified(self) -> bool:
        return self.old_hash is not None and self.new_hash is not None


class DiffCalculator:
    @staticmethod
    def compare_files(old_content: str, new_content: str, 
                     old_path: str = "a", new_path: str = "b") -> str:
        """Сравнивает содержимое двух файлов и возвращает diff в формате unified"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff_lines = list(unified_diff(
            old_lines, new_lines,
            fromfile=old_path,
            tofile=new_path,
            lineterm=""
        ))
        
        return "".join(diff_lines)
    
    @staticmethod
    def parse_patch(patch_text: str) -> List[Tuple[str, str, int]]:
        """Разбирает patch и возвращает список изменений
        Возвращает: [(действие, содержимое, номер_строки), ...]
        где действие может быть '+' (добавление) или '-' (удаление)
        """
        changes = []
        current_line = 0
        
        for line in patch_text.splitlines():
            if line.startswith('+++') or line.startswith('---'):
                continue
            elif line.startswith('@@'):
                # Парсим заголовок чанка
                parts = line.split()
                line_info = parts[2]  # +X,Y формат
                current_line = int(line_info.split(',')[0][1:])
            elif line.startswith('+'):
                changes.append(('+', line[1:], current_line))
                current_line += 1
            elif line.startswith('-'):
                changes.append(('-', line[1:], current_line))
            else:
                current_line += 1
                
        return changes
    
    @staticmethod
    def apply_patch(content: str, patch_text: str) -> str:
        """Применяет patch к содержимому файла"""
        lines = content.splitlines()
        changes = DiffCalculator.parse_patch(patch_text)
        
        # Сначала обрабатываем удаления
        for action, line_content, line_num in changes:
            if action == '-':
                if 0 <= line_num - 1 < len(lines):
                    lines.pop(line_num - 1)
        
        # Затем добавления
        for action, line_content, line_num in changes:
            if action == '+':
                if 0 <= line_num - 1 <= len(lines):
                    lines.insert(line_num - 1, line_content)
        
        return '\n'.join(lines) 