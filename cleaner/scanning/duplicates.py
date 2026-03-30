from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from cleaner import config
from cleaner.models import FileRecord


def detect_duplicate_downloads(files: list[FileRecord]) -> dict[str, list[FileRecord]]:
    candidates_by_size: dict[int, list[FileRecord]] = defaultdict(list)

    for record in files:
        if record.category != config.CATEGORY_DUPLICATE_DOWNLOAD:
            continue
        if record.protected or record.size == 0:
            continue
        candidates_by_size[record.size].append(record)

    duplicates: dict[str, list[FileRecord]] = {}
    for same_size_records in candidates_by_size.values():
        if len(same_size_records) < 2:
            continue
        grouped_by_hash: dict[str, list[FileRecord]] = defaultdict(list)
        for record in same_size_records:
            file_hash = _hash_file(record.path)
            if not file_hash:
                continue
            record.content_hash = file_hash
            grouped_by_hash[file_hash].append(record)

        for file_hash, records in grouped_by_hash.items():
            if len(records) > 1:
                duplicates[file_hash] = records

    return duplicates


def _hash_file(path: Path) -> str | None:
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                data = handle.read(config.HASH_CHUNK_SIZE)
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()
    except (PermissionError, OSError):
        return None
