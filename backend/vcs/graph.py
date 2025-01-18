from typing import Dict, Set, Optional
from pathlib import Path
import graphviz
import os

from .core import VCSRepository


class RepoGraph:
    def __init__(self, repo: VCSRepository):
        self.repo = repo
        
    def create_directory_graph(self, output_path: str, format: str = 'png', ignore_patterns: Set[str] = None) -> str:
        """
        Создает граф структуры директорий репозитория
        
        Args:
            output_path: Путь для сохранения файла с графом
            format: Формат выходного файла (png, svg, pdf и т.д.)
            ignore_patterns: Набор паттернов для игнорирования файлов/директорий
            
        Returns:
            Путь к созданному файлу
        """
        # Создаем новый граф
        dot = graphviz.Digraph(
            'repo_structure',
            comment='Repository Structure',
            format=format,
            node_attr={'shape': 'box', 'style': 'rounded'}
        )
        
        # Добавляем корневую директорию
        root_path = str(self.repo.root_path)
        root_name = os.path.basename(root_path) or 'root'
        dot.node('root', root_name, shape='folder')
        
        # Словарь для отслеживания уже добавленных узлов
        added_nodes = {'root': root_name}
        
        # Обходим все файлы и директории
        for path in self.repo.root_path.rglob('*'):
            # Пропускаем .hrs директорию
            if '.hrs' in path.parts:
                continue
                
            # Пропускаем игнорируемые паттерны
            if ignore_patterns:
                skip = False
                rel_path = str(path.relative_to(self.repo.root_path))
                for pattern in ignore_patterns:
                    if pattern in rel_path:
                        skip = True
                        break
                if skip:
                    continue
            
            # Получаем относительный путь
            rel_parts = path.relative_to(self.repo.root_path).parts
            
            # Добавляем узлы и связи для каждой части пути
            parent = 'root'
            for i, part in enumerate(rel_parts):
                # Создаем уникальный идентификатор для узла
                node_id = '_'.join(rel_parts[:i+1])
                
                if node_id not in added_nodes:
                    # Определяем тип узла (файл или директория)
                    if i == len(rel_parts) - 1 and path.is_file():
                        # Файл
                        dot.node(node_id, part, shape='note')
                        # Добавляем информацию о статусе файла
                        status = self._get_file_status(str(path.relative_to(self.repo.root_path)))
                        if status:
                            dot.node(node_id, f"{part}\n({status})", 
                                   color=self._get_status_color(status))
                    else:
                        # Директория
                        dot.node(node_id, part, shape='folder')
                    
                    added_nodes[node_id] = part
                    dot.edge(parent, node_id)
                
                parent = node_id
        
        # Сохраняем граф
        return dot.render(output_path, cleanup=True)
    
    def create_commit_graph(self, output_path: str, format: str = 'png', max_commits: int = 20) -> str:
        """
        Создает граф истории коммитов
        
        Args:
            output_path: Путь для сохранения файла с графом
            format: Формат выходного файла
            max_commits: Максимальное количество отображаемых коммитов
            
        Returns:
            Путь к созданному файлу
        """
        dot = graphviz.Digraph(
            'commit_history',
            comment='Commit History',
            format=format,
            node_attr={'shape': 'box', 'style': 'rounded'}
        )
        
        # Получаем историю коммитов
        history = self.repo.get_commit_history()[:max_commits]
        
        # Добавляем узлы для каждого коммита
        for commit in history:
            commit_hash = self.repo.hash_object(commit.serialize())
            short_hash = commit_hash[:7]
            
            # Создаем метку с информацией о коммите
            label = f"{short_hash}\\n{commit.message[:30]}...\\n{commit.author}"
            
            dot.node(commit_hash, label)
            
            # Добавляем связь с родительским коммитом
            if commit.parent:
                dot.edge(commit_hash, commit.parent)
        
        # Добавляем метки веток
        for branch in self.repo.list_branches():
            branch_commit = self.repo.get_branch_head(branch)
            if branch_commit and branch_commit in [self.repo.hash_object(c.serialize()) for c in history]:
                # Создаем узел для ветки
                branch_node = f"branch_{branch}"
                dot.node(branch_node, branch, shape='tag')
                dot.edge(branch_node, branch_commit, style='dashed')
        
        return dot.render(output_path, cleanup=True)
    
    def print_directory_tree(self, ignore_patterns: Set[str] = None, prefix: str = "") -> None:
        """
        Выводит структуру директорий в консоль в виде дерева
        
        Args:
            ignore_patterns: Набор паттернов для игнорирования файлов/директорий
            prefix: Префикс для отступов (используется рекурсивно)
        """
        root_path = self.repo.root_path
        root_name = os.path.basename(str(root_path)) or 'root'
        
        # Выводим корневую директорию
        print(f"{prefix}📁 {root_name}")
        
        # Получаем список всех файлов и директорий
        entries = []
        for path in root_path.iterdir():
            # Пропускаем .hrs директорию
            if '.hrs' in path.parts:
                continue
                
            # Пропускаем игнорируемые паттерны
            if ignore_patterns:
                skip = False
                rel_path = str(path.relative_to(root_path))
                for pattern in ignore_patterns:
                    if pattern in rel_path:
                        skip = True
                        break
                if skip:
                    continue
            
            entries.append(path)
        
        # Сортируем: сначала директории, потом файлы
        entries.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        
        # Выводим содержимое
        for i, path in enumerate(entries):
            is_last = i == len(entries) - 1
            current_prefix = prefix + ("└── " if is_last else "├── ")
            next_prefix = prefix + ("    " if is_last else "│   ")
            
            if path.is_dir():
                # Рекурсивно выводим содержимое директории
                print(f"{current_prefix}📁 {path.name}")
                self._print_directory_tree_recursive(path, ignore_patterns, next_prefix)
            else:
                # Выводим файл и его статус
                status = self._get_file_status(str(path.relative_to(root_path)))
                status_icon = self._get_status_icon(status)
                print(f"{current_prefix}{status_icon} {path.name}")
    
    def _print_directory_tree_recursive(self, directory: Path, ignore_patterns: Set[str], prefix: str) -> None:
        """Рекурсивно выводит содержимое директории"""
        entries = []
        for path in directory.iterdir():
            if '.hrs' in path.parts:
                continue
                
            if ignore_patterns:
                skip = False
                rel_path = str(path.relative_to(self.repo.root_path))
                for pattern in ignore_patterns:
                    if pattern in rel_path:
                        skip = True
                        break
                if skip:
                    continue
            
            entries.append(path)
        
        entries.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        
        for i, path in enumerate(entries):
            is_last = i == len(entries) - 1
            current_prefix = prefix + ("└── " if is_last else "├── ")
            next_prefix = prefix + ("    " if is_last else "│   ")
            
            if path.is_dir():
                print(f"{current_prefix}📁 {path.name}")
                self._print_directory_tree_recursive(path, ignore_patterns, next_prefix)
            else:
                status = self._get_file_status(str(path.relative_to(self.repo.root_path)))
                status_icon = self._get_status_icon(status)
                print(f"{current_prefix}{status_icon} {path.name}")
    
    def _get_status_icon(self, status: Optional[str]) -> str:
        """Возвращает иконку для статуса файла"""
        if status == "modified":
            return "📝"
        elif status == "added":
            return "➕"
        elif status == "deleted":
            return "❌"
        elif status == "renamed":
            return "📎"
        else:
            return "📄"
            
    def _get_file_status(self, rel_path: str) -> Optional[str]:
        """Определяет статус файла в репозитории"""
        status = self.repo.get_status()
        
        if rel_path in status["modified"]:
            return "modified"
        elif rel_path in status["new"]:
            return "new"
        elif rel_path in status["deleted"]:
            return "deleted"
        
        return None
    
    def _get_status_color(self, status: str) -> str:
        """Возвращает цвет для определенного статуса файла"""
        colors = {
            "modified": "orange",
            "new": "green",
            "deleted": "red"
        }
        return colors.get(status, "black") 