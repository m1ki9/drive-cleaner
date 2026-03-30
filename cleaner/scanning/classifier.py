from __future__ import annotations

from pathlib import Path

from cleaner import config


def classify_path(path: Path) -> str:
    normalized = str(path).replace("\\", "/").lower()

    if any(segment in normalized for segment in config.TEMP_SEGMENTS):
        return config.CATEGORY_TEMP

    if any(segment in normalized for segment in config.CACHE_SEGMENTS):
        return config.CATEGORY_CACHE

    if config.DOWNLOADS_SEGMENT in normalized:
        return config.CATEGORY_DUPLICATE_DOWNLOAD

    if path.suffix.lower() in config.JUNK_EXTENSIONS:
        return config.CATEGORY_JUNK

    return config.CATEGORY_OTHER
