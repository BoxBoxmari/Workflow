"""
core.storage — Local file persistence for runs, steps, and events.

All data is stored under a configurable runs/ directory as JSON,
JSONL, and CSV files.  No database required.

Thread safety:
  StorageManager uses a threading.Lock() for all index writes and enqueues
  all updates through a StorageWriteQueue so that Event Bus callbacks
  cannot race each other, even when multiple events fire concurrently.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import queue
import threading
import time
from pathlib import Path
from typing import Optional

from core.models import RunContext, RunSummary, StepResult

log = logging.getLogger(__name__)


class StorageWriteQueue:
    """
    Background worker that serializes file-write operations.

    All callers enqueue a zero-argument callable. The worker executes
    them one at a time on a dedicated daemon thread, preventing the
    UI event loop from blocking on disk I/O and eliminating re-entrancy
    issues when the Event Bus fires multiple callbacks concurrently.
    """

    def __init__(self) -> None:
        self._q: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._process_loop,
            daemon=True,
            name="StorageWriteQueue",
        )
        self._thread.start()

    def enqueue(self, operation) -> None:
        """Add a callable to the write queue (non-blocking)."""
        self._q.put(operation)

    def flush(self) -> None:
        """Block until all currently queued operations have completed."""
        done = threading.Event()
        self._q.put(done.set)
        done.wait()

    def stop(self) -> None:
        """Signal the worker thread to exit after draining the queue."""
        self._stop.set()
        self._q.put(None)  # Sentinel to unblock the worker
        self._thread.join(timeout=5)

    def _process_loop(self) -> None:
        while True:
            op = self._q.get()
            if op is None:  # Sentinel
                break
            try:
                op()
            except Exception as exc:
                log.exception("StorageWriteQueue: unhandled error in write op: %s", exc)


# Default runs directory relative to project root
_DEFAULT_RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


class StorageManager:
    """
    Read/write run data to local filesystem.

    Thread-safety contract:
      - All reads are unsynchronized (CSV files are append-only during a run).
      - All index writes (update_index, _write_index_rows) are serialized
        through self._write_lock and self._write_queue to prevent corruption
        when multiple threads trigger storage callbacks simultaneously.
      - All event appends (append_event) are serialized through the same
        write queue to avoid interleaving writes from concurrent callbacks.
    """

    def __init__(self, runs_dir: Optional[Path] = None):
        self.runs_dir = Path(runs_dir) if runs_dir else _DEFAULT_RUNS_DIR
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        # Mutex guards the index.csv read-modify-write cycle
        self._write_lock = threading.Lock()
        # Background queue serializes all writes so the UI thread never blocks
        self._write_queue = StorageWriteQueue()

    @property
    def index_path(self) -> Path:
        return self.runs_dir / "index.csv"

    def _run_dir(self, run_id: str) -> Path:
        return self.runs_dir / run_id

    def _steps_dir(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "steps"

    def _step_counter_path(self, run_id: str) -> Path:
        # Sidecar counter for legacy step_XX.json sequencing.
        # Stores the last allocated integer index as UTF-8 text.
        return self._steps_dir(run_id) / ".step_counter"

    def _nodes_dir(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "nodes"

    def _ports_dir(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "ports"

    def _artifacts_dir(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "artifacts"

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def create_run(self, run_ctx: RunContext) -> Path:
        """Create the directory structure for a new run."""
        run_dir = self._run_dir(run_ctx.run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        self._steps_dir(run_ctx.run_id).mkdir(exist_ok=True)
        self._artifacts_dir(run_ctx.run_id).mkdir(exist_ok=True)
        self.save_run(run_ctx)
        return run_dir

    def save_run(self, run_ctx: RunContext) -> None:
        """Write or overwrite run.json for a run."""
        path = self._run_dir(run_ctx.run_id) / "run.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(run_ctx.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load_run(self, run_id: str) -> RunContext:
        """Load run.json for a run."""
        path = self._run_dir(run_id) / "run.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return RunContext.from_dict(data)

    # ------------------------------------------------------------------
    # Steps / Nodes / Ports
    # ------------------------------------------------------------------

    def save_step(self, run_id: str, step_result: StepResult) -> None:
        """Write a step result to steps/step_XX.json."""
        steps_dir = self._steps_dir(run_id)
        steps_dir.mkdir(parents=True, exist_ok=True)

        # PERF-003: avoid glob+sort on every step write.
        # Serialize step index allocation to prevent races under concurrent callbacks.
        with self._write_lock:
            counter_path = self._step_counter_path(run_id)

            last_idx = 0
            if counter_path.is_file():
                try:
                    last_idx = int(counter_path.read_text(encoding="utf-8").strip() or "0")
                except ValueError:
                    last_idx = 0

            if last_idx <= 0:
                # Initialize counter once for legacy runs (may already have step files).
                max_idx = 0
                for p in steps_dir.glob("step_*.json"):
                    name = p.stem  # step_XX
                    if not name.startswith("step_"):
                        continue
                    suffix = name.removeprefix("step_")
                    try:
                        n = int(suffix)
                    except ValueError:
                        continue
                    max_idx = max(max_idx, n)
                last_idx = max_idx

            idx = last_idx + 1
            filename = f"step_{idx:02d}.json"
            path = steps_dir / filename

            path.write_text(
                json.dumps(step_result.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            counter_path.write_text(str(idx), encoding="utf-8")

    def load_step(self, run_id: str, step_filename: str) -> StepResult:
        """Load a specific step file."""
        path = self._steps_dir(run_id) / step_filename
        data = json.loads(path.read_text(encoding="utf-8"))
        return StepResult.from_dict(data)

    def list_step_files(self, run_id: str) -> list[str]:
        """List step filenames for a run, sorted."""
        steps_dir = self._steps_dir(run_id)
        if not steps_dir.is_dir():
            return []
        return sorted(f.name for f in steps_dir.glob("step_*.json"))

    def load_all_steps(self, run_id: str) -> list[StepResult]:
        """
        Load all step results for a run, in order.
        Acts as an adapter: loads legacy steps from 'steps/' or graph nodes from 'nodes/'.
        """
        results = []

        # Graph path
        nodes_dir = self._nodes_dir(run_id)
        if nodes_dir.is_dir():
            for path in nodes_dir.glob("*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    results.append(StepResult.from_dict(data))
                except Exception as exc:
                    log.warning(
                        "load_all_steps: skip corrupted node file %s (%s)",
                        path.name,
                        exc,
                    )
            # Sort by timestamp to ensure consistent chronological UI ordering
            results.sort(
                key=lambda s: s.metrics.timestamp
                if s.metrics and s.metrics.timestamp
                else ""
            )
            return results

        # Legacy path
        for fname in self.list_step_files(run_id):
            results.append(self.load_step(run_id, fname))
        return results

    def save_node(self, run_id: str, step_id: str, step_result: StepResult) -> None:
        """Write a graph node result to nodes/<step_id>.json."""
        nodes_dir = self._nodes_dir(run_id)
        nodes_dir.mkdir(parents=True, exist_ok=True)
        path = nodes_dir / f"{step_id}.json"
        path.write_text(
            json.dumps(step_result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load_node(self, run_id: str, step_id: str) -> StepResult:
        """Load a specific graph node result."""
        path = self._nodes_dir(run_id) / f"{step_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return StepResult.from_dict(data)

    def save_port(
        self, run_id: str, step_id: str, port_name: str, content: str | bytes
    ) -> Path:
        """Write a specific output port payload to disk."""
        ports_dir = self._ports_dir(run_id)
        ports_dir.mkdir(parents=True, exist_ok=True)
        path = ports_dir / f"{step_id}__{port_name}.json"

        # Keep port outputs as strings internally, while still allowing
        # raw bytes payloads if needed later.
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def load_port(self, run_id: str, step_id: str, port_name: str) -> str:
        """Read a specific output port payload from disk."""
        path = self._ports_dir(run_id) / f"{step_id}__{port_name}.json"
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Events (JSONL append log)
    # ------------------------------------------------------------------

    def append_event(self, run_id: str, event: dict) -> None:
        """
        Append one event to events.jsonl.

        Enqueues the append operation to guarantee line-level integrity when
        multiple event callbacks fire concurrently.
        """
        self._write_queue.enqueue(lambda: self._append_event_impl(run_id, event))

    def _append_event_impl(self, run_id: str, event: dict) -> None:
        path = self._run_dir(run_id) / "events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        line = json.dumps(event, ensure_ascii=False) + "\n"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(path, "a", encoding="utf-8", newline="") as f:
                    f.write(line)
                    f.flush()
                    os.fsync(f.fileno())
                return
            except PermissionError:
                if attempt == max_retries - 1:
                    raise
                wait = 0.2 * (attempt + 1)  # 0.2s, 0.4s, then raise
                log.warning(
                    "events.jsonl locked (append attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    wait,
                )
                time.sleep(wait)

    def load_events(self, run_id: str) -> list[dict]:
        """Load all events from events.jsonl."""
        # Ensure queued append operations are visible to immediate readers/tests.
        self._write_queue.flush()
        path = self._run_dir(run_id) / "events.jsonl"
        if not path.is_file():
            return []
        events = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    # ------------------------------------------------------------------
    # Index (CSV)
    # ------------------------------------------------------------------

    _INDEX_FIELDS = [
        "run_id",
        "workflow_id",
        "workflow_name",
        "started_at",
        "finished_at",
        "status",
        "step_count",
        "run_type",
    ]

    def update_index(self, run_ctx: RunContext) -> None:
        """
        Enqueue an index update for the given run.

        The actual write is dispatched to the background StorageWriteQueue so
        that Event Bus callbacks can fire rapidly without blocking the UI or
        racing each other over index.csv.
        """
        self._write_queue.enqueue(lambda: self._update_index_impl(run_ctx))

    def _update_index_impl(self, run_ctx: RunContext) -> None:
        """
        Internal implementation; always runs on the write-queue thread.

        Performance strategy (PERF-001):
          - Append-only for BOTH new runs and existing-run status updates (O(1)).
          - Read-side (`list_runs`) and maintenance (`compact_index`) dedupe by run_id.
        """
        with self._write_lock:
            new_row = {
                "run_id": run_ctx.run_id,
                "workflow_id": run_ctx.workflow_id,
                "workflow_name": run_ctx.workflow_name,
                "started_at": run_ctx.started_at,
                "finished_at": run_ctx.finished_at,
                "status": run_ctx.status,
                "step_count": str(len(run_ctx.step_results)),
                "run_type": run_ctx.run_type,
            }

            self._append_to_index(new_row)

    def _append_to_index(self, row: dict) -> None:
        """
        Append a single row to index.csv, creating the file with header if needed.

        O(1) operation — opens file in append mode, writes one CSV line.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                write_header = not self.index_path.is_file()
                with open(self.index_path, "a", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=self._INDEX_FIELDS)
                    if write_header:
                        writer.writeheader()
                    writer.writerow(row)
                return
            except PermissionError:
                if attempt == max_retries - 1:
                    raise
                wait = 0.5 * (attempt + 1)  # 0.5s, 1.0s, then raise
                log.warning(
                    "index.csv locked (append attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    wait,
                )
                time.sleep(wait)

    def _read_index_run_ids(self) -> set[str]:
        """Read only the run_id column from index.csv (fast membership check)."""
        if not self.index_path.is_file():
            return set()
        ids: set[str] = set()
        with open(self.index_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                run_id = row.get("run_id", "").strip()
                if run_id:
                    ids.add(run_id)
        return ids

    def compact_index(self) -> None:
        """
        Deduplicate and rewrite index.csv (periodic maintenance).

        The append-first strategy can leave duplicate rows if the same run
        is updated multiple times (e.g., re-queued). Call this periodically
        — for example, on startup or when the file exceeds a size threshold.
        Keeps the last-seen row for each run_id (preserves most recent status).
        """
        with self._write_lock:
            rows = self._read_index_rows()
            deduped_rows = self._dedupe_index_rows(rows)
            self._write_index_rows(deduped_rows)
            log.info(
                "compact_index: %d rows → %d unique runs", len(rows), len(deduped_rows)
            )

    def list_runs(self) -> list[RunSummary]:
        """Read index.csv and return RunSummary objects (deduped by run_id)."""
        # Ensure queued index updates are visible before read.
        self._write_queue.flush()
        rows = self._dedupe_index_rows(self._read_index_rows())
        summaries = []
        for row in rows:
            summaries.append(
                RunSummary(
                    run_id=row.get("run_id", ""),
                    workflow_id=row.get("workflow_id", ""),
                    workflow_name=row.get("workflow_name", ""),
                    started_at=row.get("started_at", ""),
                    finished_at=row.get("finished_at", ""),
                    status=row.get("status", ""),
                    step_count=int(row.get("step_count", "0")),
                    run_type=row.get("run_type", "standard"),
                )
            )
        return summaries

    def _dedupe_index_rows(self, rows: list[dict]) -> list[dict]:
        """
        Deduplicate index rows by run_id.

        Contract:
          - At most 1 row per run_id.
          - Field values are last-write-wins (latest occurrence wins).
          - Ordering is by first occurrence of each run_id (stable history order),
            so updating an existing run does not reorder the UI list.
        """
        first_pos: dict[str, int] = {}
        latest_row: dict[str, dict] = {}

        for i, row in enumerate(rows):
            run_id = (row.get("run_id") or "").strip()
            if not run_id:
                continue
            if run_id not in first_pos:
                first_pos[run_id] = i
            latest_row[run_id] = row

        ordered = sorted(first_pos.items(), key=lambda kv: kv[1])
        return [latest_row[run_id] for run_id, _ in ordered]

    def _read_index_rows(self) -> list[dict]:
        """Read all rows from index.csv."""
        if not self.index_path.is_file():
            return []
        with open(self.index_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_index_rows(self, rows: list[dict]) -> None:
        """
        Write all rows to index.csv atomically.

        Uses a temp-file + rename pattern so a crash mid-write never leaves
        index.csv in a partial state.  Retries with exponential back-off on
        PermissionError to handle the case where a user has index.csv open
        in Excel or another application (common on Windows).
        """
        tmp_path = self.index_path.with_suffix(".tmp")
        tmp_path.write_text(self._rows_to_csv_text(rows), encoding="utf-8")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                tmp_path.replace(self.index_path)
                return
            except PermissionError:
                if attempt == max_retries - 1:
                    raise
                wait = 0.5 * (attempt + 1)  # 0.5s, 1.0s, then raise
                log.warning(
                    "index.csv locked (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    wait,
                )
                time.sleep(wait)

    def _rows_to_csv_text(self, rows: list[dict]) -> str:
        """Serialize rows to CSV string for atomic write."""
        import io

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=self._INDEX_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Artifacts
    # ------------------------------------------------------------------

    def save_artifact(self, run_id: str, filename: str, content: str | bytes) -> Path:
        """Save an artifact file into the run's artifacts/ folder."""
        artifacts_dir = self._artifacts_dir(run_id)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = artifacts_dir / filename
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def list_artifacts(self, run_id: str) -> list[str]:
        """List artifact filenames for a run."""
        artifacts_dir = self._artifacts_dir(run_id)
        if not artifacts_dir.is_dir():
            return []
        return sorted(f.name for f in artifacts_dir.iterdir() if f.is_file())
