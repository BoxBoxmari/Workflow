"""
ui.config_watcher — Event-driven configuration file watcher.

Replaces the previous 1.5-second polling loop (which caused ~2,400 CPU
wake-ups per hour) with OS-native filesystem events via the ``watchdog``
library.  The watcher fires immediately when a config file is modified,
consuming zero CPU between events.

Usage::

    from ui.config_watcher import start_config_watcher, stop_config_watcher

    observer = start_config_watcher(config_dir, controller)
    # ... app runs ...
    stop_config_watcher(observer)
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def _build_handler(controller):
    """
    Build a FileSystemEventHandler that notifies controller about external
    config changes when a .json or .txt file is modified.

    The factory approach avoids a hard import of watchdog at module level,
    so the application still starts if watchdog is not installed (it will
    simply log a warning and fall back to no-op).
    """
    from watchdog.events import FileSystemEventHandler

    class _ConfigChangeHandler(FileSystemEventHandler):
        """Notifies the controller whenever a config file changes on disk."""

        def on_modified(self, event) -> None:
            if event.is_directory:
                return
            src = event.src_path
            if src.endswith(".json") or src.endswith(".txt"):
                log.debug("Config changed: %s — notifying controller", src)
                try:
                    if hasattr(controller, "notify_external_change"):
                        controller.notify_external_change(str(src))
                    else:
                        # Backward compatibility with older controllers.
                        controller.handle_external_change()
                except Exception as exc:
                    log.exception("external change notify raised: %s", exc)

    return _ConfigChangeHandler()


def start_config_watcher(config_dir: Path, controller):
    """
    Start watching *config_dir* for .json / .txt changes.

    Args:
        config_dir: Directory to watch (non-recursive).
        controller: Object with a ``notify_external_change(path)`` method
            (or legacy ``handle_external_change()`` fallback).

    Returns:
        A running ``watchdog.observers.Observer`` instance, or ``None``
        if the watchdog library is not installed.
    """
    try:
        from watchdog.observers import Observer
    except ImportError:
        log.warning(
            "watchdog library not installed — config file watching disabled. "
            "Install with: pip install watchdog"
        )
        return None

    handler = _build_handler(controller)
    observer = Observer()
    observer.schedule(handler, str(config_dir), recursive=False)
    observer.daemon = True
    observer.start()
    log.info("Config watcher started on: %s", config_dir)
    return observer


def stop_config_watcher(observer) -> None:
    """
    Stop and join the watchdog observer thread.

    Safe to call if *observer* is ``None`` (e.g., watchdog not installed).

    Args:
        observer: The ``Observer`` returned by ``start_config_watcher``.
    """
    if observer is None:
        return
    try:
        observer.stop()
        observer.join(timeout=3)
        log.info("Config watcher stopped.")
    except Exception as exc:
        log.warning("Error stopping config watcher: %s", exc)
