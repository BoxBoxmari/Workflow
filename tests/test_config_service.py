import unittest
import shutil
from pathlib import Path

from core.models import WorkflowDef, StepDef
from core.config_service import ConfigService


class TestConfigService(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_config_env")
        self.test_dir.mkdir(exist_ok=True)
        self.service = ConfigService(self.test_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_save_and_load_workflows(self):
        wf = WorkflowDef(
            id="test1",
            name="Test Workflow",
            steps=[StepDef(id="s1", name="step1", model="gpt-4o", prompt_version="1")],
        )
        self.service.save_workflows([wf])

        loaded = self.service.load_workflows()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].id, "test1")
        self.assertEqual(loaded[0].name, "Test Workflow")
        self.assertEqual(len(loaded[0].steps), 1)
        self.assertEqual(loaded[0].steps[0].id, "s1")

    def test_save_and_load_prompt(self):
        self.service.save_prompt("analyze", "1", "Test content")
        content = self.service.load_prompt("analyze", "1")
        self.assertEqual(content, "Test content")

    def test_list_prompt_versions(self):
        self.service.save_prompt("analyze", "1", "V1")
        self.service.save_prompt("analyze", "2", "V2")
        self.service.save_prompt("other", "1", "Other")

        versions = self.service.list_prompt_versions("analyze")
        self.assertEqual(versions, ["1", "2"])

        steps = self.service.list_prompt_steps()
        self.assertIn("analyze", steps)
        self.assertIn("other", steps)

    def test_next_prompt_version(self):
        self.assertEqual(self.service.next_prompt_version("new_step"), "1")
        self.service.save_prompt("new_step", "1", "V1")
        self.service.save_prompt("new_step", "2", "V2")
        self.assertEqual(self.service.next_prompt_version("new_step"), "3")


if __name__ == "__main__":
    unittest.main()
