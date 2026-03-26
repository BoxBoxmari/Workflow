"""
ui.result_drawer — Bottom drawer with tabs for output, raw, metrics, log.

Displays execution results for the selected step.
"""

from __future__ import annotations

import tkinter as tk
import customtkinter as ctk

from core.enums import DrawerTab
from ui import theme as T
from ui.workspace_controller import WorkspaceController


class ResultDrawer(ctk.CTkFrame):
    """Bottom drawer with tabs: Output, Raw, Metrics, Log."""

    HEIGHT = 200

    def __init__(
        self, parent: ctk.CTkFrame | tk.Widget, controller: WorkspaceController
    ) -> None:
        super().__init__(
            parent,
            height=self.HEIGHT,
            fg_color=T.CLR_BG,
            corner_radius=0,
            border_color=T.CLR_BORDER,
            border_width=1,
        )
        self.ctrl = controller
        self.pack_propagate(False)
        self._last_results: dict[str, str] = {}
        self._build()

    def _build(self) -> None:
        # Toggle bar
        toggle_frame = ctk.CTkFrame(self, fg_color=T.CLR_SURFACE, corner_radius=0)
        toggle_frame.pack(fill=tk.X)

        ctk.CTkButton(
            toggle_frame,
            text="▼ Results",
            font=T.FONT_BODY,
            fg_color="transparent",
            text_color="#f8fafc",
            hover_color=T.CLR_SELECTED,
            width=80,
            command=self.ctrl.toggle_drawer,
        ).pack(side=tk.LEFT, padx=T.PAD_SM, pady=T.PAD_XS)

        # Copy to Clipboard Button
        self.copy_btn = ctk.CTkButton(
            toggle_frame,
            text="📋 Copy",
            font=T.FONT_SMALL,
            fg_color="transparent",
            text_color=T.CLR_MUTED,
            hover_color=T.CLR_SELECTED,
            width=60,
            command=self._copy_to_clipboard,
        )
        self.copy_btn.pack(side=tk.RIGHT, padx=T.PAD_SM, pady=T.PAD_XS)

        # Tabview
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=T.CLR_BG,
            segmented_button_selected_color=T.CLR_SELECTED,
            segmented_button_selected_hover_color=T.BTN_HOVER,
            segmented_button_unselected_color=T.CLR_BG,
            segmented_button_unselected_hover_color=T.BTN_HOVER,
            text_color=T.CLR_MUTED,
        )
        self.tabview.pack(fill=tk.BOTH, expand=True, padx=T.PAD_XS, pady=(0, T.PAD_XS))

        self.textboxes: dict[str, ctk.CTkTextbox] = {}
        for tab_enum in DrawerTab:
            tab_name = tab_enum.value.capitalize()
            tab_frame = self.tabview.add(tab_name)

            txt = ctk.CTkTextbox(
                tab_frame,
                font=T.FONT_MONO,
                wrap=tk.WORD,
                fg_color=T.CLR_SURFACE,
                border_width=0,
                text_color="#f8fafc",
                activate_scrollbars=True,
            )
            txt.pack(fill=tk.BOTH, expand=True)
            txt.configure(state=tk.DISABLED)
            self.textboxes[tab_enum.value] = txt

    def _copy_to_clipboard(self) -> None:
        curr_tab = self.tabview.get().lower()
        txt_widget = self.textboxes.get(curr_tab)
        if not txt_widget:
            return

        text = txt_widget.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.copy_btn.configure(
                text="✓ Copied!",
                fg_color=T.CLR_SUCCESS,
                text_color="#ffffff",
            )
            self.after(
                3000,
                lambda: self.copy_btn.configure(
                    text="📋 Copy",
                    fg_color="transparent",
                    text_color=T.CLR_MUTED,
                ),
            )

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        state = self.ctrl.state

        # Visibility
        if not state.drawer_visible:
            self.pack_forget()
            return
        self.pack(fill=tk.X, side=tk.BOTTOM)

        # Sync current tab if changed externally
        target_tab_name = state.drawer_tab.value.capitalize()
        if self.tabview.get() != target_tab_name:
            self.tabview.set(target_tab_name)

        # Get result for selected step
        sr = None
        if state.selected_step_id and state.selected_step_id in state.run_step_results:
            sr = state.run_step_results[state.selected_step_id]

        # Populate all textboxes
        results = {t.value: "" for t in DrawerTab}

        if sr is None:
            placeholder = (
                "(⏳ Waiting...)" if state.is_running else "(No output results)"
            )
            for k in results:
                results[k] = placeholder
        else:
            if getattr(sr, "output_ports", None):
                out_strs = [f"-- {k} --\n{v}\n" for k, v in sr.output_ports.items()]
                results[DrawerTab.OUTPUT.value] = (
                    "\n".join(out_strs).strip() if out_strs else "(no outputs recorded)"
                )
            else:
                results[DrawerTab.OUTPUT.value] = sr.output_text or "(empty output)"

            if getattr(sr, "input_ports", None):
                inp_strs = [f"-- {k} --\n{v}\n" for k, v in sr.input_ports.items()]
                results[DrawerTab.INPUT.value] = (
                    "\n".join(inp_strs).strip() if inp_strs else "(no inputs recorded)"
                )
            else:
                results[DrawerTab.INPUT.value] = sr.input_text or "(no input recorded)"

            import json

            results[DrawerTab.RAW.value] = (
                json.dumps(sr.raw_response, indent=2, ensure_ascii=False)
                if sr.raw_response
                else "(no raw response)"
            )

            m = sr.metrics
            results[DrawerTab.METRICS.value] = (
                f"Latency:      {m.latency_ms:.0f} ms\n"
                f"Model:        {m.model}\n"
                f"Prompt ver:   {m.prompt_version}\n"
                f"Tokens:\n"
                f"  Prompt:     {m.prompt_tokens or 'N/A'}\n"
                f"  Completion: {m.completion_tokens or 'N/A'}\n"
                f"  Total:      {m.total_tokens or 'N/A'}\n"
                f"Timestamp:    {m.timestamp}"
            )

            # Use user-facing titles only; never expose internal step ids like step_****.
            log_step_title = (getattr(sr, "step_name", "") or "").strip() or "Untitled step"
            log_text = f"Step: {log_step_title}\nStatus: {sr.status.upper()}\n"
            if sr.error:
                log_text += f"\nError Details:\n{sr.error}\n"
            results[DrawerTab.LOG.value] = log_text

            # --- New Tabs for Graph Mode ---
            step_def = self.ctrl.state.get_selected_step()
            mode_str = step_def.execution_mode if step_def else "unknown"
            step_title = "Untitled step"
            if step_def:
                t = (getattr(step_def, "title", "") or "").strip()
                step_title = t or "Untitled step"
            results[DrawerTab.SUMMARY.value] = (
                f"Step Title:     {step_title}\n"
                f"Status:         {sr.status.upper()}\n"
                f"Execution Mode: {mode_str}\n"
            )

            if hasattr(sr, "node_events") and sr.node_events:
                evt_lines = [
                    f"[{e.get('timestamp', '').split('T')[-1][:8]}] {e.get('type') or e.get('event_type', 'event')}"
                    for e in sr.node_events
                ]
                results[DrawerTab.EVENTS.value] = "\n".join(evt_lines)
            else:
                results[DrawerTab.EVENTS.value] = "(no events recorded)"

            prov_lines = []
            if step_def and step_def.execution_mode == "graph":
                for p in step_def.inputs:
                    for s in p.sources:
                        src_def = self.ctrl.state.get_step_by_id(s.step_id)
                        src_title = (
                            (getattr(src_def, "title", "") or "").strip()
                            if src_def
                            else ""
                        )
                        src_title = src_title or "Untitled step"
                        prov_lines.append(
                            f"[{src_title}].{s.port} → [{step_title}].{p.name}"
                        )

            results[DrawerTab.PROVENANCE.value] = (
                "\n".join(prov_lines) if prov_lines else "(no provenance data)"
            )

        # Update textboxes
        for tab_val, text in results.items():
            txt = self.textboxes[tab_val]
            if self._last_results.get(tab_val) == text:
                continue
            txt.configure(state=tk.NORMAL)
            txt.delete("1.0", tk.END)
            txt.insert("1.0", text)
            txt.configure(state=tk.DISABLED)
            self._last_results[tab_val] = text
