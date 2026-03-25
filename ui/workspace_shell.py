"""
ui.workspace_shell — The main container for the AI Workflow Workbench.

Layout:
  Top Bar (Run/Stop, Undo/Redo, Title, Progress, Theme)
  Main Area (Sidebar, Canvas, Inspector)
  Bottom (Result Drawer)
"""

from __future__ import annotations

import logging
import time
import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

import ui.theme as T
from ui.flow_canvas import FlowCanvas
from ui.inspector_panel import InspectorPanel
from ui.result_drawer import ResultDrawer
from ui.sidebar_panel import SidebarPanel

if TYPE_CHECKING:
    from ui.workspace_controller import WorkspaceController
    from ui.workspace_state import WorkspaceState


log = logging.getLogger("workbench.ui.shell")


# ---------------------------------------------------------------------------
# Lightweight tooltip helper
# ---------------------------------------------------------------------------


class Tooltip:
    """Shows a floating label after a short hover delay, hides on leave.

    Python 3.14 + customtkinter compat: Toplevel is parented to the
    root window (via winfo_toplevel()), NOT to the CTkButton, to avoid
    broken nametowidget → _root() dispatch in Python 3.14.
    """

    DELAY_MS = 500

    def __init__(
        self, widget: ctk.CTkButton | ctk.CTkOptionMenu | tk.Widget, text: str
    ) -> None:
        self._widget = widget
        self._text = text
        self._job: str | None = None
        self._tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        try:
            self._cancel()
            self._job = self._widget.after(self.DELAY_MS, self._show)
        except Exception:
            pass

    def _cancel(self) -> None:
        if self._job:
            try:
                self._widget.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _show(self) -> None:
        if self._tip:
            return
        try:
            x = self._widget.winfo_rootx() + 4
            y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
            # Use the root Toplevel as parent, NOT self._widget (CTkButton).
            # Parenting a tk.Toplevel to a non-root CTk widget causes
            # nametowidget → _root() to fail in Python 3.14.
            root_win = self._widget.winfo_toplevel()
            self._tip = tw = tk.Toplevel(root_win)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            lbl = tk.Label(
                tw,
                text=self._text,
                bg="#1e293b",
                fg="#f1f5f9",
                relief="flat",
                font=("Segoe UI", 9),
                padx=6,
                pady=3,
            )
            lbl.pack()
        except Exception:
            self._tip = None

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._tip:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


# ---------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------


class WorkspaceShell(ctk.CTkFrame):
    """Main window shell that orchestrates all functional panels."""

    def __init__(self, parent: tk.Tk, controller: WorkspaceController) -> None:
        super().__init__(parent, fg_color="transparent")
        self.ctrl = controller
        self._root = parent
        self._last_save_time: float | None = None  # epoch seconds
        self._last_run_ok: bool | None = (
            None  # None=no run yet, True=success, False=fail
        )

        # Layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Build UI components
        self._build_top_bar()

        main = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        main.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        # Left sidebar
        self.sidebar = SidebarPanel(main, self.ctrl)
        self.sidebar.pack(fill=tk.Y, side=tk.LEFT)

        # Right inspector (fixed width)
        self.inspector = InspectorPanel(main, self.ctrl)
        self.inspector.pack(fill=tk.Y, side=tk.RIGHT)

        # Center canvas (flexible)
        self.canvas = FlowCanvas(main, self.ctrl)
        self.canvas.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # Bottom result drawer
        self.drawer = ResultDrawer(self, self.ctrl)
        self.drawer.pack(fill=tk.X, side=tk.BOTTOM)

        # Register as listener — controller calls this after start() loads data
        self.ctrl.set_state_changed_callback(self.refresh)

        # Keyboard shortcuts (registered on root to work from anywhere)
        self._bind_shortcuts()

    # ------------------------------------------------------------------
    # Top bar
    # ------------------------------------------------------------------

    def _build_top_bar(self) -> None:
        """Create the top execution and status bar."""
        parent = ctk.CTkFrame(self, height=48, corner_radius=0)
        parent.pack(fill=tk.X, side=tk.TOP)
        parent.pack_propagate(False)

        # ── Left cluster: Run/Stop, Undo/Redo ──────────────────────────
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(side=tk.LEFT, padx=T.PAD_MD)

        self.run_btn = ctk.CTkButton(
            btn_frame,
            text="▶ Run",
            width=80,
            fg_color=T.CLR_ACCENT,
            hover_color=T.CLR_ACCENT_HOVER,
            command=self.ctrl.start_run,
        )
        self.run_btn.pack(side=tk.LEFT, padx=T.PAD_XS)
        Tooltip(self.run_btn, "Run Workflow (F5)")

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏹ Stop",
            width=80,
            fg_color=T.CLR_PENDING,
            state="disabled",
            command=self.ctrl.stop_run,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=T.PAD_XS)
        Tooltip(self.stop_btn, "Stop Workflow")

        # Undo / Redo icon buttons
        self.undo_btn = ctk.CTkButton(
            btn_frame,
            text="↩",
            width=36,
            fg_color=T.CLR_SURFACE,
            hover_color=T.CLR_SELECTED,
            text_color=T.CLR_MUTED,
            state="disabled",
            command=self.ctrl.undo,
        )
        self.undo_btn.pack(side=tk.LEFT, padx=(T.PAD_SM, 0))
        Tooltip(self.undo_btn, "Undo (Ctrl+Z)")

        self.redo_btn = ctk.CTkButton(
            btn_frame,
            text="↪",
            width=36,
            fg_color=T.CLR_SURFACE,
            hover_color=T.CLR_SELECTED,
            text_color=T.CLR_MUTED,
            state="disabled",
            command=self.ctrl.redo,
        )
        self.redo_btn.pack(side=tk.LEFT, padx=(2, 0))
        Tooltip(self.redo_btn, "Redo (Ctrl+Y)")

        # ── Appearance mode toggle (far-left cluster, packs to RIGHT) ──
        self.appearance_var = ctk.StringVar(value=self.ctrl.state.appearance_mode)
        self.appearance_menu = ctk.CTkOptionMenu(
            btn_frame,
            values=["Dark", "Light", "System"],
            command=self._on_appearance_mode_change,
            variable=self.appearance_var,
            width=100,
        )
        self.appearance_menu.pack(side=tk.RIGHT, padx=T.PAD_XS)
        Tooltip(self.appearance_menu, "Change Appearance Mode")

        # ── Centre: Title + dirty indicator + status labels ────────────
        self.title_label = ctk.CTkLabel(
            parent, text="Workbench", font=T.FONT_HEADING, text_color=T.CLR_ACCENT
        )
        self.title_label.pack(side=tk.LEFT, padx=T.PAD_LG)

        self.dirty_label = ctk.CTkLabel(
            parent, text="• Unsaved", text_color=T.CLR_WARNING, font=T.FONT_SMALL
        )
        self.dirty_label.pack(side=tk.LEFT, padx=T.PAD_SM)

        self._save_status_label = ctk.CTkLabel(
            parent, text="", font=T.FONT_SMALL, text_color=T.CLR_MUTED
        )
        self._save_status_label.pack(side=tk.LEFT, padx=T.PAD_SM)

        self._run_status_label = ctk.CTkLabel(
            parent, text="", font=T.FONT_SMALL, text_color=T.CLR_MUTED
        )
        self._run_status_label.pack(side=tk.LEFT, padx=T.PAD_SM)

        # ── Progress bar (fills remaining horizontal space) ───────────
        self.progress = ctk.CTkProgressBar(
            parent,
            height=8,
            mode="indeterminate",
            progress_color=T.CLR_ACCENT,
        )
        self.progress.pack(side=tk.LEFT, padx=T.PAD_LG, fill=tk.X, expand=True)
        self.progress.set(0)

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _bind_shortcuts(self) -> None:
        """Register global keyboard shortcuts on the root window."""
        root = self._root

        def _guard_text(widget: object) -> bool:
            """Return True if widget is a text-input (shortcut should not fire)."""
            cls = getattr(getattr(widget, "__class__", None), "__name__", "")
            return cls in ("Entry", "Text", "CTkEntry", "CTkTextbox")

        def on_save(event: tk.Event) -> str | None:
            if _guard_text(event.widget):
                return None
            self._on_save()
            return "break"

        def on_undo(event: tk.Event) -> str | None:
            if _guard_text(event.widget):
                return None
            self.ctrl.undo()
            return "break"

        def on_redo(event: tk.Event) -> str | None:
            if _guard_text(event.widget):
                return None
            self.ctrl.redo()
            return "break"

        def on_run(event: tk.Event) -> str | None:
            if _guard_text(event.widget):
                return None
            if not self.ctrl.state.is_running:
                self.ctrl.start_run()
            return "break"

        root.bind("<Control-s>", on_save)
        root.bind("<Control-z>", on_undo)
        root.bind("<Control-y>", on_redo)
        root.bind("<F5>", on_run)

        # Note: Focus rings removed - CTkButton doesn't support border configuration
        # Keyboard navigation still works via shortcuts (Ctrl+S, Ctrl+Z, etc.)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        from tkinter import messagebox

        ok, msg = self.ctrl.save()
        if ok:
            self._last_save_time = time.time()
            self._update_save_label()
        else:
            messagebox.showerror("Save Failed", msg)

    @staticmethod
    def _relative_time(epoch: float) -> str:
        """Return human-readable relative time string from epoch seconds."""
        delta = int(time.time() - epoch)
        if delta < 60:
            return f"{delta}s ago"
        if delta < 3600:
            return f"{delta // 60}m ago"
        if delta < 86400:
            return f"{delta // 3600}h ago"
        return "Yesterday"

    def _update_save_label(self) -> None:
        if self._last_save_time is None:
            self._save_status_label.configure(text="")
        else:
            self._save_status_label.configure(
                text=f"Saved {self._relative_time(self._last_save_time)}",
                text_color=T.CLR_MUTED,
            )
        # Re-schedule for next minute
        self._root.after(60_000, self._update_save_label)

    # ------------------------------------------------------------------
    # Appearance
    # ------------------------------------------------------------------

    def _on_appearance_mode_change(self, mode: str) -> None:
        try:
            ctk.set_appearance_mode(mode)
            self.ctrl.update_appearance_mode(mode)
        except Exception as e:
            log.warning("Could not set appearance mode: %s", e)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Refresh all panels from current controller state."""
        state = self.ctrl.state
        self._on_state_changed(state)
        self.sidebar.refresh()
        self.inspector.refresh()
        self.canvas.refresh()
        self.drawer.refresh()

    def _on_state_changed(self, state: WorkspaceState) -> None:
        """Update shell top-bar components based on controller state."""
        # 1. Title
        wf = state.get_selected_workflow()
        wf_name = wf.name if wf else "No Workflow"
        self.title_label.configure(text=wf_name)

        # 2. Dirty indicator
        if state.is_dirty:
            self.dirty_label.pack(side=tk.LEFT, padx=T.PAD_SM)
        else:
            self.dirty_label.pack_forget()

        # 3. Run / Stop buttons + run status label
        if state.is_running:
            self.run_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal", fg_color=T.CLR_ERROR)
            self.progress.start()
            self._run_status_label.configure(text="⏳ Running…", text_color=T.CLR_MUTED)
        else:
            self.run_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled", fg_color=T.CLR_PENDING)
            self.progress.stop()
            self.progress.set(0)
            if self._last_run_ok is True:
                self._run_status_label.configure(
                    text="✓ Run complete", text_color=T.CLR_SUCCESS
                )
            elif self._last_run_ok is False:
                self._run_status_label.configure(
                    text="✕ Run failed", text_color=T.CLR_ERROR
                )
            else:
                self._run_status_label.configure(text="")

        # 4. Undo / Redo buttons
        _active_txt = "#f8fafc"
        _muted_txt = T.CLR_MUTED

        if self.ctrl.can_undo:
            self.undo_btn.configure(state="normal", text_color=_active_txt)
        else:
            self.undo_btn.configure(state="disabled", text_color=_muted_txt)

        if self.ctrl.can_redo:
            self.redo_btn.configure(state="normal", text_color=_active_txt)
        else:
            self.redo_btn.configure(state="disabled", text_color=_muted_txt)

        # 5. Sync appearance toggle
        if self.appearance_var.get() != state.appearance_mode:
            self.appearance_var.set(state.appearance_mode)
