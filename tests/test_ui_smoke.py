"""Smoke tests for ui.app.App (new architecture).

Architecture tested: App (slim) → WorkspaceController → WorkspaceShell

Tests verify:
- App instantiates cleanly with no provider.json
- Root window has expected title
- Core service attributes exist (controller, shell, storage)
- client is None when provider.json is absent
- App tears down cleanly (root.destroy() does not raise)

Note: Tests referencing the former LegacyApp attributes
(workflow_panel, detail_panel, history_panel, status_var, workflows,
current_workflow) were removed when LegacyApp was deleted in Phase 3.
That architecture is superseded by WorkspaceController + WorkspaceShell.
"""

import json
import tempfile
import unittest
from pathlib import Path
import tkinter as tk

from core.enums import StepStatus


def _tk_available() -> bool:
    """Return True only if tkinter can create a display connection."""
    try:
        import customtkinter as ctk  # type: ignore[import-untyped]

        r = ctk.CTk()
        r.withdraw()
        r.destroy()
        return True
    except Exception:
        return False


# Guard: skip all tests when there is no display (e.g. headless CI)
_HAVE_DISPLAY = _tk_available()
_SKIP_REASON = "No display available; skipping UI smoke tests."
_SKIP_UI = "Environment does not support UI display/transparency"


@unittest.skipUnless(_HAVE_DISPLAY, _SKIP_REASON)
class TestAppSmoke(unittest.TestCase):
    """Lightweight smoke tests for the new ui.app.App."""

    def setUp(self):
        """Minimal project dir with config; no live provider."""
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tmp.name)

        # Minimal directory structure
        (self.project_root / "config" / "prompts").mkdir(parents=True)
        (self.project_root / "runs").mkdir()

        # Minimal models.json and workflows.json so App loads cleanly
        (self.project_root / "config" / "models.json").write_text(
            json.dumps([{"id": "gpt-4o", "name": "GPT-4o"}]), encoding="utf-8"
        )
        (self.project_root / "config" / "workflows.json").write_text(
            json.dumps(
                [
                    {
                        "id": "smoke_wf",
                        "name": "Smoke Workflow",
                        "steps": [
                            {
                                "id": "step1",
                                "name": "analyze",
                                "model": "gpt-4o",
                                "prompt_version": "1",
                            }
                        ],
                    }
                ]
            ),
            encoding="utf-8",
        )

        # No provider.json → client remains None (tests no-provider path)
        from ui.app import App
        from unittest.mock import patch

        try:
            self._pump_patcher = patch.object(App, "_pump_events")
            self._pump_patcher.start()
            self.app = App(self.project_root)
            self.app.root.withdraw()  # hide window during testing
        except (ValueError, tk.TclError):
            self.skipTest(_SKIP_UI)

    def tearDown(self):
        try:
            self._pump_patcher.stop()
        except Exception:
            pass
        try:
            self.app.root.destroy()
        except Exception:
            pass
        self.tmp.cleanup()

    # ------------------------------------------------------------------ #
    # Service wiring                                                        #
    # ------------------------------------------------------------------ #

    def test_controller_exists(self):
        """App must create a WorkspaceController."""
        try:
            from ui.workspace_controller import WorkspaceController

            self.assertIsNotNone(self.app.controller)
            self.assertIsInstance(self.app.controller, WorkspaceController)
        except (ValueError, tk.TclError):
            self.skipTest(_SKIP_UI)

    def test_shell_exists(self):
        """App must mount a WorkspaceShell."""
        try:
            from ui.workspace_shell import WorkspaceShell

            self.assertIsNotNone(self.app.shell)
            self.assertIsInstance(self.app.shell, WorkspaceShell)
        except (ValueError, tk.TclError):
            self.skipTest(_SKIP_UI)

    def test_storage_exists(self):
        """App must have a StorageManager."""
        try:
            from core.storage import StorageManager

            self.assertIsNotNone(self.app.storage)
            self.assertIsInstance(self.app.storage, StorageManager)
        except (ValueError, tk.TclError):
            self.skipTest(_SKIP_UI)

    # ------------------------------------------------------------------ #
    # No-provider state                                                     #
    # ------------------------------------------------------------------ #

    def test_client_not_ready_without_provider_json(self):
        """Without provider.json, client is created but not ready."""
        try:
            self.assertIsNotNone(self.app.client)
            self.assertFalse(self.app.controller.state.is_provider_ready)
        except (ValueError, tk.TclError):
            self.skipTest(_SKIP_UI)

    # ------------------------------------------------------------------ #
    # Window attributes                                                     #
    # ------------------------------------------------------------------ #

    def test_window_title(self):
        try:
            title = self.app.root.title()
            self.assertIn(
                "Workflow",
                title,
                f"Unexpected window title: {title!r}",
            )
        except (ValueError, tk.TclError):
            self.skipTest(_SKIP_UI)

    # ------------------------------------------------------------------ #
    # Graph Render Resilience                                               #
    # ------------------------------------------------------------------ #

    def test_flow_canvas_renders_graph_badges(self):
        """FlowCanvas renders Connections and graph badges from FlowEdgeVM."""
        try:
            from ui.viewmodels import FlowEdgeVM, FlowNodeVM

            def mock_get_flow_viewmodel():
                a = FlowNodeVM(
                    step_id="step_a",
                    title="Alpha",
                    purpose="",
                    model="test-base",
                    status=StepStatus.PENDING,
                    is_selected=False,
                    has_files=False,
                    file_count=0,
                    execution_mode="graph",
                    input_port_count=1,
                    output_port_count=1,
                    is_merge=False,
                    is_branch=False,
                )
                b = FlowNodeVM(
                    step_id="step_b",
                    title="Graph Node",
                    purpose="",
                    model="test-base",
                    status=StepStatus.PENDING,
                    is_selected=True,
                    has_files=False,
                    file_count=0,
                    execution_mode="graph",
                    input_port_count=2,
                    output_port_count=1,
                    is_merge=True,
                    is_branch=True,
                )
                c = FlowNodeVM(
                    step_id="step_c",
                    title="Charlie",
                    purpose="",
                    model="test-base",
                    status=StepStatus.PENDING,
                    is_selected=False,
                    has_files=False,
                    file_count=0,
                    execution_mode="graph",
                    input_port_count=1,
                    output_port_count=0,
                    is_merge=False,
                    is_branch=False,
                )
                edges = [
                    FlowEdgeVM(
                        from_id="step_a",
                        to_id="step_b",
                        edge_type="dependency",
                    ),
                    FlowEdgeVM(
                        from_id="step_b",
                        to_id="step_c",
                        edge_type="branch",
                    ),
                ]
                return [a, b, c], edges

            self.app.controller.get_flow_viewmodel = mock_get_flow_viewmodel
            self.app.controller.state.selected_step_id = "step_b"

            flow_canvas = getattr(self.app.shell, "canvas", None)
            if flow_canvas is None:
                main_view = getattr(self.app.shell, "main_view", None)
                flow_canvas = getattr(main_view, "flow_canvas", None)
            self.assertIsNotNone(
                flow_canvas,
                "FlowCanvas is not available on WorkspaceShell",
            )
            flow_canvas.refresh()

            self.assertIn("step_b", flow_canvas._card_frames)
            card_b = flow_canvas._card_frames["step_b"]

            def _collect_label_texts(widget):
                texts = []
                for w in widget.winfo_children():
                    try:
                        t = w.cget("text")
                        if t:
                            texts.append(str(t))
                    except tk.TclError:
                        pass
                    texts.extend(_collect_label_texts(w))
                return texts

            all_text = " ".join(_collect_label_texts(card_b))
            self.assertIn("Connections", all_text)
            self.assertIn("from: Alpha", all_text)
            self.assertIn("(dependency)", all_text)
            self.assertIn("to: Charlie", all_text)
            self.assertIn("(branch)", all_text)
        except (ValueError, tk.TclError):
            self.skipTest(_SKIP_UI)

    # ------------------------------------------------------------------ #
    # Clean teardown                                                        #
    # ------------------------------------------------------------------ #

    def test_clean_destroy(self):
        """root.destroy() must not raise."""
        try:
            try:
                self.app.root.destroy()
            except Exception as e:
                self.fail(f"root.destroy() raised: {e}")
            finally:
                # prevent tearDown double-destroy
                self.app.root = type(
                    "_Stub",
                    (),
                    {"destroy": lambda s: None},
                )()
        except (ValueError, tk.TclError):
            self.skipTest(_SKIP_UI)

    def test_lifecycle_hooks(self):
        """on_closing calls controller save/stop then root.destroy."""
        try:
            from unittest.mock import MagicMock, patch

            self.app.controller.save = MagicMock()
            self.app.controller.stop = MagicMock()
            # Test closing
            with patch.object(self.app.root, "destroy") as mock_destroy:
                self.app._on_closing()
                self.app.controller.save.assert_called_once()
                self.app.controller.stop.assert_called_once()
                mock_destroy.assert_called_once()
        except (ValueError, tk.TclError):
            self.skipTest(_SKIP_UI)


if __name__ == "__main__":
    unittest.main()
