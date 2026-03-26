from unittest.mock import MagicMock
from ui.workspace_controller import WorkspaceController
from core.models import AttachmentSlot, InputPortDef, StepDef, WorkflowDef


def make_mock_ctrl():
    return WorkspaceController(
        MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
    )


def test_add_remove_input_port():
    ctrl = make_mock_ctrl()
    wf = WorkflowDef(id="w1", name="WF")
    step = StepDef(
        id="s1", name="step1", model="gpt", prompt_version="1", execution_mode="graph"
    )
    wf.steps.append(step)
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"

    ctrl.add_input_port("s1", InputPortDef(name="in1"))
    assert len(step.inputs) == 1
    assert step.inputs[0].name == "in1"

    ctrl.remove_input_port("s1", "in1")
    assert len(step.inputs) == 0


def test_update_port_config():
    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
        inputs=[InputPortDef(name="in1")],
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.selected_step_id = "s1"

    ctrl.update_port_config("s1", "input", "in1", "required", False)
    assert step.inputs[0].required is False

    ctrl.undo()
    assert step.inputs[0].required is True


def test_report_execution_mode_mismatch_treats_sequential_as_legacy_alias():
    ctrl = make_mock_ctrl()
    wf = WorkflowDef(
        id="w1",
        name="WF",
        steps=[
            StepDef(
                id="s1",
                name="legacy_step",
                model="gpt",
                prompt_version="1",
                execution_mode="legacy",
            ),
            StepDef(
                id="s2",
                name="sequential_step",
                model="gpt",
                prompt_version="1",
                execution_mode="sequential",
            ),
        ],
    )
    ctrl.state.enable_graph_runtime = False

    ctrl._report_execution_mode_mismatch(wf)

    assert ctrl._last_execution_mode_mismatches == []


def test_report_execution_mode_mismatch_flags_graph_when_legacy_expected():
    ctrl = make_mock_ctrl()
    wf = WorkflowDef(
        id="w1",
        name="WF",
        steps=[
            StepDef(
                id="s1",
                name="graph_step",
                model="gpt",
                prompt_version="1",
                execution_mode="graph",
            )
        ],
    )
    ctrl.state.enable_graph_runtime = False

    ctrl._report_execution_mode_mismatch(wf)

    # Global runtime toggle is source-of-truth; graph step mismatches.
    assert ctrl._last_execution_mode_mismatches == ["s1"]


def test_set_graph_runtime_enabled_recomputes_mismatch():
    ctrl = make_mock_ctrl()
    wf = WorkflowDef(
        id="w1",
        name="WF",
        steps=[
            StepDef(
                id="s1",
                name="legacy_step",
                model="gpt",
                prompt_version="1",
                execution_mode="legacy",
            )
        ],
    )
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.selected_workflow_id = "w1"
    ctrl.state.enable_graph_runtime = True

    ctrl.set_graph_runtime_enabled(False)

    assert ctrl.state.enable_graph_runtime is False
    assert ctrl._last_execution_mode_mismatches == []


def test_resolve_run_engine_mode_global_off_forces_legacy_even_with_graph_steps():
    ctrl = make_mock_ctrl()
    wf = WorkflowDef(
        id="w1",
        name="WF",
        steps=[
            StepDef(
                id="s1",
                name="graph_step",
                model="gpt",
                prompt_version="1",
                execution_mode="graph",
            )
        ],
    )
    ctrl.state.enable_graph_runtime = False
    assert ctrl._resolve_run_engine_mode(wf) == "legacy"


def test_resolve_run_engine_mode_global_on_forces_graph_even_with_legacy_steps():
    ctrl = make_mock_ctrl()
    wf = WorkflowDef(
        id="w1",
        name="WF",
        steps=[
            StepDef(
                id="s1",
                name="legacy_step",
                model="gpt",
                prompt_version="1",
                execution_mode="legacy",
            )
        ],
    )
    ctrl.state.enable_graph_runtime = True
    assert ctrl._resolve_run_engine_mode(wf) == "graph"


def test_add_and_remove_attachment_slot_updates_bindings():
    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.selected_workflow_id = "w1"

    slot_id = ctrl.add_attachment_slot("s1", label="Source PDF", required=True)
    assert slot_id is not None
    assert len(step.attachments) == 1
    assert step.attachments[0].slot_id == slot_id
    assert step.attachments[0].label == "Source PDF"

    key = f"s1::{slot_id}"
    ctrl.state.attachment_bindings[key] = "dummy.pdf"
    ctrl.remove_attachment_slot("s1", slot_id)

    assert step.attachments == []
    assert key not in ctrl.state.attachment_bindings


def test_update_attachment_slot_normalizes_types_and_preserves_binding_key():
    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.selected_workflow_id = "w1"

    slot_id = ctrl.add_attachment_slot("s1", label="Doc", required=False)
    assert slot_id is not None
    key = f"s1::{slot_id}"
    ctrl.state.attachment_bindings[key] = "/tmp/attached.bin"

    ok = ctrl.update_attachment_slot(
        "s1",
        slot_id,
        label="  Renamed  ",
        variable_name="user_file",
        required=True,
        accepted_types=[" PDF ", "pdf", "CSV", ""],
    )
    assert ok is True
    slot = step.attachments[0]
    assert slot.slot_id == slot_id
    assert slot.label == "Renamed"
    assert slot.variable_name == "user_file"
    assert slot.required is True
    assert slot.accepted_types == ["pdf", "csv"]
    assert key in ctrl.state.attachment_bindings
    assert ctrl.state.attachment_bindings[key] == "/tmp/attached.bin"

    ok_clear = ctrl.update_attachment_slot("s1", slot_id, accepted_types_clear=True)
    assert ok_clear is True
    assert step.attachments[0].accepted_types is None
    assert key in ctrl.state.attachment_bindings


def test_update_attachment_slot_rejects_empty_variable_name():
    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
        attachments=[
            AttachmentSlot(
                slot_id="fixed",
                variable_name="keep_me",
                label="L",
                required=False,
            )
        ],
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.selected_workflow_id = "w1"
    key = "s1::fixed"
    ctrl.state.attachment_bindings[key] = "/tmp/source.pdf"

    ok = ctrl.update_attachment_slot("s1", "fixed", variable_name="   ")
    assert ok is False
    assert step.attachments[0].variable_name == "keep_me"
    assert ctrl.state.attachment_bindings[key] == "/tmp/source.pdf"


def test_add_step_below_creates_graph_ready_step():
    ctrl = make_mock_ctrl()
    ctrl.config_service.load_models.return_value = ["gpt-test"]
    wf = WorkflowDef(id="w1", name="WF")
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.selected_workflow_id = "w1"

    sid = ctrl.add_step_below()
    assert sid is not None
    step = next(s for s in wf.steps if s.id == sid)
    assert step.execution_mode == "graph"
    assert len(step.inputs) >= 1
    assert step.inputs[0].name == "input"
    assert len(step.outputs) >= 1
    assert step.outputs[0].name == "output"


def test_rename_workflow_updates_draft_sets_dirty_and_notifies():
    ctrl = make_mock_ctrl()
    on_change = MagicMock()
    ctrl.set_state_changed_callback(on_change)

    wf = WorkflowDef(id="w1", name="Old Name")
    ctrl.state.workflow_drafts["w1"] = wf

    ok = ctrl.rename_workflow("w1", "  New Name  ")
    assert ok is True
    assert wf.name == "New Name"
    assert ctrl.state.is_dirty is True
    on_change.assert_called()


def test_rename_workflow_rejects_missing_empty_or_noop():
    ctrl = make_mock_ctrl()
    on_change = MagicMock()
    ctrl.set_state_changed_callback(on_change)

    wf = WorkflowDef(id="w1", name="WF")
    ctrl.state.workflow_drafts["w1"] = wf

    assert ctrl.rename_workflow("missing", "X") is False
    assert ctrl.rename_workflow("w1", "   ") is False
    assert ctrl.rename_workflow("w1", "WF") is False
    on_change.assert_not_called()


def test_connect_and_disconnect_step_input():
    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
        inputs=[InputPortDef(name="input")],
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.selected_workflow_id = "w1"

    ctrl.connect_step_input("s1", "upstream1", "output", "input")
    assert len(step.inputs[0].sources) == 1
    assert step.inputs[0].sources[0].step_id == "upstream1"
    assert ctrl.state.command_stack.can_undo()

    # Duplicate should not be added
    ctrl.connect_step_input("s1", "upstream1", "output", "input")
    assert len(step.inputs[0].sources) == 1

    # Add a second distinct source
    ctrl.connect_step_input("s1", "upstream2", "report", "input")
    assert len(step.inputs[0].sources) == 2

    # Disconnect by index
    ctrl.disconnect_step_input("s1", "input", 0)
    assert len(step.inputs[0].sources) == 1
    assert step.inputs[0].sources[0].step_id == "upstream2"

    # Connection operations participate in undo/redo
    ctrl.undo()
    assert len(step.inputs[0].sources) == 2
    assert step.inputs[0].sources[0].step_id == "upstream1"
    ctrl.redo()
    assert len(step.inputs[0].sources) == 1
    assert step.inputs[0].sources[0].step_id == "upstream2"


def test_connect_step_input_creates_port_if_missing():
    ctrl = make_mock_ctrl()
    step = StepDef(
        id="s1",
        name="step1",
        model="gpt",
        prompt_version="1",
        execution_mode="graph",
    )
    wf = WorkflowDef(id="w1", name="WF", steps=[step])
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.selected_workflow_id = "w1"

    assert len(step.inputs) == 0
    ctrl.connect_step_input("s1", "upstream1", "output", "data")
    assert len(step.inputs) == 1
    assert step.inputs[0].name == "data"
    assert len(step.inputs[0].sources) == 1


def test_dict_join_strategy_normalized_on_load():
    port = InputPortDef.from_dict(
        {
            "name": "test",
            "sources": [],
            "join_strategy": "dict",
        }
    )
    assert port.join_strategy == "json_map"


def test_rename_workflow_mutates_name_sets_dirty_and_notifies():
    ctrl = make_mock_ctrl()
    notify = MagicMock()
    ctrl.set_state_changed_callback(notify)

    wf = WorkflowDef(id="w1", name="WF1")
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.is_dirty = False

    ok = ctrl.rename_workflow("w1", "WF2")
    assert ok is True
    assert ctrl.state.workflow_drafts["w1"].name == "WF2"
    assert ctrl.state.is_dirty is True
    assert notify.call_count == 1


def test_rename_workflow_same_name_is_noop():
    ctrl = make_mock_ctrl()
    notify = MagicMock()
    ctrl.set_state_changed_callback(notify)

    wf = WorkflowDef(id="w1", name="WF1")
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.is_dirty = False

    ok = ctrl.rename_workflow("w1", " WF1 ")
    assert ok is False
    assert ctrl.state.workflow_drafts["w1"].name == "WF1"
    assert ctrl.state.is_dirty is False
    assert notify.call_count == 0


def test_rename_workflow_empty_name_is_rejected():
    ctrl = make_mock_ctrl()
    notify = MagicMock()
    ctrl.set_state_changed_callback(notify)

    wf = WorkflowDef(id="w1", name="WF1")
    ctrl.state.workflow_drafts["w1"] = wf
    ctrl.state.is_dirty = False

    ok = ctrl.rename_workflow("w1", "   ")
    assert ok is False
    assert ctrl.state.workflow_drafts["w1"].name == "WF1"
    assert ctrl.state.is_dirty is False
    assert notify.call_count == 0


def test_rename_workflow_missing_id_is_rejected():
    ctrl = make_mock_ctrl()
    notify = MagicMock()
    ctrl.set_state_changed_callback(notify)
    ctrl.state.is_dirty = False

    ok = ctrl.rename_workflow("missing", "WF2")
    assert ok is False
    assert ctrl.state.is_dirty is False
    assert notify.call_count == 0
