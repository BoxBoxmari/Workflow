from unittest.mock import MagicMock

from core.config_service import ConfigService
from core.events import EventBus
from core.models import AttachmentSlot, StepDef, WorkflowDef
from core.prompts import PromptRegistry
from core.provider import WorkbenchClient
from core.storage import StorageManager
from ui.workspace_controller import WorkspaceController


def _build_controller(project_root, *, start_session=False):
    config_service = ConfigService(project_root / "config")
    storage = StorageManager(project_root / "runs")
    prompt_registry = PromptRegistry(project_root / "config" / "prompts")
    event_bus = EventBus()
    client = MagicMock(spec=WorkbenchClient)
    client.base_url = "http://localhost"
    client.subscription_key = "test_key"

    ctrl = WorkspaceController(
        project_root=project_root,
        config_service=config_service,
        storage=storage,
        prompt_registry=prompt_registry,
        client=client,
        event_bus=event_bus,
    )
    ctrl.state.is_provider_ready = True
    if start_session:
        ctrl.start()
    return ctrl


def test_attachment_slot_add_edit_remove_and_can_run(temp_project_root):
    controller = _build_controller(temp_project_root)
    try:
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

        file_a = temp_project_root / "a.txt"
        file_b = temp_project_root / "b.txt"
        file_a.write_text("A", encoding="utf-8")
        file_b.write_text("B", encoding="utf-8")
        slot_key = "s1::fileA"

        assert controller.can_run is False

        controller.update_attachment_binding(slot_key, str(file_a))
        assert controller.state.attachment_bindings[slot_key] == str(file_a)
        assert controller.can_run is True

        controller.update_attachment_binding(slot_key, str(file_b))
        assert controller.state.attachment_bindings[slot_key] == str(file_b)
        assert controller.can_run is True

        controller.remove_attachment_binding(slot_key)
        assert slot_key not in controller.state.attachment_bindings
        assert controller.can_run is False
    finally:
        controller.stop()


def test_attachment_slot_persists_after_reload(temp_project_root):
    slot_key = "s1::fileA"
    file_path = temp_project_root / "bound.txt"
    file_path.write_text("hello", encoding="utf-8")

    controller = _build_controller(temp_project_root)
    try:
        controller.update_attachment_binding(slot_key, str(file_path))
        controller.stop()

        reloaded = _build_controller(temp_project_root, start_session=True)
        try:
            assert reloaded.state.attachment_bindings.get(slot_key) == str(file_path)
        finally:
            reloaded.stop()
    except Exception:
        try:
            controller.stop()
        except Exception:
            pass
        raise


def test_attachment_slot_metadata_edit_and_slot_removal(temp_project_root):
    controller = _build_controller(temp_project_root)
    try:
        step = StepDef(
            id="s1",
            name="S1",
            model="test-model-1",
            prompt_version="1",
            attachments=[],
        )
        wf = WorkflowDef(id="wf1", name="WF", steps=[step])
        controller.state.workflow_drafts["wf1"] = wf
        controller.state.selected_workflow_id = "wf1"

        slot_id = controller.add_attachment_slot("s1", label="Doc", required=False)
        assert slot_id is not None
        key = f"s1::{slot_id}"

        file_path = temp_project_root / "doc.txt"
        file_path.write_text("hello", encoding="utf-8")
        controller.update_attachment_binding(key, str(file_path))

        ok = controller.update_attachment_slot(
            "s1",
            slot_id,
            label="  Source Doc  ",
            variable_name="source_doc",
            required=True,
            accepted_types=[" PDF ", "pdf", "TXT", ""],
        )
        assert ok is True
        assert step.attachments[0].label == "Source Doc"
        assert step.attachments[0].variable_name == "source_doc"
        assert step.attachments[0].required is True
        assert step.attachments[0].accepted_types == ["pdf", "txt"]
        assert controller.state.attachment_bindings[key] == str(file_path)

        ok_clear = controller.update_attachment_slot(
            "s1", slot_id, accepted_types_clear=True
        )
        assert ok_clear is True
        assert step.attachments[0].accepted_types is None
        assert controller.state.attachment_bindings[key] == str(file_path)

        controller.remove_attachment_slot("s1", slot_id)
        assert step.attachments == []
        assert key not in controller.state.attachment_bindings
    finally:
        controller.stop()
