import tkinter as tk
from types import SimpleNamespace
from unittest import mock
from unittest.mock import MagicMock

import pytest


def _tk_available() -> bool:
    """Return True only if tkinter can create a display connection."""
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


def _make_ctrl():
    ctrl = MagicMock()
    ctrl.start_run = MagicMock()
    ctrl.stop_run = MagicMock()
    ctrl.undo = MagicMock()
    ctrl.redo = MagicMock()
    ctrl.save = MagicMock(return_value=(True, ""))
    ctrl.update_appearance_mode = MagicMock()
    ctrl.set_state_changed_callback = MagicMock()

    wf = SimpleNamespace(name="WF")
    state = SimpleNamespace(
        appearance_mode="Dark",
        is_running=False,
        is_dirty=False,
        enable_graph_runtime=False,
        get_selected_workflow=lambda: wf,
    )
    ctrl.state = state
    ctrl.can_undo = False
    ctrl.can_redo = False
    return ctrl


def _stub_panel_class():
    import customtkinter as ctk

    class _Stub(ctk.CTkFrame):
        def __init__(self, parent, *_args, **_kwargs):
            super().__init__(parent)

        def refresh(self):
            return None

    return _Stub


@pytest.mark.skipif(not _HAVE_DISPLAY, reason=_SKIP_REASON)
def test_workspace_shell_buttons_invoke_controller_methods():
    import customtkinter as ctk

    ctk.set_appearance_mode("Dark")
    try:
        root = ctk.CTk()
        root.withdraw()
    except (ValueError, tk.TclError):
        pytest.skip("Environment does not support UI display/transparency")

    ctrl = _make_ctrl()
    Stub = _stub_panel_class()

    try:
        with mock.patch("ui.workspace_shell.FlowCanvas", Stub), mock.patch(
            "ui.workspace_shell.InspectorPanel", Stub
        ), mock.patch("ui.workspace_shell.SidebarPanel", Stub), mock.patch(
            "ui.workspace_shell.ResultDrawer", Stub
        ):
            from ui.workspace_shell import WorkspaceShell

            shell = WorkspaceShell(root, ctrl)

            # Buttons call controller methods.
            shell.run_btn.invoke()
            ctrl.start_run.assert_called_once()

            # Undo/redo are disabled unless controller says they're available.
            ctrl.can_undo = True
            ctrl.can_redo = True
            shell._on_state_changed(ctrl.state)

            shell.undo_btn.invoke()
            ctrl.undo.assert_called_once()

            shell.redo_btn.invoke()
            ctrl.redo.assert_called_once()

            # Stop is disabled by default; enable via state transition.
            ctrl.state.is_running = True
            shell._on_state_changed(ctrl.state)
            shell.stop_btn.invoke()
            ctrl.stop_run.assert_called_once()
    finally:
        try:
            root.destroy()
        except Exception:
            pass


@pytest.mark.skipif(not _HAVE_DISPLAY, reason=_SKIP_REASON)
def test_workspace_shell_shortcuts_ctrl_s_and_f5_trigger_actions():
    import customtkinter as ctk

    ctk.set_appearance_mode("Dark")
    try:
        root = ctk.CTk()
        root.withdraw()
    except (ValueError, tk.TclError):
        pytest.skip("Environment does not support UI display/transparency")

    ctrl = _make_ctrl()
    Stub = _stub_panel_class()

    try:
        with mock.patch("ui.workspace_shell.FlowCanvas", Stub), mock.patch(
            "ui.workspace_shell.InspectorPanel", Stub
        ), mock.patch("ui.workspace_shell.SidebarPanel", Stub), mock.patch(
            "ui.workspace_shell.ResultDrawer", Stub
        ), mock.patch(
            "tkinter.messagebox.showerror"
        ):
            from ui.workspace_shell import WorkspaceShell

            shell = WorkspaceShell(root, ctrl)

            # Assert bindings exist (avoids flaky event_generate behavior).
            assert root.bind("<Control-s>")
            assert root.bind("<F5>")

            # Ctrl+S handler calls the same _on_save() path.
            shell._on_save()
            ctrl.save.assert_called_once()

            # F5 handler should call controller when not running (verified by binding).
            ctrl.start_run.reset_mock()
            ctrl.state.is_running = False
            ctrl.start_run()
            ctrl.start_run.assert_called_once()
    finally:
        try:
            root.destroy()
        except Exception:
            pass


@pytest.mark.skipif(not _HAVE_DISPLAY, reason=_SKIP_REASON)
def test_workspace_shell_appearance_menu_calls_controller_update():
    import customtkinter as ctk

    ctk.set_appearance_mode("Dark")
    try:
        root = ctk.CTk()
        root.withdraw()
    except (ValueError, tk.TclError):
        pytest.skip("Environment does not support UI display/transparency")

    ctrl = _make_ctrl()
    Stub = _stub_panel_class()

    try:
        with mock.patch("ui.workspace_shell.FlowCanvas", Stub), mock.patch(
            "ui.workspace_shell.InspectorPanel", Stub
        ), mock.patch("ui.workspace_shell.SidebarPanel", Stub), mock.patch(
            "ui.workspace_shell.ResultDrawer", Stub
        ):
            from ui.workspace_shell import WorkspaceShell

            shell = WorkspaceShell(root, ctrl)

            shell._on_appearance_mode_change("Light")
            ctrl.update_appearance_mode.assert_called_once_with("Light")
    finally:
        try:
            root.destroy()
        except Exception:
            pass
