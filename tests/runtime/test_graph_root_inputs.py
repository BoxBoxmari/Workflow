import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from core.async_graph_runner import AsyncGraphRunner
from core.models import (
    InputPortDef,
    OutputPortDef,
    ProviderResponse,
    SourceRef,
    StepDef,
    WorkflowDef,
)
from core.prompts import PromptRegistry
from core.provider import WorkbenchClient
from core.storage import StorageManager


class TestGraphRootInputs(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runs_dir = Path(self.tmpdir) / "runs"
        self.prompts_dir = Path(self.tmpdir) / "prompts"
        self.prompts_dir.mkdir()
        (self.prompts_dir / "consumer_v1.txt").write_text(
            "[user]\nInput: $doc\n", encoding="utf-8"
        )

        self.storage = StorageManager(self.runs_dir)
        self.registry = PromptRegistry(self.prompts_dir)
        self.client = MagicMock(
            spec=WorkbenchClient,
        )
        self.client.chat_completion.return_value = ProviderResponse(
            content="consumed",
            raw_json={},
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            status_code=200,
        )
        self.runner = AsyncGraphRunner(
            self.client,
            self.registry,
            self.storage,
        )

    def test_root_external_input_source_resolves_from_run_input(
        self,
    ):
        source_ref = SourceRef(step_id="__input__", port="input")
        wf = WorkflowDef(
            id="wf_root",
            name="Root Input Workflow",
            steps=[
                StepDef(
                    id="consumer_node",
                    name="consumer",
                    model="gpt-4o",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="doc",
                            required=True,
                            join_strategy="first",
                            sources=[source_ref],
                        )
                    ],
                    outputs=[OutputPortDef(name="out")],
                )
            ],
        )
        self.assertEqual(source_ref.step_id, "__input__")
        self.assertEqual(source_ref.port, "input")

        ctx = self.runner.run(wf, initial_input="ROOT_VALUE")
        self.assertEqual(ctx.status, "success")
        self.client.chat_completion.assert_called_once()
        req = self.client.chat_completion.call_args.args[0]
        self.assertIn("ROOT_VALUE", str(req.messages))


if __name__ == "__main__":
    unittest.main()
