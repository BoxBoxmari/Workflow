"""
core.execution_plan — Dependency-aware execution planner.

Validates the workflow dependency graph, detects cycles, and computes
a topological execution order.  Supports run-from-step semantics by
computing the set of steps reachable from a given starting point.

Usage
-----
    plan = ExecutionPlan.from_workflow(workflow_def)
    order = plan.execution_order()                      # full run
    subset = plan.reachable_from(step_id)               # run-from-step
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from core.models import WorkflowDef

log = logging.getLogger("workbench.core.execution_plan")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CycleError(ValueError):
    """Raised when a circular dependency is detected in the workflow graph."""

    def __init__(self, cycle_path: list[str]) -> None:
        self.cycle_path = cycle_path
        super().__init__(f"Cycle detected in workflow graph: {' → '.join(cycle_path)}")


class MissingDependencyError(ValueError):
    """Raised when a step declares a dependency on an unknown step ID."""

    def __init__(self, step_id: str, missing_dep: str) -> None:
        self.step_id = step_id
        self.missing_dep = missing_dep
        super().__init__(f"Step '{step_id}' depends on unknown step '{missing_dep}'")


# ---------------------------------------------------------------------------
# Plan node
# ---------------------------------------------------------------------------


@dataclass
class PlanNode:
    """A node in the execution plan."""

    step_id: str
    step_name: str
    predecessors: list[str] = field(default_factory=list)
    successors: list[str] = field(default_factory=list)
    depth: int = 0  # topological depth (0 = root)
    is_merge: bool = False  # True if >1 predecessor
    is_branch_start: bool = False  # True if >1 successor


# ---------------------------------------------------------------------------
# Execution plan
# ---------------------------------------------------------------------------


@dataclass
class ExecutionPlan:
    """Validated, topologically-sorted execution plan for a workflow.

    Attributes
    ----------
    nodes : dict mapping step_id → PlanNode
    order : list of step_ids in topological execution order
    workflow_id : source workflow id
    """

    nodes: dict[str, PlanNode] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    workflow_id: str = ""

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_workflow(cls, workflow: WorkflowDef) -> "ExecutionPlan":
        """Build and validate an ExecutionPlan from a WorkflowDef.

        Raises CycleError if circular dependencies exist.
        Raises MissingDependencyError if a step references an unknown dep.
        """
        plan = cls(workflow_id=workflow.id)
        step_ids = {s.id for s in workflow.steps}
        step_ids_ordered = [s.id for s in workflow.steps]

        # Build nodes
        for idx, step in enumerate(workflow.steps):
            # Validate dependencies exist
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise MissingDependencyError(step.id, dep)

            node = PlanNode(
                step_id=step.id,
                step_name=step.name,
                predecessors=list(step.depends_on),
            )
            plan.nodes[step.id] = node

        # Add implicit sequential edges for steps with no explicit depends_on
        for idx, step_id in enumerate(step_ids_ordered):
            node = plan.nodes[step_id]
            if not node.predecessors and idx > 0:
                prev_id = step_ids_ordered[idx - 1]
                node.predecessors.append(prev_id)

        # Populate successors
        for node in plan.nodes.values():
            for pred_id in node.predecessors:
                plan.nodes[pred_id].successors.append(node.step_id)

        # Mark merge/branch nodes
        for node in plan.nodes.values():
            node.is_merge = len(node.predecessors) > 1
            node.is_branch_start = len(node.successors) > 1

        # Topological sort (Kahn's algorithm) + cycle detection
        in_degree: dict[str, int] = {sid: 0 for sid in plan.nodes}
        for node in plan.nodes.values():
            for succ in node.successors:
                in_degree[succ] += 1

        queue = [sid for sid, d in in_degree.items() if d == 0]
        topo: list[str] = []

        while queue:
            # Prefer original list order for determinism among equals
            queue.sort(key=lambda x: step_ids_ordered.index(x))
            sid = queue.pop(0)
            topo.append(sid)
            for succ in plan.nodes[sid].successors:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        if len(topo) < len(plan.nodes):
            # Cycle exists — find it via DFS for error reporting
            visited = set(topo)
            remaining = [s for s in step_ids_ordered if s not in visited]
            cycle = _find_cycle(plan.nodes, remaining[0] if remaining else "?")
            raise CycleError(cycle)

        # Assign depths
        depth_map: dict[str, int] = {}
        for sid in topo:
            node = plan.nodes[sid]
            d = max((depth_map.get(p, -1) for p in node.predecessors), default=-1) + 1
            depth_map[sid] = d
            node.depth = d

        plan.order = topo
        return plan

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def execution_order(
        self, enabled_only: bool = True, workflow: Optional[WorkflowDef] = None
    ) -> list[str]:
        """Return step IDs in topological execution order.

        If ``workflow`` and ``enabled_only=True`` are provided, disabled
        steps are filtered out but their successors are still kept.
        """
        if enabled_only and workflow:
            disabled = {s.id for s in workflow.steps if not s.enabled}
            return [sid for sid in self.order if sid not in disabled]
        return list(self.order)

    def reachable_from(self, start_step_id: str) -> list[str]:
        """Return step IDs reachable from start_step_id (inclusive).

        Used for run-from-step semantics: only execute the step and its
        transitive successors.
        """
        if start_step_id not in self.nodes:
            return []

        visited: set[str] = set()
        queue = [start_step_id]
        while queue:
            sid = queue.pop(0)
            if sid in visited:
                continue
            visited.add(sid)
            queue.extend(self.nodes[sid].successors)

        # Return in topological order
        return [sid for sid in self.order if sid in visited]

    def predecessors_of(self, step_id: str) -> list[str]:
        """All steps that must complete before step_id (direct predecessors)."""
        if step_id not in self.nodes:
            return []
        return list(self.nodes[step_id].predecessors)

    def has_cycle(self) -> bool:
        """Returns True if the plan detected a cycle (plan will be empty)."""
        return len(self.order) < len(self.nodes)

    def validate(self) -> list[str]:
        """Return a list of validation error messages (empty = valid)."""
        errors: list[str] = []
        if self.has_cycle():
            errors.append("Workflow contains a circular dependency.")
        return errors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_cycle(nodes: dict[str, PlanNode], start: str) -> list[str]:
    """DFS-based cycle path finder for error reporting."""
    path: list[str] = []
    visited: set[str] = set()
    on_stack: set[str] = set()

    def dfs(sid: str) -> bool:
        visited.add(sid)
        on_stack.add(sid)
        path.append(sid)
        for succ in nodes.get(sid, PlanNode(step_id=sid, step_name=sid)).successors:
            if succ not in visited:
                if dfs(succ):
                    return True
            elif succ in on_stack:
                path.append(succ)
                return True
        path.pop()
        on_stack.discard(sid)
        return False

    dfs(start)
    return path
