import json
import shutil
import unittest
from pathlib import Path

from core.config_service import ConfigService


class TestSchemaMigrationV2ToV3(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_config_migration_env")
        self.test_dir.mkdir(exist_ok=True)
        self.service = ConfigService(self.test_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_v2_payload_without_graph_fields_still_loads_with_v3_contract(self):
        payload_v2 = {
            "schema_version": 2,
            "workflows": [
                {
                    "id": "wf_v2",
                    "name": "Legacy Workflow",
                    "steps": [
                        {
                            "id": "s1",
                            "name": "analyze",
                            "model": "gpt-4o",
                            "prompt_version": "1",
                        }
                    ],
                }
            ],
        }
        self.service.workflows_file.write_text(
            json.dumps(payload_v2, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        workflows = self.service.load_workflows()
        self.assertEqual(len(workflows), 1)
        wf = workflows[0]
        self.assertEqual(wf.id, "wf_v2")
        self.assertEqual(
            wf.schema_version, 3, "Workflow contract must be locked to schema v3"
        )

        self.assertEqual(len(wf.steps), 1)
        step = wf.steps[0]
        self.assertEqual(step.execution_mode, "legacy")
        self.assertEqual(step.inputs, [])
        self.assertEqual(step.outputs, [])


if __name__ == "__main__":
    unittest.main()
