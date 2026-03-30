from __future__ import annotations

from pathlib import Path

APP_NAME = "Drive Cleaner"
DB_FILE = "cleaner_data.sqlite3"

DEFAULT_SCAN_ROOT = Path("C:/")
DEFAULT_TOP_FOLDER_LIMIT = 25

CATEGORY_TEMP = "temp"
CATEGORY_CACHE = "cache"
CATEGORY_DUPLICATE_DOWNLOAD = "duplicate_download"
CATEGORY_JUNK = "junk"
CATEGORY_OTHER = "other"

CLEANUP_CATEGORIES = [
    CATEGORY_TEMP,
    CATEGORY_CACHE,
    CATEGORY_DUPLICATE_DOWNLOAD,
    CATEGORY_JUNK,
]

PROTECTED_ROOTS = {
    Path("C:/Windows"),
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path("C:/ProgramData"),
    Path("C:/$Recycle.Bin"),
    Path("C:/System Volume Information"),
    Path("C:/Recovery"),
    Path("C:/Boot"),
}

PROTECTED_EXTENSIONS = {
    ".sys",
    ".dll",
    ".exe",
    ".msi",
    ".drv",
}

TEMP_SEGMENTS = {
    "appdata/local/temp",
    "windows/temp",
    "temp",
}

CACHE_SEGMENTS = {
    "cache",
    "caches",
    "appdata/local/microsoft/windows/inetcache",
}

DOWNLOADS_SEGMENT = "downloads"

JUNK_EXTENSIONS = {
    ".tmp",
    ".bak",
    ".old",
    ".dmp",
    ".log",
}

MAX_FILES_FOR_FULL_SCAN_UI = 300_000
HASH_CHUNK_SIZE = 1024 * 1024
