import json
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


class TestJoinSemantics(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runs_dir = Path(self.tmpdir) / "runs"
        self.prompts_dir = Path(self.tmpdir) / "prompts"
        self.prompts_dir.mkdir()
        (self.prompts_dir / "src_v1.txt").write_text("[user]\nS\n", encoding="utf-8")
        (self.prompts_dir / "dest_v1.txt").write_text(
            "[user]\nJoined: $payload\n", encoding="utf-8"
        )

        self.storage = StorageManager(self.runs_dir)
        self.registry = PromptRegistry(self.prompts_dir)
        self.client = MagicMock(spec=WorkbenchClient)

    def _build_runner(self):
        return AsyncGraphRunner(
            self.client,
            self.registry,
            self.storage,
            max_concurrency=3,
        )

    def test_join_first_uses_first_non_empty_value(self):
        outputs = {
            "src_empty": "",
            "src_full": "VALUE_B",
            "dest": "DONE",
        }

        def fake_completion(req):
            if "Joined:" in str(req.messages):
                self.assertIn("VALUE_B", str(req.messages))
                return ProviderResponse(
                    content=outputs["dest"],
                    raw_json={},
                    usage={},
                    status_code=200,
                )
            if len(self.client.chat_completion.mock_calls) == 1:
                return ProviderResponse(
                    content=outputs["src_empty"],
                    raw_json={},
                    usage={},
                    status_code=200,
                )
            return ProviderResponse(
                content=outputs["src_full"],
                raw_json={},
                usage={},
                status_code=200,
            )

        self.client.chat_completion.side_effect = fake_completion
        runner = self._build_runner()

        wf = WorkflowDef(
            id="wf_first",
            name="Join First",
            steps=[
                StepDef(
                    id="src_empty",
                    name="src",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="out")],
                ),
                StepDef(
                    id="src_full",
                    name="src",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="out")],
                ),
                StepDef(
                    id="dest",
                    name="dest",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="payload",
                            required=True,
                            join_strategy="first",
                            sources=[
                                SourceRef(step_id="src_empty", port="out"),
                                SourceRef(step_id="src_full", port="out"),
                            ],
                        )
                    ],
                ),
            ],
        )

        ctx = runner.run(wf)
        self.assertEqual(ctx.status, "success")

    def test_join_json_map_maps_sources_to_json_object(self):
        def fake_completion(req):
            if "Joined:" in str(req.messages):
                msg = str(req.messages)
                self.assertIn("src_a.out", msg)
                self.assertIn("src_b.out", msg)
                return ProviderResponse(
                    content="DONE",
                    raw_json={},
                    usage={},
                    status_code=200,
                )
            if len(self.client.chat_completion.mock_calls) == 1:
                return ProviderResponse(
                    content=json.dumps({"x": 1}),
                    raw_json={},
                    usage={},
                    status_code=200,
                )
            return ProviderResponse(
                content=json.dumps({"y": 2}),
                raw_json={},
                usage={},
                status_code=200,
            )

        self.client.chat_completion.side_effect = fake_completion
        runner = self._build_runner()

        wf = WorkflowDef(
            id="wf_json_map",
            name="Join JSON Map",
            steps=[
                StepDef(
                    id="src_a",
                    name="src",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="out")],
                ),
                StepDef(
                    id="src_b",
                    name="src",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="out")],
                ),
                StepDef(
                    id="dest",
                    name="dest",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="payload",
                            required=True,
                            join_strategy="json_map",
                            sources=[
                                SourceRef(step_id="src_a", port="out"),
                                SourceRef(step_id="src_b", port="out"),
                            ],
                        )
                    ],
                ),
            ],
        )

        ctx = runner.run(wf)
        self.assertEqual(ctx.status, "success")


if __name__ == "__main__":
    unittest.main()
