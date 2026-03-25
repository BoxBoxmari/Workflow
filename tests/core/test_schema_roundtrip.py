import json
import shutil
import unittest
from pathlib import Path

from core.config_service import ConfigService
from core.models import InputPortDef, OutputPortDef, SourceRef, StepDef, WorkflowDef


class TestSchemaRoundtrip(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_config_roundtrip_env")
        self.test_dir.mkdir(exist_ok=True)
        self.service = ConfigService(self.test_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_save_load_roundtrip_keeps_execution_mode_inputs_outputs(self):
        wf = WorkflowDef(
            id="wf_roundtrip",
            name="Roundtrip Workflow",
            steps=[
                StepDef(
                    id="s1",
                    name="step1",
                    model="gpt-4o",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="doc",
                            sources=[SourceRef(step_id="input_node", port="doc")],
                            join_strategy="concat",
                        )
                    ],
                    outputs=[OutputPortDef(name="summary")],
                )
            ],
        )

        self.service.save_workflows([wf])

        raw = json.loads(self.service.workflows_file.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], 3)
        self.assertEqual(
            raw["workflows"][0].get("schema_version"),
            3,
            "Persisted workflow schema_version must be v3",
        )

        loaded = self.service.load_workflows()
        self.assertEqual(len(loaded), 1)
        loaded_wf = loaded[0]
        self.assertEqual(loaded_wf.schema_version, 3)

        loaded_step = loaded_wf.steps[0]
        self.assertEqual(loaded_step.execution_mode, "graph")
        self.assertEqual(len(loaded_step.inputs), 1)
        self.assertEqual(loaded_step.inputs[0].name, "doc")
        self.assertEqual(loaded_step.inputs[0].join_strategy, "concat")
        self.assertEqual(len(loaded_step.inputs[0].sources), 1)
        self.assertEqual(loaded_step.inputs[0].sources[0].step_id, "input_node")
        self.assertEqual(loaded_step.inputs[0].sources[0].port, "doc")
        self.assertEqual(len(loaded_step.outputs), 1)
        self.assertEqual(loaded_step.outputs[0].name, "summary")


if __name__ == "__main__":
    unittest.main()
