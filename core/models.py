"""
core.models — Data contracts for the Workflow MVP.

All shared data structures used across provider, workflow, storage,
ingestion, evaluation, and UI layers.  Implemented as dataclasses
for clarity, serialization convenience, and IDE support.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Config / Definition contracts
# ---------------------------------------------------------------------------


@dataclass
class AttachmentSlot:
    """Definition of an attachment expected by a workflow step."""

    slot_id: str
    variable_name: str
    label: str = ""
    required: bool = False
    # Optional list of accepted file extensions, e.g. [".pdf", ".docx"].
    # None means no filter (any file type accepted).
    accepted_types: Optional[list[str]] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AttachmentSlot":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SourceRef:
    """Reference to an output port of an upstream step."""

    step_id: str
    port: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SourceRef":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class InputPortDef:
    """Definition of an input port for a graph node."""

    name: str
    required: bool = True
    join_strategy: str = "concat"  # "first", "concat", "json_map"
    sources: list[SourceRef] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["sources"] = [s.to_dict() for s in self.sources]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "InputPortDef":
        s_copy = dict(data)
        if "sources" in s_copy:
            s_copy["sources"] = [SourceRef.from_dict(s) for s in s_copy["sources"]]
        # Normalize legacy join_strategy aliases
        js = s_copy.get("join_strategy", "")
        if js == "dict":
            s_copy["join_strategy"] = "json_map"
        return cls(**{k: v for k, v in s_copy.items() if k in cls.__dataclass_fields__})


@dataclass
class OutputPortDef:
    """Definition of an output port for a graph node."""

    name: str
    kind: str = "text"  # "text", "json"
    exposed: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OutputPortDef":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def ensure_graph_io(step: "StepDef") -> None:
    """Backfill default input/output ports for a graph-mode step if empty."""
    if step.execution_mode != "graph":
        return
    if not step.inputs:
        step.inputs = [InputPortDef(name="input")]
    if not step.outputs:
        step.outputs = [OutputPortDef(name="output")]


@dataclass
class StepDef:
    """Definition of a single workflow step (from config).

    Fields:
        name  — prompt template key (do NOT change meaning)
        title — user-facing display name
        purpose — short description of what this step does
        ui    — lightweight UI metadata (lane, collapsed, branch_group, color_tag)
    """

    id: str
    name: str
    model: str
    prompt_version: str
    input_mapping: str = "input"
    output_mapping: str = "output"
    depends_on: list[str] = field(default_factory=list)
    enabled: bool = True
    attachments: list[AttachmentSlot] = field(default_factory=list)
    # New fields (Phase 0 — workspace refactor)
    title: str = ""
    purpose: str = ""
    ui: dict[str, Any] = field(default_factory=dict)
    # No-code prompt fields (Phase 2 — no-code UX)
    role_text: str = ""
    task_text: str = ""
    # Schema v3 (Epic E2) graph configuration
    # Default to legacy (sequential) semantics for backward compatibility.
    # Graph-mode edges are only created when execution_mode is explicitly "graph"
    # or when deserializing a step that contains graph payload (inputs/outputs).
    execution_mode: str = "legacy"
    inputs: list[InputPortDef] = field(default_factory=list)
    outputs: list[OutputPortDef] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Auto-mapping helpers (no-code: generate variable names from titles)
    # ------------------------------------------------------------------

    def get_auto_output_mapping(self) -> str:
        """Generate an output variable name from the step title.

        'Customer Summary' → 'customer_summary'
        Falls back to step.id if title is empty.
        """
        import re

        base = (self.title or self.id).strip()
        slug = re.sub(r"[^\w\s]", "", base.lower())  # strip punctuation
        slug = re.sub(r"\s+", "_", slug).strip("_")
        return slug or "output"

    def get_auto_input_mapping(self, previous_step: Optional["StepDef"]) -> str:
        """Generate an input variable name from the previous step's auto-output.

        First step in workflow defaults to 'input'.
        """
        if previous_step:
            return previous_step.get_auto_output_mapping()
        return "input"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["attachments"] = [a.to_dict() for a in self.attachments]
        d["inputs"] = [i.to_dict() for i in self.inputs]
        d["outputs"] = [o.to_dict() for o in self.outputs]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "StepDef":
        s_copy = dict(data)
        if "attachments" in s_copy:
            s_copy["attachments"] = [
                AttachmentSlot.from_dict(a) for a in s_copy["attachments"]
            ]
        # Normalize depends_on from legacy formats
        deps = s_copy.get("depends_on")
        if deps is None:
            s_copy["depends_on"] = []
        elif isinstance(deps, str):
            s_copy["depends_on"] = [deps] if deps else []
        # Safe defaults for new fields
        s_copy.setdefault("title", "")
        s_copy.setdefault("purpose", "")
        s_copy.setdefault("ui", {})
        s_copy.setdefault("role_text", "")
        s_copy.setdefault("task_text", "")
        s_copy.setdefault("input_mapping", "")
        s_copy.setdefault("output_mapping", "")
        if "execution_mode" not in s_copy:
            has_graph_payload = bool(s_copy.get("inputs")) or bool(s_copy.get("outputs"))
            if has_graph_payload:
                s_copy["execution_mode"] = "graph"
            else:
                # Backward compatibility: mapping-only and "empty" historical steps stay legacy.
                s_copy["execution_mode"] = "legacy"

        if "inputs" in s_copy:
            s_copy["inputs"] = [InputPortDef.from_dict(i) for i in s_copy["inputs"]]
        else:
            s_copy["inputs"] = []

        if "outputs" in s_copy:
            s_copy["outputs"] = [OutputPortDef.from_dict(o) for o in s_copy["outputs"]]
        else:
            s_copy["outputs"] = []

        return cls(**{k: v for k, v in s_copy.items() if k in cls.__dataclass_fields__})


@dataclass
class Attachment:
    """Represents a file mapped to a template variable for workflow execution."""

    variable_name: str
    file_path: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Attachment":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class WorkflowDef:
    """Definition of a complete workflow (from config)."""

    id: str
    name: str
    description: str = ""
    steps: list[StepDef] = field(default_factory=list)
    schema_version: int = 3  # Phase 0 — schema versioning

    # --- serialization helpers ---
    def to_dict(self) -> dict:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        d["schema_version"] = self.schema_version
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowDef":
        steps = [StepDef.from_dict(s) for s in data.get("steps", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            steps=steps,
            schema_version=int(data.get("schema_version", 3)),
        )


# ---------------------------------------------------------------------------
# Provider contracts
# ---------------------------------------------------------------------------


@dataclass
class ProviderRequest:
    """Request payload for the Workbench API client."""

    model: str
    messages: list[dict[str, str]]
    timeout: int = 300


@dataclass
class ProviderResponse:
    """Response from the Workbench API client."""

    content: str = ""
    raw_json: dict = field(default_factory=dict)
    usage: Optional[dict] = None  # {prompt_tokens, completion_tokens, total_tokens}
    status_code: int = 0
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 300


# ---------------------------------------------------------------------------
# Runtime contracts
# ---------------------------------------------------------------------------


@dataclass
class StepMetrics:
    """Captured metrics for a single step execution."""

    latency_ms: float = 0.0
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    model: str = ""
    prompt_version: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "StepMetrics":
        if not isinstance(data, dict):
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StepResult:
    """Complete result of executing one workflow step."""

    step_id: str = ""
    step_name: str = ""
    input_text: str = ""
    rendered_prompt: list[dict[str, str]] = field(default_factory=list)
    output_text: str = ""
    raw_response: dict = field(default_factory=dict)
    metrics: StepMetrics = field(default_factory=StepMetrics)
    status: str = "pending"  # pending | running | success | error
    error: Optional[str] = None
    input_ports: dict[str, Any] = field(default_factory=dict)
    output_ports: dict[str, Any] = field(default_factory=dict)
    node_events: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "StepResult":
        metrics_data = data.get("metrics", {})
        metrics = StepMetrics.from_dict(metrics_data) if metrics_data else StepMetrics()
        return cls(
            metrics=metrics,
            **{
                k: v
                for k, v in data.items()
                if k in cls.__dataclass_fields__ and k != "metrics"
            },
        )


def _generate_run_id() -> str:
    """Generate a human-readable + unique run ID: YYYYMMDD_HHMMSS_<uuid4_short>."""
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"{ts}_{short_uuid}"


@dataclass
class RunContext:
    """Runtime state for a workflow execution."""

    run_id: str = field(default_factory=_generate_run_id)
    workflow_id: str = ""
    workflow_name: str = ""
    workflow_snapshot: Optional[dict] = None  # WorkflowDef.to_dict() at execution time
    started_at: str = ""
    finished_at: str = ""
    status: str = "pending"  # pending | running | success | error
    variables: dict[str, Any] = field(default_factory=dict)
    step_results: list[str] = field(default_factory=list)  # list of step_ids (files)
    run_type: str = "standard"  # standard | comparison
    engine_type: str = "legacy"  # legacy | graph
    schema_version: int = 3
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RunContext":
        copy_data = dict(data)
        copy_data.setdefault("engine_type", "legacy")
        copy_data.setdefault("schema_version", 3)
        return cls(
            **{k: v for k, v in copy_data.items() if k in cls.__dataclass_fields__}
        )


# ---------------------------------------------------------------------------
# Ingestion contracts
# ---------------------------------------------------------------------------


@dataclass
class IngestResult:
    """Result of ingesting a local file."""

    content: str = ""
    metadata: dict = field(default_factory=dict)  # filename, type, size, etc.
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


# ---------------------------------------------------------------------------
# Run history (lightweight summary for index listing)
# ---------------------------------------------------------------------------


@dataclass
class RunSummary:
    """Lightweight run record for index.csv listing."""

    run_id: str = ""
    workflow_id: str = ""
    workflow_name: str = ""
    started_at: str = ""
    finished_at: str = ""
    status: str = ""
    step_count: int = 0
    run_type: str = "standard"
