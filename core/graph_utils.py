"""
core.graph_utils - Helpers for graph extraction and dependency resolution.
"""

from typing import Dict, List, Set
from core.models import StepDef

ROOT_SOURCE_IDS: Set[str] = {"__input__", "workflow_input", "$input"}


def build_predecessor_map(steps: List[StepDef]) -> Dict[str, List[str]]:
    """Build a mapping of {step_id: [dependent_step_ids]}.

    If execution_mode == "graph":
        Analyzes `inputs[*].sources[*].step_id`.
    If execution_mode == "legacy":
        Uses `depends_on`.
    """
    predecessors: Dict[str, List[str]] = {}

    for step in steps:
        if not step.id:
            continue

        preds = set()
        if step.execution_mode == "graph":
            for input_def in step.inputs:
                for src in input_def.sources:
                    if src.step_id and src.step_id not in ROOT_SOURCE_IDS:
                        preds.add(src.step_id)
        else:
            for dep in step.depends_on:
                if dep:
                    preds.add(dep)

        predecessors[step.id] = list(preds)

    return predecessors


def extract_port_bindings(step: StepDef) -> List[dict[str, str]]:
    """Flatten a step's inputs for validation lookups.

    Returns a list of dicts:
    [
        {
            "input_port": "port_name",
            "source_step": "step_id",
            "source_port": "out_port",
        }
    ]
    """
    bindings: List[dict[str, str]] = []
    if step.execution_mode != "graph":
        return bindings

    for input_def in step.inputs:
        for src in input_def.sources:
            bindings.append(
                {
                    "input_port": input_def.name,
                    "source_step": src.step_id,
                    "source_port": src.port,
                }
            )

    return bindings
