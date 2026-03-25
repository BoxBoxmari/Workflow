"""Tests for core.execution_plan."""

import unittest

from core.execution_plan import (
    CycleError,
    ExecutionPlan,
    MissingDependencyError,
)
from core.models import StepDef, WorkflowDef


def _make_step(step_id: str, depends_on=None) -> StepDef:
    return StepDef(
        id=step_id,
        name=f"name_{step_id}",
        model="gpt-4o",
        prompt_version="1",
        depends_on=depends_on or [],
    )


def _make_workflow(steps: list[StepDef]) -> WorkflowDef:
    return WorkflowDef(id="wf1", name="Test Workflow", steps=steps)


class TestExecutionPlanLinear(unittest.TestCase):
    """Linear A → B → C workflow."""

    def setUp(self):
        steps = [
            _make_step("A"),
            _make_step("B"),
            _make_step("C"),
        ]
        self.workflow = _make_workflow(steps)
        self.plan = ExecutionPlan.from_workflow(self.workflow)

    def test_order_is_sequential(self):
        self.assertEqual(self.plan.execution_order(), ["A", "B", "C"])

    def test_nodes_created(self):
        self.assertIn("A", self.plan.nodes)
        self.assertIn("B", self.plan.nodes)
        self.assertIn("C", self.plan.nodes)

    def test_depths(self):
        self.assertEqual(self.plan.nodes["A"].depth, 0)
        self.assertEqual(self.plan.nodes["B"].depth, 1)
        self.assertEqual(self.plan.nodes["C"].depth, 2)

    def test_predecessors(self):
        self.assertEqual(self.plan.nodes["A"].predecessors, [])
        self.assertIn("A", self.plan.nodes["B"].predecessors)

    def test_reachable_from_b(self):
        result = self.plan.reachable_from("B")
        self.assertIn("B", result)
        self.assertIn("C", result)
        self.assertNotIn("A", result)

    def test_reachable_from_a(self):
        result = self.plan.reachable_from("A")
        self.assertEqual(result, ["A", "B", "C"])

    def test_validate_no_errors(self):
        self.assertEqual(self.plan.validate(), [])


class TestExecutionPlanExplicitDeps(unittest.TestCase):
    """Branch-and-merge: A → B, A → C, (B,C) → D."""

    def setUp(self):
        steps = [
            _make_step("A"),
            _make_step("B", depends_on=["A"]),
            _make_step("C", depends_on=["A"]),
            _make_step("D", depends_on=["B", "C"]),
        ]
        self.workflow = _make_workflow(steps)
        self.plan = ExecutionPlan.from_workflow(self.workflow)

    def test_a_is_root(self):
        self.assertEqual(self.plan.nodes["A"].predecessors, [])

    def test_d_is_merge(self):
        self.assertTrue(self.plan.nodes["D"].is_merge)

    def test_a_is_branch_start(self):
        self.assertTrue(self.plan.nodes["A"].is_branch_start)

    def test_d_comes_last(self):
        self.assertEqual(self.plan.order[-1], "D")

    def test_a_comes_first(self):
        self.assertEqual(self.plan.order[0], "A")

    def test_reachable_from_b_excludes_c(self):
        # B → D, but C is a sibling not downstream of B
        result = self.plan.reachable_from("B")
        self.assertIn("B", result)
        self.assertIn("D", result)
        self.assertNotIn("A", result)

    def test_validate_no_errors(self):
        self.assertEqual(self.plan.validate(), [])


class TestExecutionPlanCycle(unittest.TestCase):
    """A → B → A cycle should raise CycleError."""

    def test_cycle_raises(self):
        steps = [
            _make_step("A", depends_on=["B"]),
            _make_step("B", depends_on=["A"]),
        ]
        wf = _make_workflow(steps)
        with self.assertRaises(CycleError):
            ExecutionPlan.from_workflow(wf)

    def test_self_loop_raises(self):
        steps = [_make_step("A", depends_on=["A"])]
        wf = _make_workflow(steps)
        with self.assertRaises(CycleError):
            ExecutionPlan.from_workflow(wf)


class TestExecutionPlanMissingDep(unittest.TestCase):
    """A depends on unknown step 'X' should raise MissingDependencyError."""

    def test_missing_dep_raises(self):
        steps = [_make_step("A", depends_on=["X"])]
        wf = _make_workflow(steps)
        with self.assertRaises(MissingDependencyError) as ctx:
            ExecutionPlan.from_workflow(wf)
        self.assertEqual(ctx.exception.missing_dep, "X")

    def test_missing_dep_step_id(self):
        steps = [_make_step("A", depends_on=["missing"])]
        wf = _make_workflow(steps)
        with self.assertRaises(MissingDependencyError) as ctx:
            ExecutionPlan.from_workflow(wf)
        self.assertEqual(ctx.exception.step_id, "A")


class TestExecutionPlanEmpty(unittest.TestCase):
    """Empty workflow should produce empty plan."""

    def test_empty_workflow(self):
        wf = _make_workflow([])
        plan = ExecutionPlan.from_workflow(wf)
        self.assertEqual(plan.order, [])
        self.assertEqual(plan.validate(), [])

    def test_single_step(self):
        wf = _make_workflow([_make_step("only")])
        plan = ExecutionPlan.from_workflow(wf)
        self.assertEqual(plan.order, ["only"])
        self.assertEqual(plan.nodes["only"].depth, 0)


class TestExecutionPlanEnabledFilter(unittest.TestCase):
    """Disabled steps excluded from execution_order when workflow provided."""

    def test_disabled_step_filtered(self):
        steps = [
            _make_step("A"),
            StepDef(
                id="B", name="b", model="gpt-4o", prompt_version="1", enabled=False
            ),
            _make_step("C"),
        ]
        wf = _make_workflow(steps)
        plan = ExecutionPlan.from_workflow(wf)
        order = plan.execution_order(enabled_only=True, workflow=wf)
        self.assertNotIn("B", order)
        self.assertIn("A", order)
        self.assertIn("C", order)


if __name__ == "__main__":
    unittest.main()
