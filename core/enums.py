"""
core.enums — Normalized state and status types for the Workflow MVP.

All enums inherit from str so they serialize cleanly as plain strings
in JSON without a custom encoder.
"""

from __future__ import annotations

import enum


class _StrEnum(str, enum.Enum):
    """str+Enum base that works on Python 3.10 (before StrEnum was added)."""

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


# ---------------------------------------------------------------------------
# Run / Step status
# ---------------------------------------------------------------------------


class RunStatus(_StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class StepStatus(_StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Workspace UI modes
# ---------------------------------------------------------------------------


class WorkspaceMode(_StrEnum):
    SIMPLE = "simple"
    ADVANCED = "advanced"


class WorkspaceView(_StrEnum):
    DESIGN = "design"
    RESULTS = "results"


class DrawerTab(_StrEnum):
    SUMMARY = "summary"
    INPUT = "input"
    OUTPUT = "output"
    EVENTS = "events"
    PROVENANCE = "provenance"
    RAW = "raw"
    METRICS = "metrics"
    LOG = "log"
