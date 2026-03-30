from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable

from cleaner.models import FileRecord, FolderRecord, ScanResult
from cleaner.scanning.classifier import classify_path
from cleaner.cleanup.safety import SafetyPolicy

ProgressCallback = Callable[[int, int], None]


class DiskScanner:
    def __init__(self, safety_policy: SafetyPolicy) -> None:
        self.safety_policy = safety_policy

    def scan(self, root: Path, progress_callback: ProgressCallback | None = None) -> ScanResult:
        root = root.resolve()
        folders_direct_sizes: dict[Path, int] = defaultdict(int)
        folders_direct_sizes[root] = 0
        files: list[FileRecord] = []
        scanned_files = 0
        scanned_bytes = 0

        stack = [root]
        while stack:
            current = stack.pop()
            try:
                for path in current.iterdir():
                    try:
                        if path.is_dir():
                            protected, _ = self.safety_policy.is_protected(path)
                            if protected:
                                continue
                            folders_direct_sizes[path] += 0
                            stack.append(path)
                            continue

                        if not path.is_file():
                            continue

                        stat = path.stat()
                        category = classify_path(path)
                        protected, _ = self.safety_policy.is_protected(path)
                        record = FileRecord(
                            path=path,
                            size=stat.st_size,
                            mtime=stat.st_mtime,
                            parent_folder=path.parent,
                            category=category,
                            protected=protected,
                        )
                        files.append(record)
                        folders_direct_sizes[path.parent] += stat.st_size
                        scanned_files += 1
                        scanned_bytes += stat.st_size

                        if progress_callback and scanned_files % 500 == 0:
                            progress_callback(scanned_files, scanned_bytes)
                    except (PermissionError, OSError):
                        continue
            except (PermissionError, OSError):
                continue

        folder_sizes = self._aggregate_folder_sizes(folders_direct_sizes)
        folders = [FolderRecord(path=path, size=size) for path, size in folder_sizes.items()]
        folders.sort(key=lambda item: item.size, reverse=True)

        if progress_callback:
            progress_callback(scanned_files, scanned_bytes)

        return ScanResult(
            total_size=scanned_bytes,
            total_files=scanned_files,
            folders=folders,
            files=files,
        )

    @staticmethod
    def _aggregate_folder_sizes(direct_sizes: dict[Path, int]) -> dict[Path, int]:
        totals = dict(direct_sizes)
        paths_by_depth = sorted(totals.keys(), key=lambda p: len(p.parts), reverse=True)
        for path in paths_by_depth:
            size = totals[path]
            parent = path.parent
            if parent != path and parent in totals:
                totals[parent] += size
        return totals
