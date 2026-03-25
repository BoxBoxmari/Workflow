from unittest.mock import MagicMock

import pytest

from core.models import StepDef, WorkflowDef
from ui.inspector_panel import InspectorPanel
from ui.workspace_controller import WorkspaceController


def make_mock_ctrl():
    return WorkspaceController(
        MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
    )


@pytest.fixture(scope="module")
def app_root():
    import customtkinter as ctk

    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


def test_execution_mode_mismatch_shows_warning_without_mutating_step(app_root):
    ctrl = make_mock_ctrl()
    ctrl.config_service.load_models.return_value = ["gpt"]

    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="legacy",
    )
    graph_step = StepDef(
        id="s2",
        name="step2",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step, graph_step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.mode = MagicMock(value="advanced")
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"
    ctrl.state.enable_graph_runtime = False

    # Establish mismatch state from source-of-truth check.
    ctrl._report_execution_mode_mismatch(wf)

    panel = InspectorPanel(app_root, ctrl)
    panel.refresh()

    # Contract guard must never mutate persisted step declaration.
    assert step.execution_mode == "legacy"

    # Mismatch must be surfaced to user as warning/banner in inspector.
    assert panel.model_warning.winfo_manager() != ""
    assert "execution mode" in panel.model_warning.cget("text").lower()


def test_inspector_execution_mode_change_does_not_mutate_global_runner_policy(app_root):
    ctrl = make_mock_ctrl()
    ctrl.config_service.load_models.return_value = ["gpt"]

    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="legacy",
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.mode = MagicMock(value="advanced")
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"
    ctrl.state.enable_graph_runtime = False

    panel = InspectorPanel(app_root, ctrl)
    panel.refresh()
    app_root.update_idletasks()
    app_root.update()

    # Simulate user switching execution mode from inspector control.
    panel.exec_mode_var.set("graph")
    app_root.update_idletasks()
    app_root.update()

    # Per-step declaration updates, but global toggle is independent.
    assert step.execution_mode == "graph"
    assert ctrl.state.enable_graph_runtime is False
