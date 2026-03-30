from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class FileRecord:
    path: Path
    size: int
    mtime: float
    parent_folder: Path
    category: str
    protected: bool
    content_hash: str | None = None


@dataclass(slots=True)
class FolderRecord:
    path: Path
    size: int


@dataclass(slots=True)
class ScanResult:
    total_size: int
    total_files: int
    folders: list[FolderRecord]
    files: list[FileRecord]
