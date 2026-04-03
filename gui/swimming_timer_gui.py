#!/usr/bin/env python3
"""
swimming_timer_gui.py
=====================
Standalone Python/tkinter GUI for the 16-lane swimming timer.

Features
--------
- ⏱  Timer tab  : live stopwatch, 16-lane grid with SELESAI buttons, rank badges
- ⚙  Setup tab  : race metadata (nama lomba, acara, seri, nomor, gaya, gender…)
                   + per-lane athlete entry table (nama, klub, limid waktu)
- 🖨  Laporan tab: print Form Catatan Waktu (16 forms) and Buku Acara via browser
- 📋  Riwayat tab: full history of all races with print support

Database
--------
Default path: <script-dir>/swimming_timer.db
Set the DB_PATH environment variable to point at the Node.js backend database
(../backend/swimming_timer.db) to share data with the web server.

Requirements
------------
- Python 3.8+ (stdlib only: tkinter, sqlite3, webbrowser, tempfile, html, time, os)
- No external packages needed.

Usage
-----
    python3 swimming_timer_gui.py
    DB_PATH=../backend/swimming_timer.db python3 swimming_timer_gui.py
"""

import html as html_mod
import os
import sqlite3
import tempfile
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

# ── Database path ─────────────────────────────────────────────────────────────
DEFAULT_DB = Path(__file__).parent / "swimming_timer.db"
DB_PATH = os.environ.get("DB_PATH", str(DEFAULT_DB))

# ── Colours (mirror the web dark theme) ──────────────────────────────────────
C_BG     = "#0d1b2a"
C_CARD   = "#13293d"
C_BORDER = "#1b4965"
C_TEXT   = "#e0f0ff"
C_MUTED  = "#7aafc8"
C_CYAN   = "#00acc1"
C_GREEN  = "#2e7d32"
C_BLUE   = "#1565c0"
C_RED    = "#c62828"
C_TEAL   = "#00695c"
C_GOLD   = "#ffd700"
C_SILVER = "#c0c0c0"
C_BRONZE = "#cd7f32"


# ══════════════════════════════════════════════════════════════════════════════
# Database layer
# ══════════════════════════════════════════════════════════════════════════════

class Database:
    """Thin SQLite wrapper; schema is compatible with the Node.js backend."""

    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._conn: sqlite3.Connection | None = None
        self._init()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def _init(self):
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS races (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                heat          INTEGER NOT NULL DEFAULT 1,
                started_at    INTEGER NOT NULL,
                reset_at      INTEGER,
                active        INTEGER NOT NULL DEFAULT 1,
                acara         TEXT,
                seri          TEXT,
                nomor         TEXT,
                gaya          TEXT,
                gender        TEXT DEFAULT 'Putra',
                kategori      TEXT,
                nama_lomba    TEXT,
                tanggal_lomba TEXT
            );
            CREATE TABLE IF NOT EXISTS lane_times (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                race_id     INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
                lane        INTEGER NOT NULL CHECK(lane BETWEEN 1 AND 16),
                elapsed_ms  INTEGER NOT NULL,
                recorded_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lane_entries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                race_id     INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
                lane        INTEGER NOT NULL CHECK(lane BETWEEN 1 AND 16),
                nama_atlet  TEXT,
                klub        TEXT,
                limid_waktu TEXT,
                UNIQUE(race_id, lane)
            );
            CREATE INDEX IF NOT EXISTS idx_lane_times_race_id
                ON lane_times(race_id);
            CREATE INDEX IF NOT EXISTS idx_lane_entries_race_id
                ON lane_entries(race_id);
        """)
        # Migrate older DB files that may lack the new columns
        existing = {row[1] for row in conn.execute("PRAGMA table_info(races)")}
        for col, defn in [
            ("acara",         "TEXT"),
            ("seri",          "TEXT"),
            ("nomor",         "TEXT"),
            ("gaya",          "TEXT"),
            ("gender",        "TEXT DEFAULT 'Putra'"),
            ("kategori",      "TEXT"),
            ("nama_lomba",    "TEXT"),
            ("tanggal_lomba", "TEXT"),
        ]:
            if col not in existing:
                conn.execute(f"ALTER TABLE races ADD COLUMN {col} {defn}")
        conn.commit()

    # ── Public API ────────────────────────────────────────────────────────────

    def start_race(self, heat: int, meta: dict | None = None) -> dict:
        meta = meta or {}
        conn = self._connect()
        now  = int(time.time() * 1000)
        conn.execute("UPDATE races SET active = 0 WHERE active = 1")
        cur = conn.execute(
            """INSERT INTO races
               (heat, started_at, active,
                acara, seri, nomor, gaya, gender, kategori, nama_lomba, tanggal_lomba)
               VALUES (?,?,1, ?,?,?,?,?,?,?,?)""",
            (heat, now,
             meta.get("acara"),    meta.get("seri"),          meta.get("nomor"),
             meta.get("gaya"),     meta.get("gender"),        meta.get("kategori"),
             meta.get("nama_lomba"), meta.get("tanggal_lomba"))
        )
        conn.commit()
        return self._row_to_dict(
            conn.execute("SELECT * FROM races WHERE id=?", (cur.lastrowid,)).fetchone()
        )

    def get_active_race(self) -> dict | None:
        row = self._connect().execute(
            "SELECT * FROM races WHERE active=1"
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def update_race_meta(self, race_id: int, meta: dict):
        conn = self._connect()
        conn.execute(
            """UPDATE races
               SET acara=?,seri=?,nomor=?,gaya=?,gender=?,
                   kategori=?,nama_lomba=?,tanggal_lomba=?
               WHERE id=?""",
            (meta.get("acara"),    meta.get("seri"),          meta.get("nomor"),
             meta.get("gaya"),     meta.get("gender"),        meta.get("kategori"),
             meta.get("nama_lomba"), meta.get("tanggal_lomba"),
             race_id)
        )
        conn.commit()

    def record_finish(self, lane: int, elapsed_ms: int) -> dict | None:
        race = self.get_active_race()
        if not race:
            return None
        conn = self._connect()
        now  = int(time.time() * 1000)
        cur  = conn.execute(
            "INSERT INTO lane_times (race_id, lane, elapsed_ms, recorded_at) VALUES (?,?,?,?)",
            (race["id"], lane, elapsed_ms, now)
        )
        conn.commit()
        return self._row_to_dict(
            conn.execute("SELECT * FROM lane_times WHERE id=?", (cur.lastrowid,)).fetchone()
        )

    def reset_race(self) -> dict | None:
        race = self.get_active_race()
        if not race:
            return None
        conn = self._connect()
        now  = int(time.time() * 1000)
        conn.execute("DELETE FROM lane_times WHERE race_id=?", (race["id"],))
        conn.execute("UPDATE races SET active=0, reset_at=? WHERE id=?", (now, race["id"]))
        conn.commit()
        return race

    def get_lane_times(self, race_id: int) -> list[dict]:
        rows = self._connect().execute(
            "SELECT lane, elapsed_ms FROM lane_times WHERE race_id=? ORDER BY elapsed_ms ASC",
            (race_id,)
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def set_lane_entry(self, race_id: int, lane: int,
                       nama_atlet: str | None, klub: str | None,
                       limid_waktu: str | None):
        self._connect().execute(
            """INSERT INTO lane_entries (race_id, lane, nama_atlet, klub, limid_waktu)
               VALUES (?,?,?,?,?)
               ON CONFLICT(race_id, lane) DO UPDATE SET
                   nama_atlet  = excluded.nama_atlet,
                   klub        = excluded.klub,
                   limid_waktu = excluded.limid_waktu""",
            (race_id, lane, nama_atlet or None, klub or None, limid_waktu or None)
        )
        self._connect().commit()

    def get_lane_entries(self, race_id: int) -> dict[int, dict]:
        rows = self._connect().execute(
            "SELECT lane, nama_atlet, klub, limid_waktu FROM lane_entries WHERE race_id=? ORDER BY lane",
            (race_id,)
        ).fetchall()
        return {r["lane"]: self._row_to_dict(r) for r in rows}

    def get_all_races(self) -> list[dict]:
        conn  = self._connect()
        races = [self._row_to_dict(r) for r in
                 conn.execute("SELECT * FROM races ORDER BY id DESC").fetchall()]
        for race in races:
            race["lanes"]   = [self._row_to_dict(r) for r in
                                conn.execute(
                                    "SELECT lane, elapsed_ms FROM lane_times WHERE race_id=? ORDER BY elapsed_ms",
                                    (race["id"],)).fetchall()]
            race["entries"] = self.get_lane_entries(race["id"])
        return races

    @staticmethod
    def _row_to_dict(row) -> dict:
        return dict(row) if row else {}


# ══════════════════════════════════════════════════════════════════════════════
# Formatting helpers
# ══════════════════════════════════════════════════════════════════════════════

def fmt_ms(ms: int | None) -> str:
    """Format milliseconds as MM:SS.mmm  (e.g. 01:23.456)"""
    if ms is None:
        return "—"
    m   = ms // 60000
    s   = (ms % 60000) // 1000
    ms3 = ms % 1000
    return f"{m:02d}:{s:02d}.{ms3:03d}"


# ══════════════════════════════════════════════════════════════════════════════
# HTML report generators
# ══════════════════════════════════════════════════════════════════════════════

def _esc(s) -> str:
    return html_mod.escape(str(s or ""))


def generate_catatan_waktu_html(race: dict, time_map: dict[int, int],
                                 entries_map: dict[int, dict]) -> str:
    NOMORS = ["50", "100", "200", "400", "800", "1.500", "4x50", "4x100", "4x200"]
    GAYAS  = ["Bebas", "Dada", "Punggung", "Kupu-kupu",
               "Ganti Individu", "Ganti Estafet", "Bebas Estafet"]

    def opt_list(lst, selected, sep=" / ") -> str:
        parts = []
        for item in lst:
            e = _esc(item)
            if item == selected:
                parts.append(f'<span style="text-decoration:underline;font-weight:bold">{e}</span>')
            else:
                parts.append(e)
        return sep.join(parts)

    cards = ""
    for lane in range(1, 17):
        entry  = entries_map.get(lane, {})
        elapsed = time_map.get(lane)
        waktu1  = fmt_ms(elapsed) if elapsed is not None else ""
        cards += f"""
        <div class="form-card">
          <div class="hdr">
            <div class="hdr-logo">🏊</div>
            <div>
              <div class="hdr-title">{_esc(race.get('nama_lomba') or 'FORM CATATAN WAKTU')}</div>
              <div class="hdr-sub">{_esc(race.get('kategori') or '')}</div>
            </div>
          </div>
          <div class="form-title">FORM CATATAN WAKTU</div>
          <div class="lane-label">LINTASAN</div>
          <div class="lane-num">{lane}</div>
          <div class="row-f">
            <span class="lbl">ACARA</span>
            <span class="box">{_esc(race.get('acara') or '')}</span>
            <span style="margin-left:5mm">SERI</span>
            <span class="box">{_esc(race.get('seri') or '')}</span>
            <span style="margin-left:5mm;font-weight:bold">{_esc(race.get('gender') or 'PA / PI / MIX')}</span>
          </div>
          <div class="opts">
            <div><strong>NOMOR</strong> : {opt_list(NOMORS, race.get('nomor'))}</div>
            <div style="margin-top:1mm"><strong>GAYA &nbsp;</strong> : {opt_list(GAYAS, race.get('gaya'))}</div>
          </div>
          <div class="row-f" style="margin-top:3mm">
            <span class="lbl2">NAMA ATLET / TIM</span>
            <span class="dotline">{_esc(entry.get('nama_atlet') or '')}</span>
          </div>
          <div class="row-f">
            <span class="lbl2">KLUB / DAERAH</span>
            <span class="dotline">{_esc(entry.get('klub') or '')}</span>
          </div>
          <div class="waktu-sec">
            <strong>WAKTU</strong>
            <div class="w-row"><span class="w-num">: 1</span><span class="w-line">{waktu1}</span></div>
            <div class="w-row"><span class="w-num" style="padding-left:4px">2</span><span class="w-line"></span></div>
            <div class="w-row"><span class="w-num" style="padding-left:4px">3</span><span class="w-line"></span></div>
          </div>
          <div class="ket">Keterangan : Did Not Start / No Time **</div>
          <div class="sig-row">
            <div class="sig-blk"><em>Chief Timekeeper</em><div class="sig-line"></div></div>
            <div class="sig-blk"><em>Timekeeper</em><div class="sig-line"></div></div>
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="id"><head><meta charset="UTF-8"><title>Form Catatan Waktu</title>
<style>
@page{{size:A5 portrait;margin:8mm}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;font-size:10pt;background:#eee}}
@media print{{body{{background:white}}.no-print{{display:none!important}}}}
.no-print{{text-align:center;padding:10px;background:#1565c0;color:white;margin-bottom:8px}}
.no-print button{{padding:7px 18px;border:none;border-radius:6px;font-size:13px;cursor:pointer;font-weight:bold;margin:0 4px}}
.form-card{{width:140mm;min-height:192mm;background:white;border:1px solid #aaa;
  padding:7mm 8mm;margin:8mm auto;page-break-after:always}}
.form-card:last-child{{page-break-after:auto}}
.hdr{{display:flex;align-items:flex-start;gap:5mm;margin-bottom:3mm;border-bottom:1px solid #000;padding-bottom:2mm}}
.hdr-logo{{font-size:22pt;line-height:1}}
.hdr-title{{font-size:9.5pt;font-weight:bold}}
.hdr-sub{{font-size:8pt;color:#444;margin-top:1px}}
.form-title{{text-align:center;font-size:13pt;font-weight:bold;margin:3mm 0 1mm;letter-spacing:1px}}
.lane-label{{text-align:center;font-size:8pt;font-weight:bold;letter-spacing:3px}}
.lane-num{{display:block;width:24mm;height:24mm;border:3px solid black;
  font-size:36pt;font-weight:900;text-align:center;line-height:24mm;margin:2mm auto 3mm}}
.row-f{{display:flex;align-items:center;gap:3mm;margin:2mm 0;font-size:9pt}}
.lbl{{font-weight:bold;min-width:13mm}}
.lbl2{{font-weight:bold;min-width:33mm}}
.box{{border:1px solid black;min-width:15mm;height:6.5mm;display:inline-block;padding:.5mm 2mm}}
.dotline{{border-bottom:1px dotted black;flex:1;min-height:5mm;padding-bottom:1mm}}
.opts{{font-size:9pt;margin:2mm 0;line-height:1.8}}
.waktu-sec{{font-size:9pt;margin:3mm 0 1mm}}
.w-row{{display:flex;align-items:baseline;margin:1.5mm 0 1.5mm 16mm}}
.w-num{{min-width:6mm;font-weight:bold}}
.w-line{{border-bottom:1px solid black;flex:1;margin-left:2mm;min-height:4mm;padding-bottom:1mm}}
.ket{{font-size:9pt;margin-top:3mm}}
.sig-row{{display:flex;justify-content:space-between;margin-top:7mm}}
.sig-blk{{text-align:center;font-size:8.5pt;font-style:italic}}
.sig-line{{border-top:1px solid black;width:40mm;margin-top:8mm}}
</style></head><body>
<div class="no-print">
  <button style="background:#fff;color:#1565c0" onclick="window.print()">🖨 Cetak</button>
  <button style="background:#c62828;color:#fff"  onclick="window.close()">✕ Tutup</button>
</div>
{cards}
</body></html>"""


def generate_buku_acara_html(all_races: list[dict]) -> str:
    from collections import OrderedDict

    nama_lomba = next((r.get("nama_lomba") for r in all_races if r.get("nama_lomba")), "BUKU ACARA")
    tanggal    = next((r.get("tanggal_lomba") for r in all_races if r.get("tanggal_lomba")), "")

    acara_map: dict[str, list] = OrderedDict()
    for race in reversed(all_races):
        key = race.get("acara") or f"Race {race['id']}"
        acara_map.setdefault(key, []).append(race)

    def gender_full(g: str) -> str:
        return {"PA": "PUTRA", "PI": "PUTRI", "MIX": "MIX",
                "Putra": "PUTRA", "Putri": "PUTRI", "Mix": "MIX"}.get(g, (g or "").upper())

    sections = ""
    for acara_key, races in acara_map.items():
        sample   = races[0]
        nomor    = sample.get("nomor") or ""
        gaya     = (sample.get("gaya") or "").upper()
        gender   = gender_full(sample.get("gender") or "")
        event_desc = " ".join(filter(None, [f"{nomor}M" if nomor else "", f"GAYA {gaya}" if gaya else "", gender]))
        kategori = _esc(sample.get("kategori") or "")

        rows = ""
        for race in races:
            time_map  = {lt["lane"]: lt["elapsed_ms"] for lt in race.get("lanes", [])}
            entries   = race.get("entries", {})
            seri_lbl  = _esc(str(race.get("seri") or race.get("heat") or ""))

            for lane in range(1, 17):
                entry   = entries.get(lane, {})
                elapsed = time_map.get(lane)
                rows += f"""
                <tr>
                  {"<td class='sc' rowspan='16'>" + seri_lbl + "</td>" if lane == 1 else ""}
                  <td class='lc'>{lane}</td>
                  <td>{_esc(entry.get('nama_atlet') or '')}</td>
                  <td>{_esc(entry.get('klub') or '')}</td>
                  <td class='tc'>{_esc(entry.get('limid_waktu') or '')}</td>
                  <td class='tc'>{fmt_ms(elapsed) if elapsed is not None else ''}</td>
                  <td class='kc'></td>
                </tr>"""

        sections += f"""
        <div class="section">
          <div class="ahdr">
            <div class="sbox">SERI<br><span class="sv">{kategori}</span></div>
            <div>
              <div class="atitle">ACARA {_esc(str(acara_key))}</div>
              <div class="asub">: {_esc(event_desc)}</div>
            </div>
          </div>
          <table>
            <thead><tr>
              <th>SERI</th><th>LINTASAN</th><th>NAMA ATLET</th>
              <th>SEKOLAH / KLUB</th><th>LIMID WAKTU</th><th>WAKTU</th><th>KETERANGAN</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="id"><head><meta charset="UTF-8"><title>Buku Acara</title>
<style>
@page{{size:A4 landscape;margin:10mm}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;font-size:9pt;background:#eee}}
@media print{{body{{background:white}}.no-print{{display:none!important}}}}
.no-print{{text-align:center;padding:10px;background:#1565c0;color:white;margin-bottom:8px}}
.no-print button{{padding:7px 18px;border:none;border-radius:6px;font-size:13px;cursor:pointer;font-weight:bold;margin:0 4px}}
.dochdr{{text-align:center;margin:6mm 0 8mm}}
.dochdr h1{{font-size:14pt;font-weight:bold;letter-spacing:2px}}
.dochdr h2{{font-size:12pt;margin:2px 0}}
.dochdr p{{font-size:10pt}}
.section{{margin-bottom:10mm;page-break-inside:avoid}}
.ahdr{{display:flex;gap:8mm;align-items:flex-start;margin-bottom:2mm}}
.sbox{{border:1px solid black;padding:2mm 4mm;text-align:center;font-size:8pt;font-weight:bold;min-width:22mm;line-height:1.4}}
.sv{{font-size:9.5pt;display:block;margin-top:1px}}
.atitle{{font-size:11pt;font-weight:bold}}
.asub{{font-size:10pt}}
table{{width:100%;border-collapse:collapse;font-size:8.5pt}}
th,td{{border:1px solid #333;padding:1mm 2mm}}
th{{background:#ddd;font-weight:bold;text-align:center;white-space:nowrap}}
.sc{{text-align:center;width:10mm;vertical-align:middle;font-weight:bold}}
.lc{{text-align:center;width:12mm}}
.tc{{text-align:center;min-width:22mm;font-family:monospace}}
.kc{{min-width:18mm}}
</style></head><body>
<div class="no-print">
  <button style="background:#fff;color:#1565c0" onclick="window.print()">🖨 Cetak</button>
  <button style="background:#c62828;color:#fff"  onclick="window.close()">✕ Tutup</button>
</div>
<div class="dochdr">
  <h1>BUKU ACARA</h1>
  <h2>{_esc(nama_lomba)}</h2>
  {f'<p>{_esc(tanggal)}</p>' if tanggal else ''}
</div>
{sections}
</body></html>"""


def open_html_report(content: str, prefix: str = "report") -> None:
    """Write HTML to a temp file and open it in the default browser."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", prefix=prefix + "_",
        delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.close()
    webbrowser.open(f"file://{tmp.name}")


# ══════════════════════════════════════════════════════════════════════════════
# Main GUI Application
# ══════════════════════════════════════════════════════════════════════════════

class TimerGUI:
    NUM_LANES      = 16
    TICK_MS        = 50   # timer refresh interval
    COLS           = 4    # lane-card columns

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🏊 Timer Renang – 16 Lintasan")
        self.root.minsize(960, 660)
        self.root.configure(bg=C_BG)

        self.db              = Database()
        self.race: dict      = {}
        self.start_ms: float = 0.0          # time.time()*1000 when race began
        self.lane_times: dict[int, int] = {}
        self.lane_done:  set[int]       = set()
        self._tick_job: str | None      = None

        self._setup_styles()
        self._build_ui()
        self._load_active_race()
        self._tick()

    # ── Style ─────────────────────────────────────────────────────────────────

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")

        def cfg(name, **kw):
            s.configure(name, **kw)

        cfg("TNotebook",      background=C_BG,   borderwidth=0)
        cfg("TNotebook.Tab",  background=C_CARD, foreground=C_MUTED,
            padding=[14, 6],  font=("Segoe UI", 10, "bold"))
        s.map("TNotebook.Tab",
              background=[("selected", C_BORDER)],
              foreground=[("selected", C_TEXT)])

        cfg("TFrame",        background=C_BG)
        cfg("Dark.TFrame",   background=C_BG)
        cfg("Card.TFrame",   background=C_CARD)
        cfg("TLabel",        background=C_BG,  foreground=C_TEXT, font=("Segoe UI", 9))
        cfg("Muted.TLabel",  background=C_BG,  foreground=C_MUTED, font=("Segoe UI", 8))
        cfg("Title.TLabel",  background=C_BG,  foreground=C_CYAN, font=("Segoe UI", 18, "bold"))
        cfg("Status.TLabel", background=C_CARD, foreground="#ffd54f", font=("Segoe UI", 11, "bold"))
        cfg("Heat.TLabel",   background=C_CARD, foreground=C_CYAN,   font=("Segoe UI", 11, "bold"))
        cfg("Clock.TLabel",  background=C_CARD, foreground="#80cbc4", font=("Courier New", 16, "bold"))

        for name, bg, fg in [
            ("Green.TButton", C_GREEN, "white"),
            ("Blue.TButton",  C_BLUE,  "white"),
            ("Red.TButton",   C_RED,   "white"),
            ("Teal.TButton",  C_TEAL,  "white"),
            ("Gray.TButton",  "#37474f", "#e0e0e0"),
        ]:
            cfg(name, background=bg, foreground=fg,
                font=("Segoe UI", 10, "bold"), padding=[10, 7])

        cfg("Sm.TButton",   background=C_BORDER, foreground=C_MUTED,
            font=("Segoe UI", 7),  padding=[2, 2])
        cfg("SmDone.TButton", background=C_CYAN, foreground="white",
            font=("Segoe UI", 7, "bold"), padding=[2, 2])

        cfg("TEntry",    fieldbackground=C_BG,   foreground=C_TEXT, insertcolor=C_TEXT)
        cfg("TCombobox", fieldbackground=C_BG,   foreground=C_TEXT)
        cfg("TScrollbar", troughcolor=C_CARD, background=C_BORDER)
        cfg("Treeview",  background=C_CARD, foreground=C_TEXT,
            fieldbackground=C_CARD, font=("Segoe UI", 9))
        cfg("Treeview.Heading", background=C_BORDER, foreground=C_MUTED,
            font=("Segoe UI", 9, "bold"))
        s.map("Treeview", background=[("selected", C_BORDER)],
              foreground=[("selected", C_TEXT)])

    # ── Top-level UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        ttk.Label(self.root, text="🏊 Timer Renang", style="Title.TLabel").pack(pady=(12, 0))
        ttk.Label(self.root, text="16 Lintasan  |  ESP32 + Database",
                  foreground=C_MUTED, background=C_BG,
                  font=("Segoe UI", 9)).pack(pady=(0, 6))

        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.tab_timer   = ttk.Frame(nb, style="Dark.TFrame")
        self.tab_setup   = ttk.Frame(nb, style="Dark.TFrame")
        self.tab_laporan = ttk.Frame(nb, style="Dark.TFrame")
        self.tab_riwayat = ttk.Frame(nb, style="Dark.TFrame")

        nb.add(self.tab_timer,   text="⏱  Timer")
        nb.add(self.tab_setup,   text="⚙  Setup Lomba")
        nb.add(self.tab_laporan, text="🖨  Laporan")
        nb.add(self.tab_riwayat, text="📋  Riwayat")

        self._build_timer_tab()
        self._build_setup_tab()
        self._build_laporan_tab()
        self._build_riwayat_tab()

    # ── Timer tab ─────────────────────────────────────────────────────────────

    def _build_timer_tab(self):
        tab = self.tab_timer

        # Status bar
        sb = tk.Frame(tab, bg=C_CARD, bd=1, relief="solid")
        sb.pack(fill=tk.X, padx=12, pady=8)

        self.lbl_status  = ttk.Label(sb, text="Menunggu Start", style="Status.TLabel", background=C_CARD)
        self.lbl_heat    = ttk.Label(sb, text="Heat: —",        style="Heat.TLabel",   background=C_CARD)
        self.lbl_elapsed = ttk.Label(sb, text="00:00.000",      style="Clock.TLabel",  background=C_CARD)
        self.lbl_acara   = ttk.Label(sb, text="—",              background=C_CARD, foreground=C_MUTED,
                                     font=("Segoe UI", 10))

        self.lbl_status.pack(side=tk.LEFT, padx=14, pady=8)
        self.lbl_heat.pack(side=tk.LEFT, padx=14)
        self.lbl_acara.pack(side=tk.LEFT, padx=14)
        self.lbl_elapsed.pack(side=tk.RIGHT, padx=14, pady=8)

        # Lane grid (4 × 4)
        gf = tk.Frame(tab, bg=C_BG)
        gf.pack(fill=tk.BOTH, expand=True, padx=12)
        for c in range(self.COLS):
            gf.columnconfigure(c, weight=1)

        self.lane_widgets: dict[int, dict] = {}
        for i in range(self.NUM_LANES):
            lane = i + 1
            r, c = divmod(i, self.COLS)
            w = self._make_lane_card(gf, lane)
            w["frame"].grid(row=r, column=c, padx=5, pady=4, sticky="nsew")
            gf.rowconfigure(r, weight=1)
            self.lane_widgets[lane] = w

        # Control buttons
        bf = tk.Frame(tab, bg=C_BG)
        bf.pack(pady=10)
        ttk.Button(bf, text="▶  START A", style="Green.TButton",
                   command=lambda: self._start_race(1)).pack(side=tk.LEFT, padx=7)
        ttk.Button(bf, text="▶  START B", style="Blue.TButton",
                   command=lambda: self._start_race(2)).pack(side=tk.LEFT, padx=7)
        ttk.Button(bf, text="↺  RESET",   style="Red.TButton",
                   command=self._reset_race).pack(side=tk.LEFT, padx=7)

    def _make_lane_card(self, parent, lane: int) -> dict:
        frame = tk.Frame(parent, bg=C_CARD, bd=2, relief="groove")
        frame.columnconfigure(0, weight=1)

        lbl_num    = ttk.Label(frame, text=f"Lintasan {lane}",
                               background=C_CARD, foreground=C_MUTED,
                               font=("Segoe UI", 7))
        lbl_name   = ttk.Label(frame, text="", background=C_CARD, foreground=C_TEXT,
                               font=("Segoe UI", 8, "bold"), wraplength=130)
        lbl_club   = ttk.Label(frame, text="", background=C_CARD, foreground=C_MUTED,
                               font=("Segoe UI", 7))
        lbl_time   = ttk.Label(frame, text="—", background=C_CARD, foreground=C_CYAN,
                               font=("Courier New", 13, "bold"))
        lbl_rank   = ttk.Label(frame, text="", background=C_CARD, foreground=C_GOLD,
                               font=("Segoe UI", 12))
        btn_done   = ttk.Button(frame, text="SELESAI", style="Sm.TButton",
                                command=lambda l=lane: self._lane_finish(l))

        lbl_num.pack(anchor="w",  padx=6, pady=(5, 0))
        lbl_name.pack(anchor="w", padx=6)
        lbl_club.pack(anchor="w", padx=6)
        lbl_time.pack(anchor="w", padx=6, pady=(2, 0))
        lbl_rank.pack(anchor="e", padx=6)
        btn_done.pack(fill=tk.X,  padx=4, pady=(2, 5))

        return dict(frame=frame, lbl_num=lbl_num, lbl_name=lbl_name, lbl_club=lbl_club,
                    lbl_time=lbl_time, lbl_rank=lbl_rank, btn_done=btn_done)

    # ── Setup tab ─────────────────────────────────────────────────────────────

    def _build_setup_tab(self):
        tab = self.tab_setup

        canvas = tk.Canvas(tab, bg=C_BG, highlightthickness=0)
        vsb    = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        sf     = tk.Frame(canvas, bg=C_BG)
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # ── Race metadata ──────────────────────────────────────────────────────
        meta_frame = tk.LabelFrame(sf, text="  Info Lomba  ",
                                    bg=C_BG, fg=C_CYAN,
                                    font=("Segoe UI", 10, "bold"), padx=10, pady=8)
        meta_frame.pack(fill=tk.X, padx=12, pady=(10, 6))

        self.sv: dict[str, tk.StringVar] = {}

        def mke(parent, label, key, width, row, col, values=None):
            tk.Label(parent, text=label + ":", bg=C_BG, fg=C_MUTED,
                     font=("Segoe UI", 9)).grid(row=row, column=col * 2,
                                                 sticky="e", padx=(8, 2), pady=4)
            self.sv[key] = tk.StringVar()
            if values:
                cb = ttk.Combobox(parent, textvariable=self.sv[key],
                                  width=width, values=values)
                cb.grid(row=row, column=col * 2 + 1, sticky="w", padx=(2, 8), pady=4)
            else:
                ttk.Entry(parent, textvariable=self.sv[key],
                          width=width).grid(row=row, column=col * 2 + 1,
                                             sticky="w", padx=(2, 8), pady=4)

        mke(meta_frame, "Nama Lomba",    "nama_lomba",    35, 0, 0)
        mke(meta_frame, "Tanggal",       "tanggal_lomba", 18, 0, 1)
        mke(meta_frame, "Kategori",      "kategori",      14, 0, 2)
        mke(meta_frame, "Acara #",       "acara",          7, 1, 0)
        mke(meta_frame, "Seri (Heat)",   "seri",           7, 1, 1)
        mke(meta_frame, "Nomor (Jarak)", "nomor",          9, 1, 2,
            values=["50","100","200","400","800","1500","4x50","4x100","4x200"])
        mke(meta_frame, "Gaya",          "gaya",          16, 2, 0,
            values=["Bebas","Dada","Punggung","Kupu-kupu",
                    "Ganti Individu","Ganti Estafet","Bebas Estafet"])

        # Gender radio
        tk.Label(meta_frame, text="Gender:", bg=C_BG, fg=C_MUTED,
                 font=("Segoe UI", 9)).grid(row=2, column=2, sticky="e", padx=(8, 2), pady=4)
        self.sv["gender"] = tk.StringVar(value="Putra")
        gf2 = tk.Frame(meta_frame, bg=C_BG)
        gf2.grid(row=2, column=3, columnspan=3, sticky="w", pady=4)
        for g in ["Putra", "Putri", "Mix"]:
            tk.Radiobutton(gf2, text=g, variable=self.sv["gender"], value=g,
                           bg=C_BG, fg=C_TEXT, selectcolor=C_BORDER,
                           activebackground=C_BG, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=6)

        # ── Athlete entries ────────────────────────────────────────────────────
        ae_frame = tk.LabelFrame(sf, text="  Daftar Atlet  ",
                                  bg=C_BG, fg=C_CYAN,
                                  font=("Segoe UI", 10, "bold"), padx=6, pady=6)
        ae_frame.pack(fill=tk.X, padx=12, pady=6)

        for ci, (hdr, w) in enumerate(zip(["Lin.", "Nama Atlet / Tim", "Sekolah / Klub", "Limid Waktu"],
                                           [4,      28,                 20,               10])):
            tk.Label(ae_frame, text=hdr, bg=C_BORDER, fg=C_TEXT,
                     font=("Segoe UI", 9, "bold"), width=w,
                     anchor="center").grid(row=0, column=ci, padx=1, pady=1, sticky="ew")

        self.ae_svs: dict[int, dict[str, tk.StringVar]] = {}
        for lane in range(1, self.NUM_LANES + 1):
            self.ae_svs[lane] = {}
            tk.Label(ae_frame, text=str(lane), bg=C_CARD, fg=C_MUTED,
                     font=("Segoe UI", 9, "bold"), width=4,
                     anchor="center").grid(row=lane, column=0, padx=1, pady=1, sticky="ew")
            for ci, (key, w) in enumerate(zip(["nama_atlet", "klub", "limid_waktu"],
                                               [28, 20, 10])):
                sv = tk.StringVar()
                self.ae_svs[lane][key] = sv
                ttk.Entry(ae_frame, textvariable=sv,
                          width=w).grid(row=lane, column=ci + 1, padx=1, pady=1, sticky="ew")
            ae_frame.columnconfigure(1, weight=1)
            ae_frame.columnconfigure(2, weight=1)

        # Save buttons
        bf = tk.Frame(sf, bg=C_BG)
        bf.pack(pady=10)
        ttk.Button(bf, text="💾  Simpan Setup", style="Blue.TButton",
                   command=self._save_setup).pack(side=tk.LEFT, padx=8)
        ttk.Button(bf, text="🔄  Muat Data Aktif", style="Teal.TButton",
                   command=self._load_active_to_setup).pack(side=tk.LEFT, padx=8)

    # ── Laporan tab ───────────────────────────────────────────────────────────

    def _build_laporan_tab(self):
        tab = self.tab_laporan
        outer = tk.Frame(tab, bg=C_BG)
        outer.pack(expand=True)

        tk.Label(outer, text="📄 Cetak Laporan", bg=C_BG, fg=C_CYAN,
                 font=("Segoe UI", 14, "bold")).pack(pady=(30, 16))

        for title, desc, cmd, style in [
            ("📋  Form Catatan Waktu",
             "Satu form per lintasan (16 form per lomba)\nDicetak sebagai lembar untuk juri pencatat waktu",
             self._print_catatan_waktu, "Green.TButton"),
            ("📚  Buku Acara",
             "Semua acara dalam satu tabel – diurutkan per ACARA dan SERI\nTermasuk nama atlet, klub, limid waktu, dan waktu tercatat",
             self._print_buku_acara, "Blue.TButton"),
        ]:
            card = tk.Frame(outer, bg=C_CARD, bd=2, relief="groove", padx=20, pady=14)
            card.pack(fill=tk.X, padx=50, pady=8)
            tk.Label(card, text=title, bg=C_CARD, fg=C_TEXT,
                     font=("Segoe UI", 12, "bold")).pack(anchor="w")
            tk.Label(card, text=desc, bg=C_CARD, fg=C_MUTED,
                     font=("Segoe UI", 9), justify="left").pack(anchor="w", pady=6)
            ttk.Button(card, text="🖨  Buka & Cetak", style=style,
                       command=cmd).pack(anchor="w")

    # ── Riwayat tab ───────────────────────────────────────────────────────────

    def _build_riwayat_tab(self):
        tab = self.tab_riwayat
        frame = tk.Frame(tab, bg=C_BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        cols = ("#", "Acara", "Seri", "Nomor", "Gaya", "Gender",
                "Nama Lomba", "Tanggal", "Waktu Mulai", "Selesai")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=16)
        for col, w in zip(cols, [40, 60, 55, 55, 90, 65, 170, 110, 140, 80]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=w)

        vsb = ttk.Scrollbar(frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        bf = tk.Frame(tab, bg=C_BG)
        bf.pack(pady=6)
        ttk.Button(bf, text="🔄 Refresh",     style="Blue.TButton",
                   command=self._refresh_riwayat).pack(side=tk.LEFT, padx=8)
        ttk.Button(bf, text="🖨 Cetak Terpilih", style="Teal.TButton",
                   command=self._print_selected).pack(side=tk.LEFT, padx=8)

        self._refresh_riwayat()

    # ── Race logic ────────────────────────────────────────────────────────────

    def _get_meta(self) -> dict:
        return {k: sv.get().strip() or None for k, sv in self.sv.items()}

    def _start_race(self, heat: int):
        meta = self._get_meta()
        self.race       = self.db.start_race(heat, meta)
        self.start_ms   = time.time() * 1000
        self.lane_times.clear()
        self.lane_done.clear()
        self._save_entries_to_db()
        self._refresh_ui()

    def _reset_race(self):
        if not messagebox.askyesno("Reset", "Reset semua lintasan?"):
            return
        self.db.reset_race()
        self.race = {}
        self.start_ms = 0.0
        self.lane_times.clear()
        self.lane_done.clear()
        self._refresh_ui()

    def _lane_finish(self, lane: int):
        if not self.race.get("active"):
            return
        if lane in self.lane_done:
            return
        elapsed = int(time.time() * 1000 - self.start_ms)
        self.lane_times[lane] = elapsed
        self.lane_done.add(lane)
        self.db.record_finish(lane, elapsed)
        self._update_lane_card(lane)

    def _load_active_race(self):
        self.race = self.db.get_active_race() or {}
        if self.race:
            self.start_ms = float(self.race.get("started_at", 0))
            for lt in self.db.get_lane_times(self.race["id"]):
                self.lane_times[lt["lane"]] = lt["elapsed_ms"]
                self.lane_done.add(lt["lane"])
        self._refresh_ui()

    def _save_setup(self):
        race = self.db.get_active_race()
        if not race:
            messagebox.showwarning("Perhatian",
                                   "Belum ada lomba aktif.\nTekan START terlebih dahulu.")
            return
        self.db.update_race_meta(race["id"], self._get_meta())
        self._save_entries_to_db()
        messagebox.showinfo("Tersimpan", "Setup lomba berhasil disimpan.")
        self._refresh_ui()

    def _save_entries_to_db(self):
        race = self.db.get_active_race()
        if not race:
            return
        for lane in range(1, self.NUM_LANES + 1):
            svs = self.ae_svs[lane]
            self.db.set_lane_entry(
                race["id"], lane,
                svs["nama_atlet"].get().strip() or None,
                svs["klub"].get().strip()       or None,
                svs["limid_waktu"].get().strip() or None,
            )

    def _load_active_to_setup(self):
        race = self.db.get_active_race()
        if not race:
            messagebox.showinfo("Info", "Tidak ada lomba aktif.")
            return
        for key, sv in self.sv.items():
            sv.set(race.get(key) or "")
        entries = self.db.get_lane_entries(race["id"])
        for lane, svs in self.ae_svs.items():
            e = entries.get(lane, {})
            svs["nama_atlet"].set(e.get("nama_atlet") or "")
            svs["klub"].set(e.get("klub") or "")
            svs["limid_waktu"].set(e.get("limid_waktu") or "")
        messagebox.showinfo("Dimuat", "Data lomba aktif berhasil dimuat ke form setup.")

    # ── UI refresh ────────────────────────────────────────────────────────────

    def _refresh_ui(self):
        if self.race and self.race.get("active"):
            self.lbl_status.config(text="Berlomba 🏊")
            self.lbl_heat.config(text=f"Heat: {self.race.get('heat', '?')}")
            acara_info = " ".join(filter(None, [
                f"Acara {self.race['acara']}" if self.race.get("acara") else "",
                f"Seri {self.race['seri']}"   if self.race.get("seri")  else "",
            ]))
            self.lbl_acara.config(text=acara_info or "—")
        else:
            self.lbl_status.config(text="Menunggu Start")
            self.lbl_heat.config(text="Heat: —")
            self.lbl_acara.config(text="—")
            self.lbl_elapsed.config(text="00:00.000")

        entries = {}
        if self.race:
            entries = self.db.get_lane_entries(self.race["id"])

        rank_map: dict[int, int] = {}
        for rank, (lane, _) in enumerate(sorted(self.lane_times.items(), key=lambda x: x[1]), 1):
            rank_map[lane] = rank

        for lane in range(1, self.NUM_LANES + 1):
            self._update_lane_card(lane, entries=entries, rank_map=rank_map)

        self._refresh_riwayat()

    def _update_lane_card(self, lane: int, entries: dict | None = None,
                           rank_map: dict | None = None):
        w    = self.lane_widgets[lane]
        done = lane in self.lane_done

        if done:
            rank = (rank_map or {}).get(lane, 0)
            if rank == 1:
                bg, fg_t = "#3d2e00", C_GOLD
            elif rank == 2:
                bg, fg_t = "#2a2a2a", C_SILVER
            elif rank == 3:
                bg, fg_t = "#2e1800", C_BRONZE
            else:
                bg, fg_t = "#0a2e38", C_CYAN
        else:
            bg, fg_t = C_CARD, C_CYAN

        w["frame"].configure(bg=bg)
        for key in ("lbl_num", "lbl_name", "lbl_club", "lbl_time", "lbl_rank"):
            w[key].configure(background=bg)
        w["lbl_time"].configure(foreground=fg_t)

        if entries is not None:
            e = entries.get(lane, {})
            w["lbl_name"].config(text=e.get("nama_atlet") or "")
            w["lbl_club"].config(text=e.get("klub") or "")

        elapsed = self.lane_times.get(lane)
        w["lbl_time"].config(text=fmt_ms(elapsed) if elapsed is not None else "—")

        if rank_map and lane in rank_map:
            rank  = rank_map[lane]
            badge = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else ""
            w["lbl_rank"].config(text=badge)
        else:
            w["lbl_rank"].config(text="")

        if done:
            w["btn_done"].configure(text="✔ SELESAI", style="SmDone.TButton")
        else:
            w["btn_done"].configure(text="SELESAI", style="Sm.TButton")

    # ── Clock tick ────────────────────────────────────────────────────────────

    def _tick(self):
        if self.race.get("active") and self.start_ms:
            elapsed = int(time.time() * 1000 - self.start_ms)
            self.lbl_elapsed.config(text=fmt_ms(elapsed))
        self.root.after(self.TICK_MS, self._tick)

    # ── Reports ───────────────────────────────────────────────────────────────

    def _print_catatan_waktu(self):
        race = self.db.get_active_race()
        if not race:
            races = self.db.get_all_races()
            if not races:
                messagebox.showinfo("Info", "Belum ada data lomba.")
                return
            race = {k: v for k, v in races[0].items() if k not in ("lanes", "entries")}
            time_map  = {lt["lane"]: lt["elapsed_ms"] for lt in races[0].get("lanes", [])}
            entries_m = races[0].get("entries", {})
        else:
            time_map  = {lt["lane"]: lt["elapsed_ms"] for lt in self.db.get_lane_times(race["id"])}
            entries_m = self.db.get_lane_entries(race["id"])

        html = generate_catatan_waktu_html(race, time_map, entries_m)
        open_html_report(html, "catatan_waktu")

    def _print_buku_acara(self):
        races = self.db.get_all_races()
        if not races:
            messagebox.showinfo("Info", "Belum ada data lomba.")
            return
        html = generate_buku_acara_html(races)
        open_html_report(html, "buku_acara")

    def _print_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Pilih lomba dari tabel terlebih dahulu.")
            return
        race_id = self.tree.item(sel[0])["values"][0]
        races = self.db.get_all_races()
        rd    = next((r for r in races if r["id"] == race_id), None)
        if not rd:
            return
        time_map  = {lt["lane"]: lt["elapsed_ms"] for lt in rd.get("lanes", [])}
        entries_m = rd.get("entries", {})
        race      = {k: v for k, v in rd.items() if k not in ("lanes", "entries")}
        html      = generate_catatan_waktu_html(race, time_map, entries_m)
        open_html_report(html, f"catatan_waktu_race{race_id}")

    def _refresh_riwayat(self):
        self.tree.delete(*self.tree.get_children())
        for race in self.db.get_all_races():
            started = datetime.fromtimestamp(race["started_at"] / 1000).strftime("%d/%m/%Y %H:%M:%S")
            n_done  = len(race.get("lanes", []))
            self.tree.insert("", tk.END, values=(
                race["id"],
                race.get("acara")         or "—",
                race.get("seri")          or "—",
                race.get("nomor")         or "—",
                race.get("gaya")          or "—",
                race.get("gender")        or "—",
                race.get("nama_lomba")    or "—",
                race.get("tanggal_lomba") or "—",
                started,
                f"{n_done}/16",
            ))


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    app  = TimerGUI(root)
    root.mainloop()
