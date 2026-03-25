"""Tests for core.async_graph_runner — graph asynchronous step runner."""

import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from core.models import (
    ProviderResponse,
    StepDef,
    WorkflowDef,
    InputPortDef,
    OutputPortDef,
    SourceRef,
)
from core.prompts import PromptRegistry
from core.provider import WorkbenchClient
from core.storage import StorageManager
from core.async_graph_runner import AsyncGraphRunner


class TestAsyncGraphRunner(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runs_dir = Path(self.tmpdir) / "runs"
        self.prompts_dir = Path(self.tmpdir) / "prompts"
        self.prompts_dir.mkdir()

        # Create basic prompt
        (self.prompts_dir / "step1_v1.txt").write_text(
            "[user]\nProcess: $input\n", encoding="utf-8"
        )
        (self.prompts_dir / "step2_v1.txt").write_text(
            "[user]\nSummarize: $input\n", encoding="utf-8"
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

        self.runner = AsyncGraphRunner(
            self.client, self.registry, self.storage, max_concurrency=2
        )

    def test_single_step_graph(self):
        wf = WorkflowDef(
            id="wf1",
            name="Test WF",
            steps=[
                StepDef(
                    id="step1",
                    name="step1",
                    model="test-model",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="out", kind="text")],
                )
            ],
        )
        ctx = self.runner.run(wf, initial_input="test input")

        self.assertEqual(ctx.status, "success")
        self.assertEqual(len(ctx.step_results), 1)
        self.client.chat_completion.assert_called_once()

        # Verify storage
        loaded = self.storage.load_run(ctx.run_id)
        self.assertEqual(loaded.status, "success")

    def test_fan_in_concat(self):
        wf = WorkflowDef(
            id="wf2",
            name="Fan In WF",
            steps=[
                StepDef(
                    id="src1",
                    name="step1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="out")],
                ),
                StepDef(
                    id="src2",
                    name="step1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="out")],
                ),
                StepDef(
                    id="dest",
                    name="step2",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="in",
                            required=True,
                            join_strategy="concat",
                            sources=[
                                SourceRef(step_id="src1", port="out"),
                                SourceRef(step_id="src2", port="out"),
                            ],
                        )
                    ],
                ),
            ],
        )
        ctx = self.runner.run(wf)

        self.assertEqual(ctx.status, "success")
        self.assertEqual(len(ctx.step_results), 3)
        self.assertEqual(self.client.chat_completion.call_count, 3)

    def test_multi_output_json_mapping(self):
        # The mock should return JSON
        self.client.chat_completion.return_value = ProviderResponse(
            content='{"sum": "summary text", "flag": "true"}',
            raw_json={},
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            status_code=200,
        )

        wf = WorkflowDef(
            id="wfm",
            name="Multi Output",
            steps=[
                StepDef(
                    id="s1",
                    name="step1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[
                        OutputPortDef(name="sum", kind="text"),
                        OutputPortDef(name="flag", kind="text"),
                    ],
                )
            ],
        )
        ctx = self.runner.run(wf)
        self.assertEqual(ctx.status, "success")

        # We can test if the storage holds the right thing, or check the step results directly
        # run_ctx stores StepResult IDs, not full payload objects.
        # Let's load the step to check its output port parsing
        step1_res = self.storage.load_all_steps(ctx.run_id)[0]
        self.assertEqual(step1_res.output_ports.get("sum"), "summary text")
        self.assertEqual(step1_res.output_ports.get("flag"), "true")

    def test_partial_failure_blocks_downstream(self):
        # Fake completion fails if model is "failbox"
        def fake_completion(req):
            if req.model == "failbox":
                return ProviderResponse(
                    content="", raw_json={}, usage={}, status_code=500, error="API died"
                )
            return ProviderResponse(
                content="ok", raw_json={}, usage={}, status_code=200
            )

        self.client.chat_completion.side_effect = fake_completion

        wf = WorkflowDef(
            id="wf_fail",
            name="Fail Block WF",
            steps=[
                StepDef(
                    id="src_ok",
                    name="s1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="out")],
                ),
                StepDef(
                    id="src_fail",
                    name="s2",
                    model="failbox",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="out")],
                ),
                StepDef(
                    id="dest",
                    name="s3",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="in",
                            sources=[SourceRef(step_id="src_fail", port="out")],
                        )
                    ],
                ),
            ],
        )

        ctx = self.runner.run(wf)
        self.assertEqual(ctx.status, "error")
        # dest should be blocked and not executed
        # run_ctx.step_results only tracks started/executed steps
        self.assertIn("src_ok", ctx.step_results)
        self.assertIn("src_fail", ctx.step_results)
        self.assertNotIn("dest", ctx.step_results)

        events = self.storage.load_events(ctx.run_id)
        blocked_events = [e for e in events if e.get("event_type") == "node_blocked"]
        self.assertEqual(len(blocked_events), 1)
        self.assertEqual(blocked_events[0]["step_id"], "dest")

    def test_cancel_graph(self):
        wf = WorkflowDef(
            id="wfcancel",
            name="Cancel WF",
            steps=[
                StepDef(
                    id="step1",
                    name="step1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                ),
                StepDef(
                    id="step2",
                    name="step2",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="in", sources=[SourceRef(step_id="step1", port="out")]
                        )
                    ],
                ),
            ],
        )

        def fake_completion(*args, **kwargs):
            time.sleep(0.1)
            return ProviderResponse(
                content="mock", raw_json={}, usage={}, status_code=200
            )

        self.client.chat_completion.side_effect = fake_completion

        thread = self.runner.run_thread(wf)
        time.sleep(0.05)
        self.runner.cancel()
        thread.join()

        runs = self.storage.list_runs()
        ctx_metadata = runs[-1]
        ctx = self.storage.load_run(ctx_metadata.run_id)

        self.assertEqual(ctx.status, "cancelled")
        self.assertLess(len(ctx.step_results), 2)


if __name__ == "__main__":
    unittest.main()
