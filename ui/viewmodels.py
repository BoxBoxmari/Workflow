"""
ui.viewmodels — View-model layer between data models and UI rendering.

Panels render from these view-models, never directly from WorkflowDef.
The WorkspaceController builds view-models whenever state changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from core.enums import StepStatus
from core.models import WorkflowDef, StepDef, AttachmentSlot
from core.workflow_graph import build_graph
from core.workflow_layout import compute_layout


# ---------------------------------------------------------------------------
# Flow canvas view-models
# ---------------------------------------------------------------------------

_INTERNAL_STEP_NAME_RE = r"^step_[0-9a-f]{8}$"


def _is_internal_step_name(name: object) -> bool:
    s = (str(name) if name is not None else "").strip()
    if not s:
        return False
    return bool(re.match(_INTERNAL_STEP_NAME_RE, s))


def _display_title(step: StepDef) -> str:
    title = (step.title or "").strip()
    if title:
        return title
    name = (step.name or "").strip()
    if name and not _is_internal_step_name(name):
        return name
    return "Untitled step"


def _inspector_title(step: StepDef) -> str:
    return (step.title or "").strip()


@dataclass
class FlowNodeVM:
    """View-model for a single step card in the flow canvas."""

    step_id: str
    title: str  # display title (avoid leaking internal IDs)
    purpose: str  # short description
    model: str
    status: StepStatus = StepStatus.PENDING
    # Visual flow arrows — natural language, no variable names
    upstream_title: str = ""  # "Starts here" or previous step's title
    downstream_title: str = ""  # "Ends here" or next step's title
    has_files: bool = False
    file_count: int = 0
    missing_required: bool = False
    duration_ms: Optional[float] = None
    is_selected: bool = False
    is_enabled: bool = True
    output_preview: str = ""  # first N chars of output, if available
    depth: int = 0
    lane: int = 0
    is_merge: bool = False
    is_branch: bool = False
    depends_on: list[str] = field(default_factory=list)
    execution_mode: str = "legacy"
    input_port_count: int = 0
    output_port_count: int = 0
    upstream_node_ids: list[str] = field(default_factory=list)


@dataclass
class FlowEdgeVM:
    """View-model for a connector between two step cards."""

    from_id: str
    to_id: str
    edge_type: str = "sequential"  # "sequential" | "dependency" | "branch"


# ---------------------------------------------------------------------------
# Inspector view-model
# ---------------------------------------------------------------------------


@dataclass
class StepInspectorVM:
    """View-model for the right inspector panel when a step is selected."""

    step_id: str
    name: str  # prompt template key (readonly)
    title: str  # editable display title
    purpose: str  # editable description
    model: str
    prompt_version: str
    # No-code prompt fields
    role_text: str = ""  # system message
    task_text: str = ""  # user message
    # Legacy / advanced
    prompt_text: str = ""
    input_mapping: str = "input"
    output_mapping: str = "output"
    execution_mode: str = "legacy"
    inputs: list[Any] = field(default_factory=list)
    outputs: list[Any] = field(default_factory=list)
    enabled: bool = True
    depends_on: list[str] = field(default_factory=list)
    attachments: list[AttachmentSlot] = field(default_factory=list)
    # Advanced fields
    lane: int = 0
    branch_group: str = ""


# ---------------------------------------------------------------------------
# Builder functions
# ---------------------------------------------------------------------------


def build_flow_viewmodel(
    workflow: WorkflowDef,
    selected_step_id: Optional[str] = None,
    step_results: Optional[dict[str, Any]] = None,
    attachment_bindings: Optional[dict[str, str]] = None,
) -> tuple[list[FlowNodeVM], list[FlowEdgeVM]]:
    """Build rendering-ready view-models from a WorkflowDef.

    Returns (nodes, edges) for the flow canvas.

    Parameters
    ----------
    workflow : WorkflowDef
        The workflow definition.
    selected_step_id : str, optional
        Currently selected step ID for highlighting.
    step_results : dict, optional
        Step execution results for status/output preview.
    attachment_bindings : dict, optional
        Runtime file bindings: key="step_id::filename", value=file_path
    """
    graph = build_graph(workflow)
    layout = compute_layout(graph)
    results = step_results or {}
    bindings = attachment_bindings or {}

    # Build a mapping: step_id → display title for flow arrow labels
    id_to_title = {s.id: _display_title(s) for s in workflow.steps}

    nodes: list[FlowNodeVM] = []
    for i, step in enumerate(workflow.steps):
        ln = layout.nodes.get(step.id)
        gn = graph.nodes.get(step.id)
        sr = results.get(step.id)
        status = (
            StepStatus(sr.status)
            if sr and hasattr(sr, "status")
            else StepStatus.PENDING
        )
        output_preview = ""
        if sr and hasattr(sr, "output_text") and sr.output_text:
            output_preview = sr.output_text[:120]

        # Compute natural-language flow arrow labels from graph source-of-truth
        deps = list(gn.predecessors) if gn else list(step.depends_on)
        if deps:
            upstream_title = " & ".join(id_to_title.get(d, d) for d in deps)
        elif i == 0:
            upstream_title = "Starts here"
        else:
            upstream_title = id_to_title.get(workflow.steps[i - 1].id, "")

        # Who depends on this step? (source-of-truth from computed graph)
        successor_ids = list(gn.successors) if gn else []
        successors = [graph.nodes[sid] for sid in successor_ids if sid in graph.nodes]
        if successors:
            downstream_title = " & ".join(id_to_title.get(s.step_id, s.step_id) for s in successors)
        elif i == len(workflow.steps) - 1:
            downstream_title = "Ends here"
        else:
            downstream_title = id_to_title.get(workflow.steps[i + 1].id, "")

        # Count attached files based on runtime bindings matching designated slots
        step_file_count = sum(
            1 for slot in step.attachments if bindings.get(f"{step.id}::{slot.slot_id}")
        )

        missing_required = any(
            slot.required and not bindings.get(f"{step.id}::{slot.slot_id}")
            for slot in step.attachments
        )

        duration = (
            sr.metrics.latency_ms if sr and getattr(sr, "metrics", None) else None
        )

        node = FlowNodeVM(
            step_id=step.id,
            title=_display_title(step),
            purpose=getattr(step, "purpose", ""),
            model=step.model,
            status=status,
            upstream_title=upstream_title,
            downstream_title=downstream_title,
            has_files=step_file_count > 0,
            file_count=step_file_count,
            missing_required=missing_required,
            duration_ms=duration,
            is_selected=(step.id == selected_step_id),
            is_enabled=step.enabled,
            output_preview=output_preview,
            depth=ln.depth if ln else 0,
            lane=ln.lane if ln else 0,
            is_merge=ln.is_merge if ln else False,
            is_branch=len(successors) > 1,
            depends_on=deps,
            execution_mode=getattr(step, "execution_mode", "legacy"),
            input_port_count=len(getattr(step, "inputs", [])),
            output_port_count=len(getattr(step, "outputs", [])),
            upstream_node_ids=deps,
        )
        nodes.append(node)

    edges: list[FlowEdgeVM] = []
    for ge in graph.edges:
        edges.append(
            FlowEdgeVM(
                from_id=ge.from_id,
                to_id=ge.to_id,
                edge_type=ge.edge_type,
            )
        )

    return nodes, edges


def build_inspector_viewmodel(
    step: StepDef,
    prompt_text: str = "",
) -> StepInspectorVM:
    """Build inspector view-model from a StepDef."""
    return StepInspectorVM(
        step_id=step.id,
        name=step.name,
        title=_inspector_title(step),
        purpose=getattr(step, "purpose", ""),
        model=step.model,
        prompt_version=step.prompt_version,
        role_text=getattr(step, "role_text", ""),
        task_text=getattr(step, "task_text", ""),
        prompt_text=prompt_text,
        input_mapping=step.input_mapping,
        output_mapping=step.output_mapping,
        execution_mode=getattr(step, "execution_mode", "legacy"),
        inputs=list(step.inputs) if hasattr(step, "inputs") else [],
        outputs=list(step.outputs) if hasattr(step, "outputs") else [],
        enabled=step.enabled,
        depends_on=list(step.depends_on),
        attachments=list(step.attachments),
        lane=step.ui.get("lane", 0) if isinstance(step.ui, dict) else 0,
        branch_group=step.ui.get("branch_group", "")
        if isinstance(step.ui, dict)
        else "",
    )
