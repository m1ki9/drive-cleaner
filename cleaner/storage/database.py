from __future__ import annotations

import sqlite3
from pathlib import Path

from cleaner.models import FileRecord, FolderRecord, ScanResult


class ScanDatabase:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS scan_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    total_size INTEGER NOT NULL,
                    total_files INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES scan_sessions(id)
                );

                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    parent_folder TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    category TEXT NOT NULL,
                    is_protected INTEGER NOT NULL,
                    content_hash TEXT,
                    deleted INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(session_id) REFERENCES scan_sessions(id)
                );

                CREATE TABLE IF NOT EXISTS duplicate_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    hash TEXT NOT NULL,
                    path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES scan_sessions(id)
                );

                CREATE TABLE IF NOT EXISTS cleanup_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES scan_sessions(id)
                );

                CREATE INDEX IF NOT EXISTS idx_folders_session_size ON folders(session_id, size DESC);
                CREATE INDEX IF NOT EXISTS idx_files_session_category ON files(session_id, category);
                CREATE INDEX IF NOT EXISTS idx_files_session_deleted ON files(session_id, deleted);
                """
            )

    def save_scan_result(self, root_path: Path, created_at: str, result: ScanResult) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scan_sessions (created_at, root_path, total_size, total_files)
                VALUES (?, ?, ?, ?)
                """,
                (created_at, str(root_path), result.total_size, result.total_files),
            )
            session_id = int(cursor.lastrowid)

            conn.executemany(
                "INSERT INTO folders (session_id, path, size) VALUES (?, ?, ?)",
                [(session_id, str(folder.path), folder.size) for folder in result.folders],
            )

            conn.executemany(
                """
                INSERT INTO files (session_id, path, parent_folder, size, mtime, category, is_protected, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        session_id,
                        str(file.path),
                        str(file.parent_folder),
                        file.size,
                        file.mtime,
                        file.category,
                        int(file.protected),
                        file.content_hash,
                    )
                    for file in result.files
                ],
            )
        return session_id

    def save_duplicate_groups(self, session_id: int, groups: dict[str, list[FileRecord]]) -> None:
        rows = []
        for file_hash, records in groups.items():
            for record in records:
                rows.append((session_id, file_hash, str(record.path), record.size))

        if not rows:
            return

        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO duplicate_groups (session_id, hash, path, size) VALUES (?, ?, ?, ?)",
                rows,
            )

    def get_latest_session(self) -> sqlite3.Row | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM scan_sessions ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return row

    def top_folders(self, session_id: int, limit: int = 20) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT path, size FROM folders WHERE session_id = ? ORDER BY size DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return rows

    def files_for_categories(self, session_id: int, categories: list[str]) -> list[sqlite3.Row]:
        placeholders = ",".join("?" for _ in categories)
        query = (
            "SELECT id, path, size, category, is_protected "
            "FROM files WHERE session_id = ? AND deleted = 0 AND category IN (" + placeholders + ")"
        )
        with self._connect() as conn:
            rows = conn.execute(query, [session_id, *categories]).fetchall()
        return rows

    def duplicate_download_rows(self, session_id: int) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT path, size FROM duplicate_groups WHERE session_id = ?",
                (session_id,),
            ).fetchall()
        return rows

    def mark_deleted(self, file_ids: list[int]) -> None:
        if not file_ids:
            return
        placeholders = ",".join("?" for _ in file_ids)
        query = "UPDATE files SET deleted = 1 WHERE id IN (" + placeholders + ")"
        with self._connect() as conn:
            conn.execute(query, file_ids)

    def log_cleanup(self, session_id: int, path: Path, action: str, status: str, message: str, created_at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cleanup_actions (session_id, path, action, status, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, str(path), action, status, message, created_at),
            )
