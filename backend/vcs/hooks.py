import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum, auto


class HookType(Enum):
    PRE_COMMIT = auto()
    POST_COMMIT = auto()
    PRE_PUSH = auto()
    POST_MERGE = auto()


class HookManager:
    HOOK_SCRIPTS = {
        HookType.PRE_COMMIT: "pre-commit",
        HookType.POST_COMMIT: "post-commit",
        HookType.PRE_PUSH: "pre-push",
        HookType.POST_MERGE: "post-merge"
    }

    def __init__(self, vcs_dir: Path):
        self.hooks_dir = vcs_dir / "hooks"
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_sample_hooks()

    def _ensure_sample_hooks(self) -> None:
        """Создает примеры хуков"""
        for hook_type in HookType:
            sample_path = self.hooks_dir / f"{self.HOOK_SCRIPTS[hook_type]}.sample"
            if not sample_path.exists():
                with open(sample_path, 'w') as f:
                    f.write(self._get_sample_hook_content(hook_type))

    def _get_sample_hook_content(self, hook_type: HookType) -> str:
        """Возвращает содержимое примера хука"""
        return f"""#!/bin/sh
#
# Пример {self.HOOK_SCRIPTS[hook_type]} хука
#
# Для активации уберите расширение .sample
#
# Возвращаемые значения:
# 0 - успешно
# не 0 - ошибка (прерывает операцию)

echo "Выполняется {self.HOOK_SCRIPTS[hook_type]} хук"
exit 0
"""

    def _get_hook_path(self, hook_type: HookType) -> Path:
        """Возвращает путь к файлу хука"""
        return self.hooks_dir / self.HOOK_SCRIPTS[hook_type]

    def is_hook_installed(self, hook_type: HookType) -> bool:
        """Проверяет, установлен ли хук"""
        return self._get_hook_path(hook_type).exists()

    def install_hook(self, hook_type: HookType, content: str) -> None:
        """Устанавливает хук"""
        hook_path = self._get_hook_path(hook_type)
        with open(hook_path, 'w') as f:
            f.write(content)
        # Делаем файл исполняемым
        hook_path.chmod(0o755)

    def uninstall_hook(self, hook_type: HookType) -> None:
        """Удаляет хук"""
        hook_path = self._get_hook_path(hook_type)
        if hook_path.exists():
            hook_path.unlink()

    def run_hook(self, hook_type: HookType, env: Optional[Dict[str, str]] = None) -> bool:
        """Запускает хук. Возвращает True если хук выполнен успешно"""
        hook_path = self._get_hook_path(hook_type)
        if not hook_path.exists():
            return True  # Если хук не установлен, считаем что всё ок
            
        try:
            # Подготавливаем окружение
            hook_env = os.environ.copy()
            if env:
                hook_env.update(env)
            
            # Запускаем хук
            result = subprocess.run(
                [str(hook_path)],
                env=hook_env,
                capture_output=True,
                text=True
            )
            
            # Выводим результат
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Ошибка при выполнении хука: {e}", file=sys.stderr)
            return False

    def list_hooks(self) -> Dict[str, bool]:
        """Возвращает список всех хуков и их статус"""
        return {
            self.HOOK_SCRIPTS[hook_type]: self.is_hook_installed(hook_type)
            for hook_type in HookType
        } 