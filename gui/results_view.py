"""Results view – tabular display of saved results."""

import tkinter as tk
from tkinter import ttk
import database.db_manager as db


class ResultsView(ttk.Frame):
    """Displays results for a selected competition / event / heat."""

    COLUMNS = (
        ("acara", "Acara", 60),
        ("seri", "Seri", 80),
        ("heat", "Heat", 50),
        ("lane", "Lintasan", 70),
        ("athlete", "Nama Atlet", 180),
        ("school", "Sekolah", 180),
        ("time", "Waktu", 90),
        ("rank", "Peringkat", 80),
        ("notes", "Keterangan", 120),
    )

    def __init__(self, parent):
        super().__init__(parent)
        self._comp_id: int | None = None
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=4)
        ttk.Label(top, text="Filter Acara:").pack(side="left")
        self._acara_var = tk.StringVar(value="Semua")
        self._acara_combo = ttk.Combobox(top, textvariable=self._acara_var,
                                         width=20, state="readonly")
        self._acara_combo.pack(side="left", padx=4)
        self._acara_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh())
        ttk.Button(top, text="↺ Muat Ulang", command=self._refresh).pack(side="left", padx=4)

        # Treeview
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=6, pady=4)

        self._tree = ttk.Treeview(frm, show="headings",
                                  columns=[c[0] for c in self.COLUMNS])
        for cid, text, width in self.COLUMNS:
            self._tree.heading(cid, text=text)
            self._tree.column(cid, width=width, anchor="center" if cid in ("acara", "heat", "lane", "rank") else "w")

        vsb = ttk.Scrollbar(frm, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frm.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)

        # Row tag styles
        self._tree.tag_configure("oddrow", background="#F0F0FF")
        self._tree.tag_configure("evenrow", background="#FFFFFF")
        self._tree.tag_configure("top3", background="#FFF9C4")

    def load_competition(self, comp_id: int):
        self._comp_id = comp_id
        rows = db.get_full_results(comp_id)
        acara_nums = sorted({r["acara_number"] for r in rows})
        self._acara_combo["values"] = ["Semua"] + [f"Acara {n}" for n in acara_nums]
        self._acara_var.set("Semua")
        self._populate(rows)

    def _refresh(self):
        if self._comp_id is None:
            return
        rows = db.get_full_results(self._comp_id)
        sel = self._acara_var.get()
        if sel != "Semua":
            try:
                acara_num = int(sel.split()[-1])
                rows = [r for r in rows if r["acara_number"] == acara_num]
            except (ValueError, IndexError):
                pass
        self._populate(rows)

    def _populate(self, rows: list):
        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(rows):
            tag = "top3" if r.get("rank") and r["rank"] <= 3 else (
                "oddrow" if i % 2 else "evenrow"
            )
            self._tree.insert("", "end", tags=(tag,), values=(
                r["acara_number"],
                r.get("seri", ""),
                r["heat_number"],
                r["lane"],
                r["athlete_name"] or "-",
                r["school"] or "-",
                db.ms_to_str(r["time_ms"]) or "-",
                r["rank"] if r["rank"] else "-",
                r["notes"] or "",
            ))
