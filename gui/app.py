
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from organizer.categorizer import organize_folder, category_for
from organizer.duplicates import find_duplicates
from organizer.renamer import batch_rename
from organizer.history import undo_last
from organizer.logger import LOG_FILE

try:
    from organizer.scanner import scan_folder
except ImportError:
    scan_folder = None

# Distinct category palette
CATEGORY_COLORS = {
    "Documents": "#3B82F6",  # blue
    "Images": "#8B5CF6",     # purple
    "Videos": "#EF4444",     # red
    "Audio": "#22C55E",      # green
    "Archives": "#F59E0B",   # orange
    "Code": "#06B6D4",       # cyan
    "Others": "#64748B",     # slate gray
}

BG = "#F4F7FB"
CARD = "#FFFFFF"
TEXT = "#111827"
MUTED = "#6B7280"
PRIMARY = "#2563EB"
DANGER = "#DC2626"


def human_size(num):
    value = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024


class FileOrganizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart File Organizer")
        self.geometry("1180x760")
        self.minsize(980, 650)
        self.configure(bg=BG)

        self.folder = tk.StringVar()
        self.pattern = tk.StringVar(value="file_{number}")
        self.status = tk.StringVar(value="Select a folder and click Scan.")
        self.stat_vars = {
            "files": tk.StringVar(value="0"),
            "storage": tk.StringVar(value="0 B"),
            "duplicates": tk.StringVar(value="0"),
            "large": tk.StringVar(value="0"),
        }
        self.category_counts = {name: 0 for name in CATEGORY_COLORS}
        self.category_widgets = {}

        self._setup_styles()
        self._build()

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Global professional desktop styling
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)

        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=CARD, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 23))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Stat.TLabel", background=CARD, foreground=TEXT, font=("Segoe UI Semibold", 20))

        style.configure(
            "TEntry",
            fieldbackground="#FFFFFF",
            foreground=TEXT,
            bordercolor="#D7DEE8",
            lightcolor="#D7DEE8",
            darkcolor="#D7DEE8",
            padding=7,
        )

        style.configure(
            "TButton",
            background="#F8FAFC",
            foreground="#334155",
            bordercolor="#D9E0E9",
            lightcolor="#F8FAFC",
            darkcolor="#F8FAFC",
            font=("Segoe UI Semibold", 9),
            padding=(13, 9),
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("active", "#EEF3F8"), ("pressed", "#E5EBF2")],
            bordercolor=[("active", "#C8D2DF")],
        )

        style.configure(
            "Primary.TButton",
            background=PRIMARY,
            foreground="#FFFFFF",
            bordercolor=PRIMARY,
            lightcolor=PRIMARY,
            darkcolor=PRIMARY,
            font=("Segoe UI Semibold", 9),
            padding=(14, 9),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#1D4ED8"), ("pressed", "#1E40AF")],
            foreground=[("active", "#FFFFFF")],
        )

        style.configure(
            "Danger.TButton",
            background="#FEF2F2",
            foreground=DANGER,
            bordercolor="#FECACA",
            font=("Segoe UI Semibold", 9),
            padding=(14, 9),
        )

        for category, color in CATEGORY_COLORS.items():
            style.configure(
                f"{category}.Horizontal.TProgressbar",
                troughcolor="#EDF1F6",
                background=color,
                bordercolor="#EDF1F6",
                lightcolor=color,
                darkcolor=color,
                thickness=11,
            )

    def _build(self):
        # Header
        header = ttk.Frame(self, padding=(30, 24, 30, 12))
        header.pack(fill="x")

        title_row = ttk.Frame(header)
        title_row.pack(fill="x")
        ttk.Label(title_row, text="SMART FILE ORGANIZER", style="Title.TLabel").pack(side="left")
        version = tk.Label(
            title_row, text="DESKTOP", bg="#E8F0FE", fg=PRIMARY,
            font=("Segoe UI Semibold", 8), padx=9, pady=4
        )
        version.pack(side="left", padx=(12, 0))

        ttk.Label(
            header,
            text="Organize, analyze, rename and manage duplicate files from one clean workspace.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(5, 0))

        # Folder selector card
        selector_wrap = ttk.Frame(self, padding=(30, 0, 30, 14))
        selector_wrap.pack(fill="x")
        selector_card = tk.Frame(
            selector_wrap, bg=CARD, highlightbackground="#DFE5EC", highlightthickness=1
        )
        selector_card.pack(fill="x")

        selector = tk.Frame(selector_card, bg=CARD)
        selector.pack(fill="x", padx=15, pady=13)
        tk.Label(
            selector, text="Selected folder", bg=CARD, fg=MUTED,
            font=("Segoe UI Semibold", 9)
        ).pack(side="left", padx=(0, 12))

        entry = ttk.Entry(selector, textvariable=self.folder, font=("Segoe UI", 10))
        entry.pack(side="left", fill="x", expand=True)
        ttk.Button(
            selector, text="Browse Folder", style="Primary.TButton",
            command=self.select_folder
        ).pack(side="left", padx=(10, 0))

        # Statistics
        stats = ttk.Frame(self, padding=(30, 0, 30, 14))
        stats.pack(fill="x")
        cards = [
            ("TOTAL FILES", "files", "#2563EB"),
            ("STORAGE USED", "storage", "#7C3AED"),
            ("DUPLICATE COPIES", "duplicates", "#DC2626"),
            ("LARGE FILES", "large", "#EA580C"),
        ]

        for col, (label, key, accent) in enumerate(cards):
            stats.columnconfigure(col, weight=1)
            card = tk.Frame(
                stats, bg=CARD, highlightbackground="#DFE5EC",
                highlightthickness=1
            )
            card.grid(
                row=0, column=col, sticky="nsew",
                padx=(0 if col == 0 else 7, 0 if col == 3 else 7)
            )

            accent_bar = tk.Frame(card, bg=accent, width=4)
            accent_bar.pack(side="left", fill="y")

            content = tk.Frame(card, bg=CARD)
            content.pack(side="left", fill="both", expand=True, padx=16, pady=13)

            tk.Label(
                content, text=label, bg=CARD, fg=MUTED,
                font=("Segoe UI Semibold", 8)
            ).pack(anchor="w")
            tk.Label(
                content, textvariable=self.stat_vars[key], bg=CARD, fg=TEXT,
                font=("Segoe UI Semibold", 21)
            ).pack(anchor="w", pady=(3, 0))

        # Main content
        body = ttk.Frame(self, padding=(30, 0, 30, 12))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=5)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(1, weight=1)

        # Horizontal actions toolbar - same position and same actions
        toolbar_card = tk.Frame(
            body, bg=CARD, highlightbackground="#DFE5EC", highlightthickness=1
        )
        toolbar_card.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        toolbar_header = tk.Frame(toolbar_card, bg=CARD)
        toolbar_header.pack(fill="x", padx=16, pady=(11, 4))
        tk.Label(
            toolbar_header, text="Quick Actions", bg=CARD, fg=TEXT,
            font=("Segoe UI Semibold", 10)
        ).pack(side="left")
        tk.Label(
            toolbar_header, text="Choose an operation for the selected folder",
            bg=CARD, fg=MUTED, font=("Segoe UI", 8)
        ).pack(side="left", padx=(10, 0))

        toolbar = tk.Frame(toolbar_card, bg=CARD)
        toolbar.pack(fill="x", padx=12, pady=(3, 12))

        buttons = [
            ("Scan", self.scan),
            ("Preview", self.preview),
            ("Organize", self.organize),
            ("Duplicates", self.duplicates),
            ("Batch Rename", self.rename_dialog),
            ("Undo", self.undo),
        ]
        for i, (button_text, command) in enumerate(buttons):
            toolbar.columnconfigure(i, weight=1)
            style_name = "Primary.TButton" if button_text == "Scan" else "TButton"
            ttk.Button(
                toolbar, text=button_text, command=command, style=style_name
            ).grid(row=0, column=i, sticky="ew", padx=4)

        # File Categories
        category_card = tk.Frame(
            body, bg=CARD, highlightbackground="#DFE5EC", highlightthickness=1
        )
        category_card.grid(row=1, column=0, sticky="nsew", padx=(0, 7))

        cat_head = tk.Frame(category_card, bg=CARD)
        cat_head.pack(fill="x", padx=20, pady=(18, 3))
        tk.Label(
            cat_head, text="File Categories", bg=CARD, fg=TEXT,
            font=("Segoe UI Semibold", 14)
        ).pack(side="left")
        tk.Label(
            category_card, text="Distribution of files in the selected folder",
            bg=CARD, fg=MUTED, font=("Segoe UI", 9)
        ).pack(anchor="w", padx=20, pady=(0, 14))

        divider = tk.Frame(category_card, bg="#EDF0F4", height=1)
        divider.pack(fill="x", padx=20)

        cat_inner = tk.Frame(category_card, bg=CARD)
        cat_inner.pack(fill="both", expand=True, padx=20, pady=(10, 16))

        for category, color in CATEGORY_COLORS.items():
            line = tk.Frame(cat_inner, bg=CARD)
            line.pack(fill="x", pady=7)

            dot = tk.Canvas(
                line, width=11, height=11, bg=CARD, highlightthickness=0
            )
            dot.create_oval(1, 1, 10, 10, fill=color, outline=color)
            dot.pack(side="left", padx=(0, 9))

            tk.Label(
                line, text=category, width=11, anchor="w",
                bg=CARD, fg="#334155", font=("Segoe UI Semibold", 9)
            ).pack(side="left")

            count_label = tk.Label(
                line, text="0", width=7, anchor="e",
                bg=CARD, fg=color, font=("Segoe UI Semibold", 9)
            )
            count_label.pack(side="right")

            bar = ttk.Progressbar(
                line,
                style=f"{category}.Horizontal.TProgressbar",
                orient="horizontal",
                mode="determinate",
                maximum=100,
            )
            bar.pack(side="left", fill="x", expand=True, padx=(10, 12))
            self.category_widgets[category] = (bar, count_label)

        # Activity / Results
        right = tk.Frame(
            body, bg=CARD, highlightbackground="#DFE5EC", highlightthickness=1
        )
        right.grid(row=1, column=1, sticky="nsew", padx=(7, 0))

        result_head = tk.Frame(right, bg=CARD)
        result_head.pack(fill="x", padx=20, pady=(18, 3))
        tk.Label(
            result_head, text="Activity / Results", bg=CARD, fg=TEXT,
            font=("Segoe UI Semibold", 14)
        ).pack(side="left")
        tk.Label(
            right, text="Operation details and scan information",
            bg=CARD, fg=MUTED, font=("Segoe UI", 9)
        ).pack(anchor="w", padx=20, pady=(0, 14))

        divider2 = tk.Frame(right, bg="#EDF0F4", height=1)
        divider2.pack(fill="x", padx=20)

        text_frame = tk.Frame(right, bg=CARD)
        text_frame.pack(fill="both", expand=True, padx=20, pady=(12, 16))
        self.output = tk.Text(
            text_frame, wrap="word", relief="flat",
            bg="#F8FAFC", fg="#334155",
            insertbackground=TEXT,
            selectbackground="#DBEAFE",
            selectforeground=TEXT,
            font=("Cascadia Mono", 9),
            padx=12, pady=12,
            borderwidth=0,
        )
        scroll = ttk.Scrollbar(text_frame, command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set)
        self.output.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Footer/status
        footer = ttk.Frame(self, padding=(30, 0, 30, 18))
        footer.pack(fill="x")

        status_dot = tk.Canvas(
            footer, width=9, height=9, bg=BG, highlightthickness=0
        )
        status_dot.create_oval(1, 1, 8, 8, fill="#22C55E", outline="#22C55E")
        status_dot.pack(side="left", padx=(0, 7))

        ttk.Label(
            footer, textvariable=self.status, style="Muted.TLabel"
        ).pack(side="left")

        ttk.Button(
            footer, text="View Logs", command=self.view_logs
        ).pack(side="right")

    def select_folder(self):
        selected = filedialog.askdirectory()
        if selected:
            self.folder.set(selected)
            self.status.set("Folder selected. Click Scan to update the dashboard.")
            self.scan()

    def _valid_folder(self):
        path = Path(self.folder.get())
        if not path.is_dir():
            messagebox.showerror("Invalid folder", "Please select a valid folder first.")
            return None
        return path

    def _write(self, text):
        self.output.delete("1.0", "end")
        self.output.insert("end", text)

    def scan(self):
        folder = self._valid_folder()
        if not folder:
            return
        self.status.set("Scanning folder...")
        self.update_idletasks()

        files = [p for p in folder.rglob("*") if p.is_file()]
        total_size = 0
        large = 0
        counts = {name: 0 for name in CATEGORY_COLORS}

        for p in files:
            try:
                size = p.stat().st_size
                total_size += size
                if size >= 100 * 1024 * 1024:
                    large += 1
                cat = category_for(p)
                if cat not in counts:
                    cat = "Others"
                counts[cat] += 1
            except OSError:
                pass

        try:
            groups = find_duplicates(folder)
            duplicate_copies = sum(max(0, len(g) - 1) for g in groups)
        except Exception:
            groups = []
            duplicate_copies = 0

        self.stat_vars["files"].set(f"{len(files):,}")
        self.stat_vars["storage"].set(human_size(total_size))
        self.stat_vars["duplicates"].set(f"{duplicate_copies:,}")
        self.stat_vars["large"].set(f"{large:,}")

        max_count = max(counts.values(), default=1) or 1
        for category, count in counts.items():
            bar, label = self.category_widgets[category]
            # Relative-to-largest scaling keeps small categories visible.
            bar["value"] = (count / max_count) * 100
            label.config(text=f"{count:,}")

        self.category_counts = counts
        summary = ["Scan complete:", f"  Total files: {len(files):,}", f"  Storage: {human_size(total_size)}",
                   f"  Duplicate copies: {duplicate_copies:,}", f"  Large files (>100 MB): {large:,}", "", "Categories:"]
        summary += [f"  {name}: {counts[name]:,}" for name in CATEGORY_COLORS]
        self._write("\n".join(summary))
        self.status.set("Dashboard updated.")

    def preview(self):
        folder = self._valid_folder()
        if not folder:
            return
        lines = ["Organization Preview", "--------------------"]
        count = 0
        for p in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
            if p.is_file():
                category = category_for(p)
                lines.append(f"{p.name}  →  {category}/{p.name}")
                count += 1
        if not count:
            lines.append("No files directly inside this folder to organize.")
        self._write("\n".join(lines))
        self.status.set(f"Preview generated for {count} file(s).")

    def organize(self):
        folder = self._valid_folder()
        if not folder:
            return
        if not messagebox.askyesno("Confirm Organization", "Move files into category folders?\n\nYou can undo this operation."):
            return
        try:
            count = organize_folder(folder)
            self._write(f"Organization complete.\n\nFiles moved: {count}")
            self.status.set(f"{count} file(s) organized.")
            self.scan()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def duplicates(self):
        folder = self._valid_folder()
        if not folder:
            return
        try:
            groups = find_duplicates(folder)
            if not groups:
                self._write("No duplicate files found.")
                return

            lines = [f"Duplicate groups: {len(groups)}\n"]
            for i, group in enumerate(groups, 1):
                lines.append(f"Group {i} — keep first copy:")
                for j, p in enumerate(group):
                    marker = "KEEP" if j == 0 else "DUPLICATE"
                    lines.append(f"  [{marker}] {p}")
                lines.append("")
            self._write("\n".join(lines))

            duplicate_count = sum(len(g) - 1 for g in groups)
            if messagebox.askyesno(
                "Delete Duplicate Copies?",
                f"Found {duplicate_count} duplicate copy/copies.\n\n"
                "Delete all duplicates while keeping one file from each identical group?\n\n"
                "WARNING: This deletion is permanent and cannot be undone."
            ):
                deleted = 0
                for group in groups:
                    for p in group[1:]:
                        try:
                            p.unlink()
                            deleted += 1
                        except OSError:
                            pass
                self._write(f"Duplicate cleanup complete.\n\nDeleted: {deleted}\nKept one copy from every duplicate group.")
                self.status.set(f"{deleted} duplicate file(s) deleted.")
                self.scan()
        except Exception as exc:
            messagebox.showerror("Duplicate error", str(exc))

    def rename_dialog(self):
        folder = self._valid_folder()
        if not folder:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Batch Rename")
        dialog.geometry("480x220")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Batch Rename", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Use {number}, {name}, {date}, or {extension}").pack(anchor="w", pady=(4, 10))
        entry = ttk.Entry(frame, textvariable=self.pattern)
        entry.pack(fill="x", ipady=5)
        entry.focus_set()

        def run():
            pattern = self.pattern.get().strip()
            if not messagebox.askyesno("Confirm Rename", f'Rename files using "{pattern}"?', parent=dialog):
                return
            try:
                count = batch_rename(folder, pattern)
                dialog.destroy()
                self._write(f"Batch rename complete.\n\nFiles renamed: {count}")
                self.status.set(f"{count} file(s) renamed.")
                self.scan()
            except Exception as exc:
                messagebox.showerror("Rename error", str(exc), parent=dialog)

        ttk.Button(frame, text="Rename Files", command=run).pack(anchor="e", pady=16)

    def undo(self):
        ok, msg = undo_last()
        self._write(msg)
        self.status.set(msg.splitlines()[0])
        if ok:
            self.scan()
        elif msg == "Nothing to undo.":
            messagebox.showinfo("Undo", msg)

    def view_logs(self):
        try:
            text = LOG_FILE.read_text(encoding="utf-8") if LOG_FILE.exists() else "No logs yet."
            self._write(text[-15000:])
            self.status.set("Showing operation log.")
        except OSError as exc:
            messagebox.showerror("Log error", str(exc))
