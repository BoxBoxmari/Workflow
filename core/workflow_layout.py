"""
core.workflow_layout — Compute visual layout data from a WorkflowGraph.

Assigns depth (vertical position) and lane (horizontal lane) to each
graph node.  Used by ui/viewmodels.py to produce rendering data for
flow_canvas.

Phase 3 note: full multi-lane rendering is scaffolded here but the
initial implementation places all steps in lane 0 by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.workflow_graph import WorkflowGraph


@dataclass
class LayoutNode:
    """Layout-computed position for a single step."""

    step_id: str
    depth: int = 0  # vertical position (row)
    lane: int = 0  # horizontal lane (column)
    is_merge: bool = False  # True if step has >1 predecessors
    is_branch_start: bool = False  # True if step has >1 successors


@dataclass
class LayoutResult:
    """Complete layout computation result."""

    nodes: dict[str, LayoutNode] = field(default_factory=dict)
    max_depth: int = 0
    max_lane: int = 0


def compute_layout(graph: WorkflowGraph) -> LayoutResult:
    """Compute layout positions from a WorkflowGraph.

    Algorithm:
    - Use topological order to assign depth (max of predecessor depths + 1).
    - Use ui.lane from GraphNode if set, otherwise default to 0.
    - Mark merge nodes (>1 predecessor) and branch starts (>1 successor).
    """
    result = LayoutResult()
    topo = graph.topological_order()
    depth_map: dict[str, int] = {}

    for step_id in topo:
        gnode = graph.nodes[step_id]
        # Depth = max(depth of predecessors) + 1, or 0 if root
        if gnode.predecessors:
            d = max(depth_map.get(p, 0) for p in gnode.predecessors) + 1
        else:
            d = 0
        depth_map[step_id] = d

        layout_node = LayoutNode(
            step_id=step_id,
            depth=d,
            lane=gnode.lane,
            is_merge=len(gnode.predecessors) > 1,
            is_branch_start=len(gnode.successors) > 1,
        )
        result.nodes[step_id] = layout_node

    if result.nodes:
        result.max_depth = max(n.depth for n in result.nodes.values())
        result.max_lane = max(n.lane for n in result.nodes.values())

    return result
