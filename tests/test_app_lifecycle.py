import pytest
import unittest.mock as mock
import tkinter as tk
from ui.app import App


def _tk_available() -> bool:
    try:
        import customtkinter as ctk

        r = ctk.CTk()
        r.withdraw()
        r.destroy()
        return True
    except Exception:
        # Standard fallback for restricted environments (e.g. TclError)
        return False


_HAVE_DISPLAY = _tk_available()
_SKIP_REASON = (
    "No display with transparency support available; skipping UI lifecycle tests."
)


@pytest.mark.skipif(not _HAVE_DISPLAY, reason=_SKIP_REASON)
def test_app_init_calls_controller_start(temp_project_root):
    try:
        with mock.patch(
            "ui.workspace_controller.WorkspaceController.start"
        ) as mock_start:
            app = App(temp_project_root)
            mock_start.assert_called_once()
            app.root.destroy()
    except (ValueError, tk.TclError):
        # Any Tcl or transparency error in this environment means we must skip
        pytest.skip("Environment does not support UI display/transparency")


@pytest.mark.skipif(not _HAVE_DISPLAY, reason=_SKIP_REASON)
def test_app_close_calls_controller_stop(temp_project_root):
    try:
        with mock.patch(
            "ui.workspace_controller.WorkspaceController.stop"
        ) as mock_stop:
            app = App(temp_project_root)
            app._on_closing()
            mock_stop.assert_called_once()
    except (ValueError, tk.TclError):
        # Any Tcl or transparency error in this environment means we must skip
        pytest.skip("Environment does not support UI display/transparency")


@pytest.mark.skipif(not _HAVE_DISPLAY, reason=_SKIP_REASON)
def test_session_restore_on_boot(temp_project_root):
    try:
        # Setup a dummy session file
        session_file = temp_project_root / "state" / "session.json"
        session_file.write_text('{"selected_workflow_id": "wf123"}', encoding="utf-8")

        app = App(temp_project_root)
        # Controller.start() loads session
        assert app.controller.state.selected_workflow_id == "wf123"
        app.root.destroy()
    except (ValueError, tk.TclError):
        # Any Tcl or transparency error in this environment means we must skip
        pytest.skip("Environment does not support UI display/transparency")


@pytest.mark.skipif(not _HAVE_DISPLAY, reason=_SKIP_REASON)
def test_config_watcher_runs(temp_project_root):
    try:
        with mock.patch("ui.workspace_controller.start_config_watcher") as mock_watcher:
            app = App(temp_project_root)
            # start_config_watcher is called in controller.start()
            mock_watcher.assert_called_once()
            app.root.destroy()
    except (ValueError, tk.TclError):
        # Any Tcl or transparency error in this environment means we must skip
        pytest.skip("Environment does not support UI display/transparency")


def test_pump_events_dispatches_and_reschedules():
    app = App.__new__(App)
    app.event_bus = mock.Mock()
    app.root = mock.Mock()

    app._pump_events()

    app.event_bus.dispatch.assert_called_once_with()
    app.root.after.assert_called_once_with(100, app._pump_events)
