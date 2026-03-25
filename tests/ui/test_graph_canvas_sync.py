import unittest

from core.models import (
    InputPortDef,
    OutputPortDef,
    SourceRef,
    StepDef,
    WorkflowDef,
)
from ui.viewmodels import build_flow_viewmodel


class TestGraphCanvasSync(unittest.TestCase):
    def test_graph_viewmodel_uses_input_sources_as_dependency_truth(self):
        wf = WorkflowDef(
            id="wf_graph_sync",
            name="Graph Sync",
            steps=[
                StepDef(
                    id="producer",
                    name="producer",
                    title="Producer",
                    model="gpt-4o",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="sum")],
                ),
                StepDef(
                    id="consumer",
                    name="consumer",
                    title="Consumer",
                    model="gpt-4o",
                    prompt_version="1",
                    execution_mode="graph",
                    depends_on=["stale_id_should_be_ignored"],
                    inputs=[
                        InputPortDef(
                            name="payload",
                            required=True,
                            join_strategy="first",
                            sources=[
                                SourceRef(step_id="producer", port="sum")
                            ],
                        )
                    ],
                    outputs=[OutputPortDef(name="out")],
                ),
            ],
        )

        nodes, _ = build_flow_viewmodel(wf)
        by_id = {n.step_id: n for n in nodes}

        self.assertEqual(by_id["consumer"].upstream_node_ids, ["producer"])
        self.assertIn("Producer", by_id["consumer"].upstream_title)
        self.assertIn("Consumer", by_id["producer"].downstream_title)


if __name__ == "__main__":
    unittest.main()
