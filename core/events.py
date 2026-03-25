"""
core.events — Thread-safe UI event bus.

Background workers publish events into a queue.
The main (tkinter) thread polls the queue via root.after() and dispatches
events to the WorkspaceController.
"""

from __future__ import annotations

import logging
import queue
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger("workbench.core.events")


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


@dataclass
class Event:
    """Base event."""

    kind: str
    data: dict[str, Any] = field(default_factory=dict)


# Convenience constructors
def run_started(run_id: str, workflow_id: str) -> Event:
    return Event("run_started", {"run_id": run_id, "workflow_id": workflow_id})


def step_started(run_id: str, step_id: str, index: int, total: int) -> Event:
    return Event(
        "step_started",
        {
            "run_id": run_id,
            "step_id": step_id,
            "index": index,
            "total": total,
        },
    )


def step_finished(
    run_id: str, step_id: str, status: str, index: int, total: int, result: Any = None
) -> Event:
    return Event(
        "step_finished",
        {
            "run_id": run_id,
            "step_id": step_id,
            "status": status,
            "index": index,
            "total": total,
            "result": result,
        },
    )


def node_ready(run_id: str, step_id: str) -> Event:
    return Event("node_ready", {"run_id": run_id, "step_id": step_id})


def node_blocked(run_id: str, step_id: str, reason: str) -> Event:
    return Event(
        "node_blocked", {"run_id": run_id, "step_id": step_id, "reason": reason}
    )


def port_emitted(run_id: str, step_id: str, port_name: str, payload: Any) -> Event:
    return Event(
        "port_emitted",
        {
            "run_id": run_id,
            "step_id": step_id,
            "port_name": port_name,
            "payload": payload,
        },
    )


def run_finished(run_id: str, status: str) -> Event:
    return Event("run_finished", {"run_id": run_id, "status": status})


def run_failed(run_id: str, error: str) -> Event:
    return Event("run_failed", {"run_id": run_id, "error": error})


def run_cancelled(run_id: str) -> Event:
    return Event("run_cancelled", {"run_id": run_id})


def config_reloaded() -> Event:
    return Event("config_reloaded")


def external_change_detected(path: str) -> Event:
    return Event("external_change_detected", {"path": path})


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------


class EventBus:
    """Thread-safe publish/subscribe event bus backed by queue.Queue.

    Features:
    - ``subscribe(kind, handler)`` returns a token for later unsubscription.
    - Wildcard: subscribe to ``"*"`` to receive all events.
    - Exception isolation: a failing handler does not block other handlers.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        # kind → list of (token, handler)
        self._handlers: dict[str, list[tuple[int, Callable]]] = {}
        self._next_token = 0

    def publish(self, event: "Event | dict") -> None:
        """Enqueue an event (safe to call from any thread).

        Accepts both Event dataclass instances and raw dicts for backward
        compatibility with legacy code that publishes plain dicts.
        """
        if isinstance(event, Event):
            self._queue.put({"type": event.kind, **event.data, "_event": event})
        else:
            self._queue.put(event)

    def subscribe(self, kind: str, handler: Callable) -> int:
        """Register *handler* for events of *kind*.

        Parameters
        ----------
        kind : str
            Event kind string, or ``"*"`` for all events.

        Returns
        -------
        int
            Subscription token, usable for ``unsubscribe()``.
        """
        token = self._next_token
        self._next_token += 1
        self._handlers.setdefault(kind, []).append((token, handler))
        return token

    def unsubscribe(self, kind: str, token: int) -> None:
        """Remove a subscriber by token."""
        handlers = self._handlers.get(kind, [])
        self._handlers[kind] = [(t, h) for t, h in handlers if t != token]

    def poll(self) -> list[dict]:
        """Drain the queue and return all pending events (call from main thread)."""
        events: list[dict] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events

    def dispatch(self) -> int:
        """Poll + call registered handlers. Returns number of events dispatched."""
        events = self.poll()
        for raw in events:
            inner = raw.get("_event")
            if isinstance(inner, Event):
                # Handlers expect dict-like payloads (.get); never pass Event dataclass.
                payload: dict[str, Any] = {"type": inner.kind, **inner.data}
            else:
                payload = {k: v for k, v in raw.items() if k != "_event"}

            kind = payload.get("type", payload.get("kind", ""))

            # Specific handlers
            for _, handler in self._handlers.get(kind, []):
                try:
                    handler(payload)
                except Exception as e:
                    log.warning("Handler error for event '%s': %s", kind, e)

            # Wildcard handlers
            for _, handler in self._handlers.get("*", []):
                try:
                    handler(payload)
                except Exception as e:
                    log.warning("Wildcard handler error for event '%s': %s", kind, e)

        return len(events)
