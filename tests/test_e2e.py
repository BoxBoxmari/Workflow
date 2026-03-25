"""
End-to-end test: ingest file → run workflow (mocked) → verify persistence.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from core.ingestion import ingest_file
from core.models import (
    ProviderResponse,
    StepDef,
    WorkflowDef,
)
from core.prompts import PromptRegistry
from core.storage import StorageManager
from core.workflow import WorkflowRunner


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runs_dir = Path(self.tmpdir) / "runs"
        self.prompts_dir = Path(self.tmpdir) / "prompts"
        self.prompts_dir.mkdir()

        # Create prompt templates
        (self.prompts_dir / "analyze_v1.txt").write_text(
            "[system]\nAnalyze.\n\n[user]\n$input\n",
            encoding="utf-8",
        )
        (self.prompts_dir / "summarize_v1.txt").write_text(
            "[user]\nSummarize: $input\n",
            encoding="utf-8",
        )

        # Create test input file
        self.input_file = Path(self.tmpdir) / "test_input.txt"
        self.input_file.write_text(
            "This is a test document about business analysis.\n"
            "It contains important findings about project risks.\n",
            encoding="utf-8",
        )

    def test_full_flow(self):
        """Ingest file → run 2-step workflow → verify all persisted."""
        # 1. Ingest
        ingest_result = ingest_file(self.input_file)
        self.assertTrue(ingest_result.ok)
        self.assertIn("business analysis", ingest_result.content)

        # 2. Set up core services
        storage = StorageManager(self.runs_dir)
        registry = PromptRegistry(self.prompts_dir)

        client = MagicMock()
        call_count = [0]

        def mock_chat(req):
            call_count[0] += 1
            return ProviderResponse(
                content=f"Mock response #{call_count[0]}",
                raw_json={
                    "choices": [{"message": {"content": f"Mock #{call_count[0]}"}}]
                },
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                status_code=200,
            )

        client.chat_completion.side_effect = mock_chat

        # 3. Define workflow
        wf = WorkflowDef(
            id="e2e_test",
            name="E2E Test Workflow",
            steps=[
                StepDef(
                    id="analyze",
                    name="analyze",
                    model="test-model",
                    prompt_version="1",
                    output_mapping="analysis",
                ),
                StepDef(
                    id="summarize",
                    name="summarize",
                    model="test-model",
                    prompt_version="1",
                    input_mapping="analysis",
                ),
            ],
        )

        # 4. Run
        runner = WorkflowRunner(client, registry, storage)
        ctx = runner.run(wf, initial_input=ingest_result.content)

        # 5. Verify run completed
        self.assertEqual(ctx.status, "success")
        self.assertEqual(len(ctx.step_results), 2)

        # 6. Verify persistence
        loaded_run = storage.load_run(ctx.run_id)
        self.assertEqual(loaded_run.status, "success")
        self.assertIsNotNone(loaded_run.workflow_snapshot)

        all_steps = storage.load_all_steps(ctx.run_id)
        self.assertEqual(len(all_steps), 2)
        self.assertEqual(all_steps[0].step_id, "analyze")
        self.assertEqual(all_steps[1].step_id, "summarize")
        self.assertIn("Mock response #1", all_steps[0].output_text)
        self.assertIn("Mock response #2", all_steps[1].output_text)

        # 7. Verify events
        events = storage.load_events(ctx.run_id)
        event_types = [e["event_type"] for e in events]
        self.assertIn("run_started", event_types)
        self.assertIn("step_completed", event_types)
        self.assertIn("run_finished", event_types)

        # 8. Verify index
        runs = storage.list_runs()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].run_id, ctx.run_id)
        self.assertEqual(runs[0].status, "success")

        # 9. Verify variable chaining
        self.assertIn("analysis", ctx.variables)

    def test_attachments_integration(self):
        """Verify attachment resolution through ingestion and merging into variables."""
        from core.models import AttachmentSlot

        # Prompt that uses an attachment variable explicitly
        (self.prompts_dir / "attach_v1.txt").write_text(
            "[user]\nReview this attachment: $attachment_content_step1_fileA",
            encoding="utf-8",
        )

        wf = WorkflowDef(
            id="attach_wf",
            name="Attachment WF",
            steps=[
                StepDef(
                    id="step1",
                    name="attach",
                    model="test_model",
                    prompt_version="1",
                    attachments=[
                        AttachmentSlot(
                            slot_id="fileA", variable_name="varA", required=True
                        )
                    ],
                )
            ],
        )

        # 1. Create a mock attachment file
        attach_file = Path(self.tmpdir) / "attach.txt"
        attach_file.write_text("Hello attachment data.", encoding="utf-8")

        # 2. Ingest the attachment manually as the controller would do
        ingested = ingest_file(attach_file)
        initial_vars = {"attachment_content_step1_fileA": ingested.content}

        # 3. Setup core services
        storage = StorageManager(self.runs_dir)
        registry = PromptRegistry(self.prompts_dir)

        client = MagicMock()
        client.chat_completion.return_value = ProviderResponse(
            content="Attachment parsed.", raw_json={}, usage={}, status_code=200
        )

        # 4. Run workflow
        runner = WorkflowRunner(client, registry, storage)
        ctx = runner.run(wf, initial_input="noop", initial_variables=initial_vars)

        self.assertEqual(ctx.status, "success")

        # 5. Verify prompt received attachment content
        req = client.chat_completion.call_args[0][0]
        self.assertIn("Hello attachment data.", req.messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
