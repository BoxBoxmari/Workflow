"""
core.commands — Undo/redo command pattern for workflow editing.

Each editing action is a Command with execute() and undo() methods.
The CommandStack manages history and provides undo/redo operations.

Note: ``execute()`` is the primary public interface.
``do()`` is kept as an alias for backward compatibility.
"""

from __future__ import annotations

import copy
import uuid as _uuid
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

from core.models import StepDef, WorkflowDef, InputPortDef, OutputPortDef, SourceRef


# ---------------------------------------------------------------------------
# Command protocol
# ---------------------------------------------------------------------------


class Command(Protocol):
    """Protocol that all editing commands must satisfy."""

    label: str

    def execute(self) -> None: ...
    def undo(self) -> None: ...


# ---------------------------------------------------------------------------
# Concrete commands
# ---------------------------------------------------------------------------


@dataclass
class AddStepCommand:
    """Add a step to a workflow at a given index."""

    label: str
    workflow: WorkflowDef
    step: StepDef
    index: int = -1  # -1 = append

    def execute(self) -> None:
        if self.index < 0 or self.index >= len(self.workflow.steps):
            self.workflow.steps.append(self.step)
            self.index = len(self.workflow.steps) - 1
        else:
            self.workflow.steps.insert(self.index, self.step)

    # Alias for backward compat
    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        try:
            self.workflow.steps.remove(self.step)
        except ValueError:
            pass


@dataclass
class DeleteStepCommand:
    """Remove a step from a workflow, remembering its position for undo."""

    label: str
    workflow: WorkflowDef
    step_id: str
    _removed_step: Optional[StepDef] = field(default=None, repr=False)
    _removed_index: int = field(default=-1, repr=False)

    def execute(self) -> None:
        for i, s in enumerate(self.workflow.steps):
            if s.id == self.step_id:
                self._removed_step = s
                self._removed_index = i
                self.workflow.steps.pop(i)
                return

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        if self._removed_step is not None:
            idx = min(self._removed_index, len(self.workflow.steps))
            self.workflow.steps.insert(idx, self._removed_step)


@dataclass
class UpdateStepFieldCommand:
    """Change a single field on a StepDef, storing the old value for undo."""

    label: str
    step: StepDef
    field_name: str
    new_value: Any
    _old_value: Any = field(default=None, init=False, repr=False)

    def execute(self) -> None:
        self._old_value = getattr(self.step, self.field_name)
        setattr(self.step, self.field_name, self.new_value)

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        setattr(self.step, self.field_name, self._old_value)


@dataclass
class DuplicateStepCommand:
    """Duplicate a step and insert the copy immediately after the original."""

    label: str
    workflow: WorkflowDef
    source_step_id: str
    _new_step: Optional[StepDef] = field(default=None, repr=False)
    _insert_index: int = field(default=-1, repr=False)

    def execute(self) -> None:
        for i, s in enumerate(self.workflow.steps):
            if s.id == self.source_step_id:
                new = copy.deepcopy(s)
                new.id = _uuid.uuid4().hex[:8]
                new.title = f"{s.title or s.name} (copy)"
                self._new_step = new
                self._insert_index = i + 1
                self.workflow.steps.insert(self._insert_index, new)
                return

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        if self._new_step and self._new_step in self.workflow.steps:
            self.workflow.steps.remove(self._new_step)

    @property
    def new_step(self) -> Optional[StepDef]:
        return self._new_step


# ---------------------------------------------------------------------------
# Branching commands (Gap 7)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Port commands (Epic E2)
# ---------------------------------------------------------------------------


@dataclass
class AddInputPortCommand:
    """Add an input port constraint to a graph step."""

    label: str
    step: StepDef
    port: InputPortDef
    index: int = -1

    def execute(self) -> None:
        if self.index < 0 or self.index >= len(self.step.inputs):
            self.step.inputs.append(self.port)
            self.index = len(self.step.inputs) - 1
        else:
            self.step.inputs.insert(self.index, self.port)

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        try:
            self.step.inputs.remove(self.port)
        except ValueError:
            pass


@dataclass
class RemoveInputPortCommand:
    """Remove an input port constraint from a graph step."""

    label: str
    step: StepDef
    port_name: str
    _removed_port: Optional[InputPortDef] = field(default=None, repr=False)
    _removed_index: int = field(default=-1, repr=False)

    def execute(self) -> None:
        for i, p in enumerate(self.step.inputs):
            if p.name == self.port_name:
                self._removed_port = p
                self._removed_index = i
                self.step.inputs.pop(i)
                return

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        if self._removed_port is not None:
            idx = min(self._removed_index, len(self.step.inputs))
            self.step.inputs.insert(idx, self._removed_port)


@dataclass
class AddOutputPortCommand:
    """Add an output port definition to a graph step."""

    label: str
    step: StepDef
    port: OutputPortDef
    index: int = -1

    def execute(self) -> None:
        if self.index < 0 or self.index >= len(self.step.outputs):
            self.step.outputs.append(self.port)
            self.index = len(self.step.outputs) - 1
        else:
            self.step.outputs.insert(self.index, self.port)

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        try:
            self.step.outputs.remove(self.port)
        except ValueError:
            pass


@dataclass
class RemoveOutputPortCommand:
    """Remove an output port definition from a graph step."""

    label: str
    step: StepDef
    port_name: str
    _removed_port: Optional[OutputPortDef] = field(default=None, repr=False)
    _removed_index: int = field(default=-1, repr=False)

    def execute(self) -> None:
        for i, p in enumerate(self.step.outputs):
            if p.name == self.port_name:
                self._removed_port = p
                self._removed_index = i
                self.step.outputs.pop(i)
                return

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        if self._removed_port is not None:
            idx = min(self._removed_index, len(self.step.outputs))
            self.step.outputs.insert(idx, self._removed_port)


@dataclass
class UpdatePortConfigCommand:
    """Update a specific field of an input or output port."""

    label: str
    step: StepDef
    port_type: str  # "input" or "output"
    port_name: str
    field_name: str
    new_value: Any
    _old_value: Any = field(default=None, init=False, repr=False)

    def execute(self) -> None:
        ports = (
            self.step.inputs if self.port_type == "input" else self.step.outputs
        )
        for p in ports:
            if p.name == self.port_name:
                self._old_value = getattr(p, self.field_name)
                setattr(p, self.field_name, self.new_value)
                return

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        ports = (
            self.step.inputs if self.port_type == "input" else self.step.outputs
        )
        for p in ports:
            if p.name == self.port_name:
                setattr(p, self.field_name, self._old_value)
                return


@dataclass
class AddInputSourceCommand:
    """Add a source reference to an input port."""

    label: str
    step: StepDef
    port_name: str
    source: SourceRef
    _created_port: bool = field(default=False, init=False, repr=False)

    def execute(self) -> None:
        port = next((p for p in self.step.inputs if p.name == self.port_name), None)
        if port is None:
            port = InputPortDef(name=self.port_name)
            self.step.inputs.append(port)
            self._created_port = True
        if not any(
            s.step_id == self.source.step_id and s.port == self.source.port
            for s in port.sources
        ):
            port.sources.append(self.source)

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        port = next((p for p in self.step.inputs if p.name == self.port_name), None)
        if port is None:
            return
        port.sources = [
            s
            for s in port.sources
            if not (s.step_id == self.source.step_id and s.port == self.source.port)
        ]
        if self._created_port and not port.sources:
            try:
                self.step.inputs.remove(port)
            except ValueError:
                pass


@dataclass
class RemoveInputSourceCommand:
    """Remove a source reference from an input port by index."""

    label: str
    step: StepDef
    port_name: str
    source_index: int
    _removed_source: SourceRef | None = field(default=None, init=False, repr=False)

    def execute(self) -> None:
        port = next((p for p in self.step.inputs if p.name == self.port_name), None)
        if port is None:
            return
        if 0 <= self.source_index < len(port.sources):
            self._removed_source = port.sources.pop(self.source_index)

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        if self._removed_source is None:
            return
        port = next((p for p in self.step.inputs if p.name == self.port_name), None)
        if port is None:
            port = InputPortDef(name=self.port_name)
            self.step.inputs.append(port)
        idx = min(self.source_index, len(port.sources))
        port.sources.insert(idx, self._removed_source)


@dataclass
class AddBranchCommand:
    """Add a branch step in a new lane, depending on source_step_id."""

    label: str
    workflow: WorkflowDef
    source_step_id: str
    lane: int = 1
    _new_step: Optional[StepDef] = field(default=None, repr=False)
    _insert_index: int = field(default=-1, repr=False)

    def execute(self) -> None:
        source = next(
            (s for s in self.workflow.steps if s.id == self.source_step_id), None
        )
        if not source:
            return
        new_id = _uuid.uuid4().hex[:8]
        new_step = StepDef(
            id=new_id,
            name=f"branch_{new_id[:4]}",
            model=source.model,
            prompt_version=source.prompt_version,
            depends_on=[self.source_step_id],
            title="Branch Step",
            ui={"lane": self.lane},
        )
        self._new_step = new_step
        # Insert right after source
        idx = next(
            (
                i
                for i, s in enumerate(self.workflow.steps)
                if s.id == self.source_step_id
            ),
            len(self.workflow.steps) - 1,
        )
        self._insert_index = idx + 1
        self.workflow.steps.insert(self._insert_index, new_step)

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        if self._new_step and self._new_step in self.workflow.steps:
            self.workflow.steps.remove(self._new_step)

    @property
    def new_step(self) -> Optional[StepDef]:
        return self._new_step


@dataclass
class MoveStepOrderCommand:
    """Move a step up or down in the workflow list (vertical reorder).

    direction: 'up'  = swap with the previous step
               'down' = swap with the next step
    """

    label: str
    workflow: WorkflowDef
    step_id: str
    direction: str  # "up" | "down"
    _swapped_with_id: Optional[str] = field(default=None, repr=False)

    def execute(self) -> None:
        steps = self.workflow.steps
        idx = next(
            (i for i, s in enumerate(steps) if s.id == self.step_id),
            None,
        )
        if idx is None:
            return
        if self.direction == "up" and idx > 0:
            steps[idx], steps[idx - 1] = steps[idx - 1], steps[idx]
            self._swapped_with_id = steps[idx].id  # was idx-1 before swap
        elif self.direction == "down" and idx < len(steps) - 1:
            steps[idx], steps[idx + 1] = steps[idx + 1], steps[idx]
            self._swapped_with_id = steps[idx].id  # was idx+1 before swap

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        # Undo is simply the opposite move
        steps = self.workflow.steps
        idx = next(
            (i for i, s in enumerate(steps) if s.id == self.step_id),
            None,
        )
        if idx is None:
            return
        if self.direction == "up" and idx < len(steps) - 1:
            steps[idx], steps[idx + 1] = steps[idx + 1], steps[idx]
        elif self.direction == "down" and idx > 0:
            steps[idx], steps[idx - 1] = steps[idx - 1], steps[idx]


# Deprecated: use MoveStepOrderCommand.  Kept for backward compatibility.


@dataclass
class MergeBranchCommand:
    """Create a merge step that depends on a list of branch step IDs."""

    label: str
    workflow: WorkflowDef
    branch_step_ids: list[str]
    after_step_id: str  # insert after this step
    _new_step: Optional[StepDef] = field(default=None, repr=False)
    _insert_index: int = field(default=-1, repr=False)

    def execute(self) -> None:
        new_id = _uuid.uuid4().hex[:8]
        # Use model from the last branch step
        model = "gpt-4o-2024-08-06-gs-ae"
        prompt_version = "1"
        for s in self.workflow.steps:
            if s.id in self.branch_step_ids:
                model = s.model
                # Wave 0 contract lock: keep StepDef prompt version
                # aligned with branch source.
                prompt_version = s.prompt_version or "1"
                break
        new_step = StepDef(
            id=new_id,
            name=f"merge_{new_id[:4]}",
            model=model,
            prompt_version=prompt_version,
            depends_on=list(self.branch_step_ids),
            title="Merge Step",
            ui={"lane": 0},
        )
        self._new_step = new_step
        idx = next(
            (
                i
                for i, s in enumerate(self.workflow.steps)
                if s.id == self.after_step_id
            ),
            len(self.workflow.steps) - 1,
        )
        self._insert_index = idx + 1
        self.workflow.steps.insert(self._insert_index, new_step)

    def do(self) -> None:
        self.execute()

    def undo(self) -> None:
        if self._new_step and self._new_step in self.workflow.steps:
            self.workflow.steps.remove(self._new_step)

    @property
    def new_step(self) -> Optional[StepDef]:
        return self._new_step


# ---------------------------------------------------------------------------
# Command stack
# ---------------------------------------------------------------------------


class CommandStack:
    """Manages undo/redo history for commands."""

    def __init__(self, max_size: int = 50) -> None:
        self._undo: list = []
        self._redo: list = []
        self._max_size = max_size

    def execute(self, cmd) -> None:
        """Execute a command and push it onto the undo stack."""
        cmd.execute()
        self._undo.append(cmd)
        if len(self._undo) > self._max_size:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self):
        """Undo the most recent command."""
        if not self._undo:
            return None
        cmd = self._undo.pop()
        cmd.undo()
        self._redo.append(cmd)
        return cmd

    def redo(self):
        """Redo the most recently undone command."""
        if not self._redo:
            return None
        cmd = self._redo.pop()
        cmd.execute()
        self._undo.append(cmd)
        return cmd

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_label(self) -> str:
        return self._undo[-1].label if self._undo else ""

    @property
    def redo_label(self) -> str:
        return self._redo[-1].label if self._redo else ""

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
