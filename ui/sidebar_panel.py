"""
ui.sidebar_panel — Left sidebar: workflow list, create/duplicate, recent runs.
"""

from __future__ import annotations

import tkinter as tk
import customtkinter as ctk

from ui import theme as T
from ui import dialogs
from ui.workspace_controller import WorkspaceController

_PAGE_SIZE = 20


class SidebarPanel(ctk.CTkFrame):
    """Left sidebar with workflow list and recent runs."""

    WIDTH = 200

    def __init__(
        self, parent: ctk.CTkFrame | tk.Widget, controller: WorkspaceController
    ) -> None:
        super().__init__(
            parent, width=self.WIDTH, fg_color=T.CLR_SIDEBAR_BG, corner_radius=0
        )
        self.ctrl = controller
        self.pack_propagate(False)
        self._run_page: int = 1  # how many pages loaded (each page = PAGE_SIZE)
        self._build()

    def _build(self) -> None:
        # Section: Workflows
        ctk.CTkLabel(
            self, text="Workflows", font=T.FONT_HEADING, text_color=T.CLR_SIDEBAR_FG
        ).pack(anchor=tk.W, padx=T.PAD_MD, pady=(T.PAD_MD, T.PAD_XS))

        # ── Search box ──────────────────────────────────────────────────
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill=tk.X, padx=T.PAD_SM, pady=(0, T.PAD_XS))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_wf_filter())
        self._search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Search workflows…",
            textvariable=self._search_var,
            height=28,
            corner_radius=6,
            font=T.FONT_SMALL,
        )
        self._search_entry.pack(fill=tk.X)

        # ── Workflow list ─────────────────────────────────────────────
        self.wf_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            label_font=T.FONT_BODY,
            scrollbar_button_color=T.CLR_SURFACE,
        )
        self.wf_container.pack(
            fill=tk.BOTH, expand=True, padx=T.PAD_SM, pady=(0, T.PAD_SM)
        )

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=T.PAD_SM, pady=(0, T.PAD_SM))

        ctk.CTkButton(
            btn_frame,
            text="+ New",
            command=self._on_new,
            fg_color=T.BTN_FG,
            hover_color=T.BTN_HOVER,
            text_color="#f8fafc",
            width=50,
        ).pack(side=tk.LEFT)

        ctk.CTkButton(
            btn_frame,
            text="⧉ Clone",
            command=self._on_clone,
            fg_color="transparent",
            border_width=1,
            border_color=T.BORDER_COLOR,
            hover_color=T.BTN_HOVER,
            text_color="#f8fafc",
            width=50,
        ).pack(side=tk.LEFT, padx=T.PAD_XS)

        ctk.CTkButton(
            btn_frame,
            text="🗑 Delete",
            command=self._on_delete,
            fg_color="transparent",
            border_width=1,
            border_color=T.CLR_ERROR,
            hover_color="#450a0a",
            text_color=T.CLR_ERROR,
            width=50,
        ).pack(side=tk.LEFT)

        # Separator
        ctk.CTkFrame(self, height=1, fg_color=T.BORDER_COLOR, corner_radius=0).pack(
            fill=tk.X, padx=T.PAD_SM, pady=T.PAD_SM
        )

        # Save Indicator
        self.save_status = ctk.CTkLabel(
            self,
            text="✓ Auto-saved",
            font=T.FONT_META,
            text_color=T.CLR_MUTED,
        )
        self.save_status.pack(pady=(0, T.PAD_SM))

        # Section: Recent Runs
        ctk.CTkLabel(
            self, text="Recent Runs", font=T.FONT_TITLE, text_color=T.CLR_SIDEBAR_FG
        ).pack(anchor=tk.W, padx=T.PAD_MD, pady=(0, T.PAD_SM))

        self.run_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            height=150,
            scrollbar_button_color=T.CLR_SURFACE,
        )
        self.run_container.pack(
            fill=tk.BOTH, expand=True, padx=T.PAD_SM, pady=(0, T.PAD_SM)
        )

        self._wf_cards: dict[str, ctk.CTkFrame] = {}
        self._run_cards: dict[str, ctk.CTkFrame] = {}

        # Experimental features (Bottom)
        exp_frame = ctk.CTkFrame(self, fg_color="transparent")
        exp_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=T.PAD_MD, pady=T.PAD_MD)

        self._graph_var = ctk.BooleanVar(value=self.ctrl.state.enable_graph_runtime)

        def on_graph_toggle(*args):
            self.ctrl.set_graph_runtime_enabled(self._graph_var.get())

        self._graph_var.trace_add("write", on_graph_toggle)

        ctk.CTkSwitch(
            exp_frame,
            text="Graph Runtime (Beta)",
            variable=self._graph_var,
            font=T.FONT_SMALL,
            text_color=T.CLR_WARNING,
        ).pack(anchor=tk.W)

    # ------------------------------------------------------------------
    # Filter helpers
    # ------------------------------------------------------------------

    def _apply_wf_filter(self) -> None:
        """Show/hide workflow cards based on search text (no full refresh)."""
        query = self._search_var.get().lower()
        state = self.ctrl.state
        for wf_id, card in self._wf_cards.items():
            wf = state.workflow_drafts.get(wf_id)
            name = (wf.name or wf.id).lower() if wf else wf_id.lower()
            if query in name:
                card.pack(fill=tk.X, pady=T.PAD_XS)
            else:
                card.pack_forget()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        state = self.ctrl.state

        # ── Workflow list ─────────────────────────────────────────────
        for child in self.wf_container.winfo_children():
            child.destroy()
        self._wf_cards.clear()

        query = self._search_var.get().lower()
        for wf_id, wf in state.workflow_drafts.items():
            is_sel = wf_id == state.selected_workflow_id
            name = wf.name or wf.id
            visible = query in name.lower()

            card = ctk.CTkFrame(
                self.wf_container,
                fg_color=T.CARD_SELECTED if is_sel else "transparent",
                corner_radius=4,
                cursor="hand2",
            )
            if visible:
                card.pack(fill=tk.X, pady=T.PAD_XS)

            label = ctk.CTkLabel(
                card,
                text=name,
                font=T.FONT_MAIN,
                text_color="#f8fafc" if is_sel else T.CLR_SIDEBAR_FG,
            )
            label.pack(side=tk.LEFT, padx=T.PAD_SM, pady=T.PAD_SM)

            for widget in (card, label):
                widget.bind(
                    "<Button-1>", lambda e, wid=wf_id: self.ctrl.select_workflow(wid)
                )
                widget.bind(
                    "<Button-3>",
                    lambda e, wid=wf_id: self._show_workflow_context_menu(e, wid),
                )
                widget.bind(
                    "<Double-Button-1>",
                    lambda e, wid=wf_id: self._show_workflow_rename_modal(wid),
                )

            self._wf_cards[wf_id] = card

        # ── Recent runs (paginated) ────────────────────────────────────
        for child in self.run_container.winfo_children():
            child.destroy()
        self._run_cards.clear()

        all_runs = self.ctrl.load_run_history()
        visible_count = self._run_page * _PAGE_SIZE
        shown = all_runs[:visible_count]
        remaining = max(0, len(all_runs) - visible_count)

        for run in shown:
            run_id = run["run_id"]
            is_sel = (
                run_id == state.selected_run_id
                if hasattr(state, "selected_run_id")
                else False
            )

            card = ctk.CTkFrame(
                self.run_container,
                fg_color=T.CARD_SELECTED if is_sel else "transparent",
                corner_radius=4,
                cursor="hand2",
            )
            card.pack(fill=tk.X, pady=T.PAD_XS)

            status_char = (
                "✓"
                if run["status"] == "success"
                else "✗"
                if run["status"] == "error"
                else "⏳"
            )
            label_text = f"{status_char} {run['started'][11:16]} Run"

            label = ctk.CTkLabel(
                card,
                text=label_text,
                font=T.FONT_META,
                text_color=T.status_color(run["status"]),
            )
            label.pack(side=tk.LEFT, padx=T.PAD_SM, pady=T.PAD_XS)

            for widget in (card, label):
                widget.bind(
                    "<Button-1>", lambda e, rid=run_id: self.ctrl.select_run(rid)
                )

            self._run_cards[run_id] = card

        # "Load more" button
        if remaining > 0:
            ctk.CTkButton(
                self.run_container,
                text=f"Load {min(remaining, _PAGE_SIZE)} more ({remaining} left)…",
                fg_color="transparent",
                border_width=1,
                border_color=T.BORDER_COLOR,
                hover_color=T.CLR_SURFACE,
                text_color=T.CLR_MUTED,
                font=T.FONT_META,
                command=self._load_more_runs,
            ).pack(fill=tk.X, pady=T.PAD_XS)

        # Dynamic save status
        if state.is_dirty:
            self.save_status.configure(text="● Modified", text_color=T.CLR_WARNING)
        else:
            self.save_status.configure(text="✓ Auto-saved", text_color=T.CLR_MUTED)

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def _load_more_runs(self) -> None:
        self._run_page += 1
        self.refresh()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_wf_select(self, event) -> None:
        pass

    def _on_new(self) -> None:
        self.ctrl.create_workflow()

    def _on_clone(self) -> None:
        self.ctrl.duplicate_workflow()

    def _on_delete(self) -> None:
        if self.ctrl.state.selected_workflow_id:
            self.ctrl.delete_workflow(self.ctrl.state.selected_workflow_id)

    def _on_run_select(self, event) -> None:
        pass

    # ------------------------------------------------------------------
    # Workflow rename UI (context menu + double-click)
    # ------------------------------------------------------------------

    def _show_workflow_context_menu(self, event: tk.Event, workflow_id: str) -> None:
        def _on_rename() -> None:
            self._show_workflow_rename_modal(workflow_id)

        menu = tk.Menu(
            self,
            tearoff=0,
            bg=T.CLR_SURFACE,
            fg="#f8fafc",
            activebackground=T.CLR_SELECTED,
            activeforeground="#ffffff",
        )
        menu.add_command(label="Rename", command=_on_rename)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _show_workflow_rename_modal(self, workflow_id: str) -> None:
        wf = self.ctrl.state.workflow_drafts.get(workflow_id)
        initial_name = (wf.name or wf.id) if wf else workflow_id

        modal = ctk.CTkToplevel(self)
        modal.title("Rename Workflow")
        modal.geometry("420x170")
        modal.transient(self.winfo_toplevel())
        modal.grab_set()
        modal.resizable(False, False)

        name_var = tk.StringVar(value=initial_name)

        ctk.CTkLabel(
            modal, text="Workflow name:", font=T.FONT_BODY, anchor="w"
        ).pack(fill=tk.X, padx=T.PAD_LG, pady=(T.PAD_LG, 0))

        entry = ctk.CTkEntry(modal, textvariable=name_var, width=320)
        entry.pack(fill=tk.X, padx=T.PAD_LG, pady=(6, 0))
        entry.select_range(0, tk.END)
        entry.focus_set()

        btn_row = ctk.CTkFrame(modal, fg_color="transparent")
        btn_row.pack(fill=tk.X, padx=T.PAD_LG, pady=(T.PAD_LG, 0))

        def _on_cancel() -> None:
            modal.destroy()

        def _on_submit() -> None:
            new_name = (name_var.get() or "").strip()
            if not new_name:
                dialogs.show_error(
                    "Rename Workflow", "Tên workflow không được để trống."
                )
                return

            ok = self.ctrl.rename_workflow(workflow_id, new_name)
            if not ok:
                dialogs.show_error(
                    "Rename Workflow",
                    "Không thể đổi tên workflow (tên không hợp lệ hoặc không có thay đổi).",
                )
                return

            modal.destroy()

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=100,
            fg_color=T.CLR_SURFACE,
            hover_color=T.CLR_BORDER,
            command=_on_cancel,
            font=T.FONT_BODY,
        ).pack(side=tk.LEFT, padx=(0, T.PAD_SM))

        ctk.CTkButton(
            btn_row,
            text="Rename",
            width=110,
            fg_color=T.CLR_SELECTED,
            hover_color=T.CLR_BORDER,
            text_color="#f8fafc",
            command=_on_submit,
            font=T.FONT_BODY,
        ).pack(side=tk.RIGHT)
