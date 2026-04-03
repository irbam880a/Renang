"""
Timer panel – displays per-lane timer cards and race start/reset controls.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import time
import threading
from typing import Callable, Optional
from gui import theme


class LaneCard(tk.Frame):
    """A single lane timer card with professional styling."""

    def __init__(self, parent, lane: int,
                 on_stop: Callable[[int, int], None]):
        super().__init__(parent, bg=theme.BG_CARD, highlightbackground=theme.BORDER_MEDIUM,
                         highlightthickness=1, padx=1, pady=1)
        self._lane = lane
        self._on_stop = on_stop
        self._stopped = False
        self._stop_time_ms: Optional[int] = None

        # Athlete info (set externally)
        self._name_var = tk.StringVar(value="")
        self._school_var = tk.StringVar(value="")

        # ── Lane header strip ────────────────────────────────────────────
        header = tk.Frame(self, bg=theme.PRIMARY, height=30)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=f"LANE {lane}",
                 font=theme.FONT_LANE_LABEL, fg=theme.TEXT_ON_PRIMARY,
                 bg=theme.PRIMARY).pack(side="left", padx=10)

        self._rank_lbl = tk.Label(header, text="",
                                   font=theme.FONT_SMALL_BOLD,
                                   fg=theme.WARNING, bg=theme.PRIMARY)
        self._rank_lbl.pack(side="right", padx=10)

        # ── Body ─────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=theme.BG_CARD)
        body.pack(fill="both", expand=True, padx=8, pady=4)

        tk.Label(body, textvariable=self._name_var,
                 font=theme.FONT_BODY_BOLD, fg=theme.TEXT_PRIMARY,
                 bg=theme.BG_CARD, wraplength=130, anchor="w").pack(
            fill="x", pady=(4, 0))
        tk.Label(body, textvariable=self._school_var,
                 font=theme.FONT_SMALL_ITALIC, fg=theme.TEXT_SECONDARY,
                 bg=theme.BG_CARD, wraplength=130, anchor="w").pack(
            fill="x")

        # Timer display
        self._time_lbl = tk.Label(body, text="00:00.000",
                                   font=theme.FONT_TIMER_CARD,
                                   fg=theme.TIMER_READY,
                                   bg=theme.BG_CARD)
        self._time_lbl.pack(pady=(6, 2))

        self._status_lbl = tk.Label(body, text="SIAP",
                                     font=theme.FONT_SMALL_BOLD,
                                     fg=theme.TEXT_MUTED,
                                     bg=theme.BG_CARD)
        self._status_lbl.pack()

        # Stop button
        self._stop_btn = tk.Button(body, text="■  STOP",
                                    font=theme.FONT_SMALL_BOLD,
                                    bg=theme.DANGER, fg="white",
                                    activebackground=theme.DANGER_HOVER,
                                    activeforeground="white",
                                    relief="flat", padx=12, pady=3,
                                    cursor="hand2",
                                    command=self._stop_clicked,
                                    state="disabled",
                                    disabledforeground=theme.TEXT_MUTED)
        self._stop_btn.pack(pady=(4, 8))

    # ── Public API ──────────────────────────────────────────────────────────

    def set_athlete(self, name: str, school: str):
        self._name_var.set(name)
        self._school_var.set(school)

    def arm(self):
        """Called just before the race starts – re-enable stop button."""
        self._stopped = False
        self._stop_time_ms = None
        self._time_lbl.config(text="00:00.000", fg=theme.TIMER_RUNNING)
        self._status_lbl.config(text="BERLARI ●", fg=theme.TIMER_RUNNING)
        self._stop_btn.config(state="normal", bg=theme.DANGER)
        self._rank_lbl.config(text="")
        self.config(highlightbackground=theme.TIMER_RUNNING, highlightthickness=2)

    def reset(self):
        self._stopped = False
        self._stop_time_ms = None
        self._time_lbl.config(text="00:00.000", fg=theme.TIMER_READY)
        self._status_lbl.config(text="SIAP", fg=theme.TEXT_MUTED)
        self._stop_btn.config(state="disabled")
        self._rank_lbl.config(text="")
        self.config(highlightbackground=theme.BORDER_MEDIUM, highlightthickness=1)

    def update_display(self, elapsed_ms: int):
        """Called by timer thread (via after) to update the display."""
        if not self._stopped:
            self._time_lbl.config(text=_fmt(elapsed_ms))

    def force_stop(self, elapsed_ms: int):
        """Called from ESP32 signal or external code."""
        if not self._stopped:
            self._stopped = True
            self._stop_time_ms = elapsed_ms
            self._time_lbl.config(text=_fmt(elapsed_ms), fg=theme.TIMER_STOPPED)
            self._status_lbl.config(text="✓ SELESAI", fg=theme.SUCCESS)
            self._stop_btn.config(state="disabled")
            self.config(highlightbackground=theme.SUCCESS, highlightthickness=2)

    @property
    def stopped(self) -> bool:
        return self._stopped

    @property
    def stop_time_ms(self) -> Optional[int]:
        return self._stop_time_ms

    # ── Private ─────────────────────────────────────────────────────────────

    def _stop_clicked(self):
        self._stop_btn.config(state="disabled")
        self._status_lbl.config(text="✓ SELESAI", fg=theme.SUCCESS)
        self._time_lbl.config(fg=theme.TIMER_STOPPED)
        self.config(highlightbackground=theme.SUCCESS, highlightthickness=2)
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
        ctrl = tk.Frame(self, bg=theme.BG_CARD, highlightbackground=theme.BORDER_LIGHT,
                        highlightthickness=1)
        ctrl.pack(fill="x", padx=4, pady=(4, 6))

        # Left: action buttons
        btn_frame = tk.Frame(ctrl, bg=theme.BG_CARD)
        btn_frame.pack(side="left", padx=8, pady=8)

        self._start_btn = tk.Button(
            btn_frame, text="▶  START LOMBA", font=theme.FONT_BUTTON_LARGE,
            bg=theme.SUCCESS, fg="white",
            activebackground=theme.SUCCESS_HOVER, activeforeground="white",
            relief="flat", width=16, height=2, cursor="hand2",
            command=self._start_race,
        )
        self._start_btn.pack(side="left", padx=(0, 8))

        self._reset_btn = tk.Button(
            btn_frame, text="⏹  RESET SEMUA", font=theme.FONT_BUTTON_LARGE,
            bg=theme.DANGER, fg="white",
            activebackground=theme.DANGER_HOVER, activeforeground="white",
            relief="flat", width=16, height=2, cursor="hand2",
            command=self._reset_all,
        )
        self._reset_btn.pack(side="left")

        # Right: elapsed time display
        time_frame = tk.Frame(ctrl, bg=theme.BG_CARD)
        time_frame.pack(side="right", padx=12, pady=8)

        tk.Label(time_frame, text="WAKTU LOMBA",
                 font=theme.FONT_TINY, fg=theme.TEXT_MUTED,
                 bg=theme.BG_CARD).pack()
        self._elapsed_lbl = tk.Label(time_frame, text="00:00.000",
                                      font=theme.FONT_TIMER_LARGE,
                                      fg=theme.TIMER_DISPLAY,
                                      bg=theme.BG_CARD)
        self._elapsed_lbl.pack()

    def _build_lanes(self):
        if hasattr(self, "_lanes_frame"):
            self._lanes_frame.destroy()
            self._cards.clear()

        self._lanes_frame = tk.Frame(self, bg=theme.BG_MAIN)
        self._lanes_frame.pack(fill="both", expand=True, padx=4, pady=4)

        cols = 4 if self._num_lanes > 8 else (
            4 if self._num_lanes > 4 else (2 if self._num_lanes > 2 else 1)
        )
        for i in range(cols):
            self._lanes_frame.columnconfigure(i, weight=1)

        for lane in range(1, self._num_lanes + 1):
            card = LaneCard(self._lanes_frame, lane, self._lane_stop_handler)
            row = (lane - 1) // cols
            col = (lane - 1) % cols
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
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
        self._elapsed_lbl.config(text="00:00.000", fg=theme.TIMER_DISPLAY)
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
