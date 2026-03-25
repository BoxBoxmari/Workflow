"""Tests for core.workflow_layout — depth/lane assignment."""

import unittest

from core.models import StepDef, WorkflowDef
from core.workflow_graph import build_graph
from core.workflow_layout import compute_layout


def _step(step_id: str, depends_on=None, lane=0) -> StepDef:
    return StepDef(
        id=step_id,
        name=f"n_{step_id}",
        model="gpt-4o",
        prompt_version="1",
        depends_on=depends_on or [],
        ui={"lane": lane} if lane else {},
    )


def _wf(*steps) -> WorkflowDef:
    return WorkflowDef(id="wf", name="W", steps=list(steps))


class TestComputeLayoutLinear(unittest.TestCase):
    def setUp(self):
        wf = _wf(_step("A"), _step("B"), _step("C"))
        g = build_graph(wf)
        self.layout = compute_layout(g)

    def test_depths_assigned(self):
        self.assertEqual(self.layout.nodes["A"].depth, 0)
        self.assertEqual(self.layout.nodes["B"].depth, 1)
        self.assertEqual(self.layout.nodes["C"].depth, 2)

    def test_max_depth(self):
        self.assertEqual(self.layout.max_depth, 2)

    def test_lanes_default_zero(self):
        for n in self.layout.nodes.values():
            self.assertEqual(n.lane, 0)


class TestComputeLayoutBranchMerge(unittest.TestCase):
    def setUp(self):
        wf = _wf(
            _step("A"),
            _step("B", depends_on=["A"], lane=0),
            _step("C", depends_on=["A"], lane=1),
            _step("D", depends_on=["B", "C"]),
        )
        g = build_graph(wf)
        self.layout = compute_layout(g)

    def test_a_is_depth_0(self):
        self.assertEqual(self.layout.nodes["A"].depth, 0)

    def test_d_is_deepest(self):
        self.assertEqual(
            self.layout.nodes["D"].depth,
            max(n.depth for n in self.layout.nodes.values()),
        )

    def test_d_is_merge(self):
        self.assertTrue(self.layout.nodes["D"].is_merge)

    def test_a_is_branch_start(self):
        self.assertTrue(self.layout.nodes["A"].is_branch_start)

    def test_c_has_lane_1(self):
        self.assertEqual(self.layout.nodes["C"].lane, 1)


class TestComputeLayoutEmpty(unittest.TestCase):
    def test_empty_layout(self):
        wf = WorkflowDef(id="x", name="x", steps=[])
        g = build_graph(wf)
        layout = compute_layout(g)
        self.assertEqual(layout.max_depth, 0)
        self.assertEqual(layout.max_lane, 0)
        self.assertEqual(layout.nodes, {})


class TestComputeLayoutMaxLane(unittest.TestCase):
    def test_max_lane_computed(self):
        wf = _wf(
            _step("A"),
            _step("B", depends_on=["A"], lane=2),
        )
        g = build_graph(wf)
        layout = compute_layout(g)
        self.assertEqual(layout.max_lane, 2)


if __name__ == "__main__":
    unittest.main()
