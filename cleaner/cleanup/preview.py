from __future__ import annotations

from pathlib import Path

from cleaner.cleanup.safety import SafetyPolicy


def build_preview(rows: list[dict[str, object]], safety_policy: SafetyPolicy) -> dict[str, object]:
    allowed: list[Path] = []
    blocked: list[tuple[Path, str]] = []
    allowed_size = 0
    blocked_size = 0

    for row in rows:
        path = Path(str(row["path"]))
        size = int(row.get("size", 0))
        mtime_raw = row.get("mtime")
        mtime = float(mtime_raw) if mtime_raw is not None else None

        protected, reason = safety_policy.validate_deletion(path, mtime=mtime)
        if protected:
            blocked.append((path, reason))
            blocked_size += size
        else:
            allowed.append(path)
            allowed_size += size

    return {
        "allowed": allowed,
        "blocked": blocked,
        "allowed_count": len(allowed),
        "blocked_count": len(blocked),
        "allowed_size": allowed_size,
        "blocked_size": blocked_size,
    }
