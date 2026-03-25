"""
core.workflow_graph — Build a dependency graph from WorkflowDef.

Nodes represent steps, edges represent data-flow (depends_on + implicit
sequential order).  The graph is used by workflow_layout for lane placement
and by future execution planning for topological ordering.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.models import WorkflowDef

ROOT_SOURCE_IDS = {"__input__", "workflow_input", "$input"}


@dataclass
class GraphNode:
    """A node in the workflow dependency graph."""

    step_id: str
    step_name: str
    title: str
    index: int  # position in the original step list
    predecessors: list[str] = field(default_factory=list)
    successors: list[str] = field(default_factory=list)
    lane: int = 0
    depth: int = 0


@dataclass
class GraphEdge:
    """A directed edge between two nodes."""

    from_id: str
    to_id: str
    edge_type: str = "sequential"  # "sequential" | "dependency" | "branch"


@dataclass
class WorkflowGraph:
    """Computed dependency graph for a workflow."""

    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)
    root_ids: list[str] = field(default_factory=list)
    leaf_ids: list[str] = field(default_factory=list)

    def topological_order(self) -> list[str]:
        """Return step IDs in topological order (Kahn's algorithm)."""
        in_degree: dict[str, int] = {nid: 0 for nid in self.nodes}
        for edge in self.edges:
            if edge.to_id in in_degree:
                in_degree[edge.to_id] += 1

        queue = [nid for nid, d in in_degree.items() if d == 0]
        result: list[str] = []
        while queue:
            nid = queue.pop(0)
            result.append(nid)
            for edge in self.edges:
                if edge.from_id == nid and edge.to_id in in_degree:
                    in_degree[edge.to_id] -= 1
                    if in_degree[edge.to_id] == 0:
                        queue.append(edge.to_id)

        return result

    def has_cycle(self) -> bool:
        """True if the graph contains a cycle."""
        return len(self.topological_order()) < len(self.nodes)


def build_graph(workflow: WorkflowDef) -> WorkflowGraph:
    """Build a WorkflowGraph from a WorkflowDef.

    Edge logic:
    - Graph mode: edges come from `inputs[*].sources[*].step_id`
      (except root inputs).
    - Legacy mode: edges come from `depends_on`, else implicit sequential edge.
    """
    graph = WorkflowGraph()

    # Build nodes
    for idx, step in enumerate(workflow.steps):
        lane = (
            step.ui.get("lane", 0)
            if hasattr(step, "ui") and isinstance(step.ui, dict)
            else 0
        )
        node = GraphNode(
            step_id=step.id,
            step_name=step.name,
            title=getattr(step, "title", "") or step.name,
            index=idx,
            lane=lane,
        )
        graph.nodes[step.id] = node

    # Build edges
    step_ids = [s.id for s in workflow.steps]
    for idx, step in enumerate(workflow.steps):
        node = graph.nodes[step.id]
        mode = getattr(step, "execution_mode", "legacy")
        if mode == "graph":
            seen_preds: set[str] = set()
            for input_def in getattr(step, "inputs", []):
                for src in getattr(input_def, "sources", []):
                    dep_id = getattr(src, "step_id", "")
                    if dep_id and dep_id not in ROOT_SOURCE_IDS:
                        if dep_id not in graph.nodes or dep_id in seen_preds:
                            continue
                        edge = GraphEdge(
                            from_id=dep_id, to_id=step.id, edge_type="dependency"
                        )
                        graph.edges.append(edge)
                        node.predecessors.append(dep_id)
                        graph.nodes[dep_id].successors.append(step.id)
                        seen_preds.add(dep_id)
        elif step.depends_on:
            for dep_id in step.depends_on:
                if dep_id in graph.nodes:
                    edge = GraphEdge(
                        from_id=dep_id, to_id=step.id, edge_type="dependency"
                    )
                    graph.edges.append(edge)
                    node.predecessors.append(dep_id)
                    graph.nodes[dep_id].successors.append(step.id)
        elif idx > 0:
            prev_id = step_ids[idx - 1]
            edge = GraphEdge(from_id=prev_id, to_id=step.id, edge_type="sequential")
            graph.edges.append(edge)
            node.predecessors.append(prev_id)
            graph.nodes[prev_id].successors.append(step.id)

    # Identify roots and leaves
    graph.root_ids = [nid for nid, n in graph.nodes.items() if not n.predecessors]
    graph.leaf_ids = [nid for nid, n in graph.nodes.items() if not n.successors]

    return graph
