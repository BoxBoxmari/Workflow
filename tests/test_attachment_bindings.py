import pytest
from unittest.mock import MagicMock
from core.models import AttachmentSlot, IngestResult, StepDef, WorkflowDef


def test_slot_key_format_is_step_id_slot_id(controller):
    step = StepDef(id="step1", name="Step 1", model="m1", prompt_version="1")
    slot = AttachmentSlot(slot_id="fileA", variable_name="varA")
    # Format used in UI and Controller
    slot_key = f"{step.id}::{slot.slot_id}"
    assert slot_key == "step1::fileA"


def test_required_attachment_missing_blocks_run(controller, temp_project_root):
    slot = AttachmentSlot(slot_id="fileA", variable_name="varA", required=True)
    step = StepDef(
        id="s1",
        name="S1",
        model="test-model-1",
        prompt_version="1",
        attachments=[slot],
        input_mapping="input",
        output_mapping="output",
    )
    wf = WorkflowDef(id="wf1", name="WF", steps=[step])

    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    # Binding is missing
    assert "s1::fileA" not in controller.state.attachment_bindings
    assert controller.can_run is False
    with pytest.MonkeyPatch.context() as m:
        m.setattr("tkinter.messagebox.showerror", MagicMock())
        assert controller.start_run() is False


def test_optional_attachment_missing_allows_run(controller, temp_project_root):
    slot = AttachmentSlot(slot_id="fileA", variable_name="varA", required=False)
    step = StepDef(
        id="s1",
        name="S1",
        model="test-model-1",
        prompt_version="1",
        attachments=[slot],
        input_mapping="input",
        output_mapping="output",
    )
    wf = WorkflowDef(id="wf1", name="WF", steps=[step])

    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    # Binding is missing but it's optional
    assert controller.can_run is True


def test_attachments_resolve_to_variable_name(controller, temp_project_root):
    # Create a dummy attachment file
    file_path = temp_project_root / "test.txt"
    file_path.write_text("Hello attachment", encoding="utf-8")

    slot = AttachmentSlot(slot_id="fileA", variable_name="varA", required=True)
    step = StepDef(
        id="s1",
        name="S1",
        model="test-model-1",
        prompt_version="1",
        attachments=[slot],
        input_mapping="input",
        output_mapping="output",
        execution_mode="legacy",
    )
    wf = WorkflowDef(id="wf1", name="WF", steps=[step])

    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"
    controller.state.attachment_bindings["s1::fileA"] = str(file_path)

    # Mocking WorkflowRunner.run_async to check variables
    import ui.workspace_controller

    with pytest.MonkeyPatch.context() as m:
        mock_runner = MagicMock()
        m.setattr(
            ui.workspace_controller, "WorkflowRunner", lambda *a, **k: mock_runner
        )

        controller.start_run()

        kwargs = mock_runner.run_async.call_args.kwargs
        variables = kwargs["initial_variables"]
        assert "varA" in variables
        assert variables["varA"] == "Hello attachment"


def test_attachments_do_not_leak_across_steps(controller, temp_project_root):
    # Two steps, both need attachments
    slot1 = AttachmentSlot(slot_id="file1", variable_name="var1")
    slot2 = AttachmentSlot(slot_id="file2", variable_name="var2")

    s1 = StepDef(
        id="s1",
        name="S1",
        model="test-model-1",
        prompt_version="1",
        attachments=[slot1],
        input_mapping="input",
        output_mapping="output",
        execution_mode="legacy",
    )
    s2 = StepDef(
        id="s2",
        name="S2",
        model="test-model-1",
        prompt_version="1",
        attachments=[slot2],
        input_mapping="output",
        output_mapping="final_output",
        execution_mode="legacy",
    )
    wf = WorkflowDef(id="wf1", name="WF", steps=[s1, s2])

    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    f1 = temp_project_root / "f1.txt"
    f1.write_text("content1")
    f2 = temp_project_root / "f2.txt"
    f2.write_text("content2")

    controller.state.attachment_bindings["s1::file1"] = str(f1)
    controller.state.attachment_bindings["s2::file2"] = str(f2)

    import ui.workspace_controller
    from unittest.mock import MagicMock

    with pytest.MonkeyPatch.context() as m:
        mock_runner = MagicMock()
        m.setattr(
            ui.workspace_controller, "WorkflowRunner", lambda *a, **k: mock_runner
        )

        controller.start_run()
        vars = mock_runner.run_async.call_args.kwargs["initial_variables"]
        assert vars["var1"] == "content1"
        assert vars["var2"] == "content2"


def test_attachment_with_empty_ingested_content_blocks_run(controller, temp_project_root):
    file_path = temp_project_root / "empty.txt"
    file_path.write_text("", encoding="utf-8")

    slot = AttachmentSlot(slot_id="fileA", variable_name="varA", required=True)
    step = StepDef(
        id="s1",
        name="S1",
        model="test-model-1",
        prompt_version="1",
        attachments=[slot],
        input_mapping="input",
        output_mapping="output",
        execution_mode="legacy",
    )
    wf = WorkflowDef(id="wf1", name="WF", steps=[step])
    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"
    controller.state.attachment_bindings["s1::fileA"] = str(file_path)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "core.ingestion.ingest_file",
            lambda *_args, **_kwargs: IngestResult(content="   "),
        )
        m.setattr("tkinter.messagebox.showerror", MagicMock())
        assert controller.start_run() is False
