"""
ui.workspace_controller — Central coordinator for the workspace.

This replaces the old monolithic App class as the place where all
state transitions, run orchestration, event dispatch, and panel
synchronization happen.  Panels call controller methods; they never
directly access services or mutate state.
"""

from __future__ import annotations

import logging
import re
import threading
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from ui.config_watcher import start_config_watcher, stop_config_watcher

from core.commands import (
    AddStepCommand,
    DeleteStepCommand,
    DuplicateStepCommand,
    UpdateStepFieldCommand,
)
from core.config_service import ConfigService
from core.enums import DrawerTab, WorkspaceMode, WorkspaceView
from core.events import EventBus, external_change_detected, attachment_ingested
from core.models import (
    StepDef,
    StepResult,
    WorkflowDef,
    ensure_graph_io,
)
from core.prompts import PromptRegistry
from core.session import SessionState, load_session, save_session
from core.storage import StorageManager
from core.workflow import WorkflowRunner
from ui import dialogs
from ui.viewmodels import build_flow_viewmodel, build_inspector_viewmodel
from ui.workspace_state import WorkspaceState

log = logging.getLogger("workbench.ui.controller")


class WorkspaceController:
    """Central coordinator — the only place that mutates WorkspaceState."""

    def __init__(
        self,
        project_root: Path,
        config_service: ConfigService,
        storage: StorageManager,
        prompt_registry: PromptRegistry,
        client,
        event_bus: EventBus,
    ) -> None:
        self.project_root = project_root
        self.config_service = config_service
        self.storage = storage
        self.prompt_registry = prompt_registry
        self.client = client
        self.event_bus = event_bus

        self.state = WorkspaceState()
        self.runner: Optional[WorkflowRunner] = None

        self.event_bus.subscribe("run_started", self._handle_run_started)
        self.event_bus.subscribe("node_ready", self._handle_node_ready)
        self.event_bus.subscribe("step_started", self._handle_step_started)
        self.event_bus.subscribe("step_finished", self._handle_step_finished)
        self.event_bus.subscribe("node_blocked", self._handle_node_blocked)
        self.event_bus.subscribe("run_finished", self._handle_run_finished)
        self.event_bus.subscribe("run_failed", self._handle_run_failed)
        self.event_bus.subscribe(
            "external_change_detected", self._handle_external_change_detected
        )

        # Check provider readiness
        if self.client and self.client.base_url and self.client.subscription_key:
            self.state.is_provider_ready = True

        # Session dir — <project_root>/state
        self._state_dir = project_root / "state"

        # Config watcher — watchdog Observer (replaces polling thread)
        self._config_observer = None
        # Kept for snapshot diffing (used only if watchdog unavailable)
        self._watcher_thread: Optional[threading.Thread] = None
        self._watcher_stop = threading.Event()
        self._config_mtime: dict[Path, float] = {}

        # UI callback hooks — set by workspace_shell after mount
        self._on_state_changed: Optional[Callable[[], None]] = None

        # Mode contract:
        # - Current runner selection source of truth is WorkspaceState.enable_graph_runtime.
        # - StepDef.execution_mode is treated as a per-step declaration that should align
        #   with the global toggle for predictable execution semantics.
        # - Wave 0 policy: detect and report mismatches without changing runtime behavior.
        self._last_execution_mode_mismatches: list[str] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def set_state_changed_callback(self, cb: Callable[[], None]) -> None:
        self._on_state_changed = cb

    def _notify(self) -> None:
        """Signal panels to re-render from current state."""
        if self._on_state_changed:
            self._on_state_changed()

    # ------------------------------------------------------------------
    # Startup / shutdown
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Load session + start config watcher. Call after callback is registered."""
        session = load_session(self._state_dir)
        self._apply_session(session)
        self.load_workflows()
        # Start event-driven watchdog observer (replaces 1.5s polling)
        config_dir = self.config_service.workflows_file.parent
        self._config_observer = start_config_watcher(config_dir, self)

    def stop(self) -> None:
        """Save session + stop config watcher. Call on app exit."""
        self._save_session()
        stop_config_watcher(self._config_observer)
        self._config_observer = None
        # Also stop fallback polling thread if somehow still running
        self._watcher_stop.set()

    def _apply_session(self, session: SessionState) -> None:
        if session.selected_workflow_id:
            self.state.selected_workflow_id = session.selected_workflow_id
        if session.selected_step_id:
            self.state.selected_step_id = session.selected_step_id
        try:
            from core.enums import DrawerTab, WorkspaceMode, WorkspaceView

            self.state.drawer_tab = DrawerTab(session.drawer_tab)
            self.state.mode = WorkspaceMode(session.mode)
            self.state.view = WorkspaceView(session.view)
        except Exception:
            pass  # ignore bad enum values
        self.state.drawer_visible = session.drawer_visible
        self.state.attachment_bindings = dict(session.recent_bindings)
        self.state.appearance_mode = session.appearance_mode

    def _save_session(self) -> None:
        session = SessionState(
            selected_workflow_id=self.state.selected_workflow_id,
            selected_step_id=self.state.selected_step_id,
            drawer_tab=self.state.drawer_tab.value,
            drawer_visible=self.state.drawer_visible,
            mode=self.state.mode.value,
            view=self.state.view.value,
            recent_bindings=dict(self.state.attachment_bindings),
            appearance_mode=self.state.appearance_mode,
        )
        save_session(self._state_dir, session)

    def update_appearance_mode(self, mode: str) -> None:
        """Update the UI theme preference and notify panels."""
        self.state.appearance_mode = mode
        self._notify()

    # ------------------------------------------------------------------
    # Config watcher (Gap 4)
    # ------------------------------------------------------------------

    def _snapshot_mtimes(self) -> dict[Path, float]:
        """Capture mtimes for config files we want to watch."""
        watched = [self.config_service.workflows_file]
        # Also watch prompt files
        try:
            for p in self.config_service.prompts_dir.glob("*.txt"):
                watched.append(p)
        except Exception:
            pass
        return {p: p.stat().st_mtime for p in watched if p.exists()}

    def _config_watcher_loop(self) -> None:
        """Background loop: poll config mtimes every 1.5 seconds."""
        while not self._watcher_stop.wait(timeout=1.5):
            try:
                current = self._snapshot_mtimes()
                for path, mtime in current.items():
                    if self._config_mtime.get(path, mtime) != mtime:
                        log.debug("External change detected: %s", path)
                        self.notify_external_change(str(path))
                        break
                self._config_mtime = current
            except Exception as e:
                log.warning("Config watcher error: %s", e)

    def notify_external_change(self, path: str = "") -> None:
        """Thread-safe entrypoint for background watchers to emit config changes."""
        self.event_bus.publish(external_change_detected(path))

    # -------------------------------------------------------------------------
    # Run lifecycle reducers (E1-T3)
    # -------------------------------------------------------------------------
    def _reduce_run_prepared_for_start(self) -> None:
        self.state.is_running = True
        self.state.run_step_results.clear()
        self.state.view = WorkspaceView.RESULTS
        self.state.drawer_visible = True
        self.state.drawer_tab = DrawerTab.OUTPUT

    def _reduce_run_started(self, run_id: Optional[str]) -> None:
        self.state.selected_run_id = run_id

    def _reduce_node_ready(self, step_id: Optional[str]) -> bool:
        if not step_id or step_id in self.state.run_step_results:
            return False
        self.state.run_step_results[step_id] = StepResult(
            step_id=step_id, status="pending"
        )
        return True

    def _reduce_step_running(self, step_id: Optional[str]) -> bool:
        if not step_id:
            return False
        res = self.state.run_step_results.get(step_id, StepResult(step_id=step_id))
        res.status = "running"
        self.state.run_step_results[step_id] = res
        return True

    def _reduce_step_blocked(
        self, step_id: Optional[str], reason: Optional[str]
    ) -> bool:
        if not step_id:
            return False
        res = self.state.run_step_results.get(step_id, StepResult(step_id=step_id))
        res.status = "error"
        res.error = reason or "Blocked by upstream failure"
        self.state.run_step_results[step_id] = res
        return True

    def _reduce_step_finished(self, res: Optional[StepResult]) -> bool:
        if not res:
            return False
        self.state.run_step_results[res.step_id] = res
        return True

    @staticmethod
    def _events_by_step(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for ev in events:
            step_id = str(ev.get("step_id") or "").strip()
            if not step_id:
                continue
            normalized = dict(ev)
            if "type" not in normalized and "event_type" in normalized:
                normalized["type"] = normalized["event_type"]
            grouped.setdefault(step_id, []).append(normalized)
        return grouped

    def _reduce_run_ended(self) -> None:
        self.state.is_running = False
        self.state.drawer_visible = True

    def _reduce_run_stopped(self) -> None:
        self.state.is_running = False

    def _reduce_run_selected(
        self, run_id: str, step_results: dict[str, StepResult]
    ) -> None:
        self.state.selected_run_id = run_id
        self.state.view = WorkspaceView.RESULTS
        self.state.run_step_results = step_results

    def _handle_external_change_detected(self, event: Any) -> None:
        """Main-thread event handler: mark state and notify UI."""
        self.state.external_change_detected = True
        self._notify()

    def handle_external_change(
        self, confirm_cb: Optional[Callable[[], bool]] = None
    ) -> None:
        """Called by UI when external_change_detected is set.

        If not dirty, auto-reloads. If dirty, asks user via confirm_cb.
        confirm_cb should return True if user accepts reload.
        """
        if not self.state.external_change_detected:
            return
        self.state.external_change_detected = False
        if confirm_cb is None:

            def _default_confirm() -> bool:
                return True

            confirm_cb = _default_confirm
        if not self.state.is_dirty or confirm_cb():
            self.load_workflows()
            self._config_mtime = self._snapshot_mtimes()

    def load_workflows(self) -> None:
        """Load workflows from disk into state drafts."""
        workflows = self.config_service.load_workflows()
        self.state.workflow_drafts = {wf.id: wf for wf in workflows}
        if workflows and not self.state.selected_workflow_id:
            self.state.selected_workflow_id = workflows[0].id
        self._notify()

    def select_workflow(self, workflow_id: str) -> None:
        self.state.selected_workflow_id = workflow_id
        self.state.selected_step_id = None
        self._notify()

    def select_step(self, step_id: str) -> None:
        self.state.selected_step_id = step_id
        self._notify()

    def create_workflow(self) -> str:
        wf_id = uuid.uuid4().hex[:8]
        wf = WorkflowDef(id=wf_id, name="New Workflow")
        self.state.workflow_drafts[wf_id] = wf
        self.state.selected_workflow_id = wf_id
        self.state.selected_step_id = None
        self.state.is_dirty = True
        self._notify()
        return wf_id

    def duplicate_workflow(self) -> Optional[str]:
        wf = self.state.get_selected_workflow()
        if not wf:
            return None
        import copy

        new_wf = copy.deepcopy(wf)
        new_wf.id = uuid.uuid4().hex[:8]
        new_wf.name = f"{wf.name} (copy)"
        self.state.workflow_drafts[new_wf.id] = new_wf
        self.state.selected_workflow_id = new_wf.id
        self.state.is_dirty = True
        self._notify()
        return new_wf.id

    def delete_workflow(self, workflow_id: str) -> None:
        if workflow_id in self.state.workflow_drafts:
            del self.state.workflow_drafts[workflow_id]
            self.state.is_dirty = True
            if self.state.selected_workflow_id == workflow_id:
                self.state.selected_workflow_id = (
                    next(iter(self.state.workflow_drafts.keys()))
                    if self.state.workflow_drafts
                    else None
                )
            self.state.selected_step_id = None
            self._notify()

    def rename_workflow(self, workflow_id: str, new_name: str) -> bool:
        wf = self.state.workflow_drafts.get(workflow_id)
        if not wf:
            return False

        s = (new_name or "").strip()
        if not s:
            return False

        if wf.name == s:
            return False

        wf.name = s
        self.state.is_dirty = True
        self._notify()
        return True

    # ------------------------------------------------------------------
    # Step management (command-based for undo/redo)
    # ------------------------------------------------------------------

    def add_step_below(self, after_step_id: Optional[str] = None) -> Optional[str]:
        wf = self.state.get_selected_workflow()
        if not wf:
            return None
        sid = uuid.uuid4().hex[:8]
        step_name = f"step_{sid}"
        step = StepDef(
            id=sid,
            name=step_name,
            model=self.config_service.load_models(capability_filter="chat")[0]
            if self.config_service.load_models(capability_filter="chat")
            else "gpt-4o-2024-08-06-gs-ae",
            prompt_version=self._default_prompt_version_for_new_step(step_name),
            title="New Step",
            execution_mode="graph",
        )
        ensure_graph_io(step)
        idx = len(wf.steps)
        if after_step_id:
            for i, s in enumerate(wf.steps):
                if s.id == after_step_id:
                    idx = i + 1
                    break
        cmd = AddStepCommand(label="Add step", workflow=wf, step=step, index=idx)
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        self.state.selected_step_id = sid
        # Create empty no-code prompt drafts (no $input visible to user)
        self.state.role_drafts[sid] = ""
        self.state.prompt_drafts[sid] = ""
        self._notify()
        return sid

    def delete_step(self, step_id: str) -> None:
        wf = self.state.get_selected_workflow()
        if not wf:
            return
        cmd = DeleteStepCommand(label="Delete step", workflow=wf, step_id=step_id)
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        if self.state.selected_step_id == step_id:
            self.state.selected_step_id = None
        self._notify()

    def duplicate_step(self, step_id: str) -> Optional[str]:
        wf = self.state.get_selected_workflow()
        if not wf:
            return None
        cmd = DuplicateStepCommand(
            label="Duplicate step", workflow=wf, source_step_id=step_id
        )
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        if cmd.new_step:
            self.state.selected_step_id = cmd.new_step.id
        self._notify()
        return cmd.new_step.id if cmd.new_step else None

    def update_step_field(self, step_id: str, field_name: str, value: Any) -> None:
        step = self.state.get_selected_step()
        if not step or step.id != step_id:
            wf = self.state.get_selected_workflow()
            if wf:
                step = next((s for s in wf.steps if s.id == step_id), None)
        if not step:
            return
        cmd = UpdateStepFieldCommand(
            label=f"Change {field_name}",
            step=step,
            field_name=field_name,
            new_value=value,
        )
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        if field_name == "execution_mode":
            wf = self.state.get_selected_workflow()
            if wf:
                self._report_execution_mode_mismatch(wf)
        self._notify()

    def update_prompt_draft(self, step_id: str, content: str) -> None:
        """Update task_text draft for a step (no-code: user prompt field)."""
        self.state.prompt_drafts[step_id] = content
        # Also persist to step model for save/run to pick up
        wf = self.state.get_selected_workflow()
        if wf:
            step = next((s for s in wf.steps if s.id == step_id), None)
            if step:
                step.task_text = content
        self.state.is_dirty = True
        # No full notify for typing performance

    def update_role_draft(self, step_id: str, content: str) -> None:
        """Update role_text draft for a step (no-code: AI Role field)."""
        self.state.role_drafts[step_id] = content
        wf = self.state.get_selected_workflow()
        if wf:
            step = next((s for s in wf.steps if s.id == step_id), None)
            if step:
                step.role_text = content
        self.state.is_dirty = True
        # No full notify for typing performance

    def update_manual_input(self, text: str | None) -> None:
        """Store the user-supplied workflow input text that will be passed to the runner."""
        s = text or ""
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        s = re.sub(r"\n{3,}", "\n\n", s)
        self.state.manual_input = s.strip()

    # ------------------------------------------------------------------
    # Step ordering (replaces Move Lane — now vertical Up/Down)
    # ------------------------------------------------------------------

    def move_step(self, step_id: str, direction: str) -> None:
        """Reorder a step up or down. direction = 'up' | 'down'."""
        from core.commands import MoveStepOrderCommand

        wf = self.state.get_selected_workflow()
        if not wf:
            return
        cmd = MoveStepOrderCommand(
            label=f"Move step {direction}",
            workflow=wf,
            step_id=step_id,
            direction=direction,
        )
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        self._notify()

    # Deprecated shim kept for any callers that still use move_lane
    def move_lane(self, step_id: str, delta: int) -> None:
        direction = "down" if delta > 0 else "up"
        self.move_step(step_id, direction)

    def add_branch(self, after_step_id: str) -> None:
        """Add a branch step in lane 1, depending on after_step_id."""
        from core.commands import AddBranchCommand

        wf = self.state.get_selected_workflow()
        if not wf:
            return
        cmd = AddBranchCommand(
            label="Add branch", workflow=wf, source_step_id=after_step_id, lane=1
        )
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        if cmd.new_step:
            self.state.selected_step_id = cmd.new_step.id
        self._notify()

    def merge_branch(self, branch_step_ids: list[str], after_step_id: str) -> None:
        """Create a merge step depending on branch_step_ids, inserted after after_step_id."""
        from core.commands import MergeBranchCommand

        wf = self.state.get_selected_workflow()
        if not wf or not branch_step_ids:
            return
        cmd = MergeBranchCommand(
            label="Merge branch",
            workflow=wf,
            branch_step_ids=branch_step_ids,
            after_step_id=after_step_id,
        )
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        if cmd.new_step:
            self.state.selected_step_id = cmd.new_step.id
        self._notify()

    # ------------------------------------------------------------------
    # Graph Ports (Epic E2 / E6)
    # ------------------------------------------------------------------

    def add_input_port(self, step_id: str, port_def) -> None:
        from core.commands import AddInputPortCommand

        step = (
            self.state.get_selected_step()
            if self.state.selected_step_id == step_id
            else None
        )
        if not step:
            wf = self.state.get_selected_workflow()
            if wf:
                step = next((s for s in wf.steps if s.id == step_id), None)
        if not step:
            return
        cmd = AddInputPortCommand(label="Add Input Port", step=step, port=port_def)
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        self._notify()

    def remove_input_port(self, step_id: str, port_name: str) -> None:
        from core.commands import RemoveInputPortCommand

        step = (
            self.state.get_selected_step()
            if self.state.selected_step_id == step_id
            else None
        )
        if not step:
            wf = self.state.get_selected_workflow()
            if wf:
                step = next((s for s in wf.steps if s.id == step_id), None)
        if not step:
            return
        cmd = RemoveInputPortCommand(
            label="Remove Input Port", step=step, port_name=port_name
        )
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        self._notify()

    def add_output_port(self, step_id: str, port_def) -> None:
        from core.commands import AddOutputPortCommand

        step = (
            self.state.get_selected_step()
            if self.state.selected_step_id == step_id
            else None
        )
        if not step:
            wf = self.state.get_selected_workflow()
            if wf:
                step = next((s for s in wf.steps if s.id == step_id), None)
        if not step:
            return
        cmd = AddOutputPortCommand(label="Add Output Port", step=step, port=port_def)
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        self._notify()

    def remove_output_port(self, step_id: str, port_name: str) -> None:
        from core.commands import RemoveOutputPortCommand

        step = (
            self.state.get_selected_step()
            if self.state.selected_step_id == step_id
            else None
        )
        if not step:
            wf = self.state.get_selected_workflow()
            if wf:
                step = next((s for s in wf.steps if s.id == step_id), None)
        if not step:
            return
        cmd = RemoveOutputPortCommand(
            label="Remove Output Port", step=step, port_name=port_name
        )
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        self._notify()

    def update_port_config(
        self,
        step_id: str,
        port_type: str,
        port_name: str,
        field_name: str,
        new_value: Any,
    ) -> None:
        from core.commands import UpdatePortConfigCommand

        step = self.state.get_step_by_id(step_id)
        if not step:
            return

        cmd = UpdatePortConfigCommand(
            label=f"Update {port_type.title()} Port",
            step=step,
            port_type=port_type,
            port_name=port_name,
            field_name=field_name,
            new_value=new_value,
        )
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        self._notify()

    # ------------------------------------------------------------------
    # High-level connection helpers (simple-mode UX)
    # ------------------------------------------------------------------

    def connect_step_input(
        self,
        step_id: str,
        source_step_id: str,
        source_port: str = "output",
        input_port: str = "input",
    ) -> None:
        """Add an upstream source to a step's input port (creating the port if needed)."""
        from core.commands import AddInputSourceCommand
        from core.models import SourceRef

        step = self.state.get_step_by_id(step_id)
        if not step:
            return
        cmd = AddInputSourceCommand(
            label=f"Connect {(step.title or step.id)}:{input_port}",
            step=step,
            port_name=input_port,
            source=SourceRef(step_id=source_step_id, port=source_port),
        )
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        self._notify()

    def disconnect_step_input(
        self,
        step_id: str,
        input_port: str,
        source_index: int,
    ) -> None:
        """Remove a source by index from the named input port."""
        from core.commands import RemoveInputSourceCommand

        step = self.state.get_step_by_id(step_id)
        if not step:
            return
        cmd = RemoveInputSourceCommand(
            label=f"Disconnect {(step.title or step.id)}:{input_port}",
            step=step,
            port_name=input_port,
            source_index=source_index,
        )
        self.state.command_stack.execute(cmd)
        self.state.is_dirty = True
        self._notify()

    # ------------------------------------------------------------------
    # Attachment bindings (Gap 3)
    # ------------------------------------------------------------------

    def update_attachment_binding(self, variable_name: str, file_path: str) -> None:
        """Bind file_path to variable_name for the current run.

        Stored in state.attachment_bindings (persisted via session).
        """
        self.state.attachment_bindings[variable_name] = file_path
        self.state.is_dirty = True
        log.debug("Attachment binding: %s → %s", variable_name, file_path)
        self._notify()

    def attach_files_to_slot(
        self, step_id: str, slot_key: str, file_paths: list[str]
    ) -> int:
        """
        Bind one or many files starting from a selected slot.

        First file binds to the selected slot. Remaining files create new slots
        on the same step and bind one file per slot.
        """
        paths = [str(p).strip() for p in file_paths if str(p).strip()]
        if not paths:
            return 0
        step = self.state.get_step_by_id(step_id)
        if not step or "::" not in slot_key:
            return 0
        key_step_id, _ = slot_key.split("::", 1)
        if key_step_id != step_id:
            return 0

        self.state.attachment_bindings[slot_key] = paths[0]
        bound_count = 1

        used_vars = {s.variable_name for s in step.attachments}
        for path in paths[1:]:
            filename = Path(path).name
            stem = Path(path).stem
            base = re.sub(r"[^a-zA-Z0-9_]+", "_", stem).strip("_").lower() or "file"
            variable_name = f"{step_id}_{base}"
            idx = 2
            while variable_name in used_vars:
                variable_name = f"{step_id}_{base}_{idx}"
                idx += 1
            used_vars.add(variable_name)

            slot_id = self.add_attachment_slot(
                step_id,
                label=filename,
                required=False,
                variable_name=variable_name,
            )
            if not slot_id:
                continue
            self.state.attachment_bindings[f"{step_id}::{slot_id}"] = path
            bound_count += 1

        self.state.is_dirty = True
        self._notify()
        return bound_count

    def remove_attachment_binding(self, variable_name: str) -> None:
        """Remove a file binding for variable_name."""
        self.state.attachment_bindings.pop(variable_name, None)
        self.state.is_dirty = True
        self._notify()

    def delete_attached_file(
        self, slot_key: str, *, remove_binding: bool = True
    ) -> bool:
        """
        Delete physical file currently bound to a slot key.

        Returns True if a file was deleted, False otherwise.
        """
        path = self.state.attachment_bindings.get(slot_key)
        if not path:
            return False
        try:
            p = Path(path)
            if p.is_file():
                p.unlink()
        except OSError:
            return False
        if remove_binding:
            self.remove_attachment_binding(slot_key)
        return True

    @staticmethod
    def _normalize_attachment_accepted_types(
        raw: Optional[list[str]],
    ) -> Optional[list[str]]:
        """Lowercase, strip, drop empty, dedupe while preserving order."""
        if raw is None:
            return None
        seen: set[str] = set()
        out: list[str] = []
        for item in raw:
            if item is None:
                continue
            s = str(item).strip().lower()
            if not s or s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out or None

    def add_attachment_slot(
        self,
        step_id: str,
        *,
        label: str = "Input file",
        required: bool = False,
        variable_name: Optional[str] = None,
        accepted_types: Optional[list[str]] = None,
    ) -> Optional[str]:
        """Create a new attachment slot on a step."""
        step = self.state.get_step_by_id(step_id)
        if not step:
            return None

        from core.models import AttachmentSlot

        slot_id = f"slot_{uuid.uuid4().hex[:8]}"
        normalized_label = (label or "Input file").strip() or "Input file"
        normalized_var = (variable_name or "").strip() or f"{step_id}_{slot_id}"
        types_norm = self._normalize_attachment_accepted_types(accepted_types)

        step.attachments.append(
            AttachmentSlot(
                slot_id=slot_id,
                variable_name=normalized_var,
                label=normalized_label,
                required=bool(required),
                accepted_types=types_norm,
            )
        )
        self.state.is_dirty = True
        self._notify()
        return slot_id

    def update_attachment_slot(
        self,
        step_id: str,
        slot_id: str,
        *,
        label: Optional[str] = None,
        variable_name: Optional[str] = None,
        required: Optional[bool] = None,
        accepted_types: Optional[list[str]] = None,
        accepted_types_clear: bool = False,
    ) -> bool:
        """Update editable fields on an attachment slot. Binding key stays step_id::slot_id."""
        step = self.state.get_step_by_id(step_id)
        if not step:
            return False
        slot = next((s for s in step.attachments if s.slot_id == slot_id), None)
        if not slot:
            return False

        if label is not None:
            stripped = (label or "").strip()
            slot.label = stripped or "Input file"
        if variable_name is not None:
            vn = (variable_name or "").strip()
            if not vn:
                return False
            slot.variable_name = vn
        if required is not None:
            slot.required = bool(required)
        if accepted_types_clear:
            slot.accepted_types = None
        elif accepted_types is not None:
            slot.accepted_types = self._normalize_attachment_accepted_types(
                accepted_types
            )

        self.state.is_dirty = True
        self._notify()
        return True

    def remove_attachment_slot(self, step_id: str, slot_id: str) -> None:
        """Remove an attachment slot and its binding from a step."""
        step = self.state.get_step_by_id(step_id)
        if not step:
            return

        before = len(step.attachments)
        step.attachments = [
            slot for slot in step.attachments if slot.slot_id != slot_id
        ]
        if len(step.attachments) == before:
            return

        self.state.attachment_bindings.pop(f"{step_id}::{slot_id}", None)
        self.state.is_dirty = True
        self._notify()

    def set_graph_runtime_enabled(self, enabled: bool) -> None:
        """Update global runtime toggle and recompute execution mismatch warnings."""
        self.state.enable_graph_runtime = bool(enabled)
        wf = self.state.get_selected_workflow()
        if wf:
            self._report_execution_mode_mismatch(wf)
        self._notify()

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def undo(self) -> None:
        cmd = self.state.command_stack.undo()
        if cmd:
            self.state.is_dirty = True
            self._notify()

    def redo(self) -> None:
        cmd = self.state.command_stack.redo()
        if cmd:
            self.state.is_dirty = True
            self._notify()

    @property
    def can_undo(self) -> bool:
        return self.state.command_stack.can_undo()

    @property
    def can_redo(self) -> bool:
        return self.state.command_stack.can_redo()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_prompt_refs(workflows: list[WorkflowDef]) -> set[tuple[str, str]]:
        """Collect (step_name, prompt_version) references from workflows."""
        refs: set[tuple[str, str]] = set()
        for wf in workflows:
            for step in wf.steps:
                if step.name and step.prompt_version:
                    refs.add((step.name, step.prompt_version))
        return refs

    def save(self) -> tuple[bool, str]:
        """Save all workflow drafts and prompt drafts to disk.

        Returns (success, message).
        """
        if self.state.is_running:
            return False, "Cannot save while a workflow is running."

        try:
            persisted_workflows = self.config_service.load_workflows()
            persisted_prompt_refs = self._collect_prompt_refs(persisted_workflows)
            workflows = list(self.state.workflow_drafts.values())
            draft_prompt_refs = self._collect_prompt_refs(workflows)
            workflow_id_counts: dict[str, int] = {}
            for wf in workflows:
                workflow_id_counts[wf.id] = workflow_id_counts.get(wf.id, 0) + 1

            # Validate ALL workflow drafts before persisting any of them.
            # A single invalid workflow in the draft set blocks the entire save
            # so that the persisted disk state is always a trustworthy source of truth.
            from core.config_validation import validate_workflow

            available_prompts = {
                s: self.config_service.list_prompt_versions(s)
                for s in self.config_service.list_prompt_steps()
            }
            available_models = self.config_service.load_models()
            all_validation_errors: list[str] = []
            for wf_draft in workflows:
                issues = validate_workflow(
                    wf_draft,
                    workflows,
                    available_prompts,
                    available_models,
                    workflow_id_counts=workflow_id_counts,
                )
                errors = [i for i in issues if i.level == "error"]
                if errors:
                    err_lines = "\n".join(f"    - {e.message}" for e in errors)
                    all_validation_errors.append(
                        f"  Workflow '{wf_draft.name}' ({wf_draft.id}):\n{err_lines}"
                    )
            if all_validation_errors:
                summary = "\n".join(all_validation_errors)
                return (
                    False,
                    f"Save blocked — validation errors in the following workflow(s):\n{summary}",
                )

            self.config_service.save_workflows(workflows)

            # Save prompt drafts
            step_meta = {}
            for wf in workflows:
                for s in wf.steps:
                    step_meta[s.id] = (s.name, s.prompt_version)

            for step_id, content in self.state.prompt_drafts.items():
                if step_id in step_meta:
                    name, version = step_meta[step_id]
                    self.config_service.save_prompt(name, version, content)

            # Remove prompt files that were referenced before save but are no longer
            # referenced by any workflow after save (e.g. workflow deletion).
            orphan_prompt_refs = persisted_prompt_refs - draft_prompt_refs
            for step_name, version in orphan_prompt_refs:
                self.config_service.delete_prompt(step_name, version)

            self.state.is_dirty = False
            self.state.command_stack.clear()
            return True, "Saved successfully."
        except Exception as e:
            log.exception("Save failed")
            return False, f"Save failed: {e}"

    # ------------------------------------------------------------------
    # Run orchestration
    # ------------------------------------------------------------------

    @property
    def can_run(self) -> bool:
        """Check if the currently selected workflow is completely valid and can be run."""
        wf = self.state.get_selected_workflow()
        if not wf or self.state.is_running or not self.state.is_provider_ready:
            return False

        from core.config_validation import validate_workflow

        available_prompts = {
            s: self.config_service.list_prompt_versions(s)
            for s in self.config_service.list_prompt_steps()
        }
        available_models = self.config_service.load_models()
        wf_errors = validate_workflow(
            wf,
            list(self.state.workflow_drafts.values()),
            available_prompts,
            available_models,
        )
        if any(e.level == "error" for e in wf_errors):
            return False

        # Phase 2 & 7: Validate Required Attachments
        for step in wf.steps:
            for slot in step.attachments:
                if slot.required:
                    if not self.state.attachment_bindings.get(
                        f"{step.id}::{slot.slot_id}"
                    ):
                        return False
        return True

    def start_run(self) -> bool:
        """Start a workflow run on a background thread.
        Reads manual input from the state (if tracked there) or bindings,
        but for MVP we expect bindings to map slots to values.
        """
        wf = self.state.get_selected_workflow()
        if not wf or self.state.is_running or not self.client:
            return False

        # Phase 4 & 7: Validate whole workflow before running
        from core.config_validation import validate_workflow

        available_prompts = {
            s: self.config_service.list_prompt_versions(s)
            for s in self.config_service.list_prompt_steps()
        }
        available_models = self.config_service.load_models()
        wf_errors = validate_workflow(
            wf,
            list(self.state.workflow_drafts.values()),
            available_prompts,
            available_models,
        )
        critical_errors = [e for e in wf_errors if e.level == "error"]
        if critical_errors:
            msg = "\n".join(f"- {e.message}" for e in critical_errors)

            log.warning("Cannot start run, workflow is invalid:\n%s", msg)
            dialogs.show_error(
                "Workflow Error", f"Cannot run this workflow due to errors:\n{msg}"
            )
            return False

        # Phase 2 & 7: Validate Required Attachments
        variables: dict[str, Any] = {}
        attachment_meta: dict[str, dict[str, Any]] = {}
        pending_attachment_ingest_events: list[dict[str, Any]] = []
        missing_required = []
        ingest_errors = []
        for step in wf.steps:
            for slot in step.attachments:
                slot_key = f"{step.id}::{slot.slot_id}"
                path = self.state.attachment_bindings.get(slot_key)
                if not path and slot.required:
                    missing_required.append(
                        "Step "
                        f"'{step.title or step.id}': "
                        f"missing required attachment {slot.label}"
                    )
                elif path:
                    from core.ingestion import ingest_file

                    res = ingest_file(path)
                    file_sha256 = ""
                    size_bytes = 0
                    status = "ok"
                    error_msg: str | None = None
                    try:
                        file_bytes = Path(path).read_bytes()
                        file_sha256 = hashlib.sha256(file_bytes).hexdigest()
                        size_bytes = len(file_bytes)
                    except Exception:
                        status = "error"
                        error_msg = "Unable to read file for digest"
                    if res.ok:
                        variables[slot.variable_name] = res.content
                        attachment_meta[slot.variable_name] = {
                            "slot_id": slot.slot_id,
                            "step_id": step.id,
                            "sha256": file_sha256,
                            "file_path": path,
                            "size_bytes": size_bytes,
                        }
                    else:
                        status = "error"
                        error_msg = res.error or "ingest_failed"
                    pending_attachment_ingest_events.append(
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "event_type": "attachment_ingested",
                            "step_id": step.id,
                            "slot_id": slot.slot_id,
                            "variable_name": slot.variable_name,
                            "file_path": path,
                            "size_bytes": size_bytes,
                            "sha256": file_sha256,
                            "status": status,
                            "error": error_msg,
                        }
                    )
                    if not res.ok:
                        ingest_errors.append(
                            "Step "
                            f"'{step.title or step.id}': "
                            f"failed to read attachment {slot.label}"
                        )

        if missing_required:
            log.warning(
                "Cannot start run, missing required attachments: %s", missing_required
            )

            dialogs.show_error(
                "Missing Attachments",
                "Cannot run workflow. Please attach the following required files:\n\n"
                + "\n".join(f"  • {m}" for m in missing_required),
            )
            return False
        if ingest_errors:
            dialogs.show_error(
                "Attachment Error",
                "Cannot run workflow due to attachment read failures:\n\n"
                + "\n".join(f"  • {m}" for m in ingest_errors),
            )
            return False

        self._report_execution_mode_mismatch(wf)
        engine_mode = self._resolve_run_engine_mode(wf)

        self._reduce_run_prepared_for_start()
        self._notify()

        def _on_run_start_with_attachment_events(run_ctx: RunContext) -> None:
            for ev in pending_attachment_ingest_events:
                payload = dict(ev)
                payload["run_id"] = run_ctx.run_id
                self.storage.append_event(run_ctx.run_id, payload)
                if self.event_bus:
                    self.event_bus.publish(
                        attachment_ingested(
                            run_id=run_ctx.run_id,
                            step_id=payload["step_id"],
                            slot_id=payload["slot_id"],
                            variable_name=payload["variable_name"],
                            file_path=payload["file_path"],
                            size_bytes=payload["size_bytes"],
                            sha256=payload["sha256"],
                            status=payload["status"],
                            error=payload.get("error"),
                        )
                    )

        if engine_mode == "graph":
            from core.async_graph_runner import AsyncGraphRunner

            self.runner = self._build_graph_runner(AsyncGraphRunner)

            # Kick off background execution
            self._start_runner(
                workflow_def=wf,
                initial_input=self.state.manual_input,
                initial_variables=variables,
                on_run_start=_on_run_start_with_attachment_events,
                attachment_meta=attachment_meta,
            )
        else:
            self.runner = WorkflowRunner(
                client=self.client,
                prompt_registry=self.prompt_registry,
                storage=self.storage,
                event_bus=self.event_bus,
            )

            # Kick off background execution
            self._start_runner(
                workflow_def=wf,
                initial_input=self.state.manual_input,
                initial_variables=variables,
                on_run_start=_on_run_start_with_attachment_events,
                attachment_meta=attachment_meta,
            )

        return True

    def _resolve_run_engine_mode(self, wf: WorkflowDef) -> str:
        """
        Resolve effective runtime mode from the global runtime toggle.

        ARCH-004 policy:
        - WorkspaceState.enable_graph_runtime is the single source of truth for
          selecting the runner engine at run time.
        - Step-level execution_mode is retained for authoring metadata and
          mismatch warnings only.
        """
        return "graph" if self.state.enable_graph_runtime else "legacy"

    def _report_execution_mode_mismatch(self, wf: WorkflowDef) -> None:
        """
        Guard-only contract check for Wave 0.

        Detects divergence between the global runner policy
        (WorkspaceState.enable_graph_runtime) and per-step StepDef.execution_mode.
        This function intentionally does not change runtime behavior.
        """
        expected_mode = "graph" if self.state.enable_graph_runtime else "legacy"

        def _normalize_mode(mode: str) -> str:
            # Backward-compatible alias: "sequential" maps to legacy execution.
            return "legacy" if mode == "sequential" else mode

        mismatched = []
        for step in wf.steps:
            step_mode = _normalize_mode(getattr(step, "execution_mode", expected_mode))
            if step_mode != expected_mode:
                mismatched.append(step.id)
        self._last_execution_mode_mismatches = mismatched
        if mismatched:
            log.warning(
                "Execution mode contract mismatch detected: global=%s, mismatched_steps=%s",
                expected_mode,
                mismatched,
            )

    def has_execution_mode_mismatch(self, step_id: str) -> bool:
        return step_id in self._last_execution_mode_mismatches

    def _default_prompt_version_for_new_step(self, step_name: str) -> str:
        """
        Wave 0 guard: always provide a valid prompt_version when constructing StepDef.
        """
        try:
            versions = self.config_service.list_prompt_versions(step_name)
            if versions:
                return versions[-1]
        except Exception:
            log.debug(
                "Failed to list prompt versions for %s; falling back to v1",
                step_name,
                exc_info=True,
            )
        return "1"

    def _build_graph_runner(self, graph_runner_cls):
        """
        Wave 0 compatibility adapter: support both max_concurrency and max_workers.
        """
        common_kwargs = {
            "client": self.client,
            "prompt_registry": self.prompt_registry,
            "storage": self.storage,
            "event_bus": self.event_bus,
        }
        try:
            return graph_runner_cls(max_concurrency=5, **common_kwargs)
        except TypeError:
            return graph_runner_cls(max_workers=5, **common_kwargs)

    def _start_runner(self, **kwargs) -> None:
        """
        Wave 0 compatibility adapter: support both run_async and run_thread.
        """
        if not self.runner:
            raise RuntimeError("Runner was not initialized.")
        if hasattr(self.runner, "run_async"):
            self.runner.run_async(**kwargs)
            return
        if hasattr(self.runner, "run_thread"):
            self.runner.run_thread(**kwargs)
            return
        if hasattr(self.runner, "run"):
            self.runner.run(**kwargs)
            return
        raise AttributeError("Runner does not expose a supported start method.")

    def _handle_run_started(self, event: Any) -> None:
        """Executed on main thread when a run starts."""
        self._reduce_run_started(event.get("run_id"))

    def _handle_node_ready(self, event: Any) -> None:
        """Executed when a node graph is ready to be scheduled."""
        if self._reduce_node_ready(event.get("step_id")):
            self._notify()

    def _handle_step_started(self, event: Any) -> None:
        """Executed moving step to running state."""
        if self._reduce_step_running(event.get("step_id")):
            self._notify()

    def _handle_node_blocked(self, event: Any) -> None:
        """Executed when a node is blocked due to upstream failures in DAG."""
        if self._reduce_step_blocked(event.get("step_id"), event.get("reason")):
            self._notify()

    def _handle_step_finished(self, event: Any) -> None:
        """Executed on main thread when a step completes."""
        res = event.get("result")
        run_id = event.get("run_id")
        if res and run_id:
            try:
                grouped = self._events_by_step(self.storage.load_events(run_id))
                res.node_events = grouped.get(res.step_id, [])
            except Exception:
                # Never fail run rendering due to event hydration issues.
                pass
        if self._reduce_step_finished(res):
            self._notify()

    def _handle_run_finished(self, event: Any) -> None:
        """Executed on main thread when a run finishes or fails."""
        self._reduce_run_ended()
        self._notify()

    def _handle_run_failed(self, event: Any) -> None:
        """Executed on main thread when a run fails."""
        self._reduce_run_ended()
        self._notify()

    def stop_run(self) -> None:
        if self.runner:
            self.runner.cancel()
            self._reduce_run_stopped()
            self._notify()

    # Compatibility Aliases for UI/Shell
    run_workflow = start_run
    stop_execution = stop_run

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def load_run_history(self) -> list[dict]:
        """Return recent run summaries."""
        try:
            return [
                {
                    "run_id": r.run_id,
                    "workflow": r.workflow_name,
                    "status": r.status,
                    "started": r.started_at,
                }
                for r in self.storage.list_runs()[-20:]
            ]
        except Exception:
            return []

    def select_run(self, run_id: str) -> None:
        step_results: dict[str, StepResult]
        # Load step results
        try:
            self.storage.load_run(run_id)
            steps = self.storage.load_all_steps(run_id)
            step_results = {sr.step_id: sr for sr in steps}
            try:
                grouped = self._events_by_step(self.storage.load_events(run_id))
                for step_id, sr in step_results.items():
                    sr.node_events = grouped.get(step_id, sr.node_events or [])
            except Exception:
                pass
        except Exception:
            step_results = {}
        self._reduce_run_selected(run_id, step_results)
        self._notify()

    # ------------------------------------------------------------------
    # View-model builders (convenience for panels)
    # ------------------------------------------------------------------

    def get_flow_viewmodel(self):
        """Build flow canvas viewmodel with attachment file counts."""
        wf = self.state.get_selected_workflow()
        if not wf:
            return [], []
        return build_flow_viewmodel(
            wf,
            self.state.selected_step_id,
            self.state.run_step_results,
            self.state.attachment_bindings,  # Pass bindings for file count
        )

    def get_inspector_viewmodel(self):
        step = self.state.get_selected_step()
        if not step:
            return None
        prompt = self.state.prompt_drafts.get(step.id, "")
        if not prompt:
            try:
                prompt = (
                    self.config_service.load_prompt(step.name, step.prompt_version)
                    or ""
                )
            except Exception:
                prompt = ""
            self.state.prompt_drafts[step.id] = prompt
        return build_inspector_viewmodel(step, prompt)

    # ------------------------------------------------------------------
    # Mode / View toggles
    # ------------------------------------------------------------------

    def toggle_mode(self) -> None:
        if self.state.mode == WorkspaceMode.SIMPLE:
            self.state.mode = WorkspaceMode.ADVANCED
        else:
            self.state.mode = WorkspaceMode.SIMPLE
        self._notify()

    def toggle_view(self) -> None:
        if self.state.view == WorkspaceView.DESIGN:
            self.state.view = WorkspaceView.RESULTS
        else:
            self.state.view = WorkspaceView.DESIGN
        self._notify()

    def set_drawer_tab(self, tab: DrawerTab) -> None:
        self.state.drawer_tab = tab
        self._notify()

    def toggle_drawer(self) -> None:
        self.state.drawer_visible = not self.state.drawer_visible
        self._notify()
