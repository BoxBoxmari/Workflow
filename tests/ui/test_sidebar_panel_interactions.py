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
    ctrl.rename_workflow = MagicMock(return_value=True)
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


@pytest.mark.skipif(not _HAVE_DISPLAY, reason=_SKIP_REASON)
def test_sidebar_panel_double_click_rename_invokes_controller():
    import customtkinter as ctk

    ctk.set_appearance_mode("Dark")
    root = None
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
        root.update()

        # Find workflow label by displayed text.
        label = None
        for w in _walk_widgets(panel):
            if w.__class__.__name__ == "CTkLabel" and w.cget("text") == "WF 1":
                label = w
                break

        assert label is not None

        # Validate binding exists on at least one widget in the workflow card.
        # (event_generate("<Double-Button-1>") không được hỗ trợ trong một số môi trường Tk.)
        has_double_binding = any(
            getattr(w, "bind", None) and bool(w.bind("<Double-Button-1>"))
            for w in _walk_widgets(panel)
        )
        assert has_double_binding, "Missing <Double-Button-1> binding on workflow card widgets"
        panel._show_workflow_rename_modal("w1")
        root.update()

        # In the rename modal: set entry value, then invoke the Rename button.
        entry = None
        rename_btn = None
        for w in _walk_widgets(root):
            if w.__class__.__name__ == "CTkEntry" and entry is None:
                entry = w
            if w.__class__.__name__ == "CTkButton" and w.cget("text") == "Rename":
                rename_btn = w
        assert entry is not None
        assert rename_btn is not None

        entry.delete(0, tk.END)
        entry.insert(0, "WF Renamed")
        root.update()

        rename_btn.invoke()
        root.update()

        ctrl.rename_workflow.assert_called_once_with("w1", "WF Renamed")
    finally:
        try:
            if root is not None:
                root.destroy()
        except Exception:
            pass
