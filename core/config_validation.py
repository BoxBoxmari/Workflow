"""
core.config_validation — Validation rules for Workflow MVP configurations.

Verifies workflow dependencies, step definitions, and prompt templates
before persistence to ensure runtime safety.
"""

import re
from dataclasses import dataclass

from core.models import WorkflowDef, StepDef
from core.graph_utils import ROOT_SOURCE_IDS, build_predecessor_map


def _graph_step_uses_nocode_prompts(step: StepDef) -> bool:
    """True when graph step is driven by role/task text instead of template prompts."""
    role = (step.role_text or "").strip()
    task = (step.task_text or "").strip()
    return bool(role or task)


@dataclass
class ValidationIssue:
    level: str  # "error", "warning"
    scope: str  # "workflow", "step", "prompt"
    message: str


def validate_workflow(
    workflow: WorkflowDef,
    all_workflows: list[WorkflowDef],
    available_prompts: dict[str, list[str]],
    available_models: list[str] | None = None,
    workflow_id_counts: dict[str, int] | None = None,
) -> list[ValidationIssue]:
    """Validate a single workflow definition against global state."""
    issues: list[ValidationIssue] = []

    # Check duplicate workflow ID
    if workflow_id_counts is not None:
        # Precomputed duplicate detection reduces per-call cost from O(W) scan
        # to O(1) lookup; if this workflow id appears >1 time in the draft set,
        # it implies duplicates exist.
        if workflow_id_counts.get(workflow.id, 0) > 1:
            issues.append(
                ValidationIssue(
                    "error",
                    "workflow",
                    f"Duplicate workflow ID '{workflow.id}' found.",
                )
            )
    else:
        for other in all_workflows:
            if other.id == workflow.id and other is not workflow:
                issues.append(
                    ValidationIssue(
                        "error",
                        "workflow",
                        f"Duplicate workflow ID '{workflow.id}' found.",
                    )
                )

    if not workflow.steps:
        issues.append(
            ValidationIssue(
                "error", "workflow", "Workflow must contain at least one step."
            )
        )
        return issues

    seen_step_ids = set()
    available_inputs = {"input"}  # Initial input always available

    for i, step in enumerate(workflow.steps):
        prefix = f"Step {i + 1} ('{step.name}')"

        if not step.id:
            issues.append(
                ValidationIssue("error", "step", f"{prefix}: Missing step ID.")
            )
        elif step.id in seen_step_ids:
            issues.append(
                ValidationIssue(
                    "error", "step", f"{prefix}: Duplicate step ID '{step.id}'."
                )
            )
        else:
            seen_step_ids.add(step.id)

        if step.execution_mode == "graph":
            issues.extend(_validate_graph_step(step, workflow, prefix))
        else:
            # Mapping checks
            if step.input_mapping not in available_inputs:
                issues.append(
                    ValidationIssue(
                        "error",
                        "step",
                        (
                            f"{prefix}: input_mapping '{step.input_mapping}' "
                            "is not produced by any prior step."
                        ),
                    )
                )

            if step.output_mapping:
                available_inputs.add(step.output_mapping)

        # Validate model field is not empty (prevents runtime crash on API call)
        if not step.model or not step.model.strip():
            issues.append(
                ValidationIssue(
                    "error",
                    "step",
                    f"{prefix}: Model field is empty. A valid model ID is required.",
                )
            )
        elif available_models is not None and step.model not in available_models:
            issues.append(
                ValidationIssue(
                    "error",
                    "step",
                    f"{prefix}: Model '{step.model}' is not in the valid models catalog.",
                )
            )

        skip_prompt_checks = (
            step.execution_mode == "graph" and _graph_step_uses_nocode_prompts(step)
        )

        if not skip_prompt_checks:
            # Validate prompt_version field is not empty (prevents template lookup failure)
            if not step.prompt_version or not step.prompt_version.strip():
                issues.append(
                    ValidationIssue(
                        "error",
                        "step",
                        (
                            f"{prefix}: Prompt version is empty. "
                            "A numeric version string is required."
                        ),
                    )
                )

            # Prompt references
            versions = available_prompts.get(step.name, [])
            if not versions:
                issues.append(
                    ValidationIssue(
                        "error",
                        "step",
                        f"{prefix}: No prompts exist for step name '{step.name}'.",
                    )
                )
            elif step.prompt_version not in versions:
                issues.append(
                    ValidationIssue(
                        "error",
                        "step",
                        f"{prefix}: Prompt version 'v{step.prompt_version}' does not exist.",
                    )
                )

    # Phase 5: check depends_on references and cycles
    issues.extend(_check_depends_on_references(workflow))
    issues.extend(_check_dependency_cycles(workflow))

    return issues


def _validate_graph_step(
    step: StepDef, workflow: WorkflowDef, prefix: str
) -> list[ValidationIssue]:
    issues = []

    # 1. Unique port names & Validation
    input_names = set()
    for ip in step.inputs:
        if ip.name in input_names:
            issues.append(
                ValidationIssue(
                    "error", "step", f"{prefix}: Duplicate input port name '{ip.name}'."
                )
            )
        input_names.add(ip.name)

        # Validate join strategy
        if ip.join_strategy not in ["first", "concat", "json_map"]:
            issues.append(
                ValidationIssue(
                    "error",
                    "step",
                    (
                        f"{prefix}: Invalid join_strategy "
                        f"'{ip.join_strategy}' on input port '{ip.name}'."
                    ),
                )
            )

        # Required Satisfiable
        if ip.required and not ip.sources:
            issues.append(
                ValidationIssue(
                    "error",
                    "step",
                    (
                        f"{prefix}: Input port '{ip.name}' is required "
                        "but has no sources defined."
                    ),
                )
            )

        # Sources validation
        for src in ip.sources:
            if src.step_id == step.id:
                issues.append(
                    ValidationIssue(
                        "error",
                        "step",
                        (
                            f"{prefix}: Source for input port '{ip.name}' "
                            f"cannot self-reference step '{step.id}'."
                        ),
                    )
                )
            elif src.step_id in ROOT_SOURCE_IDS:
                continue
            else:
                source_step = next(
                    (s for s in workflow.steps if s.id == src.step_id), None
                )
                if not source_step:
                    issues.append(
                        ValidationIssue(
                            "error",
                            "step",
                            (
                                f"{prefix}: Source step '{src.step_id}' "
                                f"for input port '{ip.name}' does not exist."
                            ),
                        )
                    )
                else:
                    if source_step.execution_mode == "graph":
                        # Must target an existing output port
                        if not any(op.name == src.port for op in source_step.outputs):
                            issues.append(
                                ValidationIssue(
                                    "error",
                                    "step",
                                    (
                                        f"{prefix}: Source port '{src.port}' "
                                        f"does not exist on step '{src.step_id}'."
                                    ),
                                )
                            )

    output_names = set()
    for op in step.outputs:
        if op.name in output_names:
            issues.append(
                ValidationIssue(
                    "error",
                    "step",
                    f"{prefix}: Duplicate output port name '{op.name}'.",
                )
            )
        output_names.add(op.name)

    return issues


def _check_depends_on_references(
    workflow: "WorkflowDef",
) -> list[ValidationIssue]:
    """Detect depends_on entries that reference non-existent step IDs."""
    issues: list[ValidationIssue] = []
    all_step_ids = {s.id for s in workflow.steps}
    for step in workflow.steps:
        if step.execution_mode == "graph":
            continue
        for dep_id in step.depends_on:
            if dep_id not in all_step_ids:
                issues.append(
                    ValidationIssue(
                        "error",
                        "step",
                        (
                            f"Step '{step.name}' depends_on '{dep_id}' "
                            "which does not exist in this workflow."
                        ),
                    )
                )
    return issues


def _check_dependency_cycles(
    workflow: "WorkflowDef",
) -> list[ValidationIssue]:
    """Detect circular dependencies using predecessor map from graph_utils.

    Reports the first cycle found with the full offending path.
    Stops after the first cycle to avoid duplicate/confusing messages.
    """
    issues: list[ValidationIssue] = []
    graph = build_predecessor_map(workflow.steps)

    visited: set[str] = set()
    in_stack: set[str] = set()

    for start_node in graph:
        if start_node in visited:
            continue

        # Iterative DFS with an explicit path stack and a frame marker
        dfs_stack: list[tuple[str, list[str]] | str] = [(start_node, [start_node])]

        while dfs_stack:
            item = dfs_stack.pop()

            # If the item is just a string, it is a backtrack marker
            if isinstance(item, str):
                in_stack.discard(item)
                continue

            node, path = item

            if node in in_stack:
                # Found a cycle — report it
                cycle_start_idx = path.index(node)
                cycle = path[cycle_start_idx:]
                cycle_str = " → ".join(cycle)
                issues.append(
                    ValidationIssue(
                        "error",
                        "workflow",
                        f"Circular dependency detected: {cycle_str}",
                    )
                )
                return issues  # Stop on first cycle to avoid noise

            if node in visited:
                continue

            visited.add(node)
            in_stack.add(node)

            # push the backtrack marker
            dfs_stack.append(node)

            for neighbor in graph.get(node, []):
                dfs_stack.append((neighbor, path + [neighbor]))

    return issues


def validate_prompt(content: str) -> list[ValidationIssue]:
    """Validate prompt template syntax and safety."""
    issues = []

    has_system = "[system]" in content.lower()
    has_user = "[user]" in content.lower()

    if not has_user and not has_system:
        # Fallback raw prompt is technically allowed but discouraged
        issues.append(
            ValidationIssue(
                "warning",
                "prompt",
                (
                    "No [system] or [user] role markers found. "
                    "The entire text will be treated as the user message."
                ),
            )
        )

    # Very basic safety check for Python template parsing
    # Catch stray single '$' that isn't part of a valid identifier
    stray_dollars = re.findall(r"\$(?![A-Za-z_\{])", content)
    if stray_dollars:
        issues.append(
            ValidationIssue(
                "warning",
                "prompt",
                "Found unescaped '$' characters that do not form valid variables. "
                "Use '$$' for a literal dollar sign.",
            )
        )

    return issues
