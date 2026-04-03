"""Competition / Event / Heat setup dialogs."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import database.db_manager as db
from gui import theme

STROKES = ["GAYA BEBAS", "GAYA DADA", "GAYA PUNGGUNG", "GAYA KUPU-KUPU", "GAYA GANTI"]
GENDERS = ["PUTRA", "PUTRI"]
DISTANCES = ["50", "100", "200", "400", "800", "1500"]


def _style_dialog(dialog: tk.Toplevel):
    """Apply consistent professional styling to a dialog window."""
    dialog.configure(bg=theme.BG_MAIN)
    dialog.resizable(False, False)
    dialog.grab_set()


class CompetitionDialog(tk.Toplevel):
    """Add or edit a competition."""

    def __init__(self, parent, comp: dict = None, on_save=None):
        super().__init__(parent)
        self.title("Kompetisi" if comp is None else "Edit Kompetisi")
        _style_dialog(self)
        self._on_save = on_save
        self._comp = comp

        pad = {"padx": 10, "pady": 6}

        # Header
        hdr = tk.Frame(self, bg=theme.PRIMARY, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📋  " + self.title(),
                 font=theme.FONT_SUBTITLE, fg=theme.TEXT_ON_PRIMARY,
                 bg=theme.PRIMARY).pack(side="left", padx=12)

        fields = ttk.Frame(self)
        fields.pack(padx=16, pady=12)

        def row(label, widget_fn, r):
            ttk.Label(fields, text=label, font=theme.FONT_SMALL_BOLD).grid(
                row=r, column=0, sticky="w", **pad)
            w = widget_fn(fields)
            w.grid(row=r, column=1, sticky="ew", **pad)
            return w

        self._title_var = tk.StringVar(value=comp.get("title", "") if comp else "KEJURKAB")
        self._year_var = tk.StringVar(value=comp.get("year", "2024") if comp else "2024")
        self._date_var = tk.StringVar(value=comp.get("date_text", "") if comp else "")
        self._venue_var = tk.StringVar(value=comp.get("venue", "") if comp else "")
        self._lanes_var = tk.IntVar(value=comp.get("num_lanes", 8) if comp else 8)

        row("Nama Kompetisi:", lambda p: ttk.Entry(p, textvariable=self._title_var, width=30), 0)
        row("Tahun:", lambda p: ttk.Entry(p, textvariable=self._year_var, width=10), 1)
        row("Tanggal:", lambda p: ttk.Entry(p, textvariable=self._date_var, width=30), 2)
        row("Venue:", lambda p: ttk.Entry(p, textvariable=self._venue_var, width=30), 3)

        ttk.Label(fields, text="Jumlah Lintasan:",
                  font=theme.FONT_SMALL_BOLD).grid(
            row=4, column=0, sticky="w", **pad)
        ttk.Spinbox(fields, from_=1, to=16, textvariable=self._lanes_var, width=5).grid(
            row=4, column=1, sticky="w", **pad
        )

        bf = ttk.Frame(self)
        bf.pack(pady=(4, 12))
        ttk.Button(bf, text="💾  Simpan", style="Success.TButton",
                   command=self._save).pack(side="left", padx=6)
        ttk.Button(bf, text="✕  Batal", command=self.destroy).pack(
            side="left", padx=6)
        self._center()

    def _save(self):
        title = self._title_var.get().strip()
        year = self._year_var.get().strip()
        date_text = self._date_var.get().strip()
        if not title or not year:
            messagebox.showwarning("Input", "Nama dan tahun wajib diisi.", parent=self)
            return
        if self._comp:
            db.update_competition(
                self._comp["id"], title, year, date_text,
                self._venue_var.get().strip(), self._lanes_var.get()
            )
        else:
            db.add_competition(
                title, year, date_text,
                self._venue_var.get().strip(), self._lanes_var.get()
            )
        if self._on_save:
            self._on_save()
        self.destroy()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        self.geometry(f"+{x}+{y}")


class EventDialog(tk.Toplevel):
    """Add or edit an event (acara)."""

    def __init__(self, parent, competition_id: int, event: dict = None, on_save=None):
        super().__init__(parent)
        self.title("Tambah Acara" if event is None else "Edit Acara")
        _style_dialog(self)
        self._on_save = on_save
        self._comp_id = competition_id
        self._event = event

        pad = {"padx": 10, "pady": 6}

        # Header
        hdr = tk.Frame(self, bg=theme.PRIMARY, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🏊  " + self.title(),
                 font=theme.FONT_SUBTITLE, fg=theme.TEXT_ON_PRIMARY,
                 bg=theme.PRIMARY).pack(side="left", padx=12)

        f = ttk.Frame(self)
        f.pack(padx=16, pady=12)

        self._acara_var = tk.IntVar(value=event.get("acara_number", 1) if event else 1)
        self._seri_var = tk.StringVar(value=event.get("seri", "") if event else "")
        self._dist_var = tk.StringVar(value=str(event.get("distance_m", 50)) if event else "50")
        self._stroke_var = tk.StringVar(value=event.get("stroke", STROKES[0]) if event else STROKES[0])
        self._gender_var = tk.StringVar(value=event.get("gender", "PUTRA") if event else "PUTRA")
        self._desc_var = tk.StringVar(value=event.get("description", "") if event else "")

        ttk.Label(f, text="No. Acara:", font=theme.FONT_SMALL_BOLD).grid(
            row=0, column=0, sticky="w", **pad)
        ttk.Spinbox(f, from_=1, to=999, textvariable=self._acara_var, width=6).grid(
            row=0, column=1, sticky="w", **pad)

        ttk.Label(f, text="Seri (Tahun Lahir):", font=theme.FONT_SMALL_BOLD).grid(
            row=1, column=0, sticky="w", **pad)
        ttk.Entry(f, textvariable=self._seri_var, width=15).grid(
            row=1, column=1, sticky="w", **pad)

        ttk.Label(f, text="Jarak (meter):", font=theme.FONT_SMALL_BOLD).grid(
            row=2, column=0, sticky="w", **pad)
        ttk.Combobox(f, textvariable=self._dist_var, values=DISTANCES, width=8,
                     state="readonly").grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(f, text="Gaya:", font=theme.FONT_SMALL_BOLD).grid(
            row=3, column=0, sticky="w", **pad)
        ttk.Combobox(f, textvariable=self._stroke_var, values=STROKES, width=18,
                     state="readonly").grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(f, text="Kategori:", font=theme.FONT_SMALL_BOLD).grid(
            row=4, column=0, sticky="w", **pad)
        ttk.Combobox(f, textvariable=self._gender_var, values=GENDERS, width=10,
                     state="readonly").grid(row=4, column=1, sticky="w", **pad)

        ttk.Label(f, text="Deskripsi tambahan:", font=theme.FONT_SMALL_BOLD).grid(
            row=5, column=0, sticky="w", **pad)
        ttk.Entry(f, textvariable=self._desc_var, width=28).grid(
            row=5, column=1, sticky="w", **pad)

        bf = ttk.Frame(self)
        bf.pack(pady=(4, 12))
        ttk.Button(bf, text="💾  Simpan", style="Success.TButton",
                   command=self._save).pack(side="left", padx=6)
        ttk.Button(bf, text="✕  Batal", command=self.destroy).pack(
            side="left", padx=6)
        self._center()

    def _save(self):
        try:
            dist = int(self._dist_var.get())
        except ValueError:
            dist = 50
        if self._event:
            db.update_event(
                self._event["id"], self._acara_var.get(), self._seri_var.get().strip(),
                dist, self._stroke_var.get(), self._gender_var.get(), self._desc_var.get().strip()
            )
        else:
            db.add_event(
                self._comp_id, self._acara_var.get(), self._seri_var.get().strip(),
                dist, self._stroke_var.get(), self._gender_var.get(), self._desc_var.get().strip()
            )
        if self._on_save:
            self._on_save()
        self.destroy()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        self.geometry(f"+{x}+{y}")


class AthleteEntryDialog(tk.Toplevel):
    """Enter/edit athlete data for all lanes in a heat."""

    def __init__(self, parent, heat_id: int, num_lanes: int, on_save=None):
        super().__init__(parent)
        self.title(f"Input Atlet – Heat {heat_id}")
        self.configure(bg=theme.BG_MAIN)
        self.resizable(True, True)
        self.grab_set()
        self._heat_id = heat_id
        self._num_lanes = num_lanes
        self._on_save = on_save

        # Load existing results
        existing = {r["lane"]: r for r in db.get_results(heat_id)}

        # Header
        hdr = tk.Frame(self, bg=theme.PRIMARY, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f"👤  Input Atlet – Heat {heat_id}",
                 font=theme.FONT_SUBTITLE, fg=theme.TEXT_ON_PRIMARY,
                 bg=theme.PRIMARY).pack(side="left", padx=12)

        # Scrollable frame
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=12, pady=10)

        canvas = tk.Canvas(container, height=400, bg=theme.BG_CARD,
                           highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self._scroll_frame = tk.Frame(canvas, bg=theme.BG_CARD)
        self._scroll_frame.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        headers = ["Lane", "Nama Atlet", "Sekolah", "Keterangan"]
        for col, h in enumerate(headers):
            lbl = tk.Label(self._scroll_frame, text=h,
                           font=theme.FONT_SMALL_BOLD,
                           fg=theme.PRIMARY, bg=theme.TABLE_HEADER_BG,
                           padx=8, pady=4)
            lbl.grid(row=0, column=col, padx=1, pady=(0, 2), sticky="nsew")

        self._entries: dict[int, dict] = {}
        for lane in range(1, num_lanes + 1):
            r = existing.get(lane, {})
            bg = theme.TABLE_ODD if lane % 2 else theme.TABLE_EVEN
            tk.Label(self._scroll_frame, text=str(lane),
                     font=theme.FONT_BODY_BOLD, bg=bg,
                     fg=theme.PRIMARY, width=4).grid(
                row=lane, column=0, padx=1, pady=1)
            name_var = tk.StringVar(value=r.get("athlete_name", ""))
            school_var = tk.StringVar(value=r.get("school", ""))
            notes_var = tk.StringVar(value=r.get("notes", ""))
            ttk.Entry(self._scroll_frame, textvariable=name_var, width=22).grid(
                row=lane, column=1, padx=2, pady=1)
            ttk.Entry(self._scroll_frame, textvariable=school_var, width=22).grid(
                row=lane, column=2, padx=2, pady=1)
            ttk.Entry(self._scroll_frame, textvariable=notes_var, width=16).grid(
                row=lane, column=3, padx=2, pady=1)
            self._entries[lane] = {
                "name": name_var, "school": school_var, "notes": notes_var,
                "time_ms": r.get("time_ms"),
            }

        bf = ttk.Frame(self)
        bf.pack(pady=(4, 12))
        ttk.Button(bf, text="💾  Simpan", style="Success.TButton",
                   command=self._save).pack(side="left", padx=6)
        ttk.Button(bf, text="✕  Batal", command=self.destroy).pack(
            side="left", padx=6)
        self._center()

    def _save(self):
        for lane, d in self._entries.items():
            db.upsert_result(
                self._heat_id, lane,
                d["name"].get().strip(),
                d["school"].get().strip(),
                d["time_ms"],
                d["notes"].get().strip(),
            )
        if self._on_save:
            self._on_save()
        self.destroy()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        self.geometry(f"+{x}+{y}")
