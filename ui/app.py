"""
ui.app — Application entry point.

Architecture (Phase 2+):
  App (slim) → bootstraps services → creates WorkspaceController → mounts WorkspaceShell
"""

from __future__ import annotations

import json
import logging
import sys
import tkinter as tk
from pathlib import Path
from typing import Any, Optional, cast

from core.config_service import ConfigService
from core.events import EventBus
from core.prompts import PromptRegistry
from core.provider import WorkbenchClient
from core.storage import StorageManager
from ui import dialogs

log = logging.getLogger("workbench.ui.app")


class App:
    """Slim application bootstrap — the sole entry point.

    Responsibilities (and nothing else):
    1. Bootstrap core services
    2. Create root window
    3. Apply theme
    4. Create WorkspaceController
    5. Mount WorkspaceShell
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.config_dir = project_root / "config"
        self.runs_dir = project_root / "runs"

        # Core services
        self.storage = StorageManager(self.runs_dir)
        self.prompt_registry = PromptRegistry(self.config_dir / "prompts")
        self.config_service = ConfigService(self.config_dir)
        self.event_bus = EventBus()
        self.client: Optional[WorkbenchClient] = None

        # Root window
        import customtkinter as ctk

        try:
            ctk.set_appearance_mode("Dark")
        except Exception:
            pass
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()

        # ── Python 3.14 compatibility fix ──────────────────────────────
        # Python 3.14 changed _report_exception to call self._root() which
        # crashes with customtkinter (TypeError: 'CTk' object is not callable).
        # Additionally, nametowidget also calls _root() and can crash.
        # Fix: patch both at the class level to handle the TypeError.
        import tkinter as _tk

        _original_nametowidget = _tk.Misc.nametowidget

        def _safe_nametowidget(widget_self, name):
            try:
                return _original_nametowidget(widget_self, name)
            except TypeError:
                # _root() returned a CTk instance that Python 3.14 tries to
                # call again — fall back to returning the widget path string.
                return name

        setattr(cast(Any, _tk.Misc), "nametowidget", _safe_nametowidget)
        setattr(cast(Any, _tk.Misc), "_nametowidget", _safe_nametowidget)

        def _safe_report_exception(widget_self):
            """Report callback exception without calling self._root()."""
            exc_type, exc_value, exc_tb = sys.exc_info()
            if exc_type is None:
                return
            try:
                error_msg = "".join(
                    __import__("traceback").format_exception(
                        exc_type, exc_value, exc_tb
                    )
                )
                log.error("Unhandled GUI Exception:\n%s", error_msg)
            except Exception:
                pass

        setattr(cast(Any, _tk.Misc), "_report_exception", _safe_report_exception)

        self.root.title("Workflow MVP — AI Workflow Workbench")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)

        # Theme
        from ui.theme import apply_theme

        apply_theme(self.root)

        # Load provider before controller
        self._load_provider_config()

        # Controller
        from ui.workspace_controller import WorkspaceController

        self.controller = WorkspaceController(
            project_root=project_root,
            config_service=self.config_service,
            storage=self.storage,
            prompt_registry=self.prompt_registry,
            client=self.client,
            event_bus=self.event_bus,
        )

        # Mount workspace shell
        from ui.workspace_shell import WorkspaceShell

        # Shell creation needs to happen while root is fresh
        self.shell = WorkspaceShell(self.root, self.controller)
        self.shell.pack(fill=tk.BOTH, expand=True)

        # Lifecycle boot (loads session)
        self.controller.start()

        # Restore appearance mode from persisted session
        try:
            import customtkinter as ctk

            ctk.set_appearance_mode(self.controller.state.appearance_mode)
        except Exception as e:
            log.debug("Could not restore appearance mode: %s", e)

        # Handle Window Close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self) -> None:
        """Graceful teardown and auto-save on exit."""
        if hasattr(self, "controller") and self.controller:
            try:
                # Attempt save, do not block exit if it fails validation
                self.controller.save()
            except Exception as e:
                log.error("Auto-save on exit failed: %s", e)
            finally:
                self.controller.stop()
        self.root.destroy()

    def _load_provider_config(self) -> None:
        provider_file = self.config_dir / "provider.json"

        cfg = {}
        if provider_file.is_file():
            try:
                cfg = json.loads(provider_file.read_text(encoding="utf-8"))
            except Exception as e:
                log.error("Failed to parse provider.json: %s", e)

        # Build client using secure store/env for credentials only
        self.client = WorkbenchClient.from_config(cfg)

        # If plaintext credentials still exist in provider.json, warn explicitly.
        if cfg.get("subscription_key") or cfg.get("charge_code"):
            dialogs.show_warning(
                "Security Warning",
                "Detected plaintext API credentials in provider.json.\n\n"
                "These values are ignored. Move credentials to OS Credential Manager "
                "or environment variables (WORKBENCH_SUBSCRIPTION_KEY / WORKBENCH_CHARGE_CODE).",
                parent=self.root,
            )

    def _pump_events(self) -> None:
        """Poll the event bus and dispatch events on the main thread."""
        self.event_bus.dispatch()
        self.root.after(100, self._pump_events)

    def run(self) -> None:
        """Start the tkinter main loop and the event pump."""
        self._pump_events()
        self.root.mainloop()
