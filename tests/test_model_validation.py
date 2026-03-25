import pytest
from core.models import WorkflowDef, StepDef
from core.config_validation import validate_workflow


def test_valid_model_passes_validation(controller, config_service):
    # test-model-1 is in models.json via conftest fixture
    wf = WorkflowDef(
        id="wf1",
        name="WF",
        steps=[StepDef(id="s1", name="S1", model="test-model-1", prompt_version="1")],
    )

    available_prompts = {"S1": ["1"]}
    available_models = ["test-model-1"]

    errors = validate_workflow(wf, [], available_prompts, available_models)
    assert not any(e.level == "error" for e in errors)


def test_invalid_model_fails_validation(controller, config_service):
    wf = WorkflowDef(
        id="wf1",
        name="WF",
        steps=[
            StepDef(id="s1", name="S1", model="non-existent-model", prompt_version="1")
        ],
    )

    available_prompts = {"S1": ["1"]}
    available_models = ["test-model-1"]

    errors = validate_workflow(wf, [], available_prompts, available_models)
    assert any("not in the valid models catalog" in e.message for e in errors)


def test_save_blocked_when_model_invalid(controller, temp_project_root):
    # Create workflow with invalid model
    wf = WorkflowDef(
        id="wf1",
        name="WF",
        steps=[StepDef(id="s1", name="S1", model="invalid", prompt_version="1")],
    )
    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    # Try to save
    ok, msg = controller.save()
    assert ok is False
    assert "validation errors" in msg.lower()


def test_save_fails_when_selected_valid_other_draft_has_error(controller):
    bad = WorkflowDef(
        id="wf_bad",
        name="Bad",
        steps=[StepDef(id="s1", name="S1", model="invalid", prompt_version="1")],
    )
    good = WorkflowDef(
        id="wf_good",
        name="Good",
        steps=[StepDef(id="s2", name="S1", model="test-model-1", prompt_version="1")],
    )
    controller.state.workflow_drafts["wf_bad"] = bad
    controller.state.workflow_drafts["wf_good"] = good
    controller.state.selected_workflow_id = "wf_good"

    ok, msg = controller.save()
    assert ok is False
    assert "validation errors" in msg.lower()


def test_save_fails_when_none_selected_but_draft_has_error(controller):
    bad = WorkflowDef(
        id="wf_bad",
        name="Bad",
        steps=[StepDef(id="s1", name="S1", model="invalid", prompt_version="1")],
    )
    controller.state.workflow_drafts["wf_bad"] = bad
    controller.state.selected_workflow_id = None

    ok, msg = controller.save()
    assert ok is False
    assert "validation errors" in msg.lower()


def test_run_blocked_when_model_invalid(controller):
    wf = WorkflowDef(
        id="wf1",
        name="WF",
        steps=[StepDef(id="s1", name="S1", model="invalid", prompt_version="1")],
    )
    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    assert controller.can_run is False
    from unittest.mock import MagicMock

    with pytest.MonkeyPatch.context() as m:
        m.setattr("tkinter.messagebox.showerror", MagicMock())
        assert controller.start_run() is False


def test_empty_model_field_fails_validation():
    wf = WorkflowDef(
        id="wf1",
        name="WF",
        steps=[StepDef(id="s1", name="S1", model="", prompt_version="1")],
    )

    available_prompts = {"S1": ["1"]}
    available_models = ["test-model-1"]

    errors = validate_workflow(wf, [], available_prompts, available_models)
    assert any("Model field is empty" in e.message for e in errors)
