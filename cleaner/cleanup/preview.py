from __future__ import annotations

from pathlib import Path

from cleaner.cleanup.safety import SafetyPolicy


def build_preview(paths: list[Path], safety_policy: SafetyPolicy) -> dict[str, object]:
    allowed: list[Path] = []
    blocked: list[tuple[Path, str]] = []

    for path in paths:
        protected, reason = safety_policy.is_protected(path)
        if protected:
            blocked.append((path, reason))
        else:
            allowed.append(path)

    return {
        "allowed": allowed,
        "blocked": blocked,
        "allowed_count": len(allowed),
        "blocked_count": len(blocked),
    }
