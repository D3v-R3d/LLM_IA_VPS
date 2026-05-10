"""
Path Guard

Restrict file-system tools to allowed paths.
"""

from pathlib import Path
from typing import List, Set, Optional


class PathGuard:
    """
    Guard that ensures file paths are within allowed directories.
    
    Usage:
        guard = PathGuard()
        resolved = guard.resolve("/some/path")
        # raises ValueError if not allowed
    """
    
    def __init__(
        self,
        allowed_dirs: Optional[List[str]] = None,
        deny_hidden: bool = True,
        allow_symlinks: bool = False,
    ):
        default_allowed = [
            "/home",
            "/tmp",
            "/var/tmp",
        ]
        self._allowed: Set[Path] = set()
        for d in (allowed_dirs or default_allowed):
            self._allowed.add(Path(d).resolve())
        
        self._deny_hidden = deny_hidden
        self._allow_symlinks = allow_symlinks
    
    def resolve(self, path: str) -> Path:
        """
        Resolve and validate a path.
        Returns resolved Path if allowed, else raises ValueError.
        """
        try:
            p = Path(path).resolve()
        except Exception as e:
            raise ValueError(f"Invalid path: {path}") from e
        
        if self._deny_hidden:
            parts = p.parts
            for part in parts:
                if part.startswith('.') and part not in ('.', '..'):
                    raise ValueError(f"Hidden paths not allowed: {path}")
        
        if not self._allow_symlinks and p.is_symlink():
            raise ValueError(f"Symlinks not allowed: {path}")
        
        if not self._is_allowed(p):
            raise ValueError(f"Path not allowed: {path}")
        
        return p
    
    def _is_allowed(self, path: Path) -> bool:
        for allowed_dir in self._allowed:
            try:
                path.relative_to(allowed_dir)
                return True
            except ValueError:
                continue
        return False
    
    def add_allowed_dir(self, directory: str):
        self._allowed.add(Path(directory).resolve())
    
    def remove_allowed_dir(self, directory: str):
        resolved = Path(directory).resolve()
        self._allowed.discard(resolved)


_default_guard = PathGuard()


def resolve(path: str) -> Path:
    """Resolve a path using the default PathGuard instance."""
    return _default_guard.resolve(path)


def add_allowed_dir(directory: str):
    """Add a directory to the default allowed list."""
    _default_guard.add_allowed_dir(directory)


def remove_allowed_dir(directory: str):
    """Remove a directory from the default allowed list."""
    _default_guard.remove_allowed_dir(directory)