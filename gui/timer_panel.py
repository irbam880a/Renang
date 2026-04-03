"""
Timer panel – displays per-lane timer cards and race start/reset controls.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import time
import threading
from typing import Callable, Optional


class LaneCard(ttk.Frame):
    """A single lane timer card."""

    def __init__(self, parent, lane: int,
                 on_stop: Callable[[int, int], None]):
        """
        Parameters
        ----------
        lane     : 1-based lane number
        on_stop  : called with (lane, elapsed_ms) when lane is stopped
        """
        super().__init__(parent, relief="ridge", borderwidth=2)
        self._lane = lane
        self._on_stop = on_stop
        self._stopped = False
        self._stop_time_ms: Optional[int] = None

        # Athlete info (set externally)
        self._name_var = tk.StringVar(value="")
        self._school_var = tk.StringVar(value="")

        # ── Build card ─────────────────────────────────────────────────────
        lane_lbl = ttk.Label(self, text=f"Lane {lane}",
                             font=("Arial", 10, "bold"), foreground="#1F4E79")
        lane_lbl.pack(pady=(6, 0))

        ttk.Label(self, textvariable=self._name_var,
                  font=("Arial", 8), foreground="#333333",
                  wraplength=110).pack()
        ttk.Label(self, textvariable=self._school_var,
                  font=("Arial", 7, "italic"), foreground="#666666",
                  wraplength=110).pack()

        self._time_lbl = ttk.Label(self, text="00:00.000",
                                   font=("Courier", 14, "bold"),
                                   foreground="#006400")
        self._time_lbl.pack(pady=4)

        self._status_lbl = ttk.Label(self, text="SIAP",
                                     font=("Arial", 8),
                                     foreground="#999999")
        self._status_lbl.pack()

        self._stop_btn = ttk.Button(self, text="STOP",
                                    command=self._stop_clicked)
        self._stop_btn.pack(pady=(4, 6))
        self._stop_btn.config(state="disabled")

    # ── Public API ──────────────────────────────────────────────────────────

    def set_athlete(self, name: str, school: str):
        self._name_var.set(name)
        self._school_var.set(school)

    def arm(self):
        """Called just before the race starts – re-enable stop button."""
        self._stopped = False
        self._stop_time_ms = None
        self._time_lbl.config(text="00:00.000", foreground="#006400")
        self._status_lbl.config(text="BERLARI", foreground="#CC5500")
        self._stop_btn.config(state="normal")

    def reset(self):
        self._stopped = False
        self._stop_time_ms = None
        self._time_lbl.config(text="00:00.000", foreground="#006400")
        self._status_lbl.config(text="SIAP", foreground="#999999")
        self._stop_btn.config(state="disabled")

    def update_display(self, elapsed_ms: int):
        """Called by timer thread (via after) to update the display."""
        if not self._stopped:
            self._time_lbl.config(text=_fmt(elapsed_ms))

    def force_stop(self, elapsed_ms: int):
        """Called from ESP32 signal or external code."""
        if not self._stopped:
            self._stopped = True
            self._stop_time_ms = elapsed_ms
            self._time_lbl.config(text=_fmt(elapsed_ms), foreground="#CC0000")
            self._status_lbl.config(text="SELESAI", foreground="#006400")
            self._stop_btn.config(state="disabled")

    @property
    def stopped(self) -> bool:
        return self._stopped

    @property
    def stop_time_ms(self) -> Optional[int]:
        return self._stop_time_ms

    # ── Private ─────────────────────────────────────────────────────────────

    def _stop_clicked(self):
        # We don't know the exact elapsed_ms here; the panel will handle it
        self._stop_btn.config(state="disabled")
        self._status_lbl.config(text="SELESAI", foreground="#006400")
        self._time_lbl.config(foreground="#CC0000")
        # Signal will be sent up via on_stop with None – panel fills in time
        self._on_stop(self._lane, None)


def _fmt(ms: int) -> str:
    if ms is None:
        return "00:00.000"
    total_s = ms / 1000
    m = int(total_s // 60)
    s = total_s % 60
    return f"{m:02d}:{s:06.3f}"


class TimerPanel(ttk.Frame):
    """
    Main timer panel hosting all lane cards.
    Up to 16 lanes arranged in a responsive grid.
    """

    def __init__(self, parent, num_lanes: int = 8,
                 on_lane_stopped: Callable[[int, int], None] = None,
                 esp32=None):
        super().__init__(parent)
        self._num_lanes = num_lanes
        self._on_lane_stopped = on_lane_stopped
        self._esp32 = esp32

        self._start_time: Optional[float] = None
        self._running = False
        self._tick_job = None

        self._cards: dict[int, LaneCard] = {}
        self._build_controls()
        self._build_lanes()

    # ── Build UI ────────────────────────────────────────────────────────────

    def _build_controls(self):
        ctrl = ttk.Frame(self)
        ctrl.pack(fill="x", padx=6, pady=4)

        self._start_btn = tk.Button(
            ctrl, text="▶  START LOMBA", font=("Arial", 13, "bold"),
            bg="#28a745", fg="white", activebackground="#218838",
            activeforeground="white", width=18, height=2,
            command=self._start_race,
        )
        self._start_btn.pack(side="left", padx=6)

        self._reset_btn = tk.Button(
            ctrl, text="⏹  RESET SEMUA", font=("Arial", 13, "bold"),
            bg="#dc3545", fg="white", activebackground="#c82333",
            activeforeground="white", width=18, height=2,
            command=self._reset_all,
        )
        self._reset_btn.pack(side="left", padx=6)

        self._elapsed_lbl = ttk.Label(ctrl, text="00:00.000",
                                      font=("Courier", 20, "bold"),
                                      foreground="#1F4E79")
        self._elapsed_lbl.pack(side="right", padx=12)

        ttk.Label(ctrl, text="Waktu:", font=("Arial", 11)).pack(side="right")

    def _build_lanes(self):
        if hasattr(self, "_lanes_frame"):
            self._lanes_frame.destroy()
            self._cards.clear()

        self._lanes_frame = ttk.Frame(self)
        self._lanes_frame.pack(fill="both", expand=True, padx=6, pady=4)

        cols = 4 if self._num_lanes > 8 else (
            4 if self._num_lanes > 4 else (2 if self._num_lanes > 2 else 1)
        )
        for i in range(cols):
            self._lanes_frame.columnconfigure(i, weight=1)

        for lane in range(1, self._num_lanes + 1):
            card = LaneCard(self._lanes_frame, lane, self._lane_stop_handler)
            row = (lane - 1) // cols
            col = (lane - 1) % cols
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            self._lanes_frame.rowconfigure(row, weight=1)
            self._cards[lane] = card

    # ── Timer logic ─────────────────────────────────────────────────────────

    def _start_race(self):
        if self._running:
            return
        self._running = True
        self._start_time = time.perf_counter()
        self._start_btn.config(state="disabled")
        for card in self._cards.values():
            card.arm()
        if self._esp32 and self._esp32.is_connected:
            self._esp32.start_race()
        self._tick()

    def _reset_all(self):
        self._running = False
        if self._tick_job:
            self.after_cancel(self._tick_job)
            self._tick_job = None
        self._start_time = None
        self._elapsed_lbl.config(text="00:00.000")
        self._start_btn.config(state="normal")
        for card in self._cards.values():
            card.reset()
        if self._esp32 and self._esp32.is_connected:
            self._esp32.reset_race()

    def _tick(self):
        if not self._running:
            return
        elapsed_ms = int((time.perf_counter() - self._start_time) * 1000)
        self._elapsed_lbl.config(text=_fmt(elapsed_ms))
        for card in self._cards.values():
            card.update_display(elapsed_ms)
        self._tick_job = self.after(50, self._tick)  # ~20 fps

    def _lane_stop_handler(self, lane: int, time_ms: Optional[int]):
        """Called from LaneCard stop button or externally (ESP32)."""
        if not self._running:
            return
        if time_ms is None and self._start_time is not None:
            time_ms = int((time.perf_counter() - self._start_time) * 1000)
        card = self._cards.get(lane)
        if card:
            card.force_stop(time_ms)
        if self._on_lane_stopped:
            self._on_lane_stopped(lane, time_ms)
        # Check if all lanes stopped
        if all(c.stopped for c in self._cards.values()):
            self._running = False
            if self._tick_job:
                self.after_cancel(self._tick_job)
                self._tick_job = None
            self._start_btn.config(state="normal")

    # ── Public API ──────────────────────────────────────────────────────────

    def set_num_lanes(self, n: int):
        self._num_lanes = max(1, min(16, n))
        self._reset_all()
        self._build_lanes()

    def set_athletes(self, athletes: dict[int, dict]):
        """athletes = {lane: {athlete_name, school}}"""
        for lane, info in athletes.items():
            card = self._cards.get(lane)
            if card:
                card.set_athlete(
                    info.get("athlete_name", ""),
                    info.get("school", ""),
                )

    def esp32_lane_stopped(self, lane: int, time_ms: int):
        """Called from the serial comm thread – must schedule via after."""
        self.after(0, lambda: self._lane_stop_handler(lane, time_ms))

    @property
    def is_running(self) -> bool:
        return self._running

    def get_times(self) -> dict[int, Optional[int]]:
        return {lane: card.stop_time_ms for lane, card in self._cards.items()}
