"""Tests for core.workflow — sequential step runner (mocked provider)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from core.models import (
    ProviderResponse,
    StepDef,
    WorkflowDef,
)
from core.prompts import PromptRegistry
from core.provider import WorkbenchClient
from core.storage import StorageManager
from core.workflow import WorkflowRunner


class TestWorkflowRunner(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runs_dir = Path(self.tmpdir) / "runs"
        self.prompts_dir = Path(self.tmpdir) / "prompts"
        self.prompts_dir.mkdir()

        # Create test prompt templates
        (self.prompts_dir / "step1_v1.txt").write_text(
            "[system]\nTest system.\n\n[user]\nProcess: $input\n",
            encoding="utf-8",
        )
        (self.prompts_dir / "step2_v1.txt").write_text(
            "[user]\nSummarize: $input\n",
            encoding="utf-8",
        )

        self.storage = StorageManager(self.runs_dir)
        self.registry = PromptRegistry(self.prompts_dir)

        # Mock client
        self.client = MagicMock(spec=WorkbenchClient)
        self.client.chat_completion.return_value = ProviderResponse(
            content="mock output",
            raw_json={"choices": [{"message": {"content": "mock output"}}]},
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            status_code=200,
        )

        self.runner = WorkflowRunner(self.client, self.registry, self.storage)

    def test_single_step_workflow(self):
        wf = WorkflowDef(
            id="wf1",
            name="Test WF",
            steps=[
                StepDef(
                    id="step1", name="step1", model="test-model", prompt_version="1"
                )
            ],
        )
        ctx = self.runner.run(wf, initial_input="test input")

        self.assertEqual(ctx.status, "success")
        self.assertEqual(len(ctx.step_results), 1)
        self.client.chat_completion.assert_called_once()

    def test_two_step_chaining(self):
        wf = WorkflowDef(
            id="wf2",
            name="Chain WF",
            steps=[
                StepDef(
                    id="step1",
                    name="step1",
                    model="m",
                    prompt_version="1",
                    output_mapping="analysis",
                ),
                StepDef(
                    id="step2",
                    name="step2",
                    model="m",
                    prompt_version="1",
                    input_mapping="analysis",
                ),
            ],
        )
        ctx = self.runner.run(wf, initial_input="data")

        self.assertEqual(ctx.status, "success")
        self.assertEqual(len(ctx.step_results), 2)
        self.assertEqual(self.client.chat_completion.call_count, 2)
        # Verify variable chaining
        self.assertIn("analysis", ctx.variables)

    def test_disabled_step_skipped(self):
        wf = WorkflowDef(
            id="wf3",
            name="Skip WF",
            steps=[
                StepDef(id="step1", name="step1", model="m", prompt_version="1"),
                StepDef(
                    id="step2",
                    name="step2",
                    model="m",
                    prompt_version="1",
                    enabled=False,
                ),
            ],
        )
        ctx = self.runner.run(wf, initial_input="data")

        self.assertEqual(ctx.status, "success")
        self.assertEqual(len(ctx.step_results), 1)  # only step1

    def test_error_stops_workflow(self):
        self.client.chat_completion.return_value = ProviderResponse(
            status_code=500,
            error="Internal server error",
        )
        wf = WorkflowDef(
            id="wf4",
            name="Error WF",
            steps=[
                StepDef(id="step1", name="step1", model="m", prompt_version="1"),
                StepDef(id="step2", name="step2", model="m", prompt_version="1"),
            ],
        )
        ctx = self.runner.run(wf, initial_input="data")

        self.assertEqual(ctx.status, "error")
        self.assertEqual(len(ctx.step_results), 1)  # stopped after step1

    def test_callbacks_called(self):
        start_cb = MagicMock()
        complete_cb = MagicMock()
        run_cb = MagicMock()

        wf = WorkflowDef(
            id="wf5",
            name="CB WF",
            steps=[StepDef(id="step1", name="step1", model="m", prompt_version="1")],
        )
        self.runner.run(
            wf,
            initial_input="data",
            on_step_start=start_cb,
            on_step_complete=complete_cb,
            on_run_complete=run_cb,
        )

        start_cb.assert_called_once()
        complete_cb.assert_called_once()
        run_cb.assert_called_once()

    def test_run_persisted(self):
        wf = WorkflowDef(
            id="wf6",
            name="Persist WF",
            steps=[StepDef(id="step1", name="step1", model="m", prompt_version="1")],
        )
        ctx = self.runner.run(wf, initial_input="data")

        # Verify persisted
        loaded = self.storage.load_run(ctx.run_id)
        self.assertEqual(loaded.status, "success")

        steps = self.storage.load_all_steps(ctx.run_id)
        self.assertEqual(len(steps), 1)

        events = self.storage.load_events(ctx.run_id)
        self.assertGreater(len(events), 0)

        runs = self.storage.list_runs()
        self.assertEqual(len(runs), 1)

    def test_initial_variables_injection(self):
        wf = WorkflowDef(
            id="wf7",
            name="Init Vars WF",
            steps=[StepDef(id="step1", name="step1", model="m", prompt_version="1")],
        )
        ctx = self.runner.run(
            wf, initial_variables={"input": "file content", "other": "value"}
        )

        self.assertEqual(ctx.status, "success")
        self.assertEqual(ctx.variables.get("input"), "file content")
        self.assertEqual(ctx.variables.get("other"), "value")
        self.client.chat_completion.assert_called_once()

    def test_mixed_initial_input_and_variables(self):
        wf = WorkflowDef(
            id="wf8",
            name="Mixed Init WF",
            steps=[StepDef(id="step1", name="step1", model="m", prompt_version="1")],
        )
        ctx = self.runner.run(
            wf, initial_input="manual text", initial_variables={"extra": "data"}
        )

        self.assertEqual(ctx.status, "success")
        self.assertEqual(ctx.variables.get("input"), "manual text")
        self.assertEqual(ctx.variables.get("extra"), "data")
        self.client.chat_completion.assert_called_once()

    def test_run_async_cancels(self):
        wf = WorkflowDef(
            id="wf_cancel",
            name="Cancel WF",
            steps=[
                StepDef(id="step1", name="step1", model="m", prompt_version="1"),
                StepDef(id="step2", name="step2", model="m", prompt_version="1"),
            ],
        )

        # Slow down step execution to allow cancel to trigger
        import time

        def fake_completion(*args, **kwargs):
            time.sleep(0.1)
            return ProviderResponse(
                content="mock",
                raw_json={},
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                status_code=200,
            )

        self.client.chat_completion.side_effect = fake_completion

        # Start async run
        thread = self.runner.run_async(wf, initial_input="data")

        # Give it a tiny bit of time to start step 1
        time.sleep(0.05)
        self.runner.cancel()

        # Wait for thread to finish
        thread.join()

        # Ensure background writes (index update) complete before listing runs
        self.storage._write_queue.flush()

        # Because we cancelled before step 1 finished (or right after), step 2 shouldn't run.
        runs = self.storage.list_runs()
        ctx_metadata = runs[-1]
        ctx = self.storage.load_run(ctx_metadata.run_id)

        self.assertEqual(ctx.status, "cancelled")
        self.assertLess(len(ctx.step_results), 2)

    def test_run_async_unhandled_exception(self):
        wf = WorkflowDef(
            id="wf_ex",
            name="Exception WF",
            steps=[StepDef(id="step1", name="step1", model="m", prompt_version="1")],
        )
        self.client.chat_completion.side_effect = ValueError("Fatal crash")

        thread = self.runner.run_async(wf, initial_input="data")
        thread.join()

        # Ensure background write completes
        self.storage._write_queue.flush()

        runs = self.storage.list_runs()
        ctx_metadata = runs[-1]
        ctx = self.storage.load_run(ctx_metadata.run_id)

        self.assertEqual(ctx.status, "error")
        self.assertIn("Fatal crash", ctx.error)


if __name__ == "__main__":
    unittest.main()
