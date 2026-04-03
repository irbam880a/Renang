"""Settings dialog – ESP32 serial port + lane count."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from esp32.serial_comm import list_serial_ports
from gui import theme


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, current: dict, on_save):
        super().__init__(parent)
        self.title("Pengaturan")
        self.configure(bg=theme.BG_MAIN)
        self.resizable(False, False)
        self.grab_set()
        self._on_save = on_save

        pad = {"padx": 10, "pady": 6}

        # Header
        hdr = tk.Frame(self, bg=theme.PRIMARY, height=40)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        tk.Label(hdr, text="⚙  Pengaturan",
                 font=theme.FONT_SUBTITLE, fg=theme.TEXT_ON_PRIMARY,
                 bg=theme.PRIMARY).pack(side="left", padx=12)

        # ── Lane count ─────────────────────────────────────────────────────
        frm = ttk.LabelFrame(self, text="  Lintasan  ")
        frm.grid(row=1, column=0, sticky="ew", padx=16, pady=(12, 4))

        ttk.Label(frm, text="Jumlah Lintasan (1–16):",
                  font=theme.FONT_SMALL_BOLD).grid(
            row=0, column=0, **pad, sticky="w")
        self._lanes_var = tk.IntVar(value=current.get("num_lanes", 8))
        sb = ttk.Spinbox(frm, from_=1, to=16, textvariable=self._lanes_var, width=5)
        sb.grid(row=0, column=1, **pad)

        # ── ESP32 port ─────────────────────────────────────────────────────
        frm2 = ttk.LabelFrame(self, text="  ESP32 Serial Port  ")
        frm2.grid(row=2, column=0, sticky="ew", padx=16, pady=4)

        ttk.Label(frm2, text="Port:", font=theme.FONT_SMALL_BOLD).grid(
            row=0, column=0, **pad, sticky="w")
        self._port_var = tk.StringVar(value=current.get("port", ""))
        ports = list_serial_ports()
        self._port_combo = ttk.Combobox(frm2, textvariable=self._port_var,
                                        values=ports, width=18, state="normal")
        self._port_combo.grid(row=0, column=1, **pad)
        ttk.Button(frm2, text="↺ Refresh",
                   command=self._refresh_ports).grid(row=0, column=2, **pad)

        ttk.Label(frm2, text="Baud Rate:", font=theme.FONT_SMALL_BOLD).grid(
            row=1, column=0, **pad, sticky="w")
        self._baud_var = tk.StringVar(value=str(current.get("baud", 115200)))
        baud_combo = ttk.Combobox(frm2, textvariable=self._baud_var,
                                  values=["9600", "19200", "38400", "57600", "115200"],
                                  width=18, state="readonly")
        baud_combo.grid(row=1, column=1, **pad)

        # ── Buttons ────────────────────────────────────────────────────────
        btn_frm = ttk.Frame(self)
        btn_frm.grid(row=3, column=0, pady=(8, 16))
        ttk.Button(btn_frm, text="💾  Simpan", style="Success.TButton",
                   command=self._save).pack(side="left", padx=6)
        ttk.Button(btn_frm, text="✕  Batal", command=self.destroy).pack(
            side="left", padx=6)

        self.columnconfigure(0, weight=1)
        self._center()

    def _refresh_ports(self):
        ports = list_serial_ports()
        self._port_combo["values"] = ports

    def _save(self):
        try:
            lanes = int(self._lanes_var.get())
            lanes = max(1, min(16, lanes))
        except ValueError:
            lanes = 8
        self._on_save({
            "num_lanes": lanes,
            "port": self._port_var.get().strip(),
            "baud": int(self._baud_var.get()),
        })
        self.destroy()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        self.geometry(f"+{x}+{y}")
