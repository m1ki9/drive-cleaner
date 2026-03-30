from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from cleaner import config


class SafetyPolicy:
    def __init__(self, protected_roots: set[Path] | None = None, protected_extensions: set[str] | None = None) -> None:
        self.protected_roots = protected_roots or set(config.PROTECTED_ROOTS)
        self.protected_extensions = protected_extensions or set(config.PROTECTED_EXTENSIONS)
        self.protected_keywords = set(config.PROTECTED_KEYWORDS)
        self.recent_modification_days = config.RECENT_MODIFICATION_DAYS

    def is_protected(self, path: Path) -> tuple[bool, str]:
        resolved = self._safe_resolve(path)
        if resolved is None:
            return True, "Cannot resolve path"

        normalized = str(resolved).replace("\\", "/").lower()
        if any(keyword in normalized for keyword in self.protected_keywords):
            return True, "Protected by critical path keyword"

        for root in self.protected_roots:
            root_resolved = self._safe_resolve(root)
            if root_resolved and self._is_relative_to(resolved, root_resolved):
                return True, f"Protected system path: {root}"

        suffix = resolved.suffix.lower()
        if suffix in self.protected_extensions:
            return True, f"Protected extension: {suffix}"

        return False, "Allowed"

    def validate_deletion(self, path: Path, mtime: float | None = None) -> tuple[bool, str]:
        protected, reason = self.is_protected(path)
        if protected:
            return True, reason

        if mtime is None:
            return False, "Allowed"

        modified_at = datetime.fromtimestamp(mtime)
        cutoff = datetime.now() - timedelta(days=self.recent_modification_days)
        if modified_at >= cutoff:
            return True, f"Blocked recent file (<{self.recent_modification_days} days)"

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
