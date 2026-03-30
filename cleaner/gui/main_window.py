from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

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
        self.geometry("1280x820")
        self.minsize(1100, 700)

        self.db = ScanDatabase(Path(config.DB_FILE))
        self.safety_policy = SafetyPolicy()
        self.scanner = DiskScanner(self.safety_policy)
        self.cleaner = CleanupExecutor(self.db, self.safety_policy)

        self.current_session_id: int | None = None
        self.chart_type = tk.StringVar(value="bar")
        self.scan_status = tk.StringVar(value="Ready")
        self.session_summary = tk.StringVar(value="Session: -")
        self.file_summary = tk.StringVar(value="Files: 0")
        self.size_summary = tk.StringVar(value="Size: 0.00 GB")
        self.scan_cancel_event = threading.Event()
        self.scan_thread: threading.Thread | None = None
        self.selected_categories: dict[str, tk.BooleanVar] = {
            category: tk.BooleanVar(value=True) for category in config.CLEANUP_CATEGORIES
        }

        self._setup_styles()
        self._build_layout()

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#f3f5f7")
        style.configure("Header.TFrame", background="#1f2937")
        style.configure("HeaderTitle.TLabel", background="#1f2937", foreground="#f9fafb", font=("Segoe UI Semibold", 16))
        style.configure("HeaderSub.TLabel", background="#1f2937", foreground="#cbd5e1", font=("Segoe UI", 10))
        style.configure("Stat.TLabel", background="#f3f5f7", foreground="#111827", font=("Segoe UI Semibold", 10))
        style.configure("Body.TFrame", background="#f3f5f7")
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=6)

    def _build_layout(self) -> None:
        root_frame = ttk.Frame(self, style="App.TFrame", padding=0)
        root_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root_frame, style="Header.TFrame", padding=(16, 14))
        header.pack(fill=tk.X)
        ttk.Label(header, text="Drive Cleaner Desktop", style="HeaderTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header,
            text="Offline disk scanning, visualization, and safety-first cleanup",
            style="HeaderSub.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        body = ttk.Frame(root_frame, style="Body.TFrame", padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        summary_row = ttk.Frame(body, style="Body.TFrame")
        summary_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(summary_row, textvariable=self.session_summary, style="Stat.TLabel").pack(side=tk.LEFT, padx=(0, 16))
        ttk.Label(summary_row, textvariable=self.file_summary, style="Stat.TLabel").pack(side=tk.LEFT, padx=(0, 16))
        ttk.Label(summary_row, textvariable=self.size_summary, style="Stat.TLabel").pack(side=tk.LEFT)

        controls = ttk.Frame(body, style="Body.TFrame")
        controls.pack(fill=tk.X)

        self.scan_button = ttk.Button(controls, text="Scan C:/", command=self.start_scan)
        self.scan_button.pack(side=tk.LEFT, padx=(0, 8))
        self.cancel_button = ttk.Button(controls, text="Cancel Scan", command=self.cancel_scan, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(controls, text="Load Latest", command=self.load_latest_results).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(controls, text="Preview Cleanup", command=self.preview_cleanup).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(controls, text="Delete Selected", command=self.execute_cleanup).pack(side=tk.LEFT)

        ttk.Radiobutton(controls, text="Bar", variable=self.chart_type, value="bar", command=self.refresh_chart).pack(side=tk.RIGHT, padx=4)
        ttk.Radiobutton(controls, text="Pie", variable=self.chart_type, value="pie", command=self.refresh_chart).pack(side=tk.RIGHT, padx=4)

        ttk.Label(body, textvariable=self.scan_status).pack(fill=tk.X, pady=(8, 4))
        self.progress = ttk.Progressbar(body, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 8))

        category_frame = ttk.LabelFrame(body, text="Cleanup Categories")
        category_frame.pack(fill=tk.X, pady=(0, 8))
        for category in config.CLEANUP_CATEGORIES:
            ttk.Checkbutton(category_frame, text=category, variable=self.selected_categories[category]).pack(side=tk.LEFT, padx=6, pady=4)

        content = ttk.Panedwindow(body, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(content, padding=5)
        right = ttk.Frame(content, padding=5)
        content.add(left, weight=1)
        content.add(right, weight=1)

        self.folder_tree = ttk.Treeview(left, columns=("path", "size_gb"), show="headings", height=22)
        self.folder_tree.heading("path", text="Folder")
        self.folder_tree.column("path", width=580, anchor=tk.W)
        self.folder_tree.heading("size_gb", text="Size (GB)")
        self.folder_tree.column("size_gb", width=120, minwidth=100, anchor=tk.E)

        tree_wrapper = ttk.Frame(left)
        tree_wrapper.pack(fill=tk.BOTH, expand=True)
        tree_scrollbar = ttk.Scrollbar(tree_wrapper, orient=tk.VERTICAL, command=self.folder_tree.yview)
        self.folder_tree.configure(yscrollcommand=tree_scrollbar.set)
        self.folder_tree.pack(in_=tree_wrapper, side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.chart_host = ttk.Frame(right)
        self.chart_host.pack(fill=tk.BOTH, expand=True)

        log_frame = ttk.LabelFrame(right, text="Activity Log")
        log_frame.pack(fill=tk.BOTH, expand=False, pady=(8, 0))
        self.log_box = scrolledtext.ScrolledText(log_frame, height=7, state=tk.DISABLED, wrap=tk.WORD)
        self.log_box.pack(fill=tk.BOTH, expand=True)

    def _set_scan_controls(self, running: bool) -> None:
        self.scan_button.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.cancel_button.configure(state=tk.NORMAL if running else tk.DISABLED)
        if running:
            self.progress.start(10)
        else:
            self.progress.stop()

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def start_scan(self) -> None:
        if self.scan_thread and self.scan_thread.is_alive():
            return

        self.scan_cancel_event.clear()
        self._set_scan_controls(running=True)
        self.scan_status.set("Scanning C:/ ...")
        self._append_log("Scan started")
        self.scan_thread = threading.Thread(target=self._run_scan_job, daemon=True)
        self.scan_thread.start()

    def cancel_scan(self) -> None:
        if not self.scan_thread or not self.scan_thread.is_alive():
            return
        self.scan_cancel_event.set()
        self.scan_status.set("Cancelling scan ...")
        self._append_log("Scan cancellation requested")

    def _run_scan_job(self) -> None:
        def on_progress(file_count: int, bytes_count: int) -> None:
            gb = bytes_count / (1024**3)
            self.after(0, lambda: self.scan_status.set(f"Scanning... files={file_count:,} size={gb:.2f} GB"))

        try:
            result = self.scanner.scan(
                config.DEFAULT_SCAN_ROOT,
                progress_callback=on_progress,
                cancel_event=self.scan_cancel_event,
            )

            if self.scan_cancel_event.is_set():
                self.after(0, lambda: self.scan_status.set("Scan cancelled"))
                self.after(0, lambda: self._append_log("Scan cancelled"))
                return

            duplicates = detect_duplicate_downloads(result.files)
            created_at = datetime.now().isoformat(timespec="seconds")
            session_id = self.db.save_scan_result(config.DEFAULT_SCAN_ROOT, created_at, result)
            self.db.save_duplicate_groups(session_id, duplicates)

            self.current_session_id = session_id
            self.after(0, self.load_latest_results)
            self.after(0, lambda: self.scan_status.set("Scan complete"))
            self.after(0, lambda: self._append_log("Scan complete and saved"))
        except Exception as error:
            self.after(0, lambda: self.scan_status.set(f"Scan failed: {error}"))
            self.after(0, lambda: self._append_log(f"Scan failed: {error}"))
        finally:
            self.after(0, lambda: self._set_scan_controls(running=False))

    def load_latest_results(self) -> None:
        latest = self.db.get_latest_session()
        if latest is None:
            messagebox.showinfo("No Data", "No scan results found yet.")
            return

        self.current_session_id = int(latest["id"])
        self.session_summary.set(f"Session: {latest['id']}")
        self.file_summary.set(f"Files: {latest['total_files']:,}")
        self.size_summary.set(f"Size: {(latest['total_size'] / (1024**3)):.2f} GB")
        self.scan_status.set(
            f"Loaded session {latest['id']} | files={latest['total_files']:,} | total={(latest['total_size']/(1024**3)):.2f} GB"
        )
        self._append_log(f"Loaded session {latest['id']}")

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

        preview_input = [
            {
                "path": str(row["path"]),
                "size": int(row["size"]),
                "mtime": float(row["mtime"]),
            }
            for row in rows
        ]
        preview = build_preview(preview_input, self.safety_policy)

        total_bytes = sum(int(row["size"]) for row in rows)

        lines = [
            "Cleanup Preview",
            "",
            f"Selected files: {len(rows):,}",
            f"Allowed: {preview['allowed_count']:,}",
            f"Blocked: {preview['blocked_count']:,}",
            f"Total size: {total_bytes / (1024**3):.2f} GB",
            f"Allowed size: {preview['allowed_size'] / (1024**3):.2f} GB",
            f"Blocked size: {preview['blocked_size'] / (1024**3):.2f} GB",
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
        self._append_log(
            f"Previewed cleanup set: allowed={preview['allowed_count']}, blocked={preview['blocked_count']}"
        )

    def execute_cleanup(self) -> None:
        if self.current_session_id is None:
            messagebox.showinfo("Cleanup", "Load or run a scan session first.")
            return

        rows = self._candidate_cleanup_rows()
        if not rows:
            messagebox.showinfo("Cleanup", "No files found for selected categories.")
            return

        preview_input = [
            {
                "id": int(row["id"]),
                "path": str(row["path"]),
                "size": int(row["size"]),
                "mtime": float(row["mtime"]),
            }
            for row in rows
        ]
        preview = build_preview(preview_input, self.safety_policy)
        if preview["allowed_count"] == 0:
            messagebox.showinfo("Cleanup", "All selected files are blocked by safety policy.")
            self._append_log("Cleanup blocked: no eligible files")
            return

        allowed_gb = preview["allowed_size"] / (1024**3)
        if allowed_gb >= config.LARGE_CLEANUP_WARNING_GB:
            warning_ok = messagebox.askyesno(
                "Large Cleanup Warning",
                f"You are about to move {allowed_gb:.2f} GB to Recycle Bin. Continue?",
            )
            if not warning_ok:
                self._append_log("Large cleanup warning declined")
                return

        confirm = messagebox.askyesno(
            "Confirm Cleanup",
            "Only previewed and non-protected files will be moved to Recycle Bin. Continue?",
        )
        if not confirm:
            self._append_log("Cleanup cancelled by user")
            return

        allowed_set = {str(path) for path in preview["allowed"]}
        allowed_rows = [
            {
                "id": row["id"],
                "path": row["path"],
                "mtime": row["mtime"],
            }
            for row in rows
            if str(row["path"]) in allowed_set
        ]

        deleted_ids, messages = self.cleaner.delete_to_recycle_bin(self.current_session_id, allowed_rows)
        message = f"Deleted {len(deleted_ids)} files to Recycle Bin."
        if messages:
            message += "\n\nNotes:\n" + "\n".join(messages[:10])

        messagebox.showinfo("Cleanup Result", message)
        self._append_log(f"Cleanup completed: deleted={len(deleted_ids)}, notes={len(messages)}")
        self.load_latest_results()


def run_app() -> None:
    app = CleanerApp()
    app.mainloop()
