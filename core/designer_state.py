"""
core.designer_state — Shared draft state for the Design Studio
"""

from dataclasses import dataclass, field
from typing import Optional
from core.models import WorkflowDef


@dataclass
class DesignerState:
    """
    Shared draft state for the Design Studio UI.

    Holds unsaved edits while the user is managing workflows, steps, and prompts.
    """

    selected_workflow_id: Optional[str] = None
    selected_step_id: Optional[str] = None

    # Map of workflow_id to draft WorkflowDef
    workflow_drafts: dict[str, WorkflowDef] = field(default_factory=dict)

    # Map of prompt_key ("{step_name}_v{version}") to template content
    prompt_drafts: dict[str, str] = field(default_factory=dict)

    is_dirty: bool = False
    validation_issues: list[str] = field(default_factory=list)
