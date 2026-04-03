"""Main application window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import database.db_manager as db
from esp32.serial_comm import SerialComm
from gui.timer_panel import TimerPanel
from gui.settings_dialog import SettingsDialog
from gui.competition_setup import CompetitionDialog, EventDialog, AthleteEntryDialog
from gui.results_view import ResultsView


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Sistem Timer Renang")
        self.root.geometry("1200x780")
        self.root.minsize(900, 600)

        # State
        self._settings = {"num_lanes": 8, "port": "", "baud": 115200}
        self._active_comp_id: int | None = None
        self._active_event_id: int | None = None
        self._active_heat_id: int | None = None

        # ESP32 comm
        self._esp32 = SerialComm(
            on_lane_stopped=self._esp32_lane_stopped,
            on_status=self._esp32_status,
        )

        db.init_db()
        self._build_ui()

    # ── UI Builder ───────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.configure(bg="#F0F4F8")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook.Tab", font=("Arial", 10, "bold"), padding=[10, 4])
        style.configure("TLabelframe.Label", font=("Arial", 10, "bold"))

        # Header bar
        header = tk.Frame(self.root, bg="#1F4E79", height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🏊  SISTEM TIMER RENANG",
                 font=("Arial", 16, "bold"), fg="white", bg="#1F4E79").pack(
            side="left", padx=14, pady=8)

        # ESP32 status
        self._esp32_status_var = tk.StringVar(value="ESP32: Tidak Terhubung")
        self._esp32_status_lbl = tk.Label(
            header, textvariable=self._esp32_status_var,
            font=("Arial", 9), fg="#FFD700", bg="#1F4E79")
        self._esp32_status_lbl.pack(side="right", padx=14)

        # Connect button
        self._connect_btn = tk.Button(
            header, text="Hubungkan ESP32",
            font=("Arial", 9, "bold"), bg="#28a745", fg="white",
            relief="flat", padx=8, pady=2,
            command=self._toggle_esp32,
        )
        self._connect_btn.pack(side="right", padx=6)

        # Notebook tabs
        self._nb = ttk.Notebook(self.root)
        self._nb.pack(fill="both", expand=True, padx=8, pady=6)

        self._build_tab_timer()
        self._build_tab_setup()
        self._build_tab_results()
        self._build_tab_export()

        # Status bar
        self._status_var = tk.StringVar(value="Siap.")
        tk.Label(self.root, textvariable=self._status_var,
                 font=("Arial", 9), relief="sunken",
                 anchor="w", bg="#E8EDF2").pack(fill="x", side="bottom")

    # ── Tab: Timer ───────────────────────────────────────────────────────────

    def _build_tab_timer(self):
        frm = ttk.Frame(self._nb)
        self._nb.add(frm, text="⏱  Timer")

        # Top selector bar
        sel = ttk.LabelFrame(frm, text="Pilih Heat Aktif")
        sel.pack(fill="x", padx=8, pady=(6, 2))

        pad = {"padx": 6, "pady": 4}
        ttk.Label(sel, text="Kompetisi:").grid(row=0, column=0, **pad, sticky="w")
        self._timer_comp_var = tk.StringVar()
        self._timer_comp_cb = ttk.Combobox(sel, textvariable=self._timer_comp_var,
                                           width=28, state="readonly")
        self._timer_comp_cb.grid(row=0, column=1, **pad)
        self._timer_comp_cb.bind("<<ComboboxSelected>>", self._on_timer_comp_changed)

        ttk.Label(sel, text="Acara:").grid(row=0, column=2, **pad, sticky="w")
        self._timer_event_var = tk.StringVar()
        self._timer_event_cb = ttk.Combobox(sel, textvariable=self._timer_event_var,
                                            width=32, state="readonly")
        self._timer_event_cb.grid(row=0, column=3, **pad)
        self._timer_event_cb.bind("<<ComboboxSelected>>", self._on_timer_event_changed)

        ttk.Label(sel, text="Heat:").grid(row=0, column=4, **pad, sticky="w")
        self._timer_heat_var = tk.StringVar()
        self._timer_heat_cb = ttk.Combobox(sel, textvariable=self._timer_heat_var,
                                           width=10, state="readonly")
        self._timer_heat_cb.grid(row=0, column=5, **pad)
        self._timer_heat_cb.bind("<<ComboboxSelected>>", self._on_timer_heat_changed)

        ttk.Button(sel, text="Input Atlet", command=self._open_athlete_entry).grid(
            row=0, column=6, **pad)
        ttk.Button(sel, text="Simpan Hasil", command=self._save_heat_results).grid(
            row=0, column=7, **pad)

        # Timer panel
        self._timer_panel = TimerPanel(
            frm,
            num_lanes=self._settings["num_lanes"],
            on_lane_stopped=self._on_lane_stopped,
            esp32=self._esp32,
        )
        self._timer_panel.pack(fill="both", expand=True, padx=8, pady=4)

        self._refresh_timer_comps()

    # ── Tab: Setup ───────────────────────────────────────────────────────────

    def _build_tab_setup(self):
        frm = ttk.Frame(self._nb)
        self._nb.add(frm, text="📋  Setup Kompetisi")

        # Competitions list
        left = ttk.LabelFrame(frm, text="Kompetisi")
        left.pack(side="left", fill="y", padx=(8, 4), pady=8)

        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", pady=2)
        ttk.Button(btn_row, text="+ Baru", command=self._add_comp).pack(side="left", padx=2)
        ttk.Button(btn_row, text="✏ Edit", command=self._edit_comp).pack(side="left", padx=2)
        ttk.Button(btn_row, text="🗑 Hapus", command=self._del_comp).pack(side="left", padx=2)

        self._comp_list = tk.Listbox(left, width=30, height=18, font=("Arial", 10))
        self._comp_list.pack(fill="both", expand=True, padx=4, pady=4)
        self._comp_list.bind("<<ListboxSelect>>", self._on_comp_selected)

        # Events list
        mid = ttk.LabelFrame(frm, text="Acara")
        mid.pack(side="left", fill="y", padx=4, pady=8)

        btn_row2 = ttk.Frame(mid)
        btn_row2.pack(fill="x", pady=2)
        ttk.Button(btn_row2, text="+ Baru", command=self._add_event).pack(side="left", padx=2)
        ttk.Button(btn_row2, text="✏ Edit", command=self._edit_event).pack(side="left", padx=2)
        ttk.Button(btn_row2, text="🗑 Hapus", command=self._del_event).pack(side="left", padx=2)

        self._event_list = tk.Listbox(mid, width=40, height=18, font=("Arial", 10))
        self._event_list.pack(fill="both", expand=True, padx=4, pady=4)
        self._event_list.bind("<<ListboxSelect>>", self._on_event_selected)

        # Heats list
        right = ttk.LabelFrame(frm, text="Heat")
        right.pack(side="left", fill="y", padx=(4, 8), pady=8)

        btn_row3 = ttk.Frame(right)
        btn_row3.pack(fill="x", pady=2)
        ttk.Button(btn_row3, text="+ Heat", command=self._add_heat).pack(side="left", padx=2)
        ttk.Button(btn_row3, text="🗑 Hapus", command=self._del_heat).pack(side="left", padx=2)
        ttk.Button(btn_row3, text="Input Atlet", command=self._open_athlete_entry_setup).pack(side="left", padx=2)

        self._heat_list = tk.Listbox(right, width=20, height=18, font=("Arial", 10))
        self._heat_list.pack(fill="both", expand=True, padx=4, pady=4)

        self._setup_comps: list = []
        self._setup_events: list = []
        self._setup_heats: list = []
        self._refresh_comp_list()

    # ── Tab: Results ─────────────────────────────────────────────────────────

    def _build_tab_results(self):
        frm = ttk.Frame(self._nb)
        self._nb.add(frm, text="🏆  Hasil Lomba")

        top = ttk.Frame(frm)
        top.pack(fill="x", padx=8, pady=4)
        ttk.Label(top, text="Kompetisi:").pack(side="left")
        self._res_comp_var = tk.StringVar()
        self._res_comp_cb = ttk.Combobox(top, textvariable=self._res_comp_var,
                                         width=32, state="readonly")
        self._res_comp_cb.pack(side="left", padx=4)
        self._res_comp_cb.bind("<<ComboboxSelected>>", self._on_res_comp_changed)
        ttk.Button(top, text="Tampilkan", command=self._show_results).pack(side="left", padx=4)

        self._results_view = ResultsView(frm)
        self._results_view.pack(fill="both", expand=True)

        self._refresh_res_comps()

    # ── Tab: Export ──────────────────────────────────────────────────────────

    def _build_tab_export(self):
        frm = ttk.Frame(self._nb)
        self._nb.add(frm, text="💾  Ekspor")

        inner = ttk.LabelFrame(frm, text="Ekspor Hasil Lomba")
        inner.pack(padx=20, pady=20, fill="x")

        ttk.Label(inner, text="Pilih Kompetisi:").grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self._exp_comp_var = tk.StringVar()
        self._exp_comp_cb = ttk.Combobox(inner, textvariable=self._exp_comp_var,
                                         width=36, state="readonly")
        self._exp_comp_cb.grid(row=0, column=1, padx=8, pady=6)

        ttk.Button(inner, text="📊  Ekspor ke Excel (.xlsx)",
                   command=self._export_excel).grid(row=1, column=0, columnspan=2,
                                                    padx=8, pady=6, sticky="w")
        ttk.Button(inner, text="📄  Ekspor ke PDF (.pdf)",
                   command=self._export_pdf).grid(row=2, column=0, columnspan=2,
                                                  padx=8, pady=6, sticky="w")

        # Settings button
        ttk.Separator(inner).grid(row=3, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Button(inner, text="⚙  Pengaturan (Lintasan & ESP32)",
                   command=self._open_settings).grid(row=4, column=0, columnspan=2,
                                                     padx=8, pady=4, sticky="w")

        self._refresh_exp_comps()

    # ── ESP32 ────────────────────────────────────────────────────────────────

    def _toggle_esp32(self):
        if self._esp32.is_connected:
            self._esp32.disconnect()
            self._connect_btn.config(text="Hubungkan ESP32", bg="#28a745")
        else:
            port = self._settings.get("port", "")
            baud = self._settings.get("baud", 115200)
            if not port:
                messagebox.showinfo("ESP32", "Silakan pilih port ESP32 di Pengaturan.", parent=self.root)
                return
            ok = self._esp32.connect(port, baud)
            if ok:
                self._connect_btn.config(text="Putuskan ESP32", bg="#dc3545")

    def _esp32_lane_stopped(self, lane: int, time_ms: int):
        """Called from background thread."""
        self._timer_panel.esp32_lane_stopped(lane, time_ms)

    def _esp32_status(self, msg: str):
        self.root.after(0, lambda: self._esp32_status_var.set(f"ESP32: {msg}"))
        self.root.after(0, lambda: self._set_status(msg))

    # ── Lane stop callback ───────────────────────────────────────────────────

    def _on_lane_stopped(self, lane: int, time_ms: int):
        if self._active_heat_id is None:
            return
        db.update_result_time(self._active_heat_id, lane, time_ms)
        db.update_ranks(self._active_heat_id)
        self._set_status(f"Lane {lane} selesai: {db.ms_to_str(time_ms)}")

    # ── Timer tab helpers ────────────────────────────────────────────────────

    def _refresh_timer_comps(self):
        comps = db.get_competitions()
        self._timer_comps = comps
        self._timer_comp_cb["values"] = [f"{c['title']} {c['year']}" for c in comps]
        if comps:
            self._timer_comp_cb.current(0)
            self._on_timer_comp_changed()

    def _on_timer_comp_changed(self, _event=None):
        idx = self._timer_comp_cb.current()
        if idx < 0:
            return
        comp = self._timer_comps[idx]
        self._active_comp_id = comp["id"]
        self._timer_panel.set_num_lanes(comp.get("num_lanes", 8))
        events = db.get_events(comp["id"])
        self._timer_events = events
        self._timer_event_cb["values"] = [
            f"Acara {e['acara_number']} – {e['distance_m']}m {e['stroke']} {e['gender']}"
            for e in events
        ]
        self._timer_event_cb.set("")
        self._timer_heat_cb.set("")
        self._active_event_id = None
        self._active_heat_id = None

    def _on_timer_event_changed(self, _event=None):
        idx = self._timer_event_cb.current()
        if idx < 0:
            return
        event = self._timer_events[idx]
        self._active_event_id = event["id"]
        heats = db.get_heats(event["id"])
        self._timer_heats = heats
        self._timer_heat_cb["values"] = [f"Heat {h['heat_number']}" for h in heats]
        self._timer_heat_cb.set("")
        self._active_heat_id = None

    def _on_timer_heat_changed(self, _event=None):
        idx = self._timer_heat_cb.current()
        if idx < 0:
            return
        heat = self._timer_heats[idx]
        self._active_heat_id = heat["id"]
        # Load athlete data into timer panel
        results = db.get_results(heat["id"])
        athletes = {r["lane"]: r for r in results}
        self._timer_panel.set_athletes(athletes)
        self._timer_panel._reset_all()

    def _open_athlete_entry(self):
        if self._active_heat_id is None:
            messagebox.showinfo("Info", "Pilih heat terlebih dahulu.", parent=self.root)
            return
        comp = db.get_competition(self._active_comp_id)
        n = comp.get("num_lanes", 8) if comp else 8
        AthleteEntryDialog(self.root, self._active_heat_id, n,
                           on_save=self._on_timer_heat_changed)

    def _save_heat_results(self):
        if self._active_heat_id is None:
            messagebox.showinfo("Info", "Pilih heat terlebih dahulu.", parent=self.root)
            return
        times = self._timer_panel.get_times()
        for lane, t_ms in times.items():
            if t_ms is not None:
                db.update_result_time(self._active_heat_id, lane, t_ms)
        db.update_ranks(self._active_heat_id)
        messagebox.showinfo("Simpan", "Hasil berhasil disimpan.", parent=self.root)
        self._set_status("Hasil disimpan.")

    # ── Setup tab helpers ────────────────────────────────────────────────────

    def _refresh_comp_list(self):
        self._setup_comps = db.get_competitions()
        self._comp_list.delete(0, "end")
        for c in self._setup_comps:
            self._comp_list.insert("end", f"{c['title']} {c['year']}")
        self._refresh_timer_comps()
        self._refresh_res_comps()
        self._refresh_exp_comps()

    def _on_comp_selected(self, _=None):
        idx = self._comp_list.curselection()
        if not idx:
            return
        comp = self._setup_comps[idx[0]]
        events = db.get_events(comp["id"])
        self._setup_events = events
        self._event_list.delete(0, "end")
        for e in events:
            self._event_list.insert(
                "end",
                f"Acara {e['acara_number']} – {e['seri']} – "
                f"{e['distance_m']}m {e['stroke']} {e['gender']}"
            )
        self._heat_list.delete(0, "end")
        self._setup_heats = []

    def _on_event_selected(self, _=None):
        idx = self._event_list.curselection()
        if not idx:
            return
        event = self._setup_events[idx[0]]
        heats = db.get_heats(event["id"])
        self._setup_heats = heats
        self._heat_list.delete(0, "end")
        for h in heats:
            self._heat_list.insert("end", f"Heat {h['heat_number']}")

    def _selected_comp(self):
        idx = self._comp_list.curselection()
        if not idx:
            return None
        return self._setup_comps[idx[0]]

    def _selected_event(self):
        idx = self._event_list.curselection()
        if not idx:
            return None
        return self._setup_events[idx[0]]

    def _selected_heat(self):
        idx = self._heat_list.curselection()
        if not idx:
            return None
        return self._setup_heats[idx[0]]

    def _add_comp(self):
        CompetitionDialog(self.root, on_save=self._refresh_comp_list)

    def _edit_comp(self):
        comp = self._selected_comp()
        if not comp:
            messagebox.showinfo("Info", "Pilih kompetisi.", parent=self.root)
            return
        CompetitionDialog(self.root, comp=comp, on_save=self._refresh_comp_list)

    def _del_comp(self):
        comp = self._selected_comp()
        if not comp:
            return
        if messagebox.askyesno("Hapus", f"Hapus {comp['title']}?", parent=self.root):
            db.delete_competition(comp["id"])
            self._refresh_comp_list()

    def _add_event(self):
        comp = self._selected_comp()
        if not comp:
            messagebox.showinfo("Info", "Pilih kompetisi.", parent=self.root)
            return
        EventDialog(self.root, comp["id"],
                    on_save=lambda: self._on_comp_selected())

    def _edit_event(self):
        event = self._selected_event()
        if not event:
            messagebox.showinfo("Info", "Pilih acara.", parent=self.root)
            return
        comp = self._selected_comp()
        EventDialog(self.root, comp["id"], event=event,
                    on_save=lambda: self._on_comp_selected())

    def _del_event(self):
        event = self._selected_event()
        if not event:
            return
        if messagebox.askyesno("Hapus", f"Hapus Acara {event['acara_number']}?", parent=self.root):
            db.delete_event(event["id"])
            self._on_comp_selected()

    def _add_heat(self):
        event = self._selected_event()
        if not event:
            messagebox.showinfo("Info", "Pilih acara.", parent=self.root)
            return
        existing = db.get_heats(event["id"])
        new_num = max((h["heat_number"] for h in existing), default=0) + 1
        db.add_heat(event["id"], new_num)
        self._on_event_selected()

    def _del_heat(self):
        heat = self._selected_heat()
        if not heat:
            return
        if messagebox.askyesno("Hapus", f"Hapus Heat {heat['heat_number']}?", parent=self.root):
            db.delete_heat(heat["id"])
            self._on_event_selected()

    def _open_athlete_entry_setup(self):
        heat = self._selected_heat()
        comp = self._selected_comp()
        if not heat or not comp:
            messagebox.showinfo("Info", "Pilih heat.", parent=self.root)
            return
        AthleteEntryDialog(self.root, heat["id"], comp.get("num_lanes", 8),
                           on_save=lambda: self._on_event_selected())

    # ── Results tab helpers ───────────────────────────────────────────────────

    def _refresh_res_comps(self):
        if not hasattr(self, "_res_comp_cb"):
            return
        comps = db.get_competitions()
        self._res_comps = comps
        self._res_comp_cb["values"] = [f"{c['title']} {c['year']}" for c in comps]
        if comps:
            self._res_comp_cb.current(0)

    def _on_res_comp_changed(self, _=None):
        pass

    def _show_results(self):
        idx = self._res_comp_cb.current()
        if idx < 0:
            return
        comp = self._res_comps[idx]
        self._results_view.load_competition(comp["id"])

    # ── Export helpers ────────────────────────────────────────────────────────

    def _refresh_exp_comps(self):
        if not hasattr(self, "_exp_comp_cb"):
            return
        comps = db.get_competitions()
        self._exp_comps = comps
        self._exp_comp_cb["values"] = [f"{c['title']} {c['year']}" for c in comps]
        if comps:
            self._exp_comp_cb.current(0)

    def _selected_exp_comp(self):
        idx = self._exp_comp_cb.current()
        if idx < 0:
            return None
        return self._exp_comps[idx]

    def _export_excel(self):
        comp = self._selected_exp_comp()
        if not comp:
            messagebox.showinfo("Info", "Pilih kompetisi.", parent=self.root)
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"hasil_{comp['title']}_{comp['year']}.xlsx",
            parent=self.root,
        )
        if not path:
            return
        try:
            from export.excel_export import export_competition_excel
            export_competition_excel(comp["id"], path)
            messagebox.showinfo("Ekspor", f"File Excel disimpan:\n{path}", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self.root)

    def _export_pdf(self):
        comp = self._selected_exp_comp()
        if not comp:
            messagebox.showinfo("Info", "Pilih kompetisi.", parent=self.root)
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"hasil_{comp['title']}_{comp['year']}.pdf",
            parent=self.root,
        )
        if not path:
            return
        try:
            from export.pdf_export import export_competition_pdf
            export_competition_pdf(comp["id"], path)
            messagebox.showinfo("Ekspor", f"File PDF disimpan:\n{path}", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self.root)

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        def on_save(cfg):
            self._settings.update(cfg)
            self._timer_panel.set_num_lanes(cfg["num_lanes"])
            self._set_status("Pengaturan disimpan.")

        SettingsDialog(self.root, self._settings, on_save)

    # ── Utility ──────────────────────────────────────────────────────────────

    def _set_status(self, msg: str):
        self._status_var.set(msg)
