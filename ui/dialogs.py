"""
ui.dialogs - Safe wrappers around tkinter.messagebox.

Centralizes dialog calls so UI layers can remain thin and testable while
preserving existing user-visible behavior.
"""

from __future__ import annotations

import logging
from tkinter import messagebox
from typing import Literal

log = logging.getLogger("workbench.ui.dialogs")


def show_error(title: str, message: str, parent=None) -> None:
    """Show an error dialog with a best-effort parent binding."""
    try:
        if parent is not None and parent.winfo_exists():
            messagebox.showerror(title, message, parent=parent)
        else:
            messagebox.showerror(title, message)
    except Exception:
        log.exception("Failed to show error dialog: %s", title)


def show_warning(title: str, message: str, parent=None) -> None:
    """Show a warning dialog with a best-effort parent binding."""
    try:
        if parent is not None and parent.winfo_exists():
            messagebox.showwarning(title, message, parent=parent)
        else:
            messagebox.showwarning(title, message)
    except Exception:
        log.exception("Failed to show warning dialog: %s", title)


MessageBoxIcon = Literal["question", "warning", "error", "info"]


def ask_yes_no(
    title: str, message: str, *, icon: MessageBoxIcon = "question", parent=None
) -> bool:
    """Ask a yes/no question and return False on UI failures."""
    try:
        if parent is not None and parent.winfo_exists():
            return bool(messagebox.askyesno(title, message, icon=icon, parent=parent))
        return bool(messagebox.askyesno(title, message, icon=icon))
    except Exception:
        log.exception("Failed to show yes/no dialog: %s", title)
        return False
