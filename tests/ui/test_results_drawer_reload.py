from core.models import RunContext, StepMetrics, StepResult


def test_select_run_hydrates_step_results_for_results_drawer(controller):
    run_id = "run_reload_ui_hydration"
    ctx = RunContext(
        run_id=run_id,
        workflow_id="wf1",
        workflow_name="WF",
        started_at="2026-03-21T00:00:00Z",
        status="success",
        schema_version=3,
    )
    controller.storage.create_run(ctx)

    step = StepResult(
        step_id="s1",
        step_name="S1",
        status="success",
        output_text="done",
        output_ports={"final": "payload"},
        node_events=[
            {"type": "step_finished", "timestamp": "2026-03-21T00:00:02Z"}
        ],
        metrics=StepMetrics(timestamp="2026-03-21T00:00:01Z"),
    )
    controller.storage.save_node(run_id, "s1", step)

    controller.select_run(run_id)

    assert controller.state.selected_run_id == run_id
    assert "s1" in controller.state.run_step_results
    hydrated = controller.state.run_step_results["s1"]
    assert hydrated.output_ports.get("final") == "payload"
    assert hydrated.node_events
    assert hydrated.node_events[0]["type"] == "step_finished"
