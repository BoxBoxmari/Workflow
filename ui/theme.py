"""
ui.theme — Centralized ttk styling for the Workflow MVP workspace.

All panels reference style names from this module instead of patching
widgets inline.  Call ``apply_theme(root)`` once during app bootstrap.
"""

from __future__ import annotations

import tkinter as tk

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

# Spacing
PAD_XS = 2
PAD_SM = 4
PAD_MD = 8
PAD_LG = 12
PAD_XL = 16

# Fonts (scaled up for CustomTkinter)
FONT_FAMILY = "Segoe UI"
FONT_HEADING = (FONT_FAMILY, 15, "bold")
FONT_BODY = (FONT_FAMILY, 13)
FONT_SMALL = (FONT_FAMILY, 11)
FONT_MONO = ("Consolas", 12)

# Colors - Modern Dark Mode (Slate / Blue)
CLR_BG = "#0f172a"  # slate-900
CLR_SURFACE = "#1e293b"  # slate-800
CLR_SIDEBAR_BG = "#020617"  # slate-950
CLR_SIDEBAR_FG = "#e2e8f0"  # slate-200
CLR_ACCENT = "#3b82f6"  # blue-500
CLR_ACCENT_HOVER = "#2563eb"  # blue-600
CLR_SUCCESS = "#22c55e"  # green-500
CLR_ERROR = "#ef4444"  # red-500
CLR_WARNING = "#f59e0b"  # amber-500
CLR_PENDING = "#64748b"  # slate-500
CLR_RUNNING = "#0ea5e9"  # sky-500
CLR_SELECTED = "#334155"  # slate-700
CLR_BORDER = "#475569"  # slate-600
CLR_MUTED = "#94a3b8"  # slate-400

# Status color map
STATUS_COLORS = {
    "pending": CLR_PENDING,
    "running": CLR_RUNNING,
    "success": CLR_SUCCESS,
    "error": CLR_ERROR,
    "skipped": CLR_MUTED,
    "cancelled": CLR_MUTED,
}


def status_color(status: str) -> str:
    """Return the theme color for a given status string."""
    return STATUS_COLORS.get(status, CLR_PENDING)


# ---------------------------------------------------------------------------
# Theme application
# ---------------------------------------------------------------------------


def apply_theme(root: tk.Tk) -> None:
    """Apply the workspace theme to the root window (bg only)."""
    # Root window
    try:
        root.configure(bg=CLR_BG)
    except Exception:
        pass  # Some test environments don't support explicit bg config on CTk


# ---------------------------------------------------------------------------
# Semantic Tokens (for CTk widgets)
# ---------------------------------------------------------------------------

# Common Backgrounds
COLOR_BG = CLR_BG
COLOR_SURFACE = CLR_SURFACE

# Sidebar
COLOR_SIDEBAR = CLR_SIDEBAR_BG
COLOR_SIDEBAR_FG = CLR_SIDEBAR_FG

# Buttons
BTN_FG = CLR_SURFACE
BTN_HOVER = CLR_SELECTED
BTN_ACCENT = CLR_ACCENT
BTN_ACCENT_HOVER = CLR_ACCENT_HOVER

# Borders
BORDER_COLOR = CLR_BORDER
BORDER_WIDTH = 1

# Cards
CARD_BG = CLR_SURFACE
CARD_SELECTED = CLR_SELECTED
CARD_BORDER = CLR_BORDER

# Font Mapping
FONT_MAIN = FONT_BODY
FONT_TITLE = FONT_HEADING
FONT_META = FONT_SMALL
FONT_CODE = FONT_MONO
