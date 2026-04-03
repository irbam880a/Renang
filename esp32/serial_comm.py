"""
ESP32 serial communication module.

Protocol (newline-terminated plain text):
  PC  -> ESP32 :  START\\n          start all lane timers
                  RESET\\n          reset all timers to 0
                  STOP:<N>\\n       stop lane N manually from PC
                  PING\\n           connection test
  ESP32 -> PC  :  STARTED\\n        timer running
                  RESET_OK\\n       reset acknowledged
                  LANE:<N>:TIME:<ms>\\n   lane N stopped at <ms> milliseconds
                  PONG\\n           response to PING
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

try:
    import serial
    import serial.tools.list_ports
    PYSERIAL_OK = True
except ImportError:
    PYSERIAL_OK = False


def list_serial_ports() -> list[str]:
    """Return available serial port names."""
    if not PYSERIAL_OK:
        return []
    return [p.device for p in serial.tools.list_ports.comports()]


class SerialComm:
    """Background thread that reads from an ESP32 over a serial port."""

    def __init__(self, on_lane_stopped: Callable[[int, int], None],
                 on_status: Callable[[str], None]):
        """
        Parameters
        ----------
        on_lane_stopped : callable(lane_number: int, time_ms: int)
            Called (from background thread) when ESP32 reports a lane finish.
        on_status : callable(message: str)
            Called with status/log messages.
        """
        self._on_lane_stopped = on_lane_stopped
        self._on_status = on_status
        self._ser = None  # Optional[serial.Serial]
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def connect(self, port: str, baud: int = 115200) -> bool:
        if not PYSERIAL_OK:
            self._on_status("pyserial not installed. Run: pip install pyserial")
            return False
        self.disconnect()
        try:
            self._ser = serial.Serial(port, baud, timeout=1)
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._reader, daemon=True)
            self._thread.start()
            self._on_status(f"Connected to {port}")
            return True
        except serial.SerialException as exc:
            self._on_status(f"Connection failed: {exc}")
            self._ser = None
            return False

    def disconnect(self):
        self._stop_event.set()
        if self._ser and self._ser.is_open:
            try:
                self._ser.close()
            except serial.SerialException:
                pass
        self._ser = None
        self._on_status("Disconnected")

    def send(self, command: str):
        """Send a command string to the ESP32 (newline appended automatically)."""
        if not self.is_connected:
            return
        try:
            self._ser.write((command.strip() + "\n").encode())
        except serial.SerialException as exc:
            self._on_status(f"Send error: {exc}")

    def start_race(self):
        self.send("START")

    def reset_race(self):
        self.send("RESET")

    def stop_lane(self, lane: int):
        self.send(f"STOP:{lane}")

    def ping(self):
        self.send("PING")

    # ── background reader ──────────────────────────────────────────────────

    def _reader(self):
        while not self._stop_event.is_set():
            try:
                line = self._ser.readline().decode(errors="replace").strip()
            except serial.SerialException:
                self._on_status("Serial read error – disconnected")
                break
            if not line:
                continue
            self._parse(line)

    def _parse(self, line: str):
        if line == "STARTED":
            self._on_status("ESP32: timer started")
        elif line == "RESET_OK":
            self._on_status("ESP32: reset OK")
        elif line == "PONG":
            self._on_status("ESP32: pong")
        elif line.startswith("LANE:"):
            # LANE:<N>:TIME:<ms>
            try:
                parts = line.split(":")
                lane = int(parts[1])
                time_ms = int(parts[3])
                self._on_lane_stopped(lane, time_ms)
            except (IndexError, ValueError):
                self._on_status(f"ESP32: bad message: {line}")
        else:
            self._on_status(f"ESP32: {line}")
