"""Unit tests for ui.flow_canvas.index_flow_edges (pure edge indexing)."""

from __future__ import annotations

import unittest

from core.enums import StepStatus
from ui.flow_canvas import index_flow_edges
from ui.viewmodels import FlowEdgeVM, FlowNodeVM


def _node(step_id: str, title: str) -> FlowNodeVM:
    return FlowNodeVM(
        step_id=step_id,
        title=title,
        purpose="",
        model="m",
        status=StepStatus.PENDING,
    )


class TestIndexFlowEdges(unittest.TestCase):
    def test_empty_edges_builds_title_map_only(self) -> None:
        nodes = [_node("a", "A"), _node("b", "B")]
        edges_in, edges_out, id_to_title = index_flow_edges([], nodes)
        self.assertEqual(id_to_title, {"a": "A", "b": "B"})
        self.assertEqual(edges_in, {})
        self.assertEqual(edges_out, {})

    def test_groups_incoming_and_outgoing(self) -> None:
        nodes = [_node("a", "Alpha"), _node("b", "Beta"), _node("c", "Gamma")]
        e1 = FlowEdgeVM(from_id="a", to_id="b", edge_type="dependency")
        e2 = FlowEdgeVM(from_id="b", to_id="c", edge_type="branch")
        edges_in, edges_out, id_to_title = index_flow_edges([e1, e2], nodes)

        self.assertEqual(id_to_title["b"], "Beta")
        self.assertEqual(edges_in["b"], [e1])
        self.assertEqual(edges_in["c"], [e2])
        self.assertEqual(edges_out["a"], [e1])
        self.assertEqual(edges_out["b"], [e2])

    def test_multiple_edges_same_endpoints_append_in_order(self) -> None:
        nodes = [_node("x", "X"), _node("y", "Y")]
        e1 = FlowEdgeVM(from_id="x", to_id="y", edge_type="sequential")
        e2 = FlowEdgeVM(from_id="x", to_id="y", edge_type="branch")
        edges_in, edges_out, _ = index_flow_edges([e1, e2], nodes)
        self.assertEqual(edges_in["y"], [e1, e2])
        self.assertEqual(edges_out["x"], [e1, e2])


if __name__ == "__main__":
    unittest.main()
