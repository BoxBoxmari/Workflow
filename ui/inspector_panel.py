"""
ui.inspector_panel — Right inspector for editing the selected step.

No-code experience:
  - Two prompt sections: AI Role (system) + Task (user)
  - Attachment button integrated into Task section
  - Technical fields (model, input/output mapping, version) hidden by default
  - All edits route through WorkspaceController
"""

from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
import customtkinter as ctk

from core.graph_utils import ROOT_SOURCE_IDS
from ui import theme as T
from ui.viewmodels import StepInspectorVM
from ui.workspace_controller import WorkspaceController

# Combo label for workflow root sources; persisted SourceRef uses CANONICAL_WORKFLOW_ROOT_STEP_ID.
INSPECTOR_ROOT_SOURCE_DISPLAY = "Workflow input"
CANONICAL_WORKFLOW_ROOT_STEP_ID = "__input__"
# New input port: optional wiring; persisted graph uses empty sources when unset.
NO_SOURCE_LABEL = "-- No source --"

# Parses combo display strings like "My Step (step_2)" → title group + id group.
_TITLE_ID_SUFFIX_RE = re.compile(r"^(.+) \(([^)]+)\)$")


def parse_title_id_suffix(display: str) -> tuple[str, str] | None:
    """Parse combo strings like ``Title (step_id)`` into ``(title, id)``, or ``None``."""
    m = _TITLE_ID_SUFFIX_RE.match((display or "").strip())
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


def canonical_source_step_id_from_combo(combo_or_id: str) -> str:
    """Map inspector source combo text or raw id to persisted graph ``step_id``."""
    s = (combo_or_id or "").strip()
    if not s or s == "(no source step)" or s == NO_SOURCE_LABEL:
        return ""
    if s == INSPECTOR_ROOT_SOURCE_DISPLAY or s in ROOT_SOURCE_IDS:
        return CANONICAL_WORKFLOW_ROOT_STEP_ID
    m = _TITLE_ID_SUFFIX_RE.match(s)
    if m:
        inner = m.group(2).strip()
        if inner in ROOT_SOURCE_IDS:
            return CANONICAL_WORKFLOW_ROOT_STEP_ID
        return inner
    return s


def normalized_source_ref_from_choice(
    source_step_choice: str, source_port_choice: str = ""
) -> tuple[str, str]:
    """Return canonical ``(step_id, port)`` with root-input port guarantees."""
    canonical_step = canonical_source_step_id_from_combo(source_step_choice)
    if not canonical_step:
        return "", ""
    if canonical_step == CANONICAL_WORKFLOW_ROOT_STEP_ID:
        return CANONICAL_WORKFLOW_ROOT_STEP_ID, "input"
    port = (source_port_choice or "").strip() or "output"
    return canonical_step, port


def _step_base_title(step) -> str:
    """Display base for a step: title → name → id (non-empty first)."""
    for attr in ("title", "name", "id"):
        v = getattr(step, attr, None)
        if v is not None and str(v).strip():
            return str(v).strip()
    return step.id or ""


JOIN_STRATEGY_LABEL_TO_VALUE = {
    "Use first available": "first",
    "Combine all (list)": "concat",
    "Combine by source name": "json_map",
}
JOIN_STRATEGY_VALUE_TO_LABEL = {
    value: label for label, value in JOIN_STRATEGY_LABEL_TO_VALUE.items()
}


def join_strategy_to_label(strategy: str) -> str:
    """Translate canonical join strategy to user-facing label."""
    return JOIN_STRATEGY_VALUE_TO_LABEL.get(strategy, "Use first available")


def join_strategy_to_value(label_or_value: str) -> str:
    """Accept label input from UI and normalize to canonical value."""
    return JOIN_STRATEGY_LABEL_TO_VALUE.get(label_or_value, label_or_value)


class InspectorPanel(ctk.CTkFrame):
    """Right-side inspector for the selected step — no-code mode."""

    WIDTH = 320

    def __init__(
        self, parent: ctk.CTkFrame | tk.Widget, controller: WorkspaceController
    ) -> None:
        super().__init__(
            parent, width=self.WIDTH, fg_color=T.CLR_SURFACE, corner_radius=0
        )
        self.ctrl = controller
        self.pack_propagate(False)
        self._current_step_id: str | None = None
        self._current_exec_mode: str | None = None
        self._suppress_trace = False
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.inner = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        p = self.inner
        pad = {"padx": T.PAD_MD, "anchor": tk.W}

        # Header
        self.header_label = ctk.CTkLabel(
            p, text="No step selected", font=T.FONT_HEADING
        )
        self.header_label.pack(fill=tk.X, **pad, pady=(T.PAD_MD, T.PAD_SM))

        # Title
        ctk.CTkLabel(p, text="Title", font=T.FONT_BODY).pack(**pad, pady=(T.PAD_SM, 0))
        self.title_var = ctk.StringVar()
        self.title_entry = ctk.CTkEntry(
            p, textvariable=self.title_var, fg_color=T.CLR_BG, border_color=T.CLR_BORDER
        )
        self.title_entry.pack(fill=tk.X, padx=T.PAD_MD)
        self.title_var.trace_add(
            "write", lambda *a: self._on_field_change("title", self.title_var.get())
        )

        # Purpose
        ctk.CTkLabel(p, text="Purpose", font=T.FONT_BODY).pack(
            **pad, pady=(T.PAD_SM, 0)
        )
        self.purpose_var = ctk.StringVar()
        self.purpose_entry = ctk.CTkEntry(
            p,
            textvariable=self.purpose_var,
            fg_color=T.CLR_BG,
            border_color=T.CLR_BORDER,
        )
        self.purpose_entry.pack(fill=tk.X, padx=T.PAD_MD)
        self.purpose_var.trace_add(
            "write", lambda *a: self._on_field_change("purpose", self.purpose_var.get())
        )

        # Model
        ctk.CTkLabel(p, text="AI Model", font=T.FONT_BODY).pack(
            **pad, pady=(T.PAD_SM, 0)
        )
        self.model_var = ctk.StringVar()
        models = self.ctrl.config_service.load_models(capability_filter="chat")
        self.model_combo = ctk.CTkComboBox(
            p,
            variable=self.model_var,
            values=models,
            state="readonly",
            fg_color=T.CLR_BG,
            border_color=T.CLR_BORDER,
        )
        self.model_combo.pack(fill=tk.X, padx=T.PAD_MD)
        self.model_var.trace_add(
            "write", lambda *a: self._on_field_change("model", self.model_var.get())
        )
        self.model_warning = ctk.CTkLabel(
            p,
            text="⚠️ Invalid model catalog ID",
            font=T.FONT_SMALL,
            text_color=T.CLR_ERROR,
            anchor="w",
        )

        # ── AI Role ──────────────────────────────────────────────────
        ctk.CTkLabel(p, text="🤖  AI Role", font=T.FONT_BODY).pack(
            **pad, pady=(T.PAD_MD, 0)
        )
        ctk.CTkLabel(
            p,
            text="Who is the AI? What expertise does it bring?",
            font=T.FONT_BODY,
            text_color=T.CLR_MUTED,
            wraplength=260,
        ).pack(**pad)

        # Use standard Text widget for multiline editing because CTkTextbox can be quirky.
        # We will use ctk.CTkTextbox
        self.role_text = ctk.CTkTextbox(
            p,
            height=80,
            font=T.FONT_MONO,
            fg_color=T.CLR_BG,
            border_color=T.CLR_BORDER,
            border_width=1,
            wrap=tk.WORD,
        )
        self.role_text.pack(fill=tk.X, padx=T.PAD_MD, pady=(T.PAD_XS, 0))
        self.role_text.bind("<KeyRelease>", self._on_role_change)

        # ── Task ─────────────────────────────────────────────────────
        task_header = ctk.CTkFrame(p, fg_color="transparent")
        task_header.pack(fill=tk.X, padx=T.PAD_MD, pady=(T.PAD_MD, 0))
        ctk.CTkLabel(task_header, text="📋  Task", font=T.FONT_BODY).pack(side=tk.LEFT)

        ctk.CTkLabel(
            p,
            text="What should the AI do? Be specific.",
            font=T.FONT_BODY,
            text_color=T.CLR_MUTED,
            wraplength=260,
        ).pack(**pad)
        self.task_text = ctk.CTkTextbox(
            p,
            height=140,
            font=T.FONT_MONO,
            fg_color=T.CLR_BG,
            border_color=T.CLR_BORDER,
            border_width=1,
            wrap=tk.WORD,
        )
        self.task_text.pack(fill=tk.X, padx=T.PAD_MD, pady=(T.PAD_XS, 0))
        self.task_text.bind("<KeyRelease>", self._on_task_change)

        # Attachment badge
        self.att_badge_frame = ctk.CTkFrame(p, fg_color="transparent")
        self.att_badge_frame.pack(fill=tk.X, padx=T.PAD_MD, pady=(T.PAD_MD, T.PAD_MD))

        # IO Container (Input/Output setup)
        self.io_container = ctk.CTkFrame(p, fg_color="transparent")
        self.io_container.pack(fill=tk.X, padx=T.PAD_MD, pady=(0, 0))

        self.input_var = ctk.StringVar()
        self.input_var.trace_add(
            "write",
            lambda *a: self._on_field_change("input_mapping", self.input_var.get()),
        )
        self.output_var = ctk.StringVar()
        self.output_var.trace_add(
            "write",
            lambda *a: self._on_field_change("output_mapping", self.output_var.get()),
        )

        # Enabled
        self.enabled_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            p, text="Enabled", variable=self.enabled_var, font=T.FONT_BODY
        ).pack(**pad, pady=T.PAD_SM)
        self.enabled_var.trace_add(
            "write", lambda *a: self._on_field_change("enabled", self.enabled_var.get())
        )

        # ── Advanced section ──────────────────────────────────────
        self.advanced_frame = ctk.CTkFrame(
            p,
            fg_color=T.CLR_BG,
            corner_radius=6,
            border_width=1,
            border_color=T.CLR_BORDER,
        )
        self.advanced_frame.pack(fill=tk.X, padx=T.PAD_MD, pady=(T.PAD_SM, T.PAD_MD))

        ctk.CTkLabel(self.advanced_frame, text="Advanced", font=T.FONT_HEADING).pack(
            anchor=tk.W, padx=T.PAD_SM, pady=(T.PAD_SM, 0)
        )

        adv_pad = {"padx": T.PAD_SM, "anchor": tk.W}

        # Execution Mode
        ctk.CTkLabel(
            self.advanced_frame, text="Execution Engine", font=T.FONT_BODY
        ).pack(**adv_pad, pady=(T.PAD_XS, 0))
        self.exec_mode_var = ctk.StringVar(value="legacy")
        self.exec_mode_segment = ctk.CTkSegmentedButton(
            self.advanced_frame,
            variable=self.exec_mode_var,
            values=["legacy", "graph"],
            selected_color=T.CLR_SELECTED,
            selected_hover_color=T.BTN_HOVER,
            unselected_color=T.CLR_SURFACE,
            unselected_hover_color=T.BTN_HOVER,
        )
        self.exec_mode_segment.pack(fill=tk.X, padx=T.PAD_SM, pady=(0, T.PAD_SM))
        self.exec_mode_var.trace_add(
            "write",
            lambda *a: self._on_field_change(
                "execution_mode", self.exec_mode_var.get()
            ),
        )

        ctk.CTkLabel(self.advanced_frame, text="Prompt Version", font=T.FONT_BODY).pack(
            **adv_pad, pady=(T.PAD_XS, 0)
        )
        self.pv_var = ctk.StringVar()
        ctk.CTkEntry(
            self.advanced_frame,
            textvariable=self.pv_var,
            width=60,
            fg_color=T.CLR_SURFACE,
            border_color=T.CLR_BORDER,
        ).pack(anchor=tk.W, padx=T.PAD_SM)
        self.pv_var.trace_add(
            "write",
            lambda *a: self._on_field_change("prompt_version", self.pv_var.get()),
        )

        # Step ID
        self.id_frame = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        self.id_frame.pack(fill=tk.X, padx=T.PAD_SM, pady=(T.PAD_SM, T.PAD_SM))
        ctk.CTkLabel(self.id_frame, text="Step ID:", font=T.FONT_BODY).pack(
            side=tk.LEFT
        )
        self.id_label = ctk.CTkLabel(
            self.id_frame, text="", font=T.FONT_BODY, text_color=T.CLR_MUTED
        )
        self.id_label.pack(side=tk.LEFT, padx=T.PAD_XS)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        vm = self.ctrl.get_inspector_viewmodel()
        is_advanced = self.ctrl.state.mode.value == "advanced"

        # Show/hide advanced frame
        if is_advanced:
            self.advanced_frame.pack(
                fill=tk.X, padx=T.PAD_MD, pady=(T.PAD_SM, T.PAD_MD)
            )
        else:
            self.advanced_frame.pack_forget()

        if not vm:
            self._clear_inspector_state()
            return

        self._refresh_warning(vm)
        self._suppress_trace = True
        self._current_step_id = vm.step_id
        self._current_exec_mode = vm.execution_mode

        self.header_label.configure(text=f"Step: {vm.title}")
        self.title_var.set(vm.title)
        self.purpose_var.set(vm.purpose)
        self.model_var.set(vm.model)

        self.role_text.delete("1.0", tk.END)
        self.role_text.insert("1.0", vm.role_text)
        self.task_text.delete("1.0", tk.END)
        self.task_text.insert("1.0", vm.task_text)

        self.enabled_var.set(vm.enabled)

        self.exec_mode_var.set(vm.execution_mode)
        self._rebuild_io_container(vm)

        self.input_var.set(vm.input_mapping)
        self.output_var.set(vm.output_mapping)
        self.pv_var.set(vm.prompt_version)
        self.id_label.configure(text=vm.step_id)

        self._refresh_att_badge()
        self._suppress_trace = False

    def _clear_inspector_state(self) -> None:
        self._suppress_trace = True
        self._current_step_id = None
        self._current_exec_mode = None
        self.header_label.configure(text="No step selected")
        self.title_var.set("")
        self.purpose_var.set("")
        self.model_var.set("")
        self.role_text.delete("1.0", tk.END)
        self.task_text.delete("1.0", tk.END)
        self.enabled_var.set(True)
        self.exec_mode_var.set("legacy")
        self.input_var.set("")
        self.output_var.set("")
        self.pv_var.set("")
        self.id_label.configure(text="")
        self.model_warning.pack_forget()
        for w in self.io_container.winfo_children():
            w.destroy()
        for w in self.att_badge_frame.winfo_children():
            w.destroy()
        self._suppress_trace = False

    def _refresh_warning(self, vm: StepInspectorVM) -> None:
        has_mode_mismatch = False
        if hasattr(self.ctrl, "has_execution_mode_mismatch"):
            has_mode_mismatch = bool(self.ctrl.has_execution_mode_mismatch(vm.step_id))
        if has_mode_mismatch:
            self.model_warning.configure(
                text="⚠️ Execution mode mismatch with global runtime toggle"
            )
            self.model_warning.pack(
                fill=tk.X, padx=T.PAD_MD, pady=(2, 0), after=self.model_combo
            )
            return
        if vm.model not in self.ctrl.config_service.load_models():
            self.model_warning.configure(text="⚠️ Invalid model catalog ID")
            self.model_warning.pack(
                fill=tk.X, padx=T.PAD_MD, pady=(2, 0), after=self.model_combo
            )
            return
        self.model_warning.pack_forget()

    def _rebuild_io_container(self, vm) -> None:
        for w in self.io_container.winfo_children():
            w.destroy()

        is_advanced = self.ctrl.state.mode.value == "advanced"
        adv_pad = {"padx": T.PAD_SM, "anchor": tk.W}

        if vm.execution_mode == "legacy" and is_advanced:
            # Legacy mode — raw variable mapping (advanced only)
            ctk.CTkLabel(
                self.io_container, text="Input Variable", font=T.FONT_BODY
            ).pack(**adv_pad, pady=(T.PAD_XS, 0))
            ctk.CTkEntry(
                self.io_container,
                textvariable=self.input_var,
                fg_color=T.CLR_SURFACE,
                border_color=T.CLR_BORDER,
            ).pack(fill=tk.X, padx=T.PAD_SM)

            ctk.CTkLabel(
                self.io_container, text="Output Variable", font=T.FONT_BODY
            ).pack(**adv_pad, pady=(T.PAD_XS, 0))
            ctk.CTkEntry(
                self.io_container,
                textvariable=self.output_var,
                fg_color=T.CLR_SURFACE,
                border_color=T.CLR_BORDER,
            ).pack(fill=tk.X, padx=T.PAD_SM)
            return

        if not is_advanced:
            # ── Simple mode: connection editor ──────────────────────
            self._build_simple_connection_editor(vm)
            return

        # ── Advanced mode: full graph IO ────────────────────────────
        self._build_advanced_graph_io(vm)

    # ── Simple mode connection editor ───────────────────────────────
    def _build_simple_connection_editor(self, vm) -> None:
        adv_pad = {"padx": T.PAD_SM, "anchor": tk.W}

        ctk.CTkLabel(
            self.io_container,
            text="Receives input from",
            font=T.FONT_HEADING,
        ).pack(**adv_pad, pady=(T.PAD_SM, 0))

        # Determine the default input port
        default_port = next(
            (p for p in vm.inputs if p.name == "input"),
            vm.inputs[0] if vm.inputs else None,
        )
        sources = list(default_port.sources) if default_port else []
        port_name = default_port.name if default_port else "input"

        if not sources:
            ctk.CTkLabel(
                self.io_container,
                text="No connections yet.",
                font=T.FONT_BODY,
                text_color=T.CLR_MUTED,
            ).pack(**adv_pad, pady=(2, 0))
        else:
            for i, src in enumerate(sources):
                src_row = ctk.CTkFrame(self.io_container, fg_color="transparent")
                src_row.pack(fill=tk.X, padx=T.PAD_SM, pady=1)
                ctk.CTkLabel(
                    src_row,
                    text=self._format_source_line(src),
                    font=T.FONT_BODY,
                    text_color=T.CLR_MUTED,
                ).pack(side=tk.LEFT)
                ctk.CTkButton(
                    src_row,
                    text="✕",
                    width=20,
                    height=20,
                    fg_color="transparent",
                    text_color=T.CLR_ERROR,
                    hover_color=T.CLR_SURFACE,
                    command=lambda idx=i: self.ctrl.disconnect_step_input(
                        vm.step_id, port_name, idx
                    ),
                ).pack(side=tk.RIGHT)

        # + Add connection row
        add_row = ctk.CTkFrame(self.io_container, fg_color="transparent")
        add_row.pack(fill=tk.X, padx=T.PAD_SM, pady=(4, T.PAD_SM))

        step_options = self._available_source_steps(vm.step_id)
        step_var = tk.StringVar(value=step_options[0] if step_options else "(no steps)")
        step_combo = ctk.CTkComboBox(
            add_row,
            values=step_options or ["(no steps)"],
            variable=step_var,
            width=150,
            state="readonly",
        )
        step_combo.pack(side=tk.LEFT)

        _init_ports = self._available_source_ports(
            vm.step_id, step_var.get() if step_options else "(no steps)"
        )
        output_var = tk.StringVar(value=_init_ports[0] if _init_ports else "")
        output_combo = ctk.CTkComboBox(
            add_row,
            values=_init_ports,
            variable=output_var,
            width=100,
            state="readonly",
        )
        # Only show port picker if the source step has multiple outputs
        if len(_init_ports) > 1:
            output_combo.pack(side=tk.LEFT, padx=(T.PAD_XS, 0))

        def _on_step_pick(*_):
            ports = self._available_source_ports(vm.step_id, step_var.get())
            output_combo.configure(values=ports)
            output_var.set(ports[0] if ports else "")
            if len(ports) > 1:
                output_combo.pack(side=tk.LEFT, padx=(T.PAD_XS, 0))
            else:
                output_combo.pack_forget()

        step_var.trace_add("write", _on_step_pick)

        ctk.CTkButton(
            add_row,
            text="+ Add connection",
            width=100,
            height=24,
            command=lambda: self._on_simple_add_connection(
                vm.step_id, port_name, step_var.get(), output_var.get()
            ),
        ).pack(side=tk.LEFT, padx=T.PAD_SM)

        # Combine mode (only shown when ≥2 sources)
        if len(sources) >= 2 and default_port:
            combine_frame = ctk.CTkFrame(self.io_container, fg_color="transparent")
            combine_frame.pack(fill=tk.X, padx=T.PAD_SM, pady=(0, T.PAD_SM))
            ctk.CTkLabel(
                combine_frame,
                text="Combine mode:",
                font=T.FONT_BODY,
            ).pack(side=tk.LEFT)
            combine_var = ctk.StringVar(
                value=join_strategy_to_label(default_port.join_strategy)
            )
            ctk.CTkComboBox(
                combine_frame,
                values=list(JOIN_STRATEGY_LABEL_TO_VALUE.keys()),
                variable=combine_var,
                width=180,
                state="readonly",
            ).pack(side=tk.LEFT, padx=T.PAD_SM)
            combine_var.trace_add(
                "write",
                lambda *a, v=combine_var: self.ctrl.update_port_config(
                    vm.step_id,
                    "input",
                    port_name,
                    "join_strategy",
                    join_strategy_to_value(v.get()),
                ),
            )

    def _on_simple_add_connection(
        self, step_id: str, port_name: str, step_choice: str, port_choice: str
    ) -> None:
        """Handle '+ Add connection' in simple mode."""
        s = (step_choice or "").strip()
        if not s or s == "(no steps)" or s == NO_SOURCE_LABEL:
            return
        canonical_step = self._canonical_source_step_id(s)
        if not canonical_step:
            return
        if canonical_step == CANONICAL_WORKFLOW_ROOT_STEP_ID:
            canonical_port = "input"
        else:
            canonical_port = (port_choice or "").strip()
            if not canonical_port:
                return
        if not canonical_step:
            return
        self.ctrl.connect_step_input(step_id, canonical_step, canonical_port, port_name)

    # ── Advanced mode: full graph IO ────────────────────────────────
    def _build_advanced_graph_io(self, vm) -> None:
        adv_pad = {"padx": T.PAD_SM, "anchor": tk.W}

        ctk.CTkLabel(self.io_container, text="Graph Inputs", font=T.FONT_HEADING).pack(
            **adv_pad, pady=(T.PAD_SM, 0)
        )

        for port in vm.inputs:
            port_frame = ctk.CTkFrame(
                self.io_container,
                fg_color=T.CLR_BG,
                border_color=T.CLR_BORDER,
                border_width=1,
            )
            port_frame.pack(fill=tk.X, padx=T.PAD_SM, pady=2)

            header_row = ctk.CTkFrame(port_frame, fg_color="transparent")
            header_row.pack(fill=tk.X, padx=T.PAD_SM, pady=(T.PAD_SM, 2))
            ctk.CTkLabel(header_row, text=f"• {port.name}", font=T.FONT_BODY).pack(
                side=tk.LEFT
            )

            req_var = ctk.BooleanVar(value=port.required)
            req_chk = ctk.CTkCheckBox(
                header_row, text="Required", variable=req_var, width=60
            )
            req_chk.pack(side=tk.LEFT, padx=T.PAD_MD)
            req_var.trace_add(
                "write",
                lambda *a,
                pid=vm.step_id,
                pn=port.name,
                v=req_var: self.ctrl.update_port_config(
                    pid, "input", pn, "required", v.get()
                ),
            )

            join_var = ctk.StringVar(value=join_strategy_to_label(port.join_strategy))
            join_cb = ctk.CTkComboBox(
                header_row,
                values=list(JOIN_STRATEGY_LABEL_TO_VALUE.keys()),
                variable=join_var,
                width=180,
            )
            join_cb.pack(side=tk.LEFT, padx=T.PAD_SM)
            join_var.set(join_strategy_to_label(port.join_strategy))
            join_var.trace_add(
                "write",
                lambda *a,
                pid=vm.step_id,
                pn=port.name,
                v=join_var: self.ctrl.update_port_config(
                    pid,
                    "input",
                    pn,
                    "join_strategy",
                    join_strategy_to_value(v.get()),
                ),
            )

            ctk.CTkButton(
                header_row,
                text="✕",
                width=24,
                fg_color=T.CLR_ERROR,
                command=lambda p=port.name: self.ctrl.remove_input_port(vm.step_id, p),
            ).pack(side=tk.RIGHT)

            # Sources List
            for i, src in enumerate(port.sources):
                src_row = ctk.CTkFrame(port_frame, fg_color="transparent")
                src_row.pack(fill=tk.X, padx=T.PAD_MD, pady=1)
                ctk.CTkLabel(
                    src_row,
                    text=self._format_source_line(src),
                    font=T.FONT_BODY,
                    text_color=T.CLR_MUTED,
                ).pack(side=tk.LEFT)
                ctk.CTkButton(
                    src_row,
                    text="✕",
                    width=20,
                    height=20,
                    fg_color="transparent",
                    text_color=T.CLR_ERROR,
                    hover_color=T.CLR_SURFACE,
                    command=lambda p=port.name,
                    srcs=port.sources,
                    idx=i: self._on_remove_source(vm.step_id, p, srcs, idx),
                ).pack(side=tk.RIGHT)

            add_src_frame = ctk.CTkFrame(port_frame, fg_color="transparent")
            add_src_frame.pack(fill=tk.X, padx=T.PAD_MD, pady=(2, T.PAD_SM))
            step_options = self._available_source_steps(vm.step_id)
            step_var = tk.StringVar(
                value=step_options[0] if step_options else "(no source step)"
            )
            step_combo = ctk.CTkComboBox(
                add_src_frame,
                values=step_options or ["(no source step)"],
                variable=step_var,
                width=150,
                state="readonly",
            )
            step_combo.pack(side=tk.LEFT)
            _init_ports = self._available_source_ports(
                vm.step_id, step_var.get() if step_options else "(no source step)"
            )
            output_var = tk.StringVar(value=_init_ports[0] if _init_ports else "output")
            output_combo = ctk.CTkComboBox(
                add_src_frame,
                values=_init_ports,
                variable=output_var,
                width=120,
                state="readonly",
            )
            output_combo.pack(side=tk.LEFT, padx=(T.PAD_XS, 0))

            def _on_step_pick(*_):
                ports = self._available_source_ports(vm.step_id, step_var.get())
                output_combo.configure(values=ports)
                output_var.set(ports[0] if ports else "output")

            step_var.trace_add("write", _on_step_pick)
            ctk.CTkButton(
                add_src_frame,
                text="+ Source",
                width=60,
                height=24,
                command=lambda p=port.name,
                srcs=port.sources,
                step_choice=step_var,
                port_choice=output_var: self._on_add_source(
                    vm.step_id,
                    p,
                    srcs,
                    step_choice.get(),
                    port_choice.get(),
                ),
            ).pack(side=tk.LEFT, padx=T.PAD_SM)

        ctk.CTkLabel(self.io_container, text="Graph Outputs", font=T.FONT_HEADING).pack(
            **adv_pad, pady=(T.PAD_SM, 0)
        )

        for port in vm.outputs:
            port_frame = ctk.CTkFrame(
                self.io_container,
                fg_color=T.CLR_BG,
                border_color=T.CLR_BORDER,
                border_width=1,
            )
            port_frame.pack(fill=tk.X, padx=T.PAD_SM, pady=2)

            row = ctk.CTkFrame(port_frame, fg_color="transparent")
            row.pack(fill=tk.X, padx=T.PAD_SM, pady=T.PAD_SM)
            ctk.CTkLabel(row, text=f"• {port.name}", font=T.FONT_BODY).pack(
                side=tk.LEFT
            )

            exp_var = ctk.BooleanVar(value=port.exposed)
            exp_chk = ctk.CTkCheckBox(row, text="Exposed", variable=exp_var, width=60)
            exp_chk.pack(side=tk.LEFT, padx=T.PAD_MD)
            exp_var.trace_add(
                "write",
                lambda *a,
                pid=vm.step_id,
                pn=port.name,
                v=exp_var: self.ctrl.update_port_config(
                    pid, "output", pn, "exposed", v.get()
                ),
            )

            kind_var = ctk.StringVar(value=port.kind)
            kind_cb = ctk.CTkComboBox(
                row,
                values=["text", "json", "image", "binary"],
                variable=kind_var,
                width=80,
            )
            kind_cb.pack(side=tk.LEFT, padx=T.PAD_SM)
            kind_var.trace_add(
                "write",
                lambda *a,
                pid=vm.step_id,
                pn=port.name,
                v=kind_var: self.ctrl.update_port_config(
                    pid, "output", pn, "kind", v.get()
                ),
            )

            ctk.CTkButton(
                row,
                text="✕",
                width=24,
                fg_color=T.CLR_ERROR,
                command=lambda p=port.name: self.ctrl.remove_output_port(vm.step_id, p),
            ).pack(side=tk.RIGHT)

        add_out_frame = ctk.CTkFrame(self.io_container, fg_color="transparent")
        add_out_frame.pack(fill=tk.X, padx=T.PAD_SM, pady=2)
        out_name_var = tk.StringVar()
        ctk.CTkEntry(
            add_out_frame,
            textvariable=out_name_var,
            width=120,
            placeholder_text="new_port_name",
        ).pack(side=tk.LEFT, padx=(0, 2))
        ctk.CTkButton(
            add_out_frame,
            text="+ Output Port",
            width=80,
            command=lambda: self._on_add_output(vm.step_id, out_name_var.get()),
        ).pack(side=tk.LEFT, padx=(2, 0))

    def _on_add_source(
        self,
        step_id: str,
        port_name: str,
        current_sources: list,
        source_step_choice: str,
        source_port: str,
    ) -> None:
        from core.models import SourceRef

        step_key = (source_step_choice or "").strip()
        if (
            not step_key
            or step_key == "(no source step)"
            or step_key == NO_SOURCE_LABEL
        ):
            return
        canonical_step, port_key = normalized_source_ref_from_choice(
            step_key, source_port
        )
        if not canonical_step:
            return
        sources = list(current_sources)
        sources.append(SourceRef(step_id=canonical_step, port=port_key))
        self.ctrl.update_port_config(step_id, "input", port_name, "sources", sources)

    def _on_remove_source(
        self, step_id: str, port_name: str, current_sources: list, remove_idx: int
    ) -> None:
        sources = list(current_sources)
        if 0 <= remove_idx < len(sources):
            sources.pop(remove_idx)
            self.ctrl.update_port_config(
                step_id, "input", port_name, "sources", sources
            )

    def _on_add_output(self, step_id: str, name: str) -> None:
        name = name.strip()
        if not name:
            return
        from core.models import OutputPortDef

        self.ctrl.add_output_port(step_id, OutputPortDef(name=name))

    def _refresh_att_badge(self) -> None:
        """Refresh attachment badge under Task section."""
        for w in self.att_badge_frame.winfo_children():
            w.destroy()

        step = self.ctrl.state.get_selected_step()
        if not step:
            return

        bindings = self.ctrl.state.attachment_bindings

        is_advanced_mode = getattr(self.ctrl.state.mode, "value", None) == "advanced"
        if not is_advanced_mode:
            ctk.CTkLabel(
                self.att_badge_frame,
                text="Tệp đính kèm",
                font=T.FONT_BODY,
            ).pack(anchor=tk.W, pady=(0, 4))

            target_slot_key = ""
            if step.attachments:
                # Prefer the first required-but-missing slot; fallback to the first slot.
                chosen = next(
                    (
                        s
                        for s in step.attachments
                        if s.required and not bindings.get(f"{step.id}::{s.slot_id}")
                    ),
                    step.attachments[0],
                )
                target_slot_key = f"{step.id}::{chosen.slot_id}"
            else:
                # Create a single implicit slot for non-tech users.
                slot_id = self.ctrl.add_attachment_slot(
                    step.id, label="Tệp đính kèm", required=False
                )
                target_slot_key = f"{step.id}::{slot_id}"

            attached_paths: list[str] = [
                p
                for p in (bindings.get(f"{step.id}::{s.slot_id}") for s in step.attachments)
                if p is not None and p
            ]

            status = "Chưa có tệp nào được đính kèm."
            if len(attached_paths) == 1:
                status = f"Đã đính kèm: {Path(attached_paths[0]).name}"
            elif len(attached_paths) > 1:
                status = f"Đã đính kèm: {len(attached_paths)} tệp"

            ctk.CTkLabel(
                self.att_badge_frame,
                text=status,
                font=T.FONT_BODY,
                text_color=T.CLR_MUTED,
            ).pack(anchor=tk.W, pady=(0, 6))

            btn_text = "Thay tệp" if attached_paths else "Đính kèm tệp"
            ctk.CTkButton(
                self.att_badge_frame,
                text=btn_text,
                command=lambda k=target_slot_key: self._on_attach_clicked(k),
                width=160,
                fg_color=T.CLR_SELECTED,
                hover_color=T.CLR_BORDER,
                text_color="#f8fafc",
            ).pack(anchor=tk.W)
            return

        if not step.attachments:
            ctk.CTkLabel(
                self.att_badge_frame,
                text="No files expected for this step.",
                font=T.FONT_BODY,
                text_color=T.CLR_MUTED,
            ).pack(anchor=tk.W, pady=4)
            ctk.CTkButton(
                self.att_badge_frame,
                text="+ Add File Slot",
                command=lambda sid=step.id: self._add_attachment_slot(sid),
                width=140,
                fg_color=T.CLR_SELECTED,
                hover_color=T.CLR_BORDER,
                text_color="#f8fafc",
            ).pack(anchor=tk.W, pady=(2, 0))
            return

        ctk.CTkLabel(
            self.att_badge_frame,
            text="Required / Optional Files:",
            font=T.FONT_BODY,
        ).pack(anchor=tk.W, pady=(0, 4))

        content_frame = ctk.CTkFrame(self.att_badge_frame, fg_color="transparent")
        content_frame.pack(fill=tk.X)

        for slot in step.attachments:
            slot_key = f"{step.id}::{slot.slot_id}"
            path = bindings.get(slot_key)

            slot_box = ctk.CTkFrame(
                content_frame,
                fg_color=T.CLR_BG,
                border_color=T.CLR_BORDER,
                border_width=1,
            )
            slot_box.pack(fill=tk.X, pady=4)

            meta = ctk.CTkFrame(slot_box, fg_color="transparent")
            meta.pack(fill=tk.X, padx=T.PAD_SM, pady=(T.PAD_SM, 2))

            ctk.CTkLabel(
                meta, text="Label", font=T.FONT_SMALL, width=72, anchor="w"
            ).grid(row=0, column=0, sticky="w", padx=(0, 4))
            label_entry = ctk.CTkEntry(
                meta, width=200, fg_color=T.CLR_SURFACE, border_color=T.CLR_BORDER
            )
            label_entry.insert(0, slot.label or "")
            label_entry.grid(row=0, column=1, sticky="ew", padx=(0, T.PAD_SM))

            ctk.CTkLabel(
                meta, text="Variable", font=T.FONT_SMALL, width=72, anchor="w"
            ).grid(row=1, column=0, sticky="w", padx=(0, 4), pady=(4, 0))
            var_entry = ctk.CTkEntry(
                meta, width=200, fg_color=T.CLR_SURFACE, border_color=T.CLR_BORDER
            )
            var_entry.insert(0, slot.variable_name or "")
            var_entry.grid(
                row=1, column=1, sticky="ew", padx=(0, T.PAD_SM), pady=(4, 0)
            )

            ctk.CTkLabel(
                meta, text="Accepted types", font=T.FONT_SMALL, width=72, anchor="nw"
            ).grid(row=2, column=0, sticky="nw", padx=(0, 4), pady=(4, 0))
            types_entry = ctk.CTkEntry(
                meta,
                width=200,
                placeholder_text="pdf, docx, txt (comma-separated)",
                fg_color=T.CLR_SURFACE,
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
            actions.pack(fill=tk.X, padx=T.PAD_SM, pady=(0, T.PAD_SM))

            def _apply_slot(
                sid=step.id,
                sl_id=slot.slot_id,
                le=label_entry,
                ve=var_entry,
                te=types_entry,
                rv=req_var,
            ) -> None:
                raw_types = (te.get() or "").strip()
                if raw_types:
                    parts = [x.strip() for x in raw_types.split(",") if x.strip()]
                    self.ctrl.update_attachment_slot(
                        sid,
                        sl_id,
                        label=le.get(),
                        variable_name=ve.get(),
                        required=rv.get(),
                        accepted_types=parts,
                    )
                else:
                    self.ctrl.update_attachment_slot(
                        sid,
                        sl_id,
                        label=le.get(),
                        variable_name=ve.get(),
                        required=rv.get(),
                        accepted_types_clear=True,
                    )
                self._refresh_att_badge()

            def _remove_slot_ui(sid=step.id, sl_id=slot.slot_id) -> None:
                self.ctrl.remove_attachment_slot(sid, sl_id)
                self._refresh_att_badge()

            ctk.CTkButton(
                actions,
                text="Apply",
                width=72,
                fg_color=T.CLR_SELECTED,
                hover_color=T.CLR_BORDER,
                text_color="#f8fafc",
                command=_apply_slot,
            ).pack(side=tk.LEFT, padx=(0, T.PAD_XS))
            ctk.CTkButton(
                actions,
                text="Remove slot",
                width=88,
                fg_color=T.CLR_ERROR,
                hover_color="#dc2626",
                command=_remove_slot_ui,
            ).pack(side=tk.LEFT, padx=T.PAD_XS)

            file_row = ctk.CTkFrame(slot_box, fg_color="transparent")
            file_row.pack(fill=tk.X, padx=T.PAD_SM, pady=(0, T.PAD_SM))

            req_text = "*" if slot.required else ""
            ctk.CTkLabel(
                file_row,
                text=f"File{req_text}:",
                font=T.FONT_BODY,
                width=72,
                anchor="w",
            ).pack(side=tk.LEFT)

            if path:
                fname = Path(path).name
                is_missing = not Path(path).is_file()

                label_text = f"⚠ Missing: {fname}" if is_missing else f"✓ {fname}"
                label_color = T.CLR_ERROR if is_missing else T.CLR_MUTED

                ctk.CTkLabel(
                    file_row,
                    text=label_text,
                    font=T.FONT_BODY,
                    text_color=label_color,
                ).pack(side=tk.LEFT, padx=5)
                ctk.CTkButton(
                    file_row,
                    text="Clear file",
                    command=lambda k=slot_key: self._remove_attachment(k),
                    width=72,
                    fg_color=T.CLR_SURFACE,
                    hover_color=T.CLR_BORDER,
                ).pack(side=tk.RIGHT)
            else:
                ctk.CTkButton(
                    file_row,
                    text="📎 Attach",
                    command=lambda k=slot_key: self._on_attach_clicked(k),
                    width=80,
                    fg_color=T.CLR_SELECTED,
                    hover_color=T.CLR_BORDER,
                    text_color="#f8fafc",
                ).pack(side=tk.LEFT, padx=5)

        ctk.CTkButton(
            self.att_badge_frame,
            text="+ Add File Slot",
            command=lambda sid=step.id: self._add_attachment_slot(sid),
            width=140,
            fg_color=T.CLR_SELECTED,
            hover_color=T.CLR_BORDER,
            text_color="#f8fafc",
        ).pack(anchor=tk.W, pady=(T.PAD_SM, 0))

    # ------------------------------------------------------------------
    # Change handlers
    # ------------------------------------------------------------------

    def _on_field_change(self, field_name: str, value) -> None:
        if self._suppress_trace or not self._current_step_id:
            return
        self.ctrl.update_step_field(self._current_step_id, field_name, value)

    def _on_role_change(self, event) -> None:
        if self._suppress_trace or not self._current_step_id:
            return
        content = self.role_text.get("1.0", tk.END).rstrip("\\n")
        self.ctrl.update_role_draft(self._current_step_id, content)

    def _on_task_change(self, event) -> None:
        if self._suppress_trace or not self._current_step_id:
            return
        content = self.task_text.get("1.0", tk.END).rstrip("\\n")
        self.ctrl.update_prompt_draft(self._current_step_id, content)

    # ------------------------------------------------------------------
    # Attachment handlers
    # ------------------------------------------------------------------

    def _on_attach_clicked(self, slot_key: str) -> None:
        """Open file picker and attach file to the given slot."""
        if not self._current_step_id:
            return
        path = filedialog.askopenfilename(
            title="Attach file to this step",
            filetypes=[
                ("Documents", "*.pdf *.docx *.txt *.md *.csv *.xlsx *.pptx"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.ctrl.update_attachment_binding(slot_key, path)
            self._refresh_att_badge()

    def _remove_attachment(self, slot_key: str) -> None:
        """Remove attachment binding and refresh badge."""
        self.ctrl.remove_attachment_binding(slot_key)
        self._refresh_att_badge()

    def _add_attachment_slot(self, step_id: str) -> None:
        self.ctrl.add_attachment_slot(step_id)
        self._refresh_att_badge()

    def _is_root_source_combo_value(self, value: str) -> bool:
        v = (value or "").strip()
        if v == INSPECTOR_ROOT_SOURCE_DISPLAY or v in ROOT_SOURCE_IDS:
            return True
        m = _TITLE_ID_SUFFIX_RE.match(v)
        if m and m.group(2).strip() in ROOT_SOURCE_IDS:
            return True
        return False

    def _canonical_source_step_id(self, combo_or_id: str) -> str:
        # First: try canonical_source_step_id_from_combo which handles root IDs and
        # "Title (step_id)" suffix patterns.
        canonical = canonical_source_step_id_from_combo(combo_or_id)
        # canonical_source_step_id_from_combo returns the raw input when it doesn't
        # match any known pattern (root IDs, suffix format). Only short-circuit when
        # the function has positively identified the canonical form (i.e. it changed
        # the value OR the value is a known ROOT_SOURCE_ID).
        from core.graph_utils import ROOT_SOURCE_IDS

        raw = (combo_or_id or "").strip()
        if canonical and (canonical != raw or raw in ROOT_SOURCE_IDS):
            return canonical

        # Fallback: resolve title-only labels against the current workflow.
        # Only accept unambiguous matches (exactly one candidate).
        wf = self.ctrl.state.get_selected_workflow()
        if wf:
            candidates = [s for s in wf.steps if _step_base_title(s) == combo_or_id]
            if len(candidates) == 1:
                return candidates[0].id
        return ""

    def _display_label_for_source_step_id(self, step_id: str) -> str:
        if step_id in ROOT_SOURCE_IDS:
            return INSPECTOR_ROOT_SOURCE_DISPLAY
        step = self.ctrl.state.get_step_by_id(step_id)
        if step:
            return _step_base_title(step)
        return step_id

    def _format_source_line(self, src) -> str:
        label = self._display_label_for_source_step_id(src.step_id)
        return f"← {label}"

    def _format_step_combo_option(self, step, *, disambiguate: bool = False) -> str:
        """Combo display.

        Use step base title unless disambiguate=True, in which case append (step_id).
        """
        base = _step_base_title(step)
        if disambiguate:
            return f"{base} ({step.id})"
        return base

    def _available_source_steps(self, current_step_id: str) -> list[str]:
        wf = self.ctrl.state.get_selected_workflow()
        if not wf:
            return []
        candidate_steps = [
            step
            for step in wf.steps
            if step.id != current_step_id and step.execution_mode == "graph"
        ]
        # Detect label collisions so the user always gets a deterministic mapping.
        base_labels = [_step_base_title(s) for s in candidate_steps]
        label_counts: dict[str, int] = {}
        for lbl in base_labels:
            label_counts[lbl] = label_counts.get(lbl, 0) + 1
        options: list[str] = [INSPECTOR_ROOT_SOURCE_DISPLAY]
        for step in candidate_steps:
            base = _step_base_title(step)
            disambiguate = label_counts.get(base, 0) > 1
            options.append(
                self._format_step_combo_option(step, disambiguate=disambiguate)
            )
        return options

    def _available_source_ports(
        self, current_step_id: str, source_combo_value: str
    ) -> list[str]:
        if not source_combo_value or source_combo_value == "(no source step)":
            return []
        if self._is_root_source_combo_value(source_combo_value):
            return ["input"]
        canonical = self._canonical_source_step_id(source_combo_value)
        source_step = self.ctrl.state.get_step_by_id(canonical)
        if not source_step or source_step.id == current_step_id:
            return []
        outputs = (
            [port.name for port in source_step.outputs] if source_step.outputs else []
        )
        return outputs
