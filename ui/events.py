"""
ui.events — Custom events for UI state changes.
"""

from __future__ import annotations
from dataclasses import dataclass

UI_THEME_CHANGED = "ui.theme_changed"


@dataclass
class ThemeChangedEvent:
    appearance_mode: str  # "Dark", "Light", "System"
