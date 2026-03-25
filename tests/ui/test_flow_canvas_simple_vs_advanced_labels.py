import pytest
import customtkinter as ctk

from unittest.mock import MagicMock

from core.enums import StepStatus
from ui.flow_canvas import FlowCanvas
from ui.viewmodels import FlowEdgeVM, FlowNodeVM


@pytest.fixture(scope="module")
def app_root():
    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


def _walk_widgets(root_widget):
    stack = [root_widget]
    while stack:
        current = stack.pop()
        children = list(current.winfo_children())
        stack.extend(children)
        yield current


def _collect_label_texts(root_widget):
    texts = []
    for w in _walk_widgets(root_widget):
        if w.__class__.__name__ != "CTkLabel":
            continue
        try:
            t = w.cget("text")
        except Exception:
            continue
        if t is not None and t != "":
            texts.append(t)
    return texts


def _make_ctrl(mode_value: str, nodes, edges):
    ctrl = MagicMock()

    ctrl.state.mode = MagicMock(value=mode_value)
    ctrl.state.get_selected_workflow.return_value = None

    ctrl.get_flow_viewmodel.return_value = (nodes, edges)

    def _noop_select_step(_sid):
        return None

    ctrl.select_step.side_effect = _noop_select_step
    ctrl.add_step_below.side_effect = lambda: None
    return ctrl


def test_flow_canvas_simple_mode_keeps_sequential_labels(app_root):
    producer = FlowNodeVM(
        step_id="producer",
        title="Producer Title",
        purpose="",
        model="gpt",
        status=StepStatus.PENDING,
        upstream_title="",
        downstream_title="",
        execution_mode="graph",
    )
    consumer = FlowNodeVM(
        step_id="consumer",
        title="Consumer Title",
        purpose="",
        model="gpt",
        status=StepStatus.PENDING,
        upstream_title="Legacy Upstream Title",
        downstream_title="Legacy Downstream Title",
        execution_mode="graph",
        is_selected=True,
    )

    edges = [
        FlowEdgeVM(from_id="producer", to_id="consumer", edge_type="dependency")
    ]
    nodes = [producer, consumer]

    ctrl = _make_ctrl("simple", nodes, edges)
    canvas = FlowCanvas(app_root, ctrl)
    canvas.refresh()

    label_texts = _collect_label_texts(canvas)
    assert "Connections" not in label_texts
    assert "↑ from: Legacy Upstream Title" in label_texts
    assert "↓ to: Legacy Downstream Title" in label_texts


def test_flow_canvas_advanced_mode_uses_connections_block(app_root):
    producer = FlowNodeVM(
        step_id="producer",
        title="Producer Title",
        purpose="",
        model="gpt",
        status=StepStatus.PENDING,
        upstream_title="",
        downstream_title="",
        execution_mode="graph",
    )
    consumer = FlowNodeVM(
        step_id="consumer",
        title="Consumer Title",
        purpose="",
        model="gpt",
        status=StepStatus.PENDING,
        upstream_title="Legacy Upstream Title",
        downstream_title="Legacy Downstream Title",
        execution_mode="graph",
        is_selected=True,
    )

    edges = [
        FlowEdgeVM(from_id="producer", to_id="consumer", edge_type="dependency")
    ]
    nodes = [producer, consumer]

    ctrl = _make_ctrl("advanced", nodes, edges)
    canvas = FlowCanvas(app_root, ctrl)
    canvas.refresh()

    label_texts = _collect_label_texts(canvas)
    assert "Connections" in label_texts
    assert "↑ from: Legacy Upstream Title" not in label_texts
    assert "↓ to: Legacy Downstream Title" not in label_texts
