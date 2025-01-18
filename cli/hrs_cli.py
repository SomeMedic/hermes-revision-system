import click
from pathlib import Path
import sys
import os
from datetime import datetime

# Добавляем путь к backend в PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from backend.vcs.core import VCSRepository
from backend.vcs.hooks import HookType
from backend.vcs.merge import MergeTool
from backend.vcs.ignore import IgnoreManager
from backend.vcs.remote import RemoteManager
from backend.vcs.graph import RepoGraph


@click.group()
def cli():
    """Hermes Revision System - современная система контроля версий"""
    pass


@cli.command()
@click.argument('path', default='.')
def init(path):
    """Инициализировать новый репозиторий"""
    try:
        repo = VCSRepository(path)
        repo.init()
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.command()
@click.argument('files', nargs=-1)
def add(files):
    """Добавить файлы в индекс"""
    try:
        repo = VCSRepository('.')
        for file in files:
            try:
                repo.add(file)
                click.echo(f"Добавлен файл: {file}")
            except Exception as e:
                click.echo(f"Ошибка при добавлении {file}: {e}", err=True)
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.command()
@click.option('-m', '--message', required=True, help='Сообщение коммита')
@click.option('-a', '--author', default=None, help='Автор коммита')
def commit(message, author):
    """Создать новый коммит"""
    try:
        repo = VCSRepository('.')
        
        # Если автор не указан, пытаемся получить его из переменных окружения
        if author is None:
            author = os.environ.get('HRS_AUTHOR', os.environ.get('USER', 'Unknown'))
        
        commit_hash = repo.commit(message, author)
        click.echo(f"Создан коммит: {commit_hash}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.command()
def status():
    """Показать статус репозитория"""
    try:
        repo = VCSRepository('.')
        status = repo.get_status()
        
        # Показываем текущую ветку
        current_branch = repo.get_current_branch()
        if current_branch:
            click.echo(f"На ветке: {current_branch}")
        else:
            click.echo("HEAD отделен")
        
        if not any(status.values()):
            click.echo("\nНет изменений")
            return
            
        for status_type, files in status.items():
            if files:
                click.echo(f"\n{status_type.capitalize()}:")
                for file in files:
                    click.echo(f"  {file}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.command()
def log():
    """Показать историю коммитов"""
    try:
        repo = VCSRepository('.')
        history = repo.get_commit_history()
        
        if not history:
            click.echo("История коммитов пуста")
            return
            
        for commit in history:
            click.echo(f"\nCommit: {repo.hash_object(commit.serialize())}")
            click.echo(f"Author: {commit.author}")
            click.echo(f"Date: {datetime.fromtimestamp(commit.timestamp)}")
            click.echo(f"\n    {commit.message}\n")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.command()
@click.argument('name')
def branch(name):
    """Создать новую ветку"""
    try:
        repo = VCSRepository('.')
        repo.create_branch(name)
        click.echo(f"Создана ветка: {name}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.command()
def branches():
    """Показать список веток"""
    try:
        repo = VCSRepository('.')
        current = repo.get_current_branch()
        for branch in repo.list_branches():
            prefix = "* " if branch == current else "  "
            click.echo(f"{prefix}{branch}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.command()
@click.argument('name')
def delete_branch(name):
    """Удалить ветку"""
    try:
        repo = VCSRepository('.')
        repo.delete_branch(name)
        click.echo(f"Удалена ветка: {name}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.command()
@click.argument('target')
def checkout(target):
    """Переключиться на ветку или коммит"""
    try:
        repo = VCSRepository('.')
        repo.checkout(target)
        click.echo(f"Переключение на: {target}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.command()
@click.argument('branch')
@click.option('-m', '--message', help='Сообщение коммита слияния')
def merge(branch, message):
    """Слить указанную ветку в текущую"""
    try:
        repo = VCSRepository('.')
        commit_hash = repo.merge(branch, message)
        click.echo(f"Слияние выполнено успешно. Создан коммит: {commit_hash}")
    except Exception as e:
        if "конфликты слияния" in str(e):
            click.echo("Возникли конфликты слияния в следующих файлах:", err=True)
            status = repo.get_status()
            for file in status["modified"]:
                with open(repo.root_path / file, 'r', encoding='utf-8') as f:
                    if "<<<<<<< HEAD" in f.read():
                        click.echo(f"  {file}", err=True)
            click.echo("\nРазрешите конфликты и выполните коммит", err=True)
        else:
            click.echo(f"Ошибка: {e}", err=True)


@cli.command()
@click.argument('target', required=False)
@click.option('--staged', is_flag=True, help='Показать изменения в индексе')
@click.option('--commit', help='Сравнить с определенным коммитом')
def diff(target, staged, commit):
    """Показать изменения в файлах"""
    try:
        repo = VCSRepository('.')
        
        if commit:
            # Сравниваем с определенным коммитом
            current = repo._get_head()
            if not current:
                click.echo("Нет коммитов для сравнения", err=True)
                return
                
            diffs = repo.diff_commits(commit, current)
        elif staged:
            # Сравниваем индекс с последним коммитом
            current = repo._get_head()
            if not current:
                click.echo("Нет коммитов для сравнения", err=True)
                return
                
            diffs = repo.diff_commits(current, None)  # None означает текущий индекс
        else:
            # Сравниваем рабочую директорию с индексом
            diffs = repo.diff_working_tree(target)
        
        if not diffs:
            click.echo("Нет изменений")
            return
            
        for diff in diffs:
            if diff.is_new:
                click.echo(f"\nНовый файл: {diff.path}")
            elif diff.is_deleted:
                click.echo(f"\nУдален файл: {diff.path}")
            else:
                click.echo(f"\nИзменен файл: {diff.path}")
            click.echo(diff.diff_text)
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.command()
@click.argument('commit')
def revert(commit):
    """Отменить изменения коммита"""
    try:
        repo = VCSRepository('.')
        new_commit = repo.revert_commit(commit)
        click.echo(f"Создан коммит отмены: {new_commit}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.command()
@click.argument('files', nargs=-1)
@click.option('--hard', is_flag=True, help='Жестко сбросить все изменения')
@click.option('--commit', help='Сбросить до указанного коммита')
def reset(files, hard, commit):
    """Отменить изменения в файлах или сбросить до определенного коммита"""
    try:
        repo = VCSRepository('.')
        
        if hard and commit:
            # Жесткий сброс до коммита
            repo.reset_hard(commit)
            click.echo(f"Выполнен жесткий сброс до коммита {commit}")
        elif files:
            # Сброс отдельных файлов
            repo.reset_files(files)
            click.echo("Изменения в файлах отменены")
        else:
            click.echo("Укажите файлы для сброса или используйте --hard с --commit", err=True)
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.group()
def tag():
    """Управление тегами"""
    pass


@tag.command(name='create')
@click.argument('name')
@click.option('-m', '--message', help='Сообщение тега')
def tag_create(name, message):
    """Создать новый тег"""
    try:
        repo = VCSRepository('.')
        tag = repo.create_tag(name, message)
        click.echo(f"Создан тег: {tag.name} -> {tag.commit_hash}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@tag.command(name='list')
def tag_list():
    """Показать список тегов"""
    try:
        repo = VCSRepository('.')
        tags = repo.list_tags()
        
        if not tags:
            click.echo("Теги отсутствуют")
            return
            
        for tag in tags:
            click.echo(f"\nТег: {tag.name}")
            click.echo(f"Коммит: {tag.commit_hash}")
            click.echo(f"Автор: {tag.tagger}")
            click.echo(f"Дата: {datetime.fromtimestamp(tag.timestamp)}")
            if tag.message:
                click.echo(f"\n    {tag.message}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@tag.command(name='delete')
@click.argument('name')
def tag_delete(name):
    """Удалить тег"""
    try:
        repo = VCSRepository('.')
        repo.delete_tag(name)
        click.echo(f"Удален тег: {name}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@tag.command(name='checkout')
@click.argument('name')
def tag_checkout(name):
    """Переключиться на тег"""
    try:
        repo = VCSRepository('.')
        repo.checkout_tag(name)
        click.echo(f"Переключение на тег: {name}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@cli.group()
def stash():
    """Управление временным хранилищем (stash)"""
    pass


@stash.command(name='save')
@click.option('-m', '--message', help='Сообщение для stash')
def stash_save(message):
    """Сохранить текущие изменения в stash"""
    try:
        repo = VCSRepository('.')
        entry = repo.stash_save(message)
        click.echo(f"Сохранено в stash: {entry.message}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@stash.command(name='list')
def stash_list():
    """Показать список сохраненных изменений"""
    try:
        repo = VCSRepository('.')
        entries = repo.stash_list()
        
        if not entries:
            click.echo("Stash пуст")
            return
            
        for entry in entries:
            click.echo(f"\nstash@{{{entry.index}}}: {entry.message}")
            click.echo(f"Автор: {entry.author}")
            click.echo(f"Дата: {datetime.fromtimestamp(entry.timestamp)}")
            click.echo(f"Коммит: {entry.parent_commit}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@stash.command(name='pop')
@click.argument('index', type=int, default=0)
def stash_pop(index):
    """Применить и удалить сохраненные изменения"""
    try:
        repo = VCSRepository('.')
        repo.stash_pop(index)
        click.echo(f"Применены и удалены изменения из stash@{{{index}}}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@stash.command(name='apply')
@click.argument('index', type=int, default=0)
def stash_apply(index):
    """Применить сохраненные изменения без удаления"""
    try:
        repo = VCSRepository('.')
        repo.stash_apply(index)
        click.echo(f"Применены изменения из stash@{{{index}}}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@stash.command(name='drop')
@click.argument('index', type=int, default=0)
def stash_drop(index):
    """Удалить сохраненные изменения"""
    try:
        repo = VCSRepository('.')
        repo.stash_drop(index)
        click.echo(f"Удалены изменения из stash@{{{index}}}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@stash.command(name='clear')
def stash_clear():
    """Удалить все сохраненные изменения"""
    try:
        repo = VCSRepository('.')
        repo.stash_clear()
        click.echo("Все изменения из stash удалены")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


# Команды для слияния веток
@cli.group()
def merge():
    """Команды для работы со слиянием веток"""
    pass


@merge.command()
@click.argument('source')
@click.argument('target')
@click.option('--message', '-m', help='Сообщение для коммита слияния')
def branch(source, target, message):
    """Слияние веток"""
    vcs = VCSRepository('.')
    merge_tool = MergeTool(vcs)
    result = merge_tool.merge_branches(source, target, message)
    if result:
        click.echo(f"Ветки {source} и {target} успешно слиты")
    else:
        click.echo("Возникли конфликты. Пожалуйста, разрешите их и выполните коммит")


# Команды для работы с игнорируемыми файлами
@cli.group()
def ignore():
    """Команды для работы с игнорируемыми файлами"""
    pass


@ignore.command()
@click.argument('pattern')
def add(pattern):
    """Добавить паттерн в список игнорируемых"""
    ignore_manager = IgnoreManager('.')
    ignore_manager.add_pattern(pattern)
    click.echo(f"Паттерн '{pattern}' добавлен в .hrsignore")


@ignore.command()
@click.argument('pattern')
def remove(pattern):
    """Удалить паттерн из списка игнорируемых"""
    ignore_manager = IgnoreManager('.')
    ignore_manager.remove_pattern(pattern)
    click.echo(f"Паттерн '{pattern}' удален из .hrsignore")


@ignore.command()
def list():
    """Показать список игнорируемых паттернов"""
    ignore_manager = IgnoreManager('.')
    patterns = ignore_manager._load_patterns()
    if patterns:
        click.echo("Игнорируемые паттерны:")
        for pattern in patterns:
            click.echo(f"  {pattern}")
    else:
        click.echo("Список игнорируемых паттернов пуст")


@ignore.command()
def init():
    """Создать файл .hrsignore с типичными паттернами"""
    ignore_manager = IgnoreManager('.')
    ignore_manager.create_default_ignore()
    click.echo("Создан файл .hrsignore с типичными паттернами")


# Команды для работы с удаленными репозиториями
@cli.group()
def remote():
    """Команды для работы с удаленными репозиториями"""
    pass


@remote.command()
@click.argument('name')
@click.argument('url')
def add(name, url):
    """Добавить удаленный репозиторий"""
    remote_manager = RemoteManager('.')
    remote_manager.add_remote(name, url)
    click.echo(f"Добавлен удаленный репозиторий '{name}' ({url})")


@remote.command()
@click.argument('name')
def remove(name):
    """Удалить удаленный репозиторий"""
    remote_manager = RemoteManager('.')
    remote_manager.remove_remote(name)
    click.echo(f"Удален удаленный репозиторий '{name}'")


@remote.command()
def list():
    """Показать список удаленных репозиториев"""
    remote_manager = RemoteManager('.')
    remotes = remote_manager.list_remotes()
    if remotes:
        click.echo("Удаленные репозитории:")
        for name, url in remotes.items():
            click.echo(f"  {name}\t{url}")
    else:
        click.echo("Нет настроенных удаленных репозиториев")


@cli.command()
@click.argument('remote')
@click.argument('branch')
@click.option('--force', '-f', is_flag=True, help='Принудительная отправка')
def push(remote, branch, force):
    """Отправить изменения в удаленный репозиторий"""
    remote_manager = RemoteManager('.')
    remote_manager.push(remote, branch, force)
    click.echo(f"Изменения отправлены в {remote}/{branch}")


@cli.command()
@click.argument('remote')
@click.argument('branch')
def pull(remote, branch):
    """Получить изменения из удаленного репозитория"""
    remote_manager = RemoteManager('.')
    remote_manager.pull(remote, branch)
    click.echo(f"Получены изменения из {remote}/{branch}")


@cli.command()
@click.argument('remote')
@click.option('--branch', '-b', help='Конкретная ветка для загрузки')
def fetch(remote, branch):
    """Загрузить информацию об изменениях"""
    remote_manager = RemoteManager('.')
    remote_manager.fetch(remote, branch)
    click.echo(f"Загружена информация об изменениях из {remote}")


@cli.command()
@click.argument('url')
@click.argument('destination', required=False)
def clone(url, destination):
    """Клонировать удаленный репозиторий"""
    remote_manager = RemoteManager('.')
    remote_manager.clone(url, destination)
    click.echo(f"Репозиторий клонирован из {url}")


@cli.group()
def graph():
    """Команды для визуализации репозитория"""
    pass


@graph.command()
@click.argument('output', type=click.Path(), required=False)
@click.option('--format', '-f', default='png', help='Формат выходного файла (png, svg, pdf)')
@click.option('--ignore', '-i', multiple=True, help='Паттерны для игнорирования')
@click.option('--console', '-c', is_flag=True, help='Вывести структуру в консоль')
def tree(output, format, ignore, console):
    """Создать граф структуры директорий"""
    try:
        repo = VCSRepository('.')
        graph_tool = RepoGraph(repo)
        ignore_patterns = set(ignore) if ignore else None
        
        if console:
            graph_tool.print_directory_tree(ignore_patterns)
        else:
            if not output:
                click.echo("Ошибка: укажите путь для сохранения файла или используйте --console", err=True)
                return
            result_path = graph_tool.create_directory_graph(output, format, ignore_patterns)
            click.echo(f"Граф сохранен в: {result_path}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


@graph.command()
@click.argument('output', type=click.Path())
@click.option('--format', '-f', default='png', help='Формат выходного файла (png, svg, pdf)')
@click.option('--max-commits', '-n', default=20, help='Максимальное количество коммитов')
def history(output, format, max_commits):
    """Создать граф истории коммитов"""
    try:
        repo = VCSRepository('.')
        graph_tool = RepoGraph(repo)
        result_path = graph_tool.create_commit_graph(output, format, max_commits)
        click.echo(f"Граф сохранен в: {result_path}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)


if __name__ == '__main__':
    cli() 