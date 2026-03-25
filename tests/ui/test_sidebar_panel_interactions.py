import tkinter as tk
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def _tk_available() -> bool:
    try:
        import customtkinter as ctk  # type: ignore[import-untyped]

        r = ctk.CTk()
        r.withdraw()
        r.destroy()
        return True
    except (ValueError, tk.TclError):
        return False
    except Exception:
        return False


_HAVE_DISPLAY = _tk_available()
_SKIP_REASON = "No display available; skipping UI interaction tests."


def _walk_widgets(root_widget):
    stack = [root_widget]
    while stack:
        current = stack.pop()
        children = list(current.winfo_children())
        stack.extend(children)
        yield current


def _make_ctrl():
    ctrl = MagicMock()

    ctrl.create_workflow = MagicMock()
    ctrl.duplicate_workflow = MagicMock()
    ctrl.delete_workflow = MagicMock()
    ctrl.select_workflow = MagicMock()
    ctrl.load_run_history = MagicMock(return_value=[])
    ctrl.select_run = MagicMock()
    ctrl.set_graph_runtime_enabled = MagicMock()

    state = SimpleNamespace(
        workflow_drafts={},
        selected_workflow_id=None,
        is_dirty=False,
        enable_graph_runtime=False,
    )
    ctrl.state = state
    return ctrl


@pytest.mark.skipif(not _HAVE_DISPLAY, reason=_SKIP_REASON)
def test_sidebar_panel_buttons_call_controller_methods():
    import customtkinter as ctk

    ctk.set_appearance_mode("Dark")
    try:
        root = ctk.CTk()
        root.withdraw()
    except (ValueError, tk.TclError):
        pytest.skip("Environment does not support UI display/transparency")

    try:
        from ui.sidebar_panel import SidebarPanel
        from core.models import WorkflowDef

        ctrl = _make_ctrl()
        ctrl.state.workflow_drafts = {
            "w1": WorkflowDef(id="w1", name="WF 1", steps=[]),
        }
        ctrl.state.selected_workflow_id = "w1"

        panel = SidebarPanel(root, ctrl)
        panel.refresh()

        btn_text_to_mock = {
            "+ New": ctrl.create_workflow,
            "⧉ Clone": ctrl.duplicate_workflow,
            "🗑 Delete": ctrl.delete_workflow,
        }

        found = {}
        for w in _walk_widgets(panel):
            if w.__class__.__name__ != "CTkButton":
                continue
            text = w.cget("text")
            if text in btn_text_to_mock:
                found[text] = w

        assert set(found.keys()) == set(btn_text_to_mock.keys())

        found["+ New"].invoke()
        ctrl.create_workflow.assert_called_once()

        found["⧉ Clone"].invoke()
        ctrl.duplicate_workflow.assert_called_once()

        found["🗑 Delete"].invoke()
        ctrl.delete_workflow.assert_called_once_with("w1")
    finally:
        try:
            root.destroy()
        except Exception:
            pass


@pytest.mark.skipif(not _HAVE_DISPLAY, reason=_SKIP_REASON)
def test_sidebar_panel_graph_runtime_toggle_calls_controller():
    import customtkinter as ctk

    ctk.set_appearance_mode("Dark")
    try:
        root = ctk.CTk()
        root.withdraw()
    except (ValueError, tk.TclError):
        pytest.skip("Environment does not support UI display/transparency")

    try:
        from ui.sidebar_panel import SidebarPanel

        ctrl = _make_ctrl()
        panel = SidebarPanel(root, ctrl)

        ctrl.set_graph_runtime_enabled.reset_mock()
        panel._graph_var.set(True)
        root.update_idletasks()
        root.update()
        ctrl.set_graph_runtime_enabled.assert_called_with(True)
    finally:
        try:
            root.destroy()
        except Exception:
            pass
