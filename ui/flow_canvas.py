"""
ui.flow_canvas — Vertical flow cards for workflow steps.

Renders step cards in a scrollable vertical layout.
Each card shows title, model, status badge, data-flow labels,
file chip, and action context menu.
"""

from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
import customtkinter as ctk

from core.graph_utils import ROOT_SOURCE_IDS
from ui import dialogs
from ui import theme as T
from ui.workspace_controller import WorkspaceController
from ui.viewmodels import FlowEdgeVM, FlowNodeVM

WORKFLOW_INPUT_EDGE_LABEL = "Workflow input"


def _display_step_title(step) -> str:
    title = (getattr(step, "title", "") or "").strip()
    if title:
        return title
    name = (getattr(step, "name", "") or "").strip()
    if name and not re.match(r"^step_[0-9a-f]{8}$", name):
        return name
    return "Untitled step"


def incoming_peer_label(from_id: str, id_to_title: dict[str, str]) -> str:
    """Return peer label for incoming edge source id."""
    if from_id in ROOT_SOURCE_IDS:
        return WORKFLOW_INPUT_EDGE_LABEL
    label = (id_to_title.get(from_id) or "").strip()
    return label or from_id


def index_flow_edges(
    edges: list[FlowEdgeVM], nodes: list[FlowNodeVM]
) -> tuple[dict[str, list[FlowEdgeVM]], dict[str, list[FlowEdgeVM]], dict[str, str]]:
    """Group edges by target (incoming) and source (outgoing); map step id → display title."""
    id_to_title = {n.step_id: (n.title or "").strip() or "Untitled step" for n in nodes}
    edges_in: dict[str, list[FlowEdgeVM]] = {}
    edges_out: dict[str, list[FlowEdgeVM]] = {}
    for e in edges:
        edges_in.setdefault(e.to_id, []).append(e)
        edges_out.setdefault(e.from_id, []).append(e)
    return edges_in, edges_out, id_to_title


class FlowCanvas(ctk.CTkFrame):
    """Scrollable vertical list of step cards."""

    def __init__(
        self, parent: ctk.CTkFrame | tk.Widget, controller: WorkspaceController
    ) -> None:
        super().__init__(parent, fg_color=T.CLR_BG, corner_radius=0)
        self.ctrl = controller
        self._card_frames: dict[str, ctk.CTkFrame] = {}
        self._build()

    def _build(self) -> None:
        # Scrollable container
        self.inner_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.inner_frame.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Rebuild step cards from current view-model."""
        # Clear
        for w in self.inner_frame.winfo_children():
            w.destroy()
        self._card_frames.clear()

        nodes, edges = self.ctrl.get_flow_viewmodel()
        if not nodes:
            ctk.CTkLabel(
                self.inner_frame,
                text=(
                    "No steps. Click '+ New' in the sidebar to add a workflow,\n"
                    "then use '+ Add Step' below."
                ),
                font=T.FONT_BODY,
            ).pack(pady=T.PAD_XL)
        else:
            edges_in, edges_out, id_to_title = self._index_flow_edges(edges, nodes)
            for node in nodes:
                card = self._build_card(
                    self.inner_frame,
                    node,
                    nodes,
                    edges_in,
                    edges_out,
                    id_to_title,
                )
                card.pack(fill=tk.X, padx=T.PAD_LG, pady=T.PAD_SM)
                self._card_frames[node.step_id] = card

        # Add step button at bottom
        if self.ctrl.state.get_selected_workflow():
            add_frame = ctk.CTkFrame(self.inner_frame, fg_color="transparent")
            add_frame.pack(fill=tk.X, padx=T.PAD_LG, pady=T.PAD_MD)
            ctk.CTkButton(
                add_frame,
                text="+ Add Step",
                font=T.FONT_BODY,
                fg_color=T.CLR_SURFACE,
                hover_color=T.CLR_SELECTED,
                text_color="#f8fafc",
                width=120,
                command=lambda: self.ctrl.add_step_below(),
            ).pack(anchor=tk.CENTER)

    def _index_flow_edges(
        self, edges: list[FlowEdgeVM], nodes: list[FlowNodeVM]
    ) -> tuple[dict[str, list[FlowEdgeVM]], dict[str, list[FlowEdgeVM]], dict[str, str]]:
        return index_flow_edges(edges, nodes)

    def _build_card(
        self,
        parent: ctk.CTkFrame,
        node: FlowNodeVM,
        nodes: list[FlowNodeVM],
        edges_in: dict[str, list[FlowEdgeVM]],
        edges_out: dict[str, list[FlowEdgeVM]],
        id_to_title: dict[str, str],
    ) -> ctk.CTkFrame:
        sel_node_vm = next((n for n in nodes if n.is_selected), None)
        is_upstream = False
        if sel_node_vm and node.step_id in sel_node_vm.upstream_node_ids:
            is_upstream = True

        if node.is_selected:
            bg_col = T.CLR_SELECTED
            border_col = T.CLR_ACCENT
            border_width = 2
        elif is_upstream:
            bg_col = T.CLR_SURFACE
            border_col = T.CLR_WARNING
            border_width = 2
        else:
            bg_col = T.CLR_SURFACE
            border_col = T.CLR_BORDER
            border_width = 1

        card = ctk.CTkFrame(
            parent,
            fg_color=bg_col,
            border_color=border_col,
            border_width=border_width,
            corner_radius=8,
        )
        card.pack_propagate(False)

        # Let content define height; use inner padding via a nested frame.
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=T.PAD_MD, pady=T.PAD_MD)

        card.bind("<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid))
        content.bind(
            "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
        )

        # Row 1: Title + status badge
        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill=tk.X)
        row1.bind("<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid))

        title_text = node.title
        if not node.is_enabled:
            title_text = f"[Disabled] {title_text}"

        t_label = ctk.CTkLabel(
            row1,
            text=title_text,
            font=T.FONT_HEADING,
            text_color="#f8fafc" if node.is_enabled else T.CLR_MUTED,
        )
        t_label.pack(side=tk.LEFT)
        t_label.bind(
            "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
        )

        # Status badge
        badge_color = T.status_color(node.status.value)
        status_text = f" {node.status.value.upper()} "
        dur_ms = getattr(node, "duration_ms", None)
        if isinstance(dur_ms, (int, float)) and node.status.value == "success":
            status_text += f"({dur_ms / 1000:.1f}s) "

        s_badge = ctk.CTkLabel(
            row1,
            text=status_text,
            font=T.FONT_SMALL,
            fg_color=badge_color,
            text_color="#ffffff",
            corner_radius=4,
        )
        s_badge.pack(side=tk.RIGHT, padx=T.PAD_XS)
        s_badge.bind(
            "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
        )

        # Graph Badges (Right aligned, before status badge)
        mode_str = getattr(node, "execution_mode", "legacy").upper()

        exec_badge = ctk.CTkLabel(
            row1,
            text=f" [ {mode_str} ] ",
            font=T.FONT_SMALL,
            fg_color=T.CLR_BG,
            text_color=T.CLR_MUTED,
            corner_radius=4,
        )
        exec_badge.pack(side=tk.RIGHT, padx=(0, T.PAD_XS))
        exec_badge.bind(
            "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
        )

        if mode_str == "GRAPH":
            out_count = getattr(node, "output_port_count", 0)
            out_badge = ctk.CTkLabel(
                row1,
                text=f" {out_count} out ",
                font=T.FONT_SMALL,
                text_color=T.CLR_MUTED,
            )
            out_badge.pack(side=tk.RIGHT, padx=(0, 2))
            out_badge.bind(
                "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
            )

            in_count = getattr(node, "input_port_count", 0)
            in_badge = ctk.CTkLabel(
                row1, text=f" {in_count} in ", font=T.FONT_SMALL, text_color=T.CLR_MUTED
            )
            in_badge.pack(side=tk.RIGHT, padx=(0, 2))
            in_badge.bind(
                "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
            )

            # Merge/Branch badges
            if getattr(node, "is_merge", False):
                m_badge = ctk.CTkLabel(
                    row1,
                    text=" [ Join ] ",
                    font=T.FONT_SMALL,
                    fg_color=T.CLR_WARNING,
                    text_color="#1e293b",
                    corner_radius=4,
                )
                m_badge.pack(side=tk.RIGHT, padx=(0, T.PAD_XS))
                m_badge.bind(
                    "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
                )

            if getattr(node, "is_branch", False):
                b_badge = ctk.CTkLabel(
                    row1,
                    text=" [ Branch ] ",
                    font=T.FONT_SMALL,
                    fg_color=T.CLR_ACCENT,
                    text_color="#f8fafc",
                    corner_radius=4,
                )
                b_badge.pack(side=tk.RIGHT, padx=(0, T.PAD_XS))
                b_badge.bind(
                    "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
                )

        # Row 2: model + flow arrows (natural language)
        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill=tk.X, pady=(T.PAD_XS, 0))
        row2.bind("<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid))

        m_label = ctk.CTkLabel(
            row2, text=f"🤖 {node.model}", font=T.FONT_SMALL, text_color=T.CLR_MUTED
        )
        m_label.pack(side=tk.LEFT)
        m_label.bind(
            "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
        )

        # Row 3: connections from graph edges (preferred) or legacy flow labels
        incoming = edges_in.get(node.step_id, [])
        outgoing = edges_out.get(node.step_id, [])

        def _bind_select(w: tk.Widget, sid: str = node.step_id) -> None:
            def _on_click(_e: tk.Event, step_id: str = sid) -> None:
                self.ctrl.select_step(step_id)

            w.bind("<Button-1>", _on_click)

        # In simple mode, keep the natural-language sequential in/out labels visible
        # even when graph edges exist. This prevents the "1-2-3-4-5" flow labels from
        # disappearing after the user connects inputs in the inspector.
        is_advanced_mode = getattr(self.ctrl.state.mode, "value", None) == "advanced"
        show_connections = is_advanced_mode and (incoming or outgoing)

        if show_connections:
            conn = ctk.CTkFrame(content, fg_color="transparent")
            conn.pack(fill=tk.X, pady=(T.PAD_XS, 0))
            conn.bind(
                "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
            )
            head = ctk.CTkLabel(
                conn,
                text="Connections",
                font=T.FONT_SMALL,
                text_color="#94a3b8",
            )
            head.pack(anchor=tk.W)
            _bind_select(head)

            for e in sorted(
                incoming, key=lambda ed: incoming_peer_label(ed.from_id, id_to_title)
            ):
                peer = incoming_peer_label(e.from_id, id_to_title)
                et = (e.edge_type or "sequential").lower()
                line = ctk.CTkLabel(
                    conn,
                    text=f"  ↑ from: {peer}  ({et})",
                    font=T.FONT_SMALL,
                    text_color=T.CLR_MUTED,
                    justify="left",
                )
                line.pack(anchor=tk.W)
                _bind_select(line, e.from_id)

            for e in sorted(outgoing, key=lambda ed: id_to_title.get(ed.to_id, ed.to_id)):
                peer = id_to_title.get(e.to_id, e.to_id)
                et = (e.edge_type or "sequential").lower()
                line = ctk.CTkLabel(
                    conn,
                    text=f"  ↓ to: {peer}  ({et})",
                    font=T.FONT_SMALL,
                    text_color=T.CLR_MUTED,
                    justify="left",
                )
                line.pack(anchor=tk.W)
                _bind_select(line, e.to_id)
        else:
            if node.upstream_title:
                u_label = ctk.CTkLabel(
                    content,
                    text=f"↑ from: {node.upstream_title}",
                    font=T.FONT_SMALL,
                    text_color=T.CLR_MUTED,
                )
                u_label.pack(anchor=tk.W, pady=(T.PAD_XS, 0))
                _bind_select(u_label)

            if node.downstream_title:
                d_label = ctk.CTkLabel(
                    content,
                    text=f"↓ to: {node.downstream_title}",
                    font=T.FONT_SMALL,
                    text_color=T.CLR_MUTED,
                )
                d_label.pack(anchor=tk.W)
                _bind_select(d_label)

        if node.purpose:
            p_label = ctk.CTkLabel(
                content,
                text=node.purpose,
                font=T.FONT_SMALL,
                text_color=T.CLR_MUTED,
                wraplength=400,
                justify="left",
            )
            p_label.pack(fill=tk.X, pady=(T.PAD_XS, 0), anchor=tk.W)
            p_label.bind(
                "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
            )

        # Row 4: file chips (clickable badge — Gap 3)
        row_att = ctk.CTkFrame(content, fg_color="transparent")
        row_att.pack(fill=tk.X, pady=(T.PAD_XS, 0))
        row_att.bind(
            "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
        )

        if node.missing_required:
            badge_text = "⚠ Missing Required Files"
            badge_color = T.CLR_ERROR
        elif node.has_files:
            badge_text = f"📎 {node.file_count} file(s)"
            badge_color = T.CLR_ACCENT
        else:
            badge_text = "📎 Attached files"
            badge_color = T.CLR_MUTED

        badge = ctk.CTkLabel(
            row_att,
            text=badge_text,
            font=T.FONT_SMALL,
            text_color=badge_color,
            cursor="hand2",
        )
        badge.pack(side=tk.LEFT)
        badge.bind(
            "<Button-1>",
            lambda e, sid=node.step_id: self._show_attachment_modal(sid),
        )

        # Row 5: output preview (results view)
        if node.output_preview:
            out_label = ctk.CTkLabel(
                content,
                text=f"Output: {node.output_preview}",
                font=T.FONT_SMALL,
                text_color=T.CLR_MUTED,
                wraplength=400,
                justify="left",
            )
            out_label.pack(fill=tk.X, pady=(T.PAD_XS, 0), anchor=tk.W)
            out_label.bind(
                "<Button-1>", lambda e, sid=node.step_id: self.ctrl.select_step(sid)
            )

        # Context menu
        card.bind(
            "<Button-3>", lambda e, sid=node.step_id: self._show_context_menu(e, sid)
        )
        for child in content.winfo_children():
            child.bind(
                "<Button-3>",
                lambda e, sid=node.step_id: self._show_context_menu(e, sid),
            )
            for grandchild in child.winfo_children():
                grandchild.bind(
                    "<Button-3>",
                    lambda e, sid=node.step_id: self._show_context_menu(e, sid),
                )

        return card

    def _show_context_menu(self, event, step_id: str) -> None:
        menu = tk.Menu(
            self,
            tearoff=0,
            bg=T.CLR_SURFACE,
            fg="#f8fafc",
            activebackground=T.CLR_SELECTED,
            activeforeground="#ffffff",
        )
        menu.add_command(
            label="Add Below", command=lambda: self.ctrl.add_step_below(step_id)
        )
        menu.add_command(
            label="Duplicate", command=lambda: self.ctrl.duplicate_step(step_id)
        )
        menu.add_separator()
        menu.add_command(
            label="⬆ Move Up",
            command=lambda: self.ctrl.move_step(step_id, "up"),
        )
        menu.add_command(
            label="⬇ Move Down",
            command=lambda: self.ctrl.move_step(step_id, "down"),
        )
        menu.add_separator()
        menu.add_command(
            label="Delete", command=lambda: self._confirm_delete_step(step_id)
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ------------------------------------------------------------------
    # Delete confirmation
    # ------------------------------------------------------------------

    def _confirm_delete_step(self, step_id: str) -> None:
        step = self.ctrl.state.get_step_by_id(step_id)
        name = _display_step_title(step) if step else "Untitled step"
        if dialogs.ask_yes_no(
            "Delete Step",
            f"Delete step '{name}'?\n\nThis action cannot be undone.",
            icon="warning",
            parent=self.winfo_toplevel(),
        ):
            self.ctrl.delete_step(step_id)

    # ------------------------------------------------------------------
    # Attachment modal (Gap 3)
    # ------------------------------------------------------------------

    def _show_attachment_modal(self, step_id: str) -> None:
        """Open a modal to manage file attachments for a step."""
        wf = self.ctrl.state.get_selected_workflow()
        if not wf:
            return
        step = next((s for s in wf.steps if s.id == step_id), None)
        if not step:
            return

        modal = ctk.CTkToplevel(self)
        modal.title(f"Attachments — {_display_step_title(step)}")
        modal.geometry("560x520")
        modal.transient(self.winfo_toplevel())
        modal.grab_set()
        modal.resizable(False, False)

        self._build_modal_content(modal, step_id)

    def _build_modal_content(self, modal: ctk.CTkToplevel, step_id: str) -> None:
        """Build (or rebuild) the modal content frame with slot-based keys."""
        for w in modal.winfo_children():
            w.destroy()

        content = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=T.PAD_LG, pady=T.PAD_LG)

        step = self.ctrl.state.get_step_by_id(step_id)
        if not step:
            return

        bindings = self.ctrl.state.attachment_bindings

        is_advanced_mode = getattr(self.ctrl.state.mode, "value", None) == "advanced"
        if not is_advanced_mode:
            ctk.CTkLabel(content, text="Tệp đính kèm", font=T.FONT_HEADING).pack(
                anchor=tk.W, pady=(0, 6)
            )

            if step.attachments:
                chosen = next(
                    (
                        s
                        for s in step.attachments
                        if s.required and not bindings.get(f"{step_id}::{s.slot_id}")
                    ),
                    step.attachments[0],
                )
                target_slot_key = f"{step_id}::{chosen.slot_id}"
            else:
                slot_id = self.ctrl.add_attachment_slot(
                    step_id, label="Tệp đính kèm", required=False
                )
                target_slot_key = f"{step_id}::{slot_id}"

            raw_attached_paths = [
                bindings.get(f"{step_id}::{s.slot_id}") for s in step.attachments
            ]
            attached_paths = [
                p for p in raw_attached_paths if isinstance(p, str) and p
            ]

            status = "Chưa có tệp nào được đính kèm."
            if len(attached_paths) == 1:
                status = f"Đã đính kèm: {Path(attached_paths[0]).name}"
            elif len(attached_paths) > 1:
                status = f"Đã đính kèm: {len(attached_paths)} tệp"

            ctk.CTkLabel(
                content, text=status, text_color=T.CLR_MUTED, font=T.FONT_BODY
            ).pack(anchor=tk.W, pady=(0, 10))

            btn_text = "Thay tệp" if attached_paths else "Đính kèm tệp"
            ctk.CTkButton(
                content,
                text=btn_text,
                fg_color=T.CLR_SELECTED,
                hover_color=T.CLR_BORDER,
                text_color="#f8fafc",
                command=lambda k=target_slot_key, m=modal, s=step_id: self._attach_from_modal(
                    k, m, s
                ),
            ).pack(anchor=tk.W)
            return

        if not step.attachments:
            ctk.CTkLabel(
                content,
                text="No files expected for this step.",
                text_color=T.CLR_MUTED,
                font=T.FONT_BODY,
            ).pack(pady=12)
            ctk.CTkButton(
                content,
                text="+ Add File Slot",
                fg_color=T.CLR_SELECTED,
                hover_color=T.CLR_BORDER,
                text_color="#f8fafc",
                command=lambda sid=step_id, m=modal: self._add_slot_and_refresh(m, sid),
            ).pack(anchor=tk.W, pady=(0, 6))
        else:
            ctk.CTkLabel(
                content, text="Required / Optional Files:", font=T.FONT_HEADING
            ).pack(anchor=tk.W, pady=(0, 6))
            for slot in step.attachments:
                slot_key = f"{step_id}::{slot.slot_id}"
                path = bindings.get(slot_key)

                slot_box = ctk.CTkFrame(content, fg_color=T.CLR_SURFACE, corner_radius=6)
                slot_box.pack(fill=tk.X, pady=4)

                header = ctk.CTkFrame(slot_box, fg_color="transparent")
                header.pack(fill=tk.X, padx=T.PAD_SM, pady=(T.PAD_SM, 2))
                ctk.CTkLabel(
                    header,
                    text=f"Slot: {slot.slot_id}",
                    font=T.FONT_SMALL,
                    text_color=T.CLR_MUTED,
                ).pack(side=tk.LEFT)

                meta = ctk.CTkFrame(slot_box, fg_color="transparent")
                meta.pack(fill=tk.X, padx=T.PAD_SM, pady=(2, 2))

                ctk.CTkLabel(meta, text="Label", width=96, anchor="w").grid(
                    row=0, column=0, sticky="w", padx=(0, 4)
                )
                label_entry = ctk.CTkEntry(
                    meta, fg_color=T.CLR_BG, border_color=T.CLR_BORDER
                )
                label_entry.insert(0, slot.label or "")
                label_entry.grid(row=0, column=1, sticky="ew", padx=(0, T.PAD_SM))

                ctk.CTkLabel(meta, text="Variable", width=96, anchor="w").grid(
                    row=1, column=0, sticky="w", padx=(0, 4), pady=(4, 0)
                )
                var_entry = ctk.CTkEntry(
                    meta, fg_color=T.CLR_BG, border_color=T.CLR_BORDER
                )
                var_entry.insert(0, slot.variable_name or "")
                var_entry.grid(
                    row=1, column=1, sticky="ew", padx=(0, T.PAD_SM), pady=(4, 0)
                )

                ctk.CTkLabel(meta, text="Accepted types", width=96, anchor="nw").grid(
                    row=2, column=0, sticky="nw", padx=(0, 4), pady=(4, 0)
                )
                types_entry = ctk.CTkEntry(
                    meta,
                    placeholder_text="pdf, docx, txt (comma-separated)",
                    fg_color=T.CLR_BG,
                    border_color=T.CLR_BORDER,
                )
                if slot.accepted_types:
                    types_entry.insert(0, ", ".join(slot.accepted_types))
                types_entry.grid(
                    row=2, column=1, sticky="ew", padx=(0, T.PAD_SM), pady=(4, 0)
                )
                meta.grid_columnconfigure(1, weight=1)

                req_row = ctk.CTkFrame(slot_box, fg_color="transparent")
                req_row.pack(fill=tk.X, padx=T.PAD_SM, pady=(0, 2))
                req_var = tk.BooleanVar(value=bool(slot.required))
                ctk.CTkCheckBox(req_row, text="Required", variable=req_var).pack(
                    side=tk.LEFT
                )

                actions = ctk.CTkFrame(slot_box, fg_color="transparent")
                actions.pack(fill=tk.X, padx=T.PAD_SM, pady=(0, 2))

                def _on_apply(
                    _m=modal,
                    _sid=step_id,
                    _sl_id=slot.slot_id,
                    _le=label_entry,
                    _ve=var_entry,
                    _te=types_entry,
                    _rv=req_var,
                ) -> None:
                    self._apply_slot_and_refresh(
                        _m,
                        _sid,
                        _sl_id,
                        _le.get(),
                        _ve.get(),
                        _rv.get(),
                        _te.get(),
                    )

                def _on_remove_slot(
                    _m=modal, _sid=step_id, _sl_id=slot.slot_id
                ) -> None:
                    self._remove_slot_and_refresh(_m, _sid, _sl_id)

                ctk.CTkButton(
                    actions,
                    text="Apply",
                    width=72,
                    fg_color=T.CLR_SELECTED,
                    hover_color=T.CLR_BORDER,
                    text_color="#f8fafc",
                    command=_on_apply,
                ).pack(side=tk.LEFT, padx=(0, T.PAD_XS))
                ctk.CTkButton(
                    actions,
                    text="Remove slot",
                    width=96,
                    fg_color=T.CLR_ERROR,
                    hover_color="#dc2626",
                    command=_on_remove_slot,
                ).pack(side=tk.LEFT, padx=T.PAD_XS)

                file_row = ctk.CTkFrame(slot_box, fg_color="transparent")
                file_row.pack(fill=tk.X, padx=T.PAD_SM, pady=(0, T.PAD_SM))
                ctk.CTkLabel(
                    file_row, text="File:", width=96, anchor="w", font=T.FONT_BODY
                ).pack(side=tk.LEFT)
                if isinstance(path, str) and path:
                    fname = Path(path).name
                    is_missing = not Path(path).is_file()
                    label_text = f"⚠ Missing: {fname}" if is_missing else f"✓ {fname}"
                    ctk.CTkLabel(
                        file_row,
                        text=label_text,
                        font=T.FONT_BODY,
                        text_color=T.CLR_ERROR if is_missing else T.CLR_MUTED,
                    ).pack(side=tk.LEFT, padx=T.PAD_XS)
                    ctk.CTkButton(
                        file_row,
                        text="Clear file",
                        width=84,
                        fg_color=T.CLR_BG,
                        hover_color=T.CLR_BORDER,
                        command=lambda k=slot_key, m=modal, s=step_id: self._remove_and_refresh(
                            k, m, s
                        ),
                    ).pack(side=tk.RIGHT)
                else:
                    ctk.CTkButton(
                        file_row,
                        text="📎 Attach",
                        width=84,
                        fg_color=T.CLR_SELECTED,
                        hover_color=T.CLR_BORDER,
                        text_color="#f8fafc",
                        command=lambda k=slot_key, m=modal, s=step_id: self._attach_from_modal(
                            k, m, s
                        ),
                    ).pack(side=tk.LEFT, padx=T.PAD_XS)

            ctk.CTkButton(
                content,
                text="+ Add File Slot",
                fg_color=T.CLR_SELECTED,
                hover_color=T.CLR_BORDER,
                text_color="#f8fafc",
                command=lambda sid=step_id, m=modal: self._add_slot_and_refresh(m, sid),
            ).pack(anchor=tk.W, pady=(6, 2))

        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(fill=tk.X, pady=(12, 0), side=tk.BOTTOM)
        ctk.CTkButton(
            btn_row,
            text="Close",
            font=T.FONT_BODY,
            fg_color=T.CLR_SURFACE,
            hover_color=T.CLR_SELECTED,
            command=modal.destroy,
        ).pack(side=tk.RIGHT)

    def _remove_and_refresh(
        self, key: str, modal: ctk.CTkToplevel, step_id: str
    ) -> None:
        """Remove an attachment binding and refresh the modal in-place."""
        self.ctrl.remove_attachment_binding(key)
        self._build_modal_content(modal, step_id)

    def _attach_from_modal(
        self, slot_key: str, modal: ctk.CTkToplevel, step_id: str
    ) -> None:
        """Open file picker from modal, bind file, then refresh modal."""
        path = filedialog.askopenfilename(
            parent=modal,
            title="Attach file to this step",
            filetypes=[
                ("Documents", "*.pdf *.docx *.txt *.md *.csv *.xlsx *.pptx"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.ctrl.update_attachment_binding(slot_key, path)
            self._build_modal_content(modal, step_id)

    def _add_slot_and_refresh(self, modal: ctk.CTkToplevel, step_id: str) -> None:
        self.ctrl.add_attachment_slot(step_id)
        self._build_modal_content(modal, step_id)

    def _apply_slot_and_refresh(
        self,
        modal: ctk.CTkToplevel,
        step_id: str,
        slot_id: str,
        label: str,
        variable_name: str,
        required: bool,
        accepted_types_raw: str,
    ) -> None:
        raw = (accepted_types_raw or "").strip()
        if raw:
            accepted_types = [part.strip() for part in raw.split(",") if part.strip()]
            self.ctrl.update_attachment_slot(
                step_id,
                slot_id,
                label=label,
                variable_name=variable_name,
                required=required,
                accepted_types=accepted_types,
            )
        else:
            self.ctrl.update_attachment_slot(
                step_id,
                slot_id,
                label=label,
                variable_name=variable_name,
                required=required,
                accepted_types_clear=True,
            )
        self._build_modal_content(modal, step_id)

    def _remove_slot_and_refresh(
        self, modal: ctk.CTkToplevel, step_id: str, slot_id: str
    ) -> None:
        self.ctrl.remove_attachment_slot(step_id, slot_id)
        self._build_modal_content(modal, step_id)
