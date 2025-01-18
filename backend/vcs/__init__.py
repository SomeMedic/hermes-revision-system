"""
Core VCS functionality
"""

from .core import VCSRepository
from .hooks import HookManager, HookType
from .submodule import SubmoduleManager, Submodule

__all__ = [
    'VCSRepository',
    'HookManager',
    'HookType', 
    'SubmoduleManager',
    'Submodule'
] 