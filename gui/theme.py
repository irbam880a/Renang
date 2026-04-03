"""Centralized theme configuration for a professional look."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ── Color Palette ────────────────────────────────────────────────────────────

# Primary
PRIMARY = "#1B3A5C"         # Dark navy blue
PRIMARY_LIGHT = "#2A5A8C"   # Lighter navy
PRIMARY_DARK = "#0F2640"    # Very dark navy

# Accent
ACCENT = "#0D92F4"          # Bright blue
ACCENT_HOVER = "#0B7AD4"

# Status colors
SUCCESS = "#27AE60"
SUCCESS_HOVER = "#219A52"
DANGER = "#E74C3C"
DANGER_HOVER = "#C0392B"
WARNING = "#F39C12"

# Backgrounds
BG_MAIN = "#F4F6F9"         # Light cool gray
BG_CARD = "#FFFFFF"
BG_HEADER = PRIMARY
BG_STATUS = "#E2E8F0"

# Text
TEXT_PRIMARY = "#1A202C"
TEXT_SECONDARY = "#4A5568"
TEXT_MUTED = "#A0AEC0"
TEXT_ON_PRIMARY = "#FFFFFF"
TEXT_ON_ACCENT = "#FFFFFF"

# Borders
BORDER_LIGHT = "#E2E8F0"
BORDER_MEDIUM = "#CBD5E0"

# Table
TABLE_HEADER_BG = "#EDF2F7"
TABLE_ODD = "#F7FAFC"
TABLE_EVEN = "#FFFFFF"
TABLE_TOP3 = "#FEFCE8"      # Soft yellow highlight
TABLE_SELECTED = "#EBF5FF"

# Timer
TIMER_RUNNING = "#E65100"   # Orange
TIMER_STOPPED = "#C62828"   # Dark red
TIMER_READY = "#2E7D32"     # Green
TIMER_DISPLAY = "#1A237E"   # Indigo

# ── Fonts ────────────────────────────────────────────────────────────────────

FONT_FAMILY = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"

FONT_TITLE = (FONT_FAMILY, 16, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 12, "bold")
FONT_BODY = (FONT_FAMILY, 10)
FONT_BODY_BOLD = (FONT_FAMILY, 10, "bold")
FONT_SMALL = (FONT_FAMILY, 9)
FONT_SMALL_BOLD = (FONT_FAMILY, 9, "bold")
FONT_SMALL_ITALIC = (FONT_FAMILY, 9, "italic")
FONT_TINY = (FONT_FAMILY, 8)
FONT_TIMER_LARGE = (FONT_FAMILY_MONO, 22, "bold")
FONT_TIMER_CARD = (FONT_FAMILY_MONO, 16, "bold")
FONT_LANE_LABEL = (FONT_FAMILY, 11, "bold")
FONT_BUTTON = (FONT_FAMILY, 11, "bold")
FONT_BUTTON_LARGE = (FONT_FAMILY, 13, "bold")
FONT_HEADER = (FONT_FAMILY, 17, "bold")
FONT_TAB = (FONT_FAMILY, 10, "bold")
FONT_STATUS = (FONT_FAMILY, 9)
FONT_LIST = (FONT_FAMILY, 10)
FONT_TREE_HEADING = (FONT_FAMILY, 9, "bold")
FONT_TREE_BODY = (FONT_FAMILY, 9)


# ── Style Setup ──────────────────────────────────────────────────────────────

def apply_theme(root: tk.Tk):
    """Apply the professional theme to the given Tk root."""
    root.configure(bg=BG_MAIN)
    root.option_add("*Font", FONT_BODY)

    style = ttk.Style(root)
    style.theme_use("clam")

    # ── General ──────────────────────────────────────────────────────────
    style.configure(".", background=BG_MAIN, foreground=TEXT_PRIMARY,
                    font=FONT_BODY, borderwidth=0)

    # ── Notebook / Tabs ──────────────────────────────────────────────────
    style.configure("TNotebook", background=BG_MAIN, borderwidth=0,
                    tabmargins=[4, 4, 4, 0])
    style.configure("TNotebook.Tab", font=FONT_TAB, padding=[14, 6],
                    background=BORDER_LIGHT, foreground=TEXT_SECONDARY)
    style.map("TNotebook.Tab",
              background=[("selected", BG_CARD), ("active", "#E8EDF4")],
              foreground=[("selected", PRIMARY), ("active", PRIMARY_LIGHT)],
              expand=[("selected", [0, 0, 0, 2])])

    # ── Frames ───────────────────────────────────────────────────────────
    style.configure("TFrame", background=BG_MAIN)
    style.configure("Card.TFrame", background=BG_CARD, relief="flat")
    style.configure("TLabelframe", background=BG_MAIN, borderwidth=1,
                    relief="solid", bordercolor=BORDER_MEDIUM)
    style.configure("TLabelframe.Label", font=FONT_SUBTITLE,
                    foreground=PRIMARY, background=BG_MAIN)

    # ── Labels ───────────────────────────────────────────────────────────
    style.configure("TLabel", background=BG_MAIN, foreground=TEXT_PRIMARY,
                    font=FONT_BODY)
    style.configure("Heading.TLabel", font=FONT_SUBTITLE,
                    foreground=PRIMARY, background=BG_MAIN)
    style.configure("Muted.TLabel", foreground=TEXT_MUTED, font=FONT_SMALL)
    style.configure("Card.TLabel", background=BG_CARD)

    # ── Buttons ──────────────────────────────────────────────────────────
    style.configure("TButton", font=FONT_BODY_BOLD, padding=[10, 5],
                    background=ACCENT, foreground=TEXT_ON_ACCENT,
                    borderwidth=0, focuscolor="")
    style.map("TButton",
              background=[("active", ACCENT_HOVER), ("disabled", BORDER_LIGHT)],
              foreground=[("disabled", TEXT_MUTED)])

    style.configure("Success.TButton", background=SUCCESS,
                    foreground=TEXT_ON_PRIMARY, font=FONT_BODY_BOLD)
    style.map("Success.TButton",
              background=[("active", SUCCESS_HOVER)])

    style.configure("Danger.TButton", background=DANGER,
                    foreground=TEXT_ON_PRIMARY, font=FONT_BODY_BOLD)
    style.map("Danger.TButton",
              background=[("active", DANGER_HOVER)])

    # ── Entry / Combobox / Spinbox ───────────────────────────────────────
    style.configure("TEntry", fieldbackground=BG_CARD, borderwidth=1,
                    relief="solid", padding=[6, 4])
    style.map("TEntry", bordercolor=[("focus", ACCENT), ("!focus", BORDER_MEDIUM)])

    style.configure("TCombobox", fieldbackground=BG_CARD, padding=[6, 4],
                    borderwidth=1, arrowsize=14)
    style.map("TCombobox",
              bordercolor=[("focus", ACCENT), ("!focus", BORDER_MEDIUM)],
              fieldbackground=[("readonly", BG_CARD)])

    style.configure("TSpinbox", fieldbackground=BG_CARD, padding=[6, 4],
                    borderwidth=1, arrowsize=14)

    # ── Scrollbar ────────────────────────────────────────────────────────
    style.configure("TScrollbar", background=BORDER_LIGHT,
                    troughcolor=BG_MAIN, borderwidth=0, arrowsize=14)

    # ── Separator ────────────────────────────────────────────────────────
    style.configure("TSeparator", background=BORDER_MEDIUM)

    # ── Treeview ─────────────────────────────────────────────────────────
    style.configure("Treeview", background=BG_CARD,
                    fieldbackground=BG_CARD, foreground=TEXT_PRIMARY,
                    font=FONT_TREE_BODY, rowheight=28, borderwidth=0)
    style.configure("Treeview.Heading", font=FONT_TREE_HEADING,
                    background=TABLE_HEADER_BG, foreground=PRIMARY,
                    borderwidth=1, relief="flat", padding=[4, 4])
    style.map("Treeview",
              background=[("selected", TABLE_SELECTED)],
              foreground=[("selected", PRIMARY)])

    # ── Listbox (not ttk – configure via option_add) ─────────────────────
    root.option_add("*Listbox.Font", FONT_LIST)
    root.option_add("*Listbox.Background", BG_CARD)
    root.option_add("*Listbox.Foreground", TEXT_PRIMARY)
    root.option_add("*Listbox.SelectBackground", ACCENT)
    root.option_add("*Listbox.SelectForeground", TEXT_ON_ACCENT)
    root.option_add("*Listbox.BorderWidth", 1)
    root.option_add("*Listbox.Relief", "solid")
    root.option_add("*Listbox.HighlightThickness", 0)

    return style
