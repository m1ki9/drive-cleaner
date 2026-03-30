from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from cleaner import config
from cleaner.cleanup.executor import CleanupExecutor
from cleaner.cleanup.preview import build_preview
from cleaner.cleanup.safety import SafetyPolicy
from cleaner.scanning.duplicates import detect_duplicate_downloads
from cleaner.scanning.scanner import DiskScanner
from cleaner.storage.database import ScanDatabase
from cleaner.visualization.charts import create_top_folders_figure


class CleanerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(config.APP_NAME)
        self.geometry("1200x760")

        self.db = ScanDatabase(Path(config.DB_FILE))
        self.safety_policy = SafetyPolicy()
        self.scanner = DiskScanner(self.safety_policy)
        self.cleaner = CleanupExecutor(self.db, self.safety_policy)

        self.current_session_id: int | None = None
        self.chart_type = tk.StringVar(value="bar")
        self.scan_status = tk.StringVar(value="Ready")
        self.selected_categories: dict[str, tk.BooleanVar] = {
            category: tk.BooleanVar(value=True) for category in config.CLEANUP_CATEGORIES
        }

        self._build_layout()

    def _build_layout(self) -> None:
        root_frame = ttk.Frame(self, padding=10)
        root_frame.pack(fill=tk.BOTH, expand=True)

        controls = ttk.Frame(root_frame)
        controls.pack(fill=tk.X)

        ttk.Button(controls, text="Scan C:/", command=self.start_scan).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(controls, text="Load Latest", command=self.load_latest_results).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(controls, text="Preview Cleanup", command=self.preview_cleanup).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(controls, text="Delete Selected Category Files", command=self.execute_cleanup).pack(side=tk.LEFT)

        ttk.Radiobutton(controls, text="Bar", variable=self.chart_type, value="bar", command=self.refresh_chart).pack(side=tk.RIGHT, padx=4)
        ttk.Radiobutton(controls, text="Pie", variable=self.chart_type, value="pie", command=self.refresh_chart).pack(side=tk.RIGHT, padx=4)

        status = ttk.Label(root_frame, textvariable=self.scan_status)
        status.pack(fill=tk.X, pady=(8, 8))

        category_frame = ttk.LabelFrame(root_frame, text="Cleanup Categories")
        category_frame.pack(fill=tk.X, pady=(0, 8))
        for category in config.CLEANUP_CATEGORIES:
            ttk.Checkbutton(category_frame, text=category, variable=self.selected_categories[category]).pack(side=tk.LEFT, padx=6, pady=4)

        content = ttk.Panedwindow(root_frame, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(content, padding=5)
        right = ttk.Frame(content, padding=5)
        content.add(left, weight=1)
        content.add(right, weight=1)

        self.folder_tree = ttk.Treeview(left, columns=("path", "size_gb"), show="headings", height=26)
        self.folder_tree.heading("path", text="Folder")
        self.folder_tree.column("path", width=520, anchor=tk.W)
        self.folder_tree.heading("size_gb", text="Size (GB)")
        self.folder_tree.column("size_gb", width=120, anchor=tk.E)
        self.folder_tree.pack(fill=tk.BOTH, expand=True)

        self.chart_host = ttk.Frame(right)
        self.chart_host.pack(fill=tk.BOTH, expand=True)

    def start_scan(self) -> None:
        self.scan_status.set("Scanning C:/ ...")
        thread = threading.Thread(target=self._run_scan_job, daemon=True)
        thread.start()

    def _run_scan_job(self) -> None:
        def on_progress(file_count: int, bytes_count: int) -> None:
            gb = bytes_count / (1024**3)
            self.after(0, lambda: self.scan_status.set(f"Scanning... files={file_count:,} size={gb:.2f} GB"))

        result = self.scanner.scan(config.DEFAULT_SCAN_ROOT, progress_callback=on_progress)
        duplicates = detect_duplicate_downloads(result.files)

        created_at = datetime.now().isoformat(timespec="seconds")
        session_id = self.db.save_scan_result(config.DEFAULT_SCAN_ROOT, created_at, result)
        self.db.save_duplicate_groups(session_id, duplicates)

        self.current_session_id = session_id
        self.after(0, self.load_latest_results)
        self.after(0, lambda: self.scan_status.set("Scan complete"))

    def load_latest_results(self) -> None:
        latest = self.db.get_latest_session()
        if latest is None:
            messagebox.showinfo("No Data", "No scan results found yet.")
            return

        self.current_session_id = int(latest["id"])
        self.scan_status.set(
            f"Loaded session {latest['id']} | files={latest['total_files']:,} | total={(latest['total_size']/(1024**3)):.2f} GB"
        )

        rows = self.db.top_folders(self.current_session_id, config.DEFAULT_TOP_FOLDER_LIMIT)
        self._render_folder_rows(rows)
        self.refresh_chart()

    def _render_folder_rows(self, rows: list[object]) -> None:
        for item in self.folder_tree.get_children():
            self.folder_tree.delete(item)

        for row in rows:
            path = str(row["path"])
            size_gb = float(row["size"]) / (1024**3)
            self.folder_tree.insert("", tk.END, values=(path, f"{size_gb:.2f}"))

    def refresh_chart(self) -> None:
        if self.current_session_id is None:
            return

        rows = self.db.top_folders(self.current_session_id, config.DEFAULT_TOP_FOLDER_LIMIT)
        tuple_rows = [(str(row["path"]), int(row["size"])) for row in rows]

        for child in self.chart_host.winfo_children():
            child.destroy()

        figure = create_top_folders_figure(tuple_rows, chart_type=self.chart_type.get())
        canvas = FigureCanvasTkAgg(figure, master=self.chart_host)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _selected_cleanup_categories(self) -> list[str]:
        return [name for name, variable in self.selected_categories.items() if variable.get()]

    def _candidate_cleanup_rows(self) -> list[object]:
        if self.current_session_id is None:
            return []

        categories = self._selected_cleanup_categories()
        if not categories:
            return []

        return self.db.files_for_categories(self.current_session_id, categories)

    def preview_cleanup(self) -> None:
        rows = self._candidate_cleanup_rows()
        if not rows:
            messagebox.showinfo("Preview", "No files found for selected categories.")
            return

        paths = [Path(str(row["path"])) for row in rows]
        preview = build_preview(paths, self.safety_policy)

        total_bytes = 0
        for row in rows:
            total_bytes += int(row["size"])

        lines = [
            "Cleanup Preview",
            "",
            f"Selected files: {len(rows):,}",
            f"Allowed: {preview['allowed_count']:,}",
            f"Blocked: {preview['blocked_count']:,}",
            f"Total size: {total_bytes / (1024**3):.2f} GB",
            "",
            "Blocked examples:",
        ]
        blocked = list(preview["blocked"])[:10]
        if not blocked:
            lines.append("None")
        else:
            for blocked_path, reason in blocked:
                lines.append(f"- {blocked_path} | {reason}")

        messagebox.showinfo("Preview", "\n".join(lines))

    def execute_cleanup(self) -> None:
        rows = self._candidate_cleanup_rows()
        if not rows:
            messagebox.showinfo("Cleanup", "No files found for selected categories.")
            return

        paths = [Path(str(row["path"])) for row in rows]
        preview = build_preview(paths, self.safety_policy)
        if preview["allowed_count"] == 0:
            messagebox.showinfo("Cleanup", "All selected files are blocked by safety policy.")
            return

        confirm = messagebox.askyesno(
            "Confirm Cleanup",
            "Only previewed and non-protected files will be moved to Recycle Bin. Continue?",
        )
        if not confirm:
            return

        allowed_set = {str(path) for path in preview["allowed"]}
        allowed_rows = [
            {
                "id": row["id"],
                "path": row["path"],
            }
            for row in rows
            if str(row["path"]) in allowed_set
        ]

        deleted_ids, messages = self.cleaner.delete_to_recycle_bin(self.current_session_id or 0, allowed_rows)
        message = f"Deleted {len(deleted_ids)} files to Recycle Bin."
        if messages:
            message += "\n\nNotes:\n" + "\n".join(messages[:10])

        messagebox.showinfo("Cleanup Result", message)
        self.load_latest_results()


def run_app() -> None:
    app = CleanerApp()
    app.mainloop()
