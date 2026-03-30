from __future__ import annotations

from pathlib import Path

from cleaner import config


class SafetyPolicy:
    def __init__(self, protected_roots: set[Path] | None = None, protected_extensions: set[str] | None = None) -> None:
        self.protected_roots = protected_roots or set(config.PROTECTED_ROOTS)
        self.protected_extensions = protected_extensions or set(config.PROTECTED_EXTENSIONS)

    def is_protected(self, path: Path) -> tuple[bool, str]:
        resolved = self._safe_resolve(path)
        if resolved is None:
            return True, "Cannot resolve path"

        for root in self.protected_roots:
            root_resolved = self._safe_resolve(root)
            if root_resolved and self._is_relative_to(resolved, root_resolved):
                return True, f"Protected system path: {root}"

        suffix = resolved.suffix.lower()
        if suffix in self.protected_extensions:
            return True, f"Protected extension: {suffix}"

        return False, "Allowed"

    @staticmethod
    def _safe_resolve(path: Path) -> Path | None:
        try:
            return path.resolve()
        except OSError:
            return None

    @staticmethod
    def _is_relative_to(path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False
