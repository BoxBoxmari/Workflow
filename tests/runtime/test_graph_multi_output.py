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


class TestGraphMultiOutput(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runs_dir = Path(self.tmpdir) / "runs"
        self.prompts_dir = Path(self.tmpdir) / "prompts"
        self.prompts_dir.mkdir()
        (self.prompts_dir / "producer_v1.txt").write_text(
            "[user]\nProduce\n",
            encoding="utf-8",
        )
        (self.prompts_dir / "consumer_sum_v1.txt").write_text(
            "[user]\nValue: $payload\n",
            encoding="utf-8",
        )
        (self.prompts_dir / "consumer_flag_v1.txt").write_text(
            "[user]\nValue: $payload\n",
            encoding="utf-8",
        )

        self.storage = StorageManager(self.runs_dir)
        self.registry = PromptRegistry(self.prompts_dir)
        self.client = MagicMock(spec=WorkbenchClient)
        self.runner = AsyncGraphRunner(
            self.client,
            self.registry,
            self.storage,
            max_concurrency=3,
        )

    def test_multi_output_ports_route_to_correct_downstream_edges(self):
        def fake_completion(req):
            msg = str(req.messages)
            if "Produce" in msg:
                return ProviderResponse(
                    content='{"sum":"TOTAL_42","flag":"FLAG_TRUE"}',
                    raw_json={},
                    usage={},
                    status_code=200,
                )
            if "Value: TOTAL_42" in msg:
                self.assertIn("TOTAL_42", msg)
                self.assertNotIn("FLAG_TRUE", msg)
                return ProviderResponse(
                    content="SUM_DONE",
                    raw_json={},
                    usage={},
                    status_code=200,
                )
            if "Value: FLAG_TRUE" in msg:
                self.assertIn("FLAG_TRUE", msg)
                self.assertNotIn("TOTAL_42", msg)
                return ProviderResponse(
                    content="FLAG_DONE",
                    raw_json={},
                    usage={},
                    status_code=200,
                )
            raise AssertionError(f"Unexpected prompt payload: {msg}")

        self.client.chat_completion.side_effect = fake_completion

        wf = WorkflowDef(
            id="wf_multi_output",
            name="Multi Output Routing",
            steps=[
                StepDef(
                    id="producer",
                    name="producer",
                    model="gpt-4o",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="sum"), OutputPortDef(name="flag")],
                ),
                StepDef(
                    id="consumer_sum",
                    name="consumer_sum",
                    model="gpt-4o",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="payload",
                            required=True,
                            join_strategy="first",
                            sources=[SourceRef(step_id="producer", port="sum")],
                        )
                    ],
                    outputs=[OutputPortDef(name="out")],
                ),
                StepDef(
                    id="consumer_flag",
                    name="consumer_flag",
                    model="gpt-4o",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="payload",
                            required=True,
                            join_strategy="first",
                            sources=[SourceRef(step_id="producer", port="flag")],
                        )
                    ],
                    outputs=[OutputPortDef(name="out")],
                ),
            ],
        )

        ctx = self.runner.run(wf)
        self.assertEqual(ctx.status, "success", ctx.error)

        loaded_steps = self.storage.load_all_steps(ctx.run_id)
        producer = next(s for s in loaded_steps if s.step_id == "producer")
        self.assertEqual(producer.output_ports.get("sum"), "TOTAL_42")
        self.assertEqual(producer.output_ports.get("flag"), "FLAG_TRUE")

        c_sum = next(s for s in loaded_steps if s.step_id == "consumer_sum")
        c_flag = next(s for s in loaded_steps if s.step_id == "consumer_flag")
        self.assertEqual(c_sum.status, "success")
        self.assertEqual(c_flag.status, "success")


if __name__ == "__main__":
    unittest.main()
