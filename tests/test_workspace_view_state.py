from core.enums import WorkspaceView, DrawerTab
from core.models import WorkflowDef, StepDef


def test_design_results_toggle_changes_state(controller):
    # Default is DESIGN
    assert controller.state.view == WorkspaceView.DESIGN

    controller.toggle_view()
    assert controller.state.view == WorkspaceView.RESULTS

    controller.toggle_view()
    assert controller.state.view == WorkspaceView.DESIGN


def test_start_run_forces_results_view(controller):
    wf = WorkflowDef(
        id="wf1",
        name="WF",
        steps=[StepDef(id="s1", name="S1", model="test-model-1", prompt_version="1")],
    )
    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    controller.state.view = WorkspaceView.DESIGN
    controller.start_run()

    assert controller.state.view == WorkspaceView.RESULTS


def test_start_run_opens_drawer(controller):
    wf = WorkflowDef(
        id="wf1",
        name="WF",
        steps=[StepDef(id="s1", name="S1", model="test-model-1", prompt_version="1")],
    )
    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    controller.state.drawer_visible = False
    controller.start_run()

    assert controller.state.drawer_visible is True


def test_drawer_tab_defaults_to_output(controller):
    wf = WorkflowDef(
        id="wf1",
        name="WF",
        steps=[StepDef(id="s1", name="S1", model="test-model-1", prompt_version="1")],
    )
    controller.state.workflow_drafts["wf1"] = wf
    controller.state.selected_workflow_id = "wf1"

    controller.state.drawer_tab = DrawerTab.LOG
    controller.start_run()

    assert controller.state.drawer_tab == DrawerTab.OUTPUT
