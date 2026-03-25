import pytest
from unittest.mock import MagicMock

from core.models import WorkflowDef, StepDef, StepResult
from core.enums import StepStatus, WorkspaceView, DrawerTab


def test_controller_constructs_runner_correctly(controller):
    assert controller.runner is None


def test_start_run_calls_run_async_with_params(controller):
    wf = WorkflowDef(
        id="wf1",
        name="WF",
        steps=[StepDef(id="s1", name="S1", model="test-model-1", prompt_version="1")],
    )
    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    # Needs a mock run_async
    import ui.workspace_controller

    with pytest.MonkeyPatch.context() as m:
        mock_runner = MagicMock()
        m.setattr(
            ui.workspace_controller, "WorkflowRunner", lambda *a, **k: mock_runner
        )

        # Start run
        res = controller.start_run()

        assert res is True
        assert controller.state.is_running is True
        assert controller.state.view == WorkspaceView.RESULTS
        assert controller.state.drawer_visible is True
        assert controller.state.drawer_tab == DrawerTab.OUTPUT

        mock_runner.run_async.assert_called_once()
        kwargs = mock_runner.run_async.call_args.kwargs
        assert kwargs["workflow_def"] == wf
        assert "initial_variables" in kwargs


def test_stop_run_calls_cancel(controller):
    controller.runner = MagicMock()
    controller.state.is_running = True

    controller.stop_run()

    controller.runner.cancel.assert_called_once()
    assert controller.state.is_running is False


def test_event_handlers_update_state(controller):
    # test _handle_step_finished
    sr = StepResult(
        step_id="s1",
        step_name="S1",
        status=StepStatus.SUCCESS.value,
        output_text="Done",
    )
    controller._handle_step_finished({"result": sr})
    assert controller.state.run_step_results["s1"] == sr

    # test _handle_run_finished
    controller.state.is_running = True
    controller._handle_run_finished({"run_id": "run1", "status": "success"})
    assert controller.state.is_running is False
    assert controller.state.drawer_visible is True


def test_run_blocked_when_no_workflow(controller):
    controller.state.selected_workflow_id = None
    assert controller.can_run is False
    assert controller.start_run() is False


def test_run_blocked_when_already_running(controller):
    wf = WorkflowDef(id="wf1", name="WF", steps=[])
    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    controller.state.is_running = True
    assert controller.can_run is False
    assert controller.start_run() is False


def test_run_blocked_when_provider_not_ready(controller):
    wf = WorkflowDef(id="wf1", name="WF", steps=[])
    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    controller.state.is_provider_ready = False
    assert controller.can_run is False
    # start_run() should also fail if client is not set
    controller.client = None
    assert controller.start_run() is False
