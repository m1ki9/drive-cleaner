from __future__ import annotations

from datetime import datetime
from pathlib import Path

from send2trash import send2trash

from cleaner.cleanup.safety import SafetyPolicy
from cleaner.storage.database import ScanDatabase


class CleanupExecutor:
    def __init__(self, db: ScanDatabase, safety_policy: SafetyPolicy) -> None:
        self.db = db
        self.safety_policy = safety_policy

    def delete_to_recycle_bin(self, session_id: int, file_rows: list[dict[str, object]]) -> tuple[list[int], list[str]]:
        deleted_file_ids: list[int] = []
        messages: list[str] = []

        for row in file_rows:
            file_id = int(row["id"])
            path = Path(str(row["path"]))
            mtime_raw = row.get("mtime")
            mtime = float(mtime_raw) if mtime_raw is not None else None
            protected, reason = self.safety_policy.validate_deletion(path, mtime=mtime)

            now = datetime.now().isoformat(timespec="seconds")
            if protected:
                msg = f"Blocked: {path} ({reason})"
                self.db.log_cleanup(session_id, path, "delete", "blocked", reason, now)
                messages.append(msg)
                continue

            try:
                send2trash(str(path))
                deleted_file_ids.append(file_id)
                self.db.log_cleanup(session_id, path, "delete", "success", "Moved to Recycle Bin", now)
            except OSError as error:
                msg = f"Failed: {path} ({error})"
                self.db.log_cleanup(session_id, path, "delete", "failed", str(error), now)
                messages.append(msg)

        self.db.mark_deleted(deleted_file_ids)
        return deleted_file_ids, messages
