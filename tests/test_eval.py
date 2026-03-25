"""Tests for core.eval — model and prompt comparison logic (mocked provider).

Gap H1: this file was planned but missing from the implementation.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from core.eval import compare_models, compare_prompts
from core.models import ProviderResponse, StepDef
from core.prompts import PromptRegistry
from core.provider import WorkbenchClient
from core.storage import StorageManager


def _make_mock_client(
    content: str = "mock output", status_code: int = 200
) -> MagicMock:
    """Return a mock WorkbenchClient whose chat_completion always succeeds."""
    client = MagicMock(spec=WorkbenchClient)
    client.chat_completion.return_value = ProviderResponse(
        content=content,
        raw_json={"choices": [{"message": {"content": content}}]},
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        status_code=status_code,
    )
    return client


def _make_prompt_registry(
    tmp_dir: Path, step_name: str, versions: list[str]
) -> PromptRegistry:
    """Write minimal prompt templates and return a PromptRegistry pointing at them."""
    prompts_dir = tmp_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    for v in versions:
        (prompts_dir / f"{step_name}_v{v}.txt").write_text(
            f"[system]\nYou are a test assistant v{v}.\n\n[user]\n$input\n",
            encoding="utf-8",
        )
    return PromptRegistry(prompts_dir)


class TestCompareModels(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.storage = StorageManager(self.tmp_path / "runs")

        self.step_name = "analyze"
        self.step_def = StepDef(
            id="analyze_step",
            name=self.step_name,
            model="gpt-4o",
            prompt_version="1",
        )
        self.prompt_registry = _make_prompt_registry(
            self.tmp_path, self.step_name, ["1"]
        )

    def tearDown(self):
        self.storage._write_queue.stop()
        self.tmp.cleanup()

    def test_compare_models_returns_one_result_per_model(self):
        client = _make_mock_client()
        models = ["model-a", "model-b", "model-c"]
        run_ctx, results = compare_models(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="test input",
            models=models,
        )
        self.assertEqual(len(results), 3, "Expected one StepResult per model")
        self.assertEqual(client.chat_completion.call_count, 3)

    def test_compare_models_run_type_is_comparison(self):
        client = _make_mock_client()
        run_ctx, results = compare_models(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="hello",
            models=["model-a", "model-b"],
        )
        self.assertEqual(run_ctx.run_type, "comparison")

    def test_compare_models_all_success_sets_run_status(self):
        client = _make_mock_client(status_code=200)
        run_ctx, results = compare_models(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="hello",
            models=["model-a", "model-b"],
        )
        self.assertEqual(run_ctx.status, "success")
        for r in results:
            self.assertEqual(r.status, "success")

    def test_compare_models_persists_run_to_storage(self):
        client = _make_mock_client()
        run_ctx, _ = compare_models(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="hello",
            models=["model-a", "model-b"],
        )
        self.storage._write_queue.flush()
        run_json = self.tmp_path / "runs" / run_ctx.run_id / "run.json"
        self.assertTrue(run_json.is_file(), f"run.json not found at {run_json}")

    def test_compare_models_each_result_uses_requested_model(self):
        client = _make_mock_client()
        models = ["alpha", "beta"]
        _, results = compare_models(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="hi",
            models=models,
        )
        result_models = [r.metrics.model for r in results]
        for m in models:
            self.assertIn(m, result_models)

    def test_compare_models_provider_error_marks_status_error(self):
        client = _make_mock_client(status_code=500)
        # status_code 500 → ProviderResponse.ok is False when error flag set
        client.chat_completion.return_value = ProviderResponse(
            content="",
            status_code=500,
            error="HTTP 500: Internal Server Error",
        )
        run_ctx, results = compare_models(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="hi",
            models=["model-a"],
        )
        self.assertEqual(results[0].status, "error")
        self.assertEqual(run_ctx.status, "error")


class TestComparePrompts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.storage = StorageManager(self.tmp_path / "runs")

        self.step_name = "summarize"
        self.step_def = StepDef(
            id="summarize_step",
            name=self.step_name,
            model="gpt-4o",
            prompt_version="1",
        )
        self.prompt_registry = _make_prompt_registry(
            self.tmp_path, self.step_name, ["1", "2", "3"]
        )

    def tearDown(self):
        self.storage._write_queue.stop()
        self.tmp.cleanup()

    def test_compare_prompts_returns_one_result_per_version(self):
        client = _make_mock_client()
        versions = ["1", "2", "3"]
        run_ctx, results = compare_prompts(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="test input",
            prompt_versions=versions,
        )
        self.assertEqual(len(results), 3)
        self.assertEqual(client.chat_completion.call_count, 3)

    def test_compare_prompts_run_type_is_comparison(self):
        client = _make_mock_client()
        run_ctx, _ = compare_prompts(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="hello",
            prompt_versions=["1", "2"],
        )
        self.assertEqual(run_ctx.run_type, "comparison")

    def test_compare_prompts_each_result_tracks_version(self):
        client = _make_mock_client()
        _, results = compare_prompts(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="hi",
            prompt_versions=["1", "2"],
        )
        versions_used = [r.metrics.prompt_version for r in results]
        self.assertIn("1", versions_used)
        self.assertIn("2", versions_used)

    def test_compare_prompts_persists_run_to_storage(self):
        client = _make_mock_client()
        run_ctx, _ = compare_prompts(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="hello",
            prompt_versions=["1", "2"],
        )
        self.storage._write_queue.flush()
        run_json = self.tmp_path / "runs" / run_ctx.run_id / "run.json"
        self.assertTrue(run_json.is_file(), f"run.json not found at {run_json}")

    def test_compare_prompts_all_use_same_model(self):
        client = _make_mock_client()
        _, results = compare_prompts(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="hi",
            prompt_versions=["1", "2"],
        )
        for r in results:
            self.assertEqual(r.metrics.model, self.step_def.model)

    def test_compare_prompts_missing_template_marks_error(self):
        client = _make_mock_client()
        # version "99" template does not exist → should produce error result
        run_ctx, results = compare_prompts(
            client=client,
            prompt_registry=self.prompt_registry,
            storage=self.storage,
            step_def=self.step_def,
            input_text="hi",
            prompt_versions=["99"],  # non-existent
        )
        self.assertEqual(results[0].status, "error")


if __name__ == "__main__":
    unittest.main()
