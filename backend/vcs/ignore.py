from pathlib import Path
import fnmatch
import os
from typing import List, Set

class IgnoreManager:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.ignore_file = self.root_path / '.hrsignore'
        self.patterns = self._load_patterns()
        
    def _load_patterns(self) -> List[str]:
        """
        Загружает паттерны игнорирования из .hrsignore
        """
        if not self.ignore_file.exists():
            return []
            
        with open(self.ignore_file, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
    def save_patterns(self, patterns: List[str]):
        """
        Сохраняет паттерны игнорирования в .hrsignore
        """
        with open(self.ignore_file, 'w') as f:
            f.write('\n'.join(patterns))
            
    def add_pattern(self, pattern: str):
        """
        Добавляет новый паттерн игнорирования
        """
        if pattern not in self.patterns:
            self.patterns.append(pattern)
            self.save_patterns(self.patterns)
            
    def remove_pattern(self, pattern: str):
        """
        Удаляет паттерн игнорирования
        """
        if pattern in self.patterns:
            self.patterns.remove(pattern)
            self.save_patterns(self.patterns)
            
    def is_ignored(self, path: str) -> bool:
        """
        Проверяет, должен ли файл быть проигнорирован
        """
        rel_path = str(Path(path).relative_to(self.root_path))
        
        for pattern in self.patterns:
            if pattern.startswith('/'):
                # Абсолютный путь относительно корня репозитория
                if fnmatch.fnmatch(rel_path, pattern[1:]):
                    return True
            else:
                # Паттерн может совпадать в любой директории
                if fnmatch.fnmatch(rel_path, f"**/{pattern}"):
                    return True
                    
        return False
        
    def get_ignored_files(self) -> Set[str]:
        """
        Возвращает список всех игнорируемых файлов
        """
        ignored = set()
        
        for root, dirs, files in os.walk(self.root_path):
            for item in files + dirs:
                full_path = os.path.join(root, item)
                if self.is_ignored(full_path):
                    ignored.add(full_path)
                    if item in dirs:
                        dirs.remove(item)  # Пропускаем игнорируемые директории
                        
        return ignored
        
    def create_default_ignore(self):
        """
        Создает файл .hrsignore с типичными паттернами
        """
        default_patterns = [
            '*.pyc',
            '__pycache__/',
            '*.pyo',
            '*.pyd',
            '.Python',
            'env/',
            'venv/',
            '.env',
            '.venv',
            'pip-log.txt',
            'pip-delete-this-directory.txt',
            '.tox/',
            '.coverage',
            '.coverage.*',
            '.cache',
            'nosetests.xml',
            'coverage.xml',
            '*.cover',
            '*.log',
            '.pytest_cache/',
            '.idea/',
            '.vscode/',
            '*.swp',
            '*.swo',
            '*~',
            '.DS_Store'
        ]
        
        self.patterns = default_patterns
        self.save_patterns(default_patterns) 