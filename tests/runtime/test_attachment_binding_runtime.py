from unittest.mock import MagicMock, patch

from core.models import AttachmentSlot, StepDef, WorkflowDef


def test_runtime_uses_attachment_binding_as_initial_variables(controller, tmp_path):
    slot = AttachmentSlot(slot_id="fileA", variable_name="varA", required=True)
    step = StepDef(
        id="s1",
        name="S1",
        model="test-model-1",
        prompt_version="1",
        attachments=[slot],
    )
    wf = WorkflowDef(id="wf1", name="WF", steps=[step])
    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    bound_file = tmp_path / "bound.txt"
    bound_file.write_text("hello", encoding="utf-8")
    controller.update_attachment_binding("s1::fileA", str(bound_file))

    with (
        patch("core.ingestion.ingest_file") as mock_ingest,
        patch("ui.workspace_controller.WorkflowRunner") as mock_runner_cls,
        patch.object(controller, "_start_runner") as mock_start_runner,
    ):
        mock_ingest.return_value = MagicMock(ok=True, content="INGESTED")
        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner

        ok = controller.start_run()

        assert ok is True
        mock_start_runner.assert_called_once()
        kwargs = mock_start_runner.call_args.kwargs
        assert kwargs["initial_variables"] == {"varA": "INGESTED"}
        assert kwargs["workflow_def"].id == "wf1"


def test_runtime_returns_false_when_required_attachment_ingestion_fails(
    controller, tmp_path
):
    slot = AttachmentSlot(slot_id="fileA", variable_name="varA", required=True)
    step = StepDef(
        id="s1",
        name="S1",
        model="test-model-1",
        prompt_version="1",
        attachments=[slot],
    )
    wf = WorkflowDef(id="wf1", name="WF", steps=[step])
    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    bound_file = tmp_path / "broken.txt"
    bound_file.write_text("bad", encoding="utf-8")
    controller.update_attachment_binding("s1::fileA", str(bound_file))

    with (
        patch("core.ingestion.ingest_file") as mock_ingest,
        patch.object(controller, "_start_runner") as mock_start_runner,
    ):
        mock_ingest.return_value = MagicMock(ok=False, content="")

        ok = controller.start_run()

        assert ok is False
        mock_start_runner.assert_not_called()
