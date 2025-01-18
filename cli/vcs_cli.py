import click
from pathlib import Path
import sys
import os
from datetime import datetime

# Добавляем путь к backend в PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from backend.vcs.core import VCSRepository
from backend.vcs.hooks import HookType


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


if __name__ == '__main__':
    cli() 