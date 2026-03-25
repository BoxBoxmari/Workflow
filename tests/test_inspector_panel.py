import pytest
import tkinter as tk
from unittest.mock import MagicMock
from core.models import InputPortDef, OutputPortDef, SourceRef, StepDef, WorkflowDef
from ui.inspector_panel import InspectorPanel, JOIN_STRATEGY_LABEL_TO_VALUE
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


def test_inspector_panel_rendering(app_root):
    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
        inputs=[InputPortDef(name="in1")],
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.mode = MagicMock(value="advanced")
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"

    panel = InspectorPanel(app_root, ctrl)
    panel.refresh()

    # Verify the execution mode variable is bound correctly
    assert panel.exec_mode_var.get() == "graph"


def test_inspector_graph_join_strategy_values_use_user_friendly_labels(app_root):
    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
        inputs=[InputPortDef(name="in1", join_strategy="concat")],
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.mode = MagicMock(value="advanced")
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"

    panel = InspectorPanel(app_root, ctrl)
    panel.refresh()

    def _walk_widgets(root_widget):
        stack = [root_widget]
        while stack:
            current = stack.pop()
            children = list(current.winfo_children())
            stack.extend(children)
            yield current

    join_values = None
    for widget in _walk_widgets(panel.io_container):
        if widget.__class__.__name__ != "CTkComboBox":
            continue
        try:
            values = list(widget.cget("values"))
        except Exception:
            continue
        if set(JOIN_STRATEGY_LABEL_TO_VALUE.keys()).issubset(set(values)):
            join_values = values
            break

    assert join_values is not None, "Join strategy combobox was not found"
    assert join_values == list(JOIN_STRATEGY_LABEL_TO_VALUE.keys())


def test_result_drawer_rendering(app_root):
    from ui.result_drawer import ResultDrawer
    from core.models import StepResult

    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1", name="step1", model="gpt", prompt_version="1", execution_mode="graph"
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"
    ctrl.state.drawer_visible = True

    res = StepResult(
        step_id="s1",
        step_name="step1",
        status="success",
        node_events=[{"type": "node_ready", "timestamp": "2026-03-21T15:00:00"}],
    )
    ctrl.state.run_step_results["s1"] = res

    drawer = ResultDrawer(app_root, ctrl)
    drawer.refresh()

    # Assert events tab was populated by Graph Mode output
    evt_text = drawer.textboxes["events"].get("1.0", tk.END)
    assert "node_ready" in evt_text


def _walk_widgets(root_widget):
    stack = [root_widget]
    while stack:
        current = stack.pop()
        children = list(current.winfo_children())
        stack.extend(children)
        yield current


def test_graph_mode_no_add_input_port_button(app_root):
    """In Graph mode the '+ Input Port' button must not exist."""
    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
        inputs=[InputPortDef(name="in1")],
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.mode = MagicMock(value="advanced")
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"

    panel = InspectorPanel(app_root, ctrl)
    panel.refresh()

    button_texts = [
        w.cget("text")
        for w in _walk_widgets(panel.io_container)
        if w.__class__.__name__ == "CTkButton"
    ]
    assert "+ Input Port" not in button_texts, (
        "'+ Input Port' button must not appear in Graph mode"
    )


def test_graph_mode_add_source_button_present(app_root):
    """In Graph mode each input port must still have a '+ Source' button."""
    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
        inputs=[InputPortDef(name="in1"), InputPortDef(name="in2")],
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.mode = MagicMock(value="advanced")
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"

    panel = InspectorPanel(app_root, ctrl)
    panel.refresh()

    button_texts = [
        w.cget("text")
        for w in _walk_widgets(panel.io_container)
        if w.__class__.__name__ == "CTkButton"
    ]
    add_source_count = button_texts.count("+ Source")
    assert add_source_count == 2, (
        f"Expected one '+ Source' button per input port, got {add_source_count}"
    )


def test_simple_mode_shows_connection_editor(app_root):
    """In simple mode, IO container shows 'Add connection' instead of 'Graph Inputs'."""
    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
        inputs=[InputPortDef(name="input")],
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.mode = MagicMock(value="simple")
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"

    panel = InspectorPanel(app_root, ctrl)
    panel.refresh()

    label_texts = [
        w.cget("text")
        for w in _walk_widgets(panel.io_container)
        if w.__class__.__name__ == "CTkLabel"
    ]
    button_texts = [
        w.cget("text")
        for w in _walk_widgets(panel.io_container)
        if w.__class__.__name__ == "CTkButton"
    ]
    assert "Receives input from" in label_texts
    assert "Graph Inputs" not in label_texts
    assert "+ Add connection" in button_texts


def test_inspector_rebuilds_io_on_same_step(app_root):
    """After adding a source, refresh() on same step_id must update IO container."""
    from core.models import SourceRef

    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
        inputs=[InputPortDef(name="input")],
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.mode = MagicMock(value="simple")
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"

    panel = InspectorPanel(app_root, ctrl)
    panel.refresh()

    # Initially "No connections yet."
    label_texts = [
        w.cget("text")
        for w in _walk_widgets(panel.io_container)
        if w.__class__.__name__ == "CTkLabel"
    ]
    assert "No connections yet." in label_texts

    # Add a source, then refresh same step
    step.inputs[0].sources.append(SourceRef(step_id="upstream1", port="output"))
    panel.refresh()

    label_texts_after = [
        w.cget("text")
        for w in _walk_widgets(panel.io_container)
        if w.__class__.__name__ == "CTkLabel"
    ]
    assert "No connections yet." not in label_texts_after


def test_simple_mode_hides_internal_ids_and_ports(app_root):
    ctrl = make_mock_ctrl()
    upstream = StepDef(
        id="u1",
        name="upstream_step",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
        outputs=[OutputPortDef(name="report")],
    )
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
        inputs=[
            InputPortDef(
                name="input",
                sources=[SourceRef(step_id="u1", port="report")],
            )
        ],
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[upstream, step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.mode = MagicMock(value="simple")
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"

    panel = InspectorPanel(app_root, ctrl)
    panel.refresh()

    # Display text should hide internal ids and raw port suffixes.
    label_texts = [
        w.cget("text")
        for w in _walk_widgets(panel.io_container)
        if w.__class__.__name__ == "CTkLabel"
    ]
    assert "← upstream_step" in label_texts
    assert all("·" not in text for text in label_texts)
    assert all("(u1)" not in text for text in label_texts)
