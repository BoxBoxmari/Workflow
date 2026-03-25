"""Tests for core.migrations — schema v1→v2 pipeline."""

import unittest

from core.migrations import migrate, normalize_workflow_dict


class TestMigrateV1ToV2(unittest.TestCase):
    def _v1_doc(self, steps=None):
        return {
            "workflows": [
                {
                    "id": "wf1",
                    "name": "Test",
                    "steps": steps
                    or [
                        {
                            "id": "s1",
                            "name": "analyze",
                            "model": "gpt-4o",
                            "prompt_version": "1",
                        }
                    ],
                }
            ]
        }

    def test_adds_schema_version(self):
        result = migrate(self._v1_doc())
        self.assertEqual(result["schema_version"], 3)

    def test_steps_get_title_purpose_ui(self):
        result = migrate(self._v1_doc())
        step = result["workflows"][0]["steps"][0]
        self.assertIn("title", step)
        self.assertIn("purpose", step)
        self.assertIn("ui", step)
        self.assertEqual(step["title"], "")
        self.assertEqual(step["purpose"], "")
        self.assertEqual(step["ui"], {})

    def test_existing_schema_version_not_downgraded(self):
        doc = self._v1_doc()
        doc["schema_version"] = 3
        result = migrate(doc)
        self.assertEqual(result["schema_version"], 3)

    def test_depends_on_string_normalized_to_list(self):
        doc = self._v1_doc(
            steps=[
                {
                    "id": "s1",
                    "name": "a",
                    "model": "gpt-4o",
                    "prompt_version": "1",
                    "depends_on": "s0",
                }
            ]
        )
        result = migrate(doc)
        step = result["workflows"][0]["steps"][0]
        self.assertIsInstance(step["depends_on"], list)
        self.assertEqual(step["depends_on"], ["s0"])

    def test_depends_on_none_normalized_to_list(self):
        doc = self._v1_doc(
            steps=[
                {
                    "id": "s1",
                    "name": "a",
                    "model": "gpt-4o",
                    "prompt_version": "1",
                    "depends_on": None,
                }
            ]
        )
        result = migrate(doc)
        step = result["workflows"][0]["steps"][0]
        self.assertEqual(step["depends_on"], [])

    def test_empty_string_depends_on_normalized(self):
        doc = self._v1_doc(
            steps=[
                {
                    "id": "s1",
                    "name": "a",
                    "model": "gpt-4o",
                    "prompt_version": "1",
                    "depends_on": "",
                }
            ]
        )
        result = migrate(doc)
        self.assertEqual(result["workflows"][0]["steps"][0]["depends_on"], [])

    def test_existing_title_preserved(self):
        doc = self._v1_doc(
            steps=[
                {
                    "id": "s1",
                    "name": "a",
                    "model": "gpt-4o",
                    "prompt_version": "1",
                    "title": "My Custom Title",
                }
            ]
        )
        result = migrate(doc)
        self.assertEqual(result["workflows"][0]["steps"][0]["title"], "My Custom Title")

    def test_multiple_workflows_migrated(self):
        doc = {
            "workflows": [
                {"id": "wf1", "name": "A", "steps": []},
                {"id": "wf2", "name": "B", "steps": []},
            ]
        }
        result = migrate(doc)
        self.assertEqual(len(result["workflows"]), 2)


class TestMigrateV2ToV3(unittest.TestCase):
    def _v2_doc(self):
        return {
            "schema_version": 2,
            "workflows": [
                {
                    "id": "wf1",
                    "name": "Test",
                    "steps": [
                        {
                            "id": "s1",
                            "name": "analyze",
                        }
                    ],
                }
            ],
        }

    def test_migration_v2_to_v3(self):
        result = migrate(self._v2_doc())
        self.assertEqual(result["schema_version"], 3)
        step = result["workflows"][0]["steps"][0]
        self.assertEqual(step["execution_mode"], "legacy")
        self.assertEqual(step["inputs"], [])
        self.assertEqual(step["outputs"], [])


class TestNormalizeWorkflowDict(unittest.TestCase):
    def test_adds_missing_description(self):
        result = normalize_workflow_dict({"id": "x", "name": "X", "steps": []})
        self.assertIn("description", result)

    def test_keeps_existing_description(self):
        result = normalize_workflow_dict(
            {"id": "x", "name": "X", "description": "hello", "steps": []}
        )
        self.assertEqual(result["description"], "hello")


if __name__ == "__main__":
    unittest.main()
