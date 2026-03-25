import unittest
from core.models import WorkflowDef, StepDef, AttachmentSlot
from core.enums import StepStatus
from ui.viewmodels import build_flow_viewmodel, build_inspector_viewmodel


class TestUIViewModels(unittest.TestCase):
    def setUp(self):
        self.wf = WorkflowDef(
            id="test_wf",
            name="Test",
            steps=[
                StepDef(
                    id="step1",
                    name="analyze",
                    title="Input Step",
                    model="m",
                    prompt_version="1",
                    attachments=[
                        AttachmentSlot(
                            slot_id="file1", variable_name="var1", required=True
                        ),
                        AttachmentSlot(
                            slot_id="file2", variable_name="var2", required=False
                        ),
                    ],
                    execution_mode="legacy",
                ),
                StepDef(
                    id="step2",
                    name="summarize",
                    model="m",
                    prompt_version="1",
                    depends_on=["step1"],
                    input_mapping="step1",
                    output_mapping="out",
                    execution_mode="legacy",
                ),
            ],
        )

    def test_build_flow_viewmodel_basic(self):
        nodes, edges = build_flow_viewmodel(self.wf)

        self.assertEqual(len(nodes), 2)
        self.assertEqual(len(edges), 1)

        node1 = nodes[0]
        self.assertEqual(node1.step_id, "step1")
        self.assertEqual(node1.title, "Input Step")
        self.assertEqual(node1.upstream_title, "Starts here")
        self.assertEqual(node1.downstream_title, "summarize")
        self.assertEqual(node1.status, StepStatus.PENDING)
        self.assertTrue(node1.missing_required)  # no bindings provided

        node2 = nodes[1]
        self.assertEqual(node2.step_id, "step2")
        self.assertEqual(node2.title, "summarize")  # fallback to name
        self.assertEqual(node2.upstream_title, "Input Step")
        self.assertEqual(node2.downstream_title, "Ends here")

    def test_build_flow_viewmodel_with_bindings_and_results(self):
        # Create a mock result object
        class MockMetrics:
            latency_ms = 150.5

        class MockResult:
            status = StepStatus.SUCCESS.value
            output_text = "Analysis complete."
            metrics = MockMetrics()

        bindings = {"step1::file1": "path/to/file1.txt"}
        results = {"step1": MockResult()}

        nodes, edges = build_flow_viewmodel(
            self.wf,
            selected_step_id="step2",
            step_results=results,
            attachment_bindings=bindings,
        )

        node1 = nodes[0]
        self.assertFalse(node1.missing_required)  # required file1 is provided
        self.assertEqual(node1.file_count, 1)
        self.assertEqual(node1.status, StepStatus.SUCCESS)
        self.assertEqual(node1.output_preview, "Analysis complete.")
        self.assertEqual(node1.duration_ms, 150.5)
        self.assertFalse(node1.is_selected)

        node2 = nodes[1]
        self.assertEqual(node2.status, StepStatus.PENDING)
        self.assertTrue(node2.is_selected)

    def test_build_inspector_viewmodel(self):
        step = self.wf.steps[0]
        step.purpose = "Analyze input"
        step.role_text = "You are a system"
        step.task_text = "Do this"
        step.ui = {"lane": 1, "branch_group": "A"}

        vm = build_inspector_viewmodel(step, prompt_text="full text")

        self.assertEqual(vm.step_id, "step1")
        self.assertEqual(vm.name, "analyze")
        self.assertEqual(vm.title, "Input Step")
        self.assertEqual(vm.purpose, "Analyze input")
        self.assertEqual(vm.role_text, "You are a system")
        self.assertEqual(vm.task_text, "Do this")
        self.assertEqual(vm.prompt_text, "full text")
        self.assertEqual(vm.lane, 1)
        self.assertEqual(vm.branch_group, "A")
        self.assertEqual(len(vm.attachments), 2)


if __name__ == "__main__":
    unittest.main()
