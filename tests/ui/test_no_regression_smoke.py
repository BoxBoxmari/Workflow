from unittest.mock import MagicMock

from core.enums import DrawerTab, StepStatus, WorkspaceView
from core.models import RunContext, StepDef, StepMetrics, StepResult, WorkflowDef


def test_no_regression_smoke_open_edit_run_result_reload(controller, monkeypatch):
    wf = WorkflowDef(
        id="wf_smoke",
        name="Smoke WF",
        steps=[StepDef(id="s1", name="Step 1", model="test-model", prompt_version="1")],
    )
    controller.state.workflow_drafts[wf.id] = wf
    controller.select_workflow(wf.id)
    controller.select_step("s1")

    controller.update_step_field("s1", "name", "Step 1 Edited")
    assert controller.state.get_selected_step().name == "Step 1 Edited"

    import ui.workspace_controller as wc
    import core.config_validation as cfg_validation

    fake_runner = MagicMock()
    monkeypatch.setattr(wc, "WorkflowRunner", lambda *args, **kwargs: fake_runner)
    monkeypatch.setattr(cfg_validation, "validate_workflow", lambda *args, **kwargs: [])

    started = controller.start_run()
    assert started is True
    assert controller.state.view == WorkspaceView.RESULTS
    assert controller.state.drawer_visible is True
    assert controller.state.drawer_tab == DrawerTab.OUTPUT
    fake_runner.run_async.assert_called_once()

    result = StepResult(
        step_id="s1",
        step_name="Step 1 Edited",
        status=StepStatus.SUCCESS.value,
        output_text="ok",
        output_ports={"final": "ok"},
        node_events=[{"type": "step_finished", "timestamp": "2026-03-21T00:00:00Z"}],
        metrics=StepMetrics(timestamp="2026-03-21T00:00:00Z"),
    )
    controller._handle_step_finished({"result": result})
    assert controller.state.run_step_results["s1"].output_ports["final"] == "ok"

    run_id = "run_smoke_reload"
    ctx = RunContext(
        run_id=run_id,
        workflow_id=wf.id,
        workflow_name=wf.name,
        started_at="2026-03-21T00:00:00Z",
        status=StepStatus.SUCCESS.value,
        schema_version=3,
    )
    controller.storage.create_run(ctx)
    controller.storage.save_node(run_id, "s1", result)

    controller.select_run(run_id)
    assert controller.state.selected_run_id == run_id
    assert controller.state.run_step_results["s1"].node_events[0]["type"] == "step_finished"
