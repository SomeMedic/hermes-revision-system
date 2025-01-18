import os
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Set, Union, Tuple
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .commit import Commit
from .tree import Tree
from .branch import Branch
from .diff_calculator import DiffCalculator, FileDiff
from .tag import TagManager, Tag
from .stash import StashManager, StashEntry
from .hooks import HookManager, HookType
from .submodule import SubmoduleManager, Submodule


class MergeConflict(Exception):
    def __init__(self, path: str, base_content: str, ours_content: str, theirs_content: str):
        self.path = path
        self.base_content = base_content
        self.ours_content = ours_content
        self.theirs_content = theirs_content
        super().__init__(f"Конфликт слияния в файле {path}")


class VCSFileHandler(FileSystemEventHandler):
    def __init__(self, repository):
        self.repository = repository

    def on_modified(self, event):
        if not event.is_directory and not event.src_path.startswith(str(self.repository.vcs_dir)):
            self.repository.mark_file_modified(event.src_path)


class VCSRepository:
    def __init__(self, path: str):
        self.root_path = Path(path)
        self.vcs_dir = self.root_path / ".hrs"
        self.objects_dir = self.vcs_dir / "objects"
        self.refs_dir = self.vcs_dir / "refs"
        self.index_file = self.vcs_dir / "index"
        self.head_file = self.vcs_dir / "HEAD"
        self._index: Dict[str, str] = {}
        self._modified_files: Set[str] = set()
        self.observer = None
        self.tag_manager = TagManager(self.vcs_dir)
        self.stash_manager = StashManager(self.vcs_dir)
        self.hook_manager = HookManager(self.vcs_dir)
        self.submodule_manager = SubmoduleManager(self.vcs_dir)
        
    def init(self) -> None:
        """Инициализация репозитория"""
        # Проверяем существование директории и её содержимое
        if self.vcs_dir.exists():
            # Проверяем, является ли это действительно инициализированным репозиторием
            if (self.objects_dir.exists() and self.refs_dir.exists() and 
                self.head_file.exists() and self.index_file.exists()):
                raise Exception("Репозиторий уже инициализирован")
            else:
                # Если директория существует, но репозиторий не полностью инициализирован,
                # удаляем её и создаем заново
                import shutil
                shutil.rmtree(self.vcs_dir)
            
        # Создаем структуру директорий
        self.vcs_dir.mkdir()
        self.objects_dir.mkdir()
        self.refs_dir.mkdir()
        
        # Инициализируем индекс
        self._save_index({})
        
        # Инициализируем HEAD
        with open(self.head_file, 'w') as f:
            f.write('')
        
        # Создаем основную ветку main
        Branch.create_branch_file(self.refs_dir, "main", "")
        
        # Запускаем отслеживание изменений
        self._start_file_watching()
        
        print(f"Инициализирован пустой репозиторий в {self.root_path}")
    
    def _start_file_watching(self):
        """Запускает отслеживание изменений файлов"""
        self.observer = Observer()
        handler = VCSFileHandler(self)
        self.observer.schedule(handler, str(self.root_path), recursive=True)
        self.observer.start()
    
    def _save_index(self, index: Dict[str, str]) -> None:
        """Сохраняет индекс в файл"""
        with open(self.index_file, 'w') as f:
            json.dump(index, f)
        self._index = index
    
    def _load_index(self) -> Dict[str, str]:
        """Загружает индекс из файла"""
        if not self.index_file.exists():
            return {}
        with open(self.index_file, 'r') as f:
            self._index = json.load(f)
        return self._index
    
    def _get_object(self, hash_value: str) -> Optional[bytes]:
        """Получает объект по хешу"""
        path = self.objects_dir / hash_value
        if not path.exists():
            return None
        with open(path, 'rb') as f:
            return f.read()
    
    def _update_head(self, commit_hash: str) -> None:
        """Обновляет HEAD на новый коммит"""
        with open(self.head_file, 'w') as f:
            f.write(commit_hash)
            
        # Обновляем текущую ветку
        current_branch = self.get_current_branch()
        if current_branch:
            Branch.create_branch_file(self.refs_dir, current_branch, commit_hash)
    
    def _get_head(self) -> Optional[str]:
        """Возвращает хеш текущего коммита"""
        if not self.head_file.exists():
            return None
        with open(self.head_file, 'r') as f:
            return f.read().strip() or None
    
    def create_branch(self, name: str) -> None:
        """Создает новую ветку"""
        current_commit = self._get_head()
        if current_commit is None:
            raise Exception("Невозможно создать ветку: нет коммитов")
            
        if name in self.list_branches():
            raise Exception(f"Ветка {name} уже существует")
            
        Branch.create_branch_file(self.refs_dir, name, current_commit)
    
    def delete_branch(self, name: str) -> None:
        """Удаляет ветку"""
        if name == "main":
            raise Exception("Невозможно удалить основную ветку")
            
        if name == self.get_current_branch():
            raise Exception("Невозможно удалить текущую ветку")
            
        Branch.delete_branch(self.refs_dir, name)
    
    def list_branches(self) -> List[str]:
        """Возвращает список всех веток"""
        return Branch.list_branches(self.refs_dir)
    
    def get_current_branch(self) -> Optional[str]:
        """Возвращает имя текущей ветки"""
        return Branch.get_current_branch(self.head_file, self.refs_dir)
    
    def checkout(self, target: str) -> None:
        """Переключается на указанную ветку или коммит"""
        # Проверяем, есть ли несохраненные изменения
        if any(self.get_status().values()):
            raise Exception("Есть несохраненные изменения")
        
        # Проверяем, существует ли ветка
        branch_commit = Branch.get_branch_commit(self.refs_dir, target)
        if branch_commit is not None:
            # Переключаемся на ветку
            self._update_head(branch_commit)
            self._restore_working_directory(branch_commit)
            return
            
        # Проверяем, существует ли коммит
        commit_data = self._get_object(target)
        if commit_data is not None:
            # Переключаемся на коммит
            self._update_head(target)
            self._restore_working_directory(target)
            return
            
        raise Exception(f"Ветка или коммит {target} не найдены")
    
    def _restore_working_directory(self, commit_hash: str) -> None:
        """Восстанавливает рабочую директорию из коммита"""
        commit = self.get_commit(commit_hash)
        if commit is None:
            raise Exception(f"Коммит {commit_hash} не найден")
            
        # Получаем дерево файлов
        tree_data = self._get_object(commit.tree_hash)
        if tree_data is None:
            raise Exception(f"Дерево {commit.tree_hash} не найдено")
            
        tree = Tree.deserialize(tree_data)
        
        # Очищаем индекс
        self._save_index({})
        
        # Восстанавливаем файлы
        for file_path, file_hash in tree.entries.items():
            file_data = self._get_object(file_hash)
            if file_data is None:
                continue
                
            # Создаем директории если нужно
            abs_path = self.root_path / file_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Записываем файл
            with open(abs_path, 'wb') as f:
                f.write(file_data)
            
            # Обновляем индекс
            self._index[file_path] = file_hash
            
        self._save_index(self._index)
        
    def hash_object(self, data: bytes) -> str:
        """Хеширует данные и сохраняет их в objects"""
        hash_obj = hashlib.sha1(data).hexdigest()
        path = self.objects_dir / hash_obj
        
        if not path.exists():
            with open(path, "wb") as f:
                f.write(data)
                
        return hash_obj
    
    def hash_file(self, file_path: str) -> str:
        """Хеширует содержимое файла"""
        abs_path = self.root_path / file_path
        with open(abs_path, 'rb') as f:
            return self.hash_object(f.read())
    
    def mark_file_modified(self, file_path: str) -> None:
        """Отмечает файл как измененный"""
        rel_path = str(Path(file_path).relative_to(self.root_path))
        if not rel_path.startswith('.vcs'):
            self._modified_files.add(rel_path)
    
    def add(self, file_path: str) -> None:
        """Добавляет файл в индекс"""
        rel_path = str(Path(file_path).relative_to(self.root_path))
        if rel_path.startswith('.vcs'):
            return
            
        file_hash = self.hash_file(rel_path)
        self._index[rel_path] = file_hash
        self._save_index(self._index)
        self._modified_files.discard(rel_path)
    
    def commit(self, message: str, author: str) -> str:
        """Создает новый коммит"""
        # Запускаем pre-commit хук
        if not self.hook_manager.run_hook(HookType.PRE_COMMIT):
            raise Exception("Pre-commit хук завершился с ошибкой")
        
        # Создаем дерево из текущего индекса
        tree = Tree(self._load_index())
        tree_hash = self.hash_object(tree.serialize())
        
        # Создаем коммит
        commit = Commit(
            tree_hash=tree_hash,
            message=message,
            author=author,
            parent=self._get_head()
        )
        
        # Сохраняем коммит
        commit_hash = self.hash_object(commit.serialize())
        
        # Обновляем HEAD и текущую ветку
        current_branch = self.get_current_branch()
        if current_branch:
            Branch.create_branch_file(self.refs_dir, current_branch, commit_hash)
        self._update_head(commit_hash)
        
        # Запускаем post-commit хук
        self.hook_manager.run_hook(HookType.POST_COMMIT, {
            'HRS_COMMIT_HASH': commit_hash,
            'HRS_COMMIT_MESSAGE': message,
            'HRS_COMMIT_AUTHOR': author
        })
        
        return commit_hash
    
    def get_commit(self, commit_hash: str) -> Optional[Commit]:
        """Возвращает коммит по хешу"""
        data = self._get_object(commit_hash)
        if data is None:
            return None
        return Commit.deserialize(data)
    
    def get_commit_history(self, start_commit: Optional[str] = None) -> List[Commit]:
        """Возвращает историю коммитов"""
        history = []
        current_hash = start_commit or self._get_head()
        
        while current_hash:
            commit = self.get_commit(current_hash)
            if commit is None:
                break
                
            history.append(commit)
            current_hash = commit.parent
            
        return history
        
    def get_status(self) -> Dict[str, List[str]]:
        """Возвращает статус репозитория"""
        status = {
            "modified": [],
            "new": [],
            "deleted": []
        }
        
        # Загружаем текущий индекс
        current_index = self._load_index()
        
        # Проверяем все файлы в директории
        for file_path in self.root_path.rglob('*'):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(self.root_path))
                
                # Пропускаем .hrs директорию и все её содержимое
                if rel_path.startswith('.hrs'):
                    continue
                    
                if rel_path in current_index:
                    # Проверяем изменился ли файл
                    current_hash = self.hash_file(rel_path)
                    if current_hash != current_index[rel_path]:
                        status["modified"].append(rel_path)
                else:
                    status["new"].append(rel_path)
        
        # Проверяем удаленные файлы
        for indexed_file in current_index:
            if not (self.root_path / indexed_file).exists():
                status["deleted"].append(indexed_file)
        
        return status 

    def get_object_content(self, file_hash: str) -> Optional[str]:
        """Получает содержимое файла по хешу"""
        data = self._get_object(file_hash)
        if data is None:
            return None
        return data.decode('utf-8', errors='replace')

    def get_file_content_from_commit(self, commit_hash: str, file_path: str) -> Optional[str]:
        """Получает содержимое файла из определенного коммита"""
        commit = self.get_commit(commit_hash)
        if commit is None:
            return None
            
        tree_data = self._get_object(commit.tree_hash)
        if tree_data is None:
            return None
            
        tree = Tree.deserialize(tree_data)
        file_hash = tree.get_entry(file_path)
        
        if file_hash is None:
            return None
            
        return self.get_object_content(file_hash)

    def diff_commits(self, old_commit: str, new_commit: str) -> List[FileDiff]:
        """Сравнивает два коммита и возвращает список изменений"""
        old_tree = None
        new_tree = None
        
        # Получаем деревья файлов
        if old_commit:
            old_commit_obj = self.get_commit(old_commit)
            if old_commit_obj:
                old_tree_data = self._get_object(old_commit_obj.tree_hash)
                if old_tree_data:
                    old_tree = Tree.deserialize(old_tree_data)
        
        if new_commit:
            new_commit_obj = self.get_commit(new_commit)
            if new_commit_obj:
                new_tree_data = self._get_object(new_commit_obj.tree_hash)
                if new_tree_data:
                    new_tree = Tree.deserialize(new_tree_data)
        
        diffs = []
        all_files = set()
        
        # Собираем все файлы из обоих коммитов
        if old_tree:
            all_files.update(old_tree.entries.keys())
        if new_tree:
            all_files.update(new_tree.entries.keys())
        
        for file_path in sorted(all_files):
            old_hash = old_tree.get_entry(file_path) if old_tree else None
            new_hash = new_tree.get_entry(file_path) if new_tree else None
            
            if old_hash == new_hash:
                continue
            
            old_content = self.get_object_content(old_hash) if old_hash else ""
            new_content = self.get_object_content(new_hash) if new_hash else ""
            
            diff_text = DiffCalculator.compare_files(
                old_content, new_content,
                f"a/{file_path}", f"b/{file_path}"
            )
            
            diffs.append(FileDiff(
                path=file_path,
                old_hash=old_hash,
                new_hash=new_hash,
                diff_text=diff_text
            ))
        
        return diffs

    def diff_working_tree(self, file_path: Optional[str] = None) -> List[FileDiff]:
        """Сравнивает рабочую директорию с индексом"""
        current_index = self._load_index()
        diffs = []
        
        def process_file(path: str) -> None:
            rel_path = str(Path(path).relative_to(self.root_path))
            if rel_path.startswith('.vcs'):
                return
                
            old_hash = current_index.get(rel_path)
            
            try:
                with open(self.root_path / rel_path, 'r', encoding='utf-8') as f:
                    new_content = f.read()
            except Exception:
                new_content = ""
                
            old_content = self.get_object_content(old_hash) if old_hash else ""
            
            diff_text = DiffCalculator.compare_files(
                old_content, new_content,
                f"a/{rel_path}", f"b/{rel_path}"
            )
            
            if diff_text:
                new_hash = self.hash_object(new_content.encode('utf-8'))
                diffs.append(FileDiff(
                    path=rel_path,
                    old_hash=old_hash,
                    new_hash=new_hash,
                    diff_text=diff_text
                ))
        
        if file_path:
            process_file(file_path)
        else:
            # Проверяем все файлы в рабочей директории
            for path in self.root_path.rglob('*'):
                if path.is_file():
                    process_file(str(path))
            
            # Проверяем удаленные файлы
            for indexed_file in current_index:
                if not (self.root_path / indexed_file).exists():
                    diffs.append(FileDiff(
                        path=indexed_file,
                        old_hash=current_index[indexed_file],
                        new_hash=None,
                        diff_text=f"--- a/{indexed_file}\n+++ /dev/null\n@@ -1,0 +0,0 @@\n"
                    ))
        
        return diffs 

    def revert_commit(self, commit_hash: str) -> str:
        """Создает новый коммит, отменяющий изменения указанного коммита"""
        commit = self.get_commit(commit_hash)
        if commit is None:
            raise Exception(f"Коммит {commit_hash} не найден")
            
        # Получаем родительский коммит
        parent_commit = None
        if commit.parent:
            parent_commit = self.get_commit(commit.parent)
            if parent_commit is None:
                raise Exception(f"Родительский коммит {commit.parent} не найден")
        
        # Получаем изменения, которые нужно отменить
        diffs = self.diff_commits(commit.parent or "", commit_hash)
        
        # Создаем обратные изменения
        for diff in diffs:
            if diff.is_new:
                # Файл был добавлен - удаляем его
                file_path = self.root_path / diff.path
                if file_path.exists():
                    file_path.unlink()
            elif diff.is_deleted:
                # Файл был удален - восстанавливаем его
                old_content = self.get_object_content(diff.old_hash)
                if old_content is not None:
                    file_path = self.root_path / diff.path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(old_content)
            else:
                # Файл был изменен - применяем обратный patch
                current_content = self.get_file_content_from_commit(commit_hash, diff.path)
                if current_content is not None:
                    old_content = self.get_object_content(diff.old_hash)
                    if old_content is not None:
                        file_path = self.root_path / diff.path
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(old_content)
        
        # Добавляем все измененные файлы в индекс
        for diff in diffs:
            if not diff.is_deleted:
                self.add(diff.path)
        
        # Создаем коммит отмены
        return self.commit(
            message=f"Revert commit {commit_hash}\n\nThis reverts commit {commit_hash}",
            author=os.environ.get('VCS_AUTHOR', os.environ.get('USER', 'Unknown'))
        )

    def reset_files(self, files: List[str]) -> None:
        """Отменяет изменения в указанных файлах, возвращая их к состоянию в индексе"""
        current_index = self._load_index()
        
        for file_path in files:
            rel_path = str(Path(file_path).relative_to(self.root_path))
            if rel_path not in current_index:
                continue
                
            # Получаем содержимое файла из индекса
            file_hash = current_index[rel_path]
            content = self.get_object_content(file_hash)
            
            if content is not None:
                # Восстанавливаем файл
                abs_path = self.root_path / rel_path
                with open(abs_path, 'w', encoding='utf-8') as f:
                    f.write(content)

    def reset_hard(self, commit_hash: str) -> None:
        """Жестко сбрасывает все изменения до указанного коммита"""
        self.checkout(commit_hash)  # Используем существующий метод checkout 

    def find_merge_base(self, commit1: str, commit2: str) -> Optional[str]:
        """Находит общий базовый коммит для двух коммитов"""
        # Получаем историю первого коммита
        history1 = set()
        current = commit1
        while current:
            history1.add(current)
            commit = self.get_commit(current)
            if commit is None:
                break
            current = commit.parent
        
        # Ищем первый коммит из второй ветки, который есть в истории первой
        current = commit2
        while current:
            if current in history1:
                return current
            commit = self.get_commit(current)
            if commit is None:
                break
            current = commit.parent
        
        return None

    def merge_files(self, base_content: str, ours_content: str, theirs_content: str,
                   path: str) -> Tuple[str, bool]:
        """Пытается слить два файла. Возвращает (результат, имел_ли_конфликты)"""
        if ours_content == theirs_content:
            return ours_content, False
            
        # Если один из файлов не изменился относительно базы, используем другой
        if ours_content == base_content:
            return theirs_content, False
        if theirs_content == base_content:
            return ours_content, False
            
        # Пытаемся автоматически слить изменения
        try:
            # Создаем diff между базой и каждой версией
            ours_diff = DiffCalculator.compare_files(base_content, ours_content)
            theirs_diff = DiffCalculator.compare_files(base_content, theirs_content)
            
            # Если изменения в разных местах, можем их объединить
            if not (set(ours_diff.splitlines()) & set(theirs_diff.splitlines())):
                result = base_content
                result = DiffCalculator.apply_patch(result, ours_diff)
                result = DiffCalculator.apply_patch(result, theirs_diff)
                return result, False
        except Exception:
            pass
            
        # Если автоматическое слияние не удалось, создаем конфликт
        raise MergeConflict(path, base_content, ours_content, theirs_content)

    def create_conflict_file(self, path: str, base: str, ours: str, theirs: str) -> None:
        """Создает файл с конфликтом слияния"""
        content = f"""<<<<<<< HEAD
{ours}
=======
{theirs}
>>>>>>> MERGE
"""
        with open(self.root_path / path, 'w', encoding='utf-8') as f:
            f.write(content)

    def merge(self, branch_name: str, message: Optional[str] = None) -> str:
        """Сливает указанную ветку в текущую"""
        result = super().merge(branch_name, message)
        
        # Запускаем post-merge хук
        self.hook_manager.run_hook(HookType.POST_MERGE, {
            'VCS_MERGED_BRANCH': branch_name,
            'VCS_MERGE_COMMIT': result
        })
        
        return result
    
    def install_hook(self, hook_type: HookType, content: str) -> None:
        """Устанавливает хук"""
        self.hook_manager.install_hook(hook_type, content)
    
    def uninstall_hook(self, hook_type: HookType) -> None:
        """Удаляет хук"""
        self.hook_manager.uninstall_hook(hook_type)
    
    def list_hooks(self) -> Dict[str, bool]:
        """Возвращает список всех хуков и их статус"""
        return self.hook_manager.list_hooks()

    def create_tag(self, name: str, message: Optional[str] = None) -> Tag:
        """Создает новый тег на текущем коммите"""
        commit_hash = self._get_head()
        if not commit_hash:
            raise Exception("Нет коммитов для создания тега")
            
        tagger = os.environ.get('VCS_AUTHOR', os.environ.get('USER', 'Unknown'))
        return self.tag_manager.create_tag(name, commit_hash, message, tagger)
    
    def get_tag(self, name: str) -> Optional[Tag]:
        """Возвращает тег по имени"""
        return self.tag_manager.get_tag(name)
    
    def delete_tag(self, name: str) -> None:
        """Удаляет тег"""
        self.tag_manager.delete_tag(name)
    
    def list_tags(self) -> List[Tag]:
        """Возвращает список всех тегов"""
        return self.tag_manager.list_tags()
    
    def checkout_tag(self, tag_name: str) -> None:
        """Переключается на указанный тег"""
        tag = self.get_tag(tag_name)
        if tag is None:
            raise Exception(f"Тег {tag_name} не найден")
        self.checkout(tag.commit_hash) 

    def stash_save(self, message: Optional[str] = None) -> StashEntry:
        """Сохраняет текущие изменения в stash"""
        # Проверяем, есть ли изменения для сохранения
        status = self.get_status()
        if not any(status.values()):
            raise Exception("Нет изменений для сохранения")
        
        # Создаем дерево из текущего состояния
        tree = Tree(self._load_index())
        tree_hash = self.hash_object(tree.serialize())
        
        # Получаем текущий коммит
        parent_commit = self._get_head()
        if not parent_commit:
            raise Exception("Нет коммитов в репозитории")
        
        # Создаем stash запись
        author = os.environ.get('VCS_AUTHOR', os.environ.get('USER', 'Unknown'))
        entry = self.stash_manager.save(
            message or "WIP on " + self.get_current_branch(),
            tree_hash,
            parent_commit,
            author
        )
        
        # Очищаем рабочую директорию
        self.reset_hard(parent_commit)
        
        return entry
    
    def stash_pop(self, index: int = 0) -> None:
        """Применяет последнюю stash запись и удаляет её"""
        entry = self.stash_manager.get_entry(index)
        if entry is None:
            raise Exception(f"Stash запись {index} не найдена")
            
        # Проверяем, есть ли несохраненные изменения
        if any(self.get_status().values()):
            raise Exception("Есть несохраненные изменения")
        
        # Восстанавливаем состояние из stash
        tree_data = self._get_object(entry.tree_hash)
        if tree_data is None:
            raise Exception(f"Дерево {entry.tree_hash} не найдено")
            
        tree = Tree.deserialize(tree_data)
        
        # Восстанавливаем файлы
        for file_path, file_hash in tree.entries.items():
            file_data = self._get_object(file_hash)
            if file_data is None:
                continue
                
            # Создаем директории если нужно
            abs_path = self.root_path / file_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Записываем файл
            with open(abs_path, 'wb') as f:
                f.write(file_data)
            
            # Добавляем в индекс
            self.add(file_path)
        
        # Удаляем stash запись
        self.stash_manager.drop(index)
    
    def stash_apply(self, index: int = 0) -> None:
        """Применяет stash запись без её удаления"""
        entry = self.stash_manager.get_entry(index)
        if entry is None:
            raise Exception(f"Stash запись {index} не найдена")
            
        # Проверяем, есть ли несохраненные изменения
        if any(self.get_status().values()):
            raise Exception("Есть несохраненные изменения")
        
        # Восстанавливаем состояние из stash
        tree_data = self._get_object(entry.tree_hash)
        if tree_data is None:
            raise Exception(f"Дерево {entry.tree_hash} не найдено")
            
        tree = Tree.deserialize(tree_data)
        
        # Восстанавливаем файлы
        for file_path, file_hash in tree.entries.items():
            file_data = self._get_object(file_hash)
            if file_data is None:
                continue
                
            # Создаем директории если нужно
            abs_path = self.root_path / file_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Записываем файл
            with open(abs_path, 'wb') as f:
                f.write(file_data)
            
            # Добавляем в индекс
            self.add(file_path)
    
    def stash_drop(self, index: int = 0) -> None:
        """Удаляет stash запись"""
        self.stash_manager.drop(index)
    
    def stash_clear(self) -> None:
        """Удаляет все stash записи"""
        self.stash_manager.clear()
    
    def stash_list(self) -> List[StashEntry]:
        """Возвращает список всех stash записей"""
        return self.stash_manager.list_entries()
    
    def add_submodule(self, name: str, url: str, path: str) -> Submodule:
        """Добавляет новый подмодуль"""
        abs_path = self.root_path / path
        if abs_path.exists():
            raise Exception(f"Путь {path} уже существует")
            
        # Клонируем репозиторий
        try:
            subprocess.run(
                ["git", "clone", url, str(abs_path)],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise Exception(f"Ошибка при клонировании репозитория: {e.stderr}")
        
        # Получаем текущий коммит
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(abs_path),
                check=True,
                capture_output=True,
                text=True
            )
            commit = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            shutil.rmtree(abs_path)
            raise Exception(f"Ошибка при получении коммита: {e.stderr}")
        
        # Добавляем подмодуль в конфигурацию
        return self.submodule_manager.add_submodule(name, path, url, commit)
    
    def remove_submodule(self, name: str) -> None:
        """Удаляет подмодуль"""
        submodule = self.submodule_manager.get_submodule(name)
        if submodule is None:
            raise Exception(f"Подмодуль {name} не найден")
            
        # Удаляем директорию подмодуля
        abs_path = self.root_path / submodule.path
        if abs_path.exists():
            shutil.rmtree(abs_path)
            
        # Удаляем из конфигурации
        self.submodule_manager.remove_submodule(name)
    
    def update_submodule(self, name: str, commit: Optional[str] = None) -> None:
        """Обновляет подмодуль до указанного коммита"""
        submodule = self.submodule_manager.get_submodule(name)
        if submodule is None:
            raise Exception(f"Подмодуль {name} не найден")
            
        abs_path = self.root_path / submodule.path
        if not abs_path.exists():
            raise Exception(f"Директория подмодуля {submodule.path} не существует")
        
        try:
            if commit:
                # Переключаемся на указанный коммит
                subprocess.run(
                    ["git", "checkout", commit],
                    cwd=str(abs_path),
                    check=True,
                    capture_output=True,
                    text=True
                )
            else:
                # Обновляем до последнего коммита
                subprocess.run(
                    ["git", "pull"],
                    cwd=str(abs_path),
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                # Получаем текущий коммит
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(abs_path),
                    check=True,
                    capture_output=True,
                    text=True
                )
                commit = result.stdout.strip()
            
            # Обновляем информацию в конфигурации
            self.submodule_manager.update_submodule(name, commit)
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Ошибка при обновлении подмодуля: {e.stderr}")
    
    def list_submodules(self) -> List[Submodule]:
        """Возвращает список всех подмодулей"""
        return self.submodule_manager.list_submodules()
    
    def get_submodule(self, name: str) -> Optional[Submodule]:
        """Возвращает информацию о подмодуле"""
        return self.submodule_manager.get_submodule(name)
    
    def get_commit_files(self, commit_hash: str) -> Set[str]:
        """
        Получает список файлов в коммите
        """
        if not commit_hash:
            return set()
        
        commit = self.get_commit(commit_hash)
        if not commit:
            return set()
        
        tree_data = self._get_object(commit.tree_hash)
        if not tree_data:
            return set()
        
        tree = Tree.deserialize(tree_data)
        return set(tree.entries.keys())

    def get_file_content(self, commit_hash: str, file_path: str) -> str:
        """
        Получает содержимое файла из коммита
        """
        if not commit_hash:
            return ""
        
        commit = self.get_commit(commit_hash)
        if not commit:
            return ""
        
        tree_data = self._get_object(commit.tree_hash)
        if not tree_data:
            return ""
        
        tree = Tree.deserialize(tree_data)
        if file_path not in tree.entries:
            return ""
        
        file_hash = tree.entries[file_path]
        file_data = self._get_object(file_hash)
        if not file_data:
            return ""
        
        return file_data.decode('utf-8')

    def get_branch_head(self, branch_name: str) -> Optional[str]:
        """
        Получает хеш последнего коммита в ветке
        """
        return Branch.get_branch_commit(self.refs_dir, branch_name) 