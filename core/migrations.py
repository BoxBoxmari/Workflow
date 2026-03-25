"""
core.migrations — Schema versioning and migration pipeline for workflow config.

Detects schema_version, applies migrations to bring data up to the current
version, and normalizes defaults.  Backward-compatible: v1 (legacy) configs
are auto-migrated on load without breaking existing files on disk.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

log = logging.getLogger("workbench.core.migrations")

CURRENT_SCHEMA_VERSION = 3


def detect_version(raw: dict[str, Any]) -> int:
    """Return the schema_version from raw config data, defaulting to 1."""
    return int(raw.get("schema_version", 1))


def migrate(raw: dict[str, Any]) -> dict[str, Any]:
    """Run the full migration pipeline on raw config dict, returning upgraded data."""
    data = copy.deepcopy(raw)
    version = detect_version(data)

    if version < 2:
        data = _migrate_v1_to_v2(data)
        log.info("Migrated workflow config from v1 → v2")
        version = 2

    if version < 3:
        data = _migrate_v2_to_v3(data)
        log.info("Migrated workflow config from v2 → v3")

    data["schema_version"] = CURRENT_SCHEMA_VERSION
    return data


def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """v1 → v2: add title/purpose/ui to steps, normalize depends_on."""
    workflows = data.get("workflows", [])
    if isinstance(data, list):
        # Legacy format: top-level is list of workflows
        workflows = data
        data = {"workflows": workflows}

    for wf in workflows:
        for step in wf.get("steps", []):
            # Add new display fields with safe defaults
            step.setdefault("title", "")
            step.setdefault("purpose", "")
            step.setdefault("ui", {})

            # Normalize depends_on
            deps = step.get("depends_on")
            if deps is None:
                step["depends_on"] = []
            elif isinstance(deps, str):
                step["depends_on"] = [deps] if deps else []
            elif not isinstance(deps, list):
                step["depends_on"] = []

            # Normalize attachments
            step.setdefault("attachments", [])
            for att in step["attachments"]:
                att.setdefault("accepted_types", None)

    data["schema_version"] = 2
    return data


def _migrate_v2_to_v3(data: dict[str, Any]) -> dict[str, Any]:
    """v2 → v3: Add execution_mode, inputs, outputs for graph support."""
    workflows = data.get("workflows", [])

    for wf in workflows:
        wf["schema_version"] = 3
        for step in wf.get("steps", []):
            step.setdefault("execution_mode", "legacy")
            step.setdefault("inputs", [])
            step.setdefault("outputs", [])

    data["schema_version"] = 3
    return data


def normalize_workflow_dict(wf_dict: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single workflow dict (apply defaults, fix types)."""
    wf_dict.setdefault("schema_version", CURRENT_SCHEMA_VERSION)
    wf_dict.setdefault("description", "")
    wf_dict.setdefault("steps", [])
    for step in wf_dict["steps"]:
        step.setdefault("title", "")
        step.setdefault("purpose", "")
        step.setdefault("ui", {})
        step.setdefault("input_mapping", "input")
        step.setdefault("output_mapping", "output")
        step.setdefault("enabled", True)
        step.setdefault("attachments", [])

        # v3 schema
        step.setdefault("execution_mode", "legacy")
        step.setdefault("inputs", [])
        step.setdefault("outputs", [])
        # Normalize depends_on
        deps = step.get("depends_on")
        if deps is None:
            step["depends_on"] = []
        elif isinstance(deps, str):
            step["depends_on"] = [deps] if deps else []
    return wf_dict
