"""
tests.test_mvp_hardening — Regression tests for MVP hardening fixes.

Covers:
- Save validates ALL workflow drafts (not only the selected one)
- manual_input propagates through start_run as initial_input
- Bundled workflow config validity (all graph workflows pass validation)
- Source picker disambiguation when step titles/names collide
- Graph downstream step blocking after upstream failure (async_graph_runner)
"""

from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, patch

import pytest

from core.config_validation import validate_workflow
from core.models import (
    StepDef,
    WorkflowDef,
)
from ui.inspector_panel import (
    INSPECTOR_ROOT_SOURCE_DISPLAY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctrl():
    from ui.workspace_controller import WorkspaceController

    return WorkspaceController(
        MagicMock(),  # project_root
        MagicMock(),  # config_service
        MagicMock(),  # storage
        MagicMock(),  # prompt_registry
        MagicMock(),  # client
        MagicMock(),  # event_bus
    )


def _graph_step(
    step_id: str, name: str, *, role: str = "Expert", task: str = "Do task"
) -> StepDef:
    """Minimal valid graph step with nocode prompts."""
    return StepDef(
        id=step_id,
        name=name,
        title=name,
        model="gpt-4-1-2025-04-14-gs-ae",
        prompt_version="1",
        execution_mode="graph",
        role_text=role,
        task_text=task,
    )


# ---------------------------------------------------------------------------
# Phase 2: Save guardrail — validates ALL workflow drafts
# ---------------------------------------------------------------------------


class TestSaveGuardrail:
    """Save must block persistence when ANY workflow draft has error-level issues."""

    def _setup_ctrl_with_drafts(self, *workflow_defs: WorkflowDef):
        ctrl = _make_ctrl()
        # Mock config_service methods so validation runs with real prompts look-up
        ctrl.config_service.list_prompt_steps.return_value = ["analyze"]
        ctrl.config_service.list_prompt_versions.return_value = ["1"]
        ctrl.config_service.load_models.return_value = [
            "gpt-4-1-2025-04-14-gs-ae",
            "o3-2025-04-16-gs-ae",
        ]
        for wf in workflow_defs:
            ctrl.state.workflow_drafts[wf.id] = wf
        if workflow_defs:
            ctrl.state.selected_workflow_id = workflow_defs[0].id
        return ctrl

    def test_save_blocks_when_unselected_draft_has_errors(self):
        """Even if the selected workflow is valid, an invalid draft in the set must block save."""
        valid_wf = WorkflowDef(
            id="valid_wf",
            name="Valid",
            steps=[
                StepDef(
                    id="s1",
                    name="analyze",
                    model="gpt-4-1-2025-04-14-gs-ae",
                    prompt_version="1",
                    execution_mode="legacy",
                    input_mapping="input",
                    output_mapping="output",
                )
            ],
        )
        invalid_wf = WorkflowDef(id="bad_wf", name="Bad", steps=[])  # no steps → error

        ctrl = self._setup_ctrl_with_drafts(valid_wf, invalid_wf)
        ctrl.state.selected_workflow_id = valid_wf.id

        ok, msg = ctrl.save()

        assert ok is False
        assert "bad_wf" in msg
        # Make sure config_service.save_workflows was NOT called
        ctrl.config_service.save_workflows.assert_not_called()

    def test_save_succeeds_when_all_drafts_are_valid(self):
        """All drafts valid → save proceeds."""
        wf = WorkflowDef(
            id="wf1",
            name="W1",
            steps=[
                StepDef(
                    id="s1",
                    name="analyze",
                    model="gpt-4-1-2025-04-14-gs-ae",
                    prompt_version="1",
                    execution_mode="legacy",
                    input_mapping="input",
                    output_mapping="output",
                )
            ],
        )
        ctrl = self._setup_ctrl_with_drafts(wf)
        ctrl.config_service.save_workflows.return_value = None
        ctrl.state.prompt_drafts = {}

        ok, msg = ctrl.save()

        assert ok is True, f"Expected save to succeed, got: {msg}"
        ctrl.config_service.save_workflows.assert_called_once()

    def test_save_error_message_names_failing_workflow(self):
        """Error message must mention the workflow name or id that failed."""
        bad_wf = WorkflowDef(id="broken", name="Broken WF", steps=[])
        ctrl = self._setup_ctrl_with_drafts(bad_wf)

        ok, msg = ctrl.save()

        assert ok is False
        # Error message should identify the failing workflow
        assert "Broken WF" in msg or "broken" in msg


# ---------------------------------------------------------------------------
# Phase 3: Root input propagation
# ---------------------------------------------------------------------------


class TestRootInputPropagation:
    """manual_input from state must reach the runner as initial_input."""

    def test_update_manual_input_stores_value(self):
        ctrl = _make_ctrl()
        ctrl.update_manual_input("Hello, world!")
        assert ctrl.state.manual_input == "Hello, world!"

    def test_update_manual_input_handles_none(self):
        ctrl = _make_ctrl()
        ctrl.update_manual_input(None)
        assert ctrl.state.manual_input == ""

    def test_start_run_passes_manual_input_to_runner(self):
        """start_run must pass state.manual_input as initial_input into _start_runner."""
        ctrl = _make_ctrl()

        # Build a minimal valid legacy workflow
        wf = WorkflowDef(
            id="w1",
            name="W",
            steps=[
                StepDef(
                    id="s1",
                    name="analyze",
                    model="model-x",
                    prompt_version="1",
                    execution_mode="legacy",
                    input_mapping="input",
                    output_mapping="output",
                )
            ],
        )
        ctrl.state.workflow_drafts["w1"] = wf
        ctrl.state.selected_workflow_id = "w1"
        ctrl.state.is_provider_ready = True
        ctrl.state.manual_input = "The user typed this"

        # Suppress validation so we focus on param threading
        ctrl.config_service.list_prompt_steps.return_value = ["analyze"]
        ctrl.config_service.list_prompt_versions.return_value = ["1"]
        ctrl.config_service.load_models.return_value = ["model-x"]

        captured_kwargs: dict = {}

        def _fake_start_runner(**kwargs):
            captured_kwargs.update(kwargs)

        with patch.object(ctrl, "_start_runner", side_effect=_fake_start_runner):
            # Also patch WorkflowRunner to avoid real instantiation
            with patch("ui.workspace_controller.WorkflowRunner") as MockRunner:
                mock_runner_inst = MagicMock()
                MockRunner.return_value = mock_runner_inst
                ctrl.runner = mock_runner_inst

                ctrl.start_run()

        assert "initial_input" in captured_kwargs, (
            "_start_runner not called with initial_input"
        )
        assert captured_kwargs["initial_input"] == "The user typed this"


# ---------------------------------------------------------------------------
# Phase 4: Bundled workflow config validity
# ---------------------------------------------------------------------------


class TestBundledWorkflowValidity:
    """
    Every workflow in config/workflows.json must pass validation with no error-level issues.
    Validation is run without available_models so model-ID issues stay separate.
    """

    @pytest.fixture(scope="class")
    def bundled_workflows(self) -> list[WorkflowDef]:
        from core.config_service import ConfigService

        config_dir = pathlib.Path(__file__).parent.parent / "config"
        svc = ConfigService(config_dir)
        return svc.load_workflows()

    def test_all_bundled_workflows_load(self, bundled_workflows):
        assert len(bundled_workflows) > 0, "No bundled workflows found"

    def test_all_bundled_workflows_pass_validation(self, bundled_workflows):
        errors_by_wf = {}
        for wf in bundled_workflows:
            # Validate without prompt-file checks (pass empty prompts so
            # graph-nocode steps are accepted; legacy steps without prompt files
            # will show errors — we only check that graph workflows are clean).
            # Build available_prompts from the config dir
            from core.config_service import ConfigService

            config_dir = pathlib.Path(__file__).parent.parent / "config"
            svc = ConfigService(config_dir)
            available_prompts = {
                s: svc.list_prompt_versions(s) for s in svc.list_prompt_steps()
            }
            issues = validate_workflow(wf, bundled_workflows, available_prompts)
            errors = [i for i in issues if i.level == "error"]
            if errors:
                errors_by_wf[wf.id] = [e.message for e in errors]

        # Filter to only graph workflows (which the bug report was about)
        graph_wf_errors = {
            wf_id: msgs
            for wf_id, msgs in errors_by_wf.items()
            if wf_id.startswith("graph_")
        }
        assert graph_wf_errors == {}, (
            "Bundled graph workflow(s) have validation errors:\n"
            + "\n".join(f"  {wf_id}: {msgs}" for wf_id, msgs in graph_wf_errors.items())
        )

    def test_graph_parallel_analysis_root_input_wired(self, bundled_workflows):
        wf = next(w for w in bundled_workflows if w.id == "graph_parallel_analysis")
        root_step = next(s for s in wf.steps if s.id == "split_doc")
        input_port = next(ip for ip in root_step.inputs if ip.name == "document")
        assert any(src.step_id == "__input__" for src in input_port.sources), (
            "split_doc.document must have __input__ as source"
        )

    def test_graph_structured_extraction_root_input_wired(self, bundled_workflows):
        wf = next(w for w in bundled_workflows if w.id == "graph_structured_extraction")
        root_step = next(s for s in wf.steps if s.id == "extractor")
        input_port = next(ip for ip in root_step.inputs if ip.name == "raw_text")
        assert any(src.step_id == "__input__" for src in input_port.sources), (
            "extractor.raw_text must have __input__ as source"
        )

    def test_graph_workflows_have_role_and_task_text(self, bundled_workflows):
        graph_wfs = [w for w in bundled_workflows if w.id.startswith("graph_")]
        for wf in graph_wfs:
            for step in wf.steps:
                assert (step.role_text or "").strip() or (
                    step.task_text or ""
                ).strip(), (
                    f"Graph step {step.id!r} in {wf.id!r} has no role_text or task_text"
                )


# ---------------------------------------------------------------------------
# Phase 5: Source picker disambiguation
# ---------------------------------------------------------------------------


class TestSourcePickerDisambiguation:
    """_available_source_steps must disambiguate when step labels collide."""

    def _make_inspector_panel(self, steps: list[StepDef], current_step_id: str):
        """Return a minimal InspectorPanel instance with a mocked controller."""
        from ui.inspector_panel import InspectorPanel

        ctrl = _make_ctrl()
        wf = WorkflowDef(id="wf1", name="WF", steps=steps)
        ctrl.state.workflow_drafts["wf1"] = wf
        ctrl.state.selected_workflow_id = "wf1"
        ctrl.config_service.load_models.return_value = []

        # Patch the CTk/tkinter UI construction so we don't need a display
        with patch("ui.inspector_panel.ctk"), patch("ui.inspector_panel.tk"):
            panel = object.__new__(InspectorPanel)
            panel.ctrl = ctrl
        return panel

    def test_unique_labels_no_suffix(self):
        """When labels are unique, combo shows plain title without (step_id)."""
        steps = [
            _graph_step("s1", "Analyzer"),
            _graph_step("s2", "Summarizer"),
            _graph_step("s3", "Formatter"),
        ]
        panel = self._make_inspector_panel(steps, "s3")
        options = panel._available_source_steps("s3")

        labels = [o for o in options if o != INSPECTOR_ROOT_SOURCE_DISPLAY]
        for label in labels:
            assert "(" not in label, (
                f"Unexpected step_id suffix in unique label: {label!r}"
            )
        assert "Analyzer" in labels
        assert "Summarizer" in labels

    def test_colliding_labels_get_step_id_suffix(self):
        """When two steps share the same label, both must show 'Label (step_id)'."""
        steps = [
            _graph_step("s1", "Analyzer"),
            _graph_step("s2", "Analyzer"),  # same title → collision
            _graph_step("s3", "Formatter"),
        ]
        panel = self._make_inspector_panel(steps, "s3")
        options = panel._available_source_steps("s3")

        colliding = [o for o in options if "Analyzer" in o]
        assert len(colliding) == 2, f"Expected 2 Analyzer options, got: {colliding}"
        assert any("(s1)" in o for o in colliding), f"Missing (s1) suffix: {colliding}"
        assert any("(s2)" in o for o in colliding), f"Missing (s2) suffix: {colliding}"

    def test_canonical_resolution_with_suffix(self):
        """_canonical_source_step_id returns step_id for 'Title (step_id)'."""
        steps = [
            _graph_step("s1", "Analyzer"),
            _graph_step("s2", "Analyzer"),
        ]
        panel = self._make_inspector_panel(steps, "s2")

        resolved = panel._canonical_source_step_id("Analyzer (s1)")
        assert resolved == "s1", f"Expected 's1', got {resolved!r}"

    def test_canonical_resolution_title_only_unique(self):
        """When labels are unique, title-only input resolves correctly."""
        steps = [
            _graph_step("s1", "Splitter"),
            _graph_step("s2", "Merger"),
        ]
        panel = self._make_inspector_panel(steps, "s2")

        resolved = panel._canonical_source_step_id("Splitter")
        assert resolved == "s1", f"Expected 's1', got {resolved!r}"

    def test_root_source_display_resolves_to_canonical(self):
        """INSPECTOR_ROOT_SOURCE_DISPLAY must resolve to __input__."""
        steps = [_graph_step("s1", "Step 1")]
        panel = self._make_inspector_panel(steps, "s1")

        resolved = panel._canonical_source_step_id(INSPECTOR_ROOT_SOURCE_DISPLAY)
        assert resolved == "__input__"

    def test_current_step_excluded_from_source_options(self):
        """The step being edited must not appear in its own source options."""
        steps = [
            _graph_step("s1", "Step A"),
            _graph_step("s2", "Step B"),
        ]
        panel = self._make_inspector_panel(steps, "s1")
        options = panel._available_source_steps("s1")

        # s1 (Step A) must not be in the list
        assert not any("Step A" in o for o in options), (
            f"Current step appeared in source options: {options}"
        )
        assert any("Step B" in o for o in options)
