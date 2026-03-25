"""Tests for core.prompts — prompt registry and rendering."""

import tempfile
import unittest
from pathlib import Path

from core.prompts import PromptRegistry


class TestPromptRegistry(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = PromptRegistry(Path(self.tmpdir))

        # Create test templates
        (Path(self.tmpdir) / "analyze_v1.txt").write_text(
            "[system]\nYou are a tester.\n\n[user]\nAnalyze: $input\n",
            encoding="utf-8",
        )
        (Path(self.tmpdir) / "analyze_v2.txt").write_text(
            "[system]\nExpert tester.\n\n[user]\nDeep analysis: $input\n",
            encoding="utf-8",
        )
        (Path(self.tmpdir) / "summarize_v1.txt").write_text(
            "[user]\nSummarize: $input\n",
            encoding="utf-8",
        )

    def test_list_steps(self):
        steps = self.registry.list_steps()
        self.assertIn("analyze", steps)
        self.assertIn("summarize", steps)

    def test_list_versions(self):
        versions = self.registry.list_versions("analyze")
        self.assertEqual(versions, ["1", "2"])

    def test_render_two_roles(self):
        messages = self.registry.render("analyze", "1", {"input": "test data"})
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("tester", messages[0]["content"])
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("test data", messages[1]["content"])

    def test_render_single_role(self):
        messages = self.registry.render("summarize", "1", {"input": "summary"})
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertIn("summary", messages[0]["content"])

    def test_render_missing_template(self):
        with self.assertRaises(FileNotFoundError):
            self.registry.render("nonexistent", "1", {})

    def test_safe_substitute(self):
        """Missing variables should be left as-is."""
        messages = self.registry.render("analyze", "1", {})
        self.assertIn("$input", messages[1]["content"])


_FIXTURES = Path(__file__).parent / "fixtures" / "golden"
_CONFIG_PROMPTS = Path(__file__).parent.parent / "config" / "prompts"


@unittest.skipUnless(
    _FIXTURES.is_dir(), "Golden fixtures not found, skipping regression"
)
class TestGoldenPrompt(unittest.TestCase):
    """M2 — Regression test: analyze_v1 renders exactly as the golden fixture specifies."""

    def test_golden_analyze_v1_prompt(self):
        """Rendered messages from analyze_v1.txt must match golden_expected_prompt.json."""
        import json as _json

        golden_input = (
            (_FIXTURES / "golden_input.txt").read_text(encoding="utf-8").strip()
        )
        expected = _json.loads(
            (_FIXTURES / "golden_expected_prompt.json").read_text(encoding="utf-8")
        )

        registry = PromptRegistry(_CONFIG_PROMPTS)
        messages = registry.render("analyze", "1", {"input1": golden_input})

        self.assertEqual(
            len(messages),
            len(expected),
            f"Message count mismatch: got {len(messages)}, expected {len(expected)}",
        )
        for i, (actual_msg, expected_msg) in enumerate(zip(messages, expected)):
            self.assertEqual(
                actual_msg["role"],
                expected_msg["role"],
                f"Role mismatch at message {i}",
            )
            self.assertEqual(
                actual_msg["content"],
                expected_msg["content"],
                f"Content mismatch at message {i} — template may have drifted",
            )


if __name__ == "__main__":
    unittest.main()
