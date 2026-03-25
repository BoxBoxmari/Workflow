"""Tests for core.workflow_graph — dependency graph builder."""

import unittest

from core.workflow_graph import build_graph
from core.models import StepDef, WorkflowDef


def _step(step_id: str, depends_on=None) -> StepDef:
    return StepDef(
        id=step_id,
        name=f"n_{step_id}",
        model="gpt-4o",
        prompt_version="1",
        depends_on=depends_on or [],
        execution_mode="legacy",
    )


def _wf(*step_ids, explicit_deps=None) -> WorkflowDef:
    steps = [_step(s) for s in step_ids]
    if explicit_deps:
        for sid, deps in explicit_deps.items():
            for s in steps:
                if s.id == sid:
                    s.depends_on = deps
    return WorkflowDef(id="wf", name="W", steps=steps)


class TestBuildGraphLinear(unittest.TestCase):
    def setUp(self):
        self.wf = _wf("A", "B", "C")
        self.g = build_graph(self.wf)

    def test_nodes_created(self):
        self.assertEqual(set(self.g.nodes.keys()), {"A", "B", "C"})

    def test_sequential_edges(self):
        edge_pairs = {(e.from_id, e.to_id) for e in self.g.edges}
        self.assertIn(("A", "B"), edge_pairs)
        self.assertIn(("B", "C"), edge_pairs)

    def test_root_is_a(self):
        self.assertEqual(self.g.root_ids, ["A"])

    def test_leaf_is_c(self):
        self.assertEqual(self.g.leaf_ids, ["C"])

    def test_successors(self):
        self.assertIn("B", self.g.nodes["A"].successors)


class TestBuildGraphExplicit(unittest.TestCase):
    """A → B, A → C, (B,C) → D"""

    def setUp(self):
        self.wf = _wf(
            "A",
            "B",
            "C",
            "D",
            explicit_deps={"B": ["A"], "C": ["A"], "D": ["B", "C"]},
        )
        self.g = build_graph(self.wf)

    def test_d_has_two_predecessors(self):
        self.assertEqual(len(self.g.nodes["D"].predecessors), 2)

    def test_a_has_two_successors(self):
        self.assertEqual(len(self.g.nodes["A"].successors), 2)

    def test_no_spurious_sequential_edges(self):
        # B has explicit dep, should NOT also have implicit seq edge from A
        b_preds = self.g.nodes["B"].predecessors
        self.assertEqual(b_preds.count("A"), 1)

    def test_dependency_edge_type(self):
        dep_edges = [e for e in self.g.edges if e.to_id == "D"]
        self.assertTrue(all(e.edge_type == "dependency" for e in dep_edges))


class TestTopologicalOrder(unittest.TestCase):
    def test_linear_order(self):
        wf = _wf("A", "B", "C")
        g = build_graph(wf)
        order = g.topological_order()
        self.assertEqual(order, ["A", "B", "C"])

    def test_branch_merge_order(self):
        wf = _wf(
            "A", "B", "C", "D", explicit_deps={"B": ["A"], "C": ["A"], "D": ["B", "C"]}
        )
        g = build_graph(wf)
        order = g.topological_order()
        self.assertLess(order.index("A"), order.index("B"))
        self.assertLess(order.index("A"), order.index("C"))
        self.assertLess(order.index("B"), order.index("D"))
        self.assertLess(order.index("C"), order.index("D"))

    def test_has_cycle_false_for_linear(self):
        wf = _wf("A", "B")
        g = build_graph(wf)
        self.assertFalse(g.has_cycle())

    def test_empty_workflow(self):
        wf = WorkflowDef(id="x", name="x", steps=[])
        g = build_graph(wf)
        self.assertEqual(g.topological_order(), [])


if __name__ == "__main__":
    unittest.main()
