"""
ui.workspace_state — Central state container for the workspace UI.

Replaces the old DesignerState with a richer, explicitly-typed model
that tracks selection, mode, view, drafts, run state, and undo history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.commands import CommandStack
from core.enums import DrawerTab, WorkspaceMode, WorkspaceView
from core.models import WorkflowDef, StepResult


@dataclass
class WorkspaceState:
    """All mutable workspace state in one place.

    The WorkspaceController is the sole mutator.
    Panels read this state to render; they never set it directly.
    """

    # Selection
    selected_workflow_id: Optional[str] = None
    selected_step_id: Optional[str] = None
    selected_run_id: Optional[str] = None

    # UI mode
    mode: WorkspaceMode = WorkspaceMode.SIMPLE
    view: WorkspaceView = WorkspaceView.DESIGN

    # Drafts (key = workflow_id or step_id)
    workflow_drafts: dict[str, WorkflowDef] = field(default_factory=dict)
    prompt_drafts: dict[str, str] = field(default_factory=dict)  # task_text per step
    role_drafts: dict[str, str] = field(default_factory=dict)  # role_text per step

    # Run state
    run_step_results: dict[str, StepResult] = field(default_factory=dict)
    attachment_bindings: dict[str, str] = field(
        default_factory=dict
    )  # step_id::slot_id → file_path

    # Drawer
    drawer_tab: DrawerTab = DrawerTab.OUTPUT
    drawer_visible: bool = False

    # Flags
    is_dirty: bool = False
    is_running: bool = False
    external_change_detected: bool = False
    is_provider_ready: bool = False
    enable_graph_runtime: bool = False

    # Manual workflow input (set by UI before run)
    manual_input: str = ""

    # Undo/redo
    command_stack: CommandStack = field(default_factory=CommandStack)

    # Appearance
    appearance_mode: str = "Dark"

    def get_selected_workflow(self) -> Optional[WorkflowDef]:
        """Return the currently selected workflow draft, or None."""
        if self.selected_workflow_id:
            return self.workflow_drafts.get(self.selected_workflow_id)
        return None

    def get_step_by_id(self, step_id: str):
        """Return a specific step in the current workflow, or None."""
        wf = self.get_selected_workflow()
        if wf:
            for s in wf.steps:
                if s.id == step_id:
                    return s
        return None

    def get_selected_step(self):
        """Return the currently selected StepDef, or None."""
        if self.selected_step_id:
            return self.get_step_by_id(self.selected_step_id)
        return None
