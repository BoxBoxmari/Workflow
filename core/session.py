"""
core.session — Session state persistence.

Saves and restores UI session state (selected workflow/step, view mode,
drawer tab, recent file bindings) to state/session.json so the workspace
resumes from where the user left off.

Usage
-----
    from core.session import load_session, save_session, SessionState
    state = load_session(state_dir)
    # ... app runs ...
    save_session(state_dir, session)
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from core.io_utils import atomic_write_json

log = logging.getLogger("workbench.core.session")

SESSION_FILENAME = "session.json"


@dataclass
class SessionState:
    """Persisted workspace session fields.

    All fields are optional with safe defaults so a missing or corrupt
    session file degrades gracefully to a fresh start.
    """

    selected_workflow_id: Optional[str] = None
    selected_step_id: Optional[str] = None
    drawer_tab: str = "output"  # DrawerTab string value
    drawer_visible: bool = False
    mode: str = "simple"  # WorkspaceMode string value
    view: str = "design"  # WorkspaceView string value
    # Recent file bindings: variable_name → absolute file path
    recent_bindings: dict[str, str] = field(default_factory=dict)
    # Last used prompts directory (for file-picker default)
    last_prompt_dir: str = ""
    # Theme preference (Dark, Light, System)
    appearance_mode: str = "Dark"


def load_session(state_dir: Path) -> SessionState:
    """Load session from ``state_dir/session.json``.

    Returns a default SessionState if the file is missing or unreadable.
    """
    path = state_dir / SESSION_FILENAME
    if not path.is_file():
        return SessionState()

    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _from_dict(data)
    except Exception as e:
        log.warning("Could not load session (using defaults): %s", e)
        return SessionState()


def save_session(state_dir: Path, session: SessionState) -> None:
    """Save session to ``state_dir/session.json`` atomically.

    Creates ``state_dir`` if it does not exist.
    Silently ignores write errors to avoid crashing the app.
    """
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(state_dir / SESSION_FILENAME, asdict(session))
    except Exception as e:
        log.warning("Could not save session: %s", e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _from_dict(data: dict) -> SessionState:
    """Safely build SessionState from raw dict, ignoring unknown keys."""
    known = set(SessionState.__dataclass_fields__.keys())
    filtered = {k: v for k, v in data.items() if k in known}
    return SessionState(**filtered)
