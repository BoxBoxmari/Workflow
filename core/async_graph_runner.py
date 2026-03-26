"""
core.async_graph_runner — Asynchronous DAG workflow runner.

Executes a WorkflowDef in graph execution mode using asyncio for concurrency.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional, Any

from core.events import (
    EventBus,
    run_finished,
    run_failed,
    run_cancelled,
    run_started,
    step_started,
    step_finished,
    node_ready,
    node_blocked,
    port_emitted,
    attachment_consumed_by_step,
)
from core.models import (
    ProviderRequest,
    RunContext,
    StepDef,
    StepMetrics,
    StepResult,
    WorkflowDef,
    _generate_run_id,
)
from core.prompts import PromptRegistry
from core.provider import WorkbenchClient
from core.storage import StorageManager
from core.graph_utils import build_predecessor_map

log = logging.getLogger("workbench.core.async_graph_runner")


class AsyncGraphRunner:
    """Runs a graph workflow using asyncio."""

    def __init__(
        self,
        client: WorkbenchClient,
        prompt_registry: PromptRegistry,
        storage: StorageManager,
        event_bus: Optional[EventBus] = None,
        max_concurrency: int = 10,
    ):
        self.client = client
        self.prompts = prompt_registry
        self.storage = storage
        self.event_bus = event_bus
        self.max_concurrency = max_concurrency
        # threading.Event: cancel() may be called from UI thread while asyncio.run
        # executes on a worker thread; asyncio.Event is not safe across threads.
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Signal the runner to stop executing further steps."""
        self._cancel_event.set()

    def run(
        self,
        workflow_def: WorkflowDef,
        initial_input: str = "",
        initial_variables: Optional[dict[str, Any]] = None,
        attachment_meta: Optional[dict[str, dict[str, Any]]] = None,
        on_run_start: Optional[Callable[[RunContext], None]] = None,
        on_step_start: Optional[Callable[[StepDef, int, int], None]] = None,
        on_step_complete: Optional[Callable[[StepResult, int, int], None]] = None,
        on_run_complete: Optional[Callable[[RunContext], None]] = None,
    ) -> RunContext:
        """
        Synchronous entry point that wraps the asyncio execution.
        """
        return asyncio.run(
            self._execute_graph(
                workflow_def,
                initial_input,
                initial_variables,
                attachment_meta,
                on_run_start,
                on_step_start,
                on_step_complete,
                on_run_complete,
            )
        )

    def run_thread(
        self,
        workflow_def: WorkflowDef,
        initial_input: str = "",
        initial_variables: Optional[dict[str, Any]] = None,
        attachment_meta: Optional[dict[str, dict[str, Any]]] = None,
        on_run_start: Optional[Callable[[RunContext], None]] = None,
        on_step_start: Optional[Callable[[StepDef, int, int], None]] = None,
        on_step_complete: Optional[Callable[[StepResult, int, int], None]] = None,
        on_run_complete: Optional[Callable[[RunContext], None]] = None,
    ) -> threading.Thread:
        """Start the graph execution on a background thread. Returns the thread."""
        thread = threading.Thread(
            target=self.run,
            args=(workflow_def, initial_input, initial_variables, attachment_meta),
            kwargs={
                "on_run_start": on_run_start,
                "on_step_start": on_step_start,
                "on_step_complete": on_step_complete,
                "on_run_complete": on_run_complete,
            },
            daemon=True,
        )
        thread.start()
        return thread

    async def _execute_graph(
        self,
        workflow_def: WorkflowDef,
        initial_input: str = "",
        initial_variables: Optional[dict[str, Any]] = None,
        attachment_meta: Optional[dict[str, dict[str, Any]]] = None,
        on_run_start: Optional[Callable[[RunContext], None]] = None,
        on_step_start: Optional[Callable[[StepDef, int, int], None]] = None,
        on_step_complete: Optional[Callable[[StepResult, int, int], None]] = None,
        on_run_complete: Optional[Callable[[RunContext], None]] = None,
    ) -> RunContext:
        """
        Core async scheduling logic.
        """
        self._cancel_event.clear()

        # Initialize run context
        run_ctx = RunContext(
            run_id=_generate_run_id(),
            workflow_id=workflow_def.id,
            workflow_name=workflow_def.name,
            workflow_snapshot=workflow_def.to_dict(),
            started_at=datetime.now(timezone.utc).isoformat(),
            status="running",
            run_type="graph",
            engine_type="graph",
            schema_version=3,
        )

        run_ctx.variables["input"] = initial_input
        if initial_variables:
            for k, v in initial_variables.items():
                run_ctx.variables[k] = v

        self.storage.create_run(run_ctx)
        self.storage.append_event(
            run_ctx.run_id,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "run_started",
                "message": f"Graph Workflow '{workflow_def.name}' started",
            },
        )
        if on_run_start:
            on_run_start(run_ctx)
        if self.event_bus:
            self.event_bus.publish(run_started(run_ctx.run_id, workflow_def.id))

        enabled_steps = [s for s in workflow_def.steps if s.enabled]
        if not enabled_steps:
            run_ctx.status = "success"
            run_ctx.finished_at = datetime.now(timezone.utc).isoformat()
            self.storage.save_run(run_ctx)
            if on_run_complete:
                on_run_complete(run_ctx)
            if self.event_bus:
                self.event_bus.publish(run_finished(run_ctx.run_id, run_ctx.status))
            return run_ctx

        step_map = {s.id: s for s in enabled_steps}
        preds = build_predecessor_map(enabled_steps)

        # State tracking: step_id -> status ('pending', 'running', 'success', 'error', 'blocked')
        node_states = {s.id: "pending" for s in enabled_steps}
        # In-memory output cache: step_id -> port_name -> output string
        port_outputs: dict[str, dict[str, str]] = {s.id: {} for s in enabled_steps}
        attachment_meta = attachment_meta or {}

        semaphore = asyncio.Semaphore(self.max_concurrency)
        tasks: set[asyncio.Task] = set()

        def check_readiness():
            """Returns a list of step IDs that are ready to be scheduled."""
            ready = []
            for s_id, status in node_states.items():
                if status == "pending":
                    all_success = True
                    is_blocked = False
                    for p_id in preds[s_id]:
                        p_status = node_states.get(p_id, "unknown")
                        if p_status in ("error", "blocked"):
                            is_blocked = True
                            break
                        elif p_status != "success":
                            all_success = False
                            break

                    if is_blocked:
                        node_states[s_id] = "blocked"
                        if self.event_bus:
                            self.event_bus.publish(
                                node_blocked(run_ctx.run_id, s_id, "upstream failure")
                            )
                        self.storage.append_event(
                            run_ctx.run_id,
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "event_type": "node_blocked",
                                "step_id": s_id,
                                "message": "Blocked due to upstream failure",
                            },
                        )
                    elif all_success:
                        ready.append(s_id)
            return ready

        async def execute_node_task(step_id: str, index: int, total: int):
            async with semaphore:
                step_def = step_map[step_id]
                node_states[step_id] = "running"

                if self.event_bus:
                    self.event_bus.publish(node_ready(run_ctx.run_id, step_id))
                    self.event_bus.publish(
                        step_started(run_ctx.run_id, step_id, index, total)
                    )
                if on_step_start:
                    on_step_start(step_def, index, total)

                try:
                    result = await self._execute_step_async(
                        step_def, run_ctx, port_outputs, attachment_meta
                    )
                except Exception as e:
                    result = StepResult(
                        step_id=step_id,
                        step_name=step_def.name,
                        status="error",
                        error=f"Unhandled exception: {e}",
                    )

                run_ctx.step_results.append(step_id)

                if result.status == "success":
                    node_states[step_id] = "success"
                else:
                    node_states[step_id] = "error"
                    run_ctx.status = "error"
                    run_ctx.error = f"Step '{step_def.name}' failed: {result.error}"

                # Persist step
                self.storage.save_node(run_ctx.run_id, step_id, result)
                self.storage.append_event(
                    run_ctx.run_id,
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event_type": "step_completed",
                        "step_id": step_id,
                        "status": result.status,
                        "latency_ms": result.metrics.latency_ms
                        if result.metrics
                        else 0,
                    },
                )

                if on_step_complete:
                    on_step_complete(result, index, total)
                if self.event_bus:
                    self.event_bus.publish(
                        step_finished(
                            run_ctx.run_id, step_id, result.status, index, total, result
                        )
                    )

                return step_id

        # Main orchestration loop
        total_steps = len(enabled_steps)
        scheduled: set[str] = set()
        index_counter = 0

        while len(scheduled) < total_steps or tasks:
            if self._cancel_event.is_set():
                if run_ctx.status != "error":
                    run_ctx.status = "cancelled"
                    self.storage.append_event(
                        run_ctx.run_id,
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "event_type": "run_cancelled",
                            "message": "Graph run cancelled by user",
                        },
                    )
                break

            ready_steps = check_readiness()
            for s_id in ready_steps:
                if s_id not in scheduled:
                    scheduled.add(s_id)
                    task = asyncio.create_task(
                        execute_node_task(s_id, index_counter, total_steps)
                    )
                    index_counter += 1
                    tasks.add(task)
                    task.add_done_callback(tasks.discard)

            if not tasks:
                break

            # Process completed tasks if any or simply delay slightly for task resolution
            done, _ = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED, timeout=0.1
            )

        if tasks:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        if run_ctx.status == "running":
            run_ctx.status = "success"

        run_ctx.finished_at = datetime.now(timezone.utc).isoformat()
        self.storage.save_run(run_ctx)
        self.storage.update_index(run_ctx)
        self.storage.append_event(
            run_ctx.run_id,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "run_finished",
                "status": run_ctx.status,
            },
        )

        if on_run_complete:
            on_run_complete(run_ctx)

        if self.event_bus:
            if run_ctx.status == "error":
                self.event_bus.publish(run_failed(run_ctx.run_id, run_ctx.error or ""))
            elif run_ctx.status == "cancelled":
                self.event_bus.publish(run_cancelled(run_ctx.run_id))
            else:
                self.event_bus.publish(run_finished(run_ctx.run_id, run_ctx.status))

        return run_ctx

    async def _execute_step_async(
        self,
        step_def: StepDef,
        run_ctx: RunContext,
        port_outputs: dict[str, dict[str, str]],
        attachment_meta: dict[str, dict[str, Any]],
    ) -> StepResult:
        """
        Execute a single graph workflow step with join strategies.
        """
        result = StepResult(
            step_id=step_def.id,
            step_name=step_def.name,
            status="running",
        )

        input_data = {}

        # Fill input_data based on step_def.inputs and join strategies
        root_source_ids = {"__input__", "workflow_input", "$input"}
        consumed_attachment_vars: set[str] = set()
        for p in step_def.inputs:
            resolved_values = []
            for src in p.sources:
                if src.step_id in root_source_ids:
                    val = str(run_ctx.variables.get(src.port, ""))
                else:
                    val = port_outputs.get(src.step_id, {}).get(src.port, "")
                resolved_values.append(val)

            joined_val = ""
            if p.join_strategy == "first":
                joined_val = next((v for v in resolved_values if v), "")
            elif p.join_strategy == "concat":
                joined_val = "\n".join(v for v in resolved_values if v)
            elif p.join_strategy == "json_map":
                # Build dict from source values; fallback to string mapping
                # when a value is not valid JSON.
                jsp = {}
                for idx, src in enumerate(p.sources):
                    key = f"{src.step_id}.{src.port}"
                    try:
                        jsp[key] = json.loads(resolved_values[idx])
                    except (json.JSONDecodeError, IndexError, TypeError):
                        jsp[key] = (
                            resolved_values[idx] if idx < len(resolved_values) else ""
                        )
                joined_val = json.dumps(jsp, ensure_ascii=False)
            else:
                joined_val = "\n".join(v for v in resolved_values if v)

            if p.required and not joined_val:
                result.status = "error"
                result.error = (
                    f"Input port '{p.name}' is required "
                    "but received no non-empty sequence."
                )
                return result

            input_data[p.name] = joined_val
            if isinstance(joined_val, str) and joined_val.strip():
                for src in p.sources:
                    if (
                        src.step_id in root_source_ids
                        and src.port in attachment_meta
                        and src.port not in consumed_attachment_vars
                    ):
                        meta = attachment_meta[src.port]
                        consumed_event = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "event_type": "attachment_consumed_by_step",
                            "run_id": run_ctx.run_id,
                            "step_id": step_def.id,
                            "variable_name": src.port,
                            "source_file_sha256": meta.get("sha256", ""),
                            "slot_id": meta.get("slot_id"),
                        }
                        self.storage.append_event(run_ctx.run_id, consumed_event)
                        if self.event_bus:
                            self.event_bus.publish(
                                attachment_consumed_by_step(
                                    run_id=run_ctx.run_id,
                                    step_id=step_def.id,
                                    variable_name=src.port,
                                    source_file_sha256=meta.get("sha256", ""),
                                    slot_id=meta.get("slot_id"),
                                )
                            )
                        consumed_attachment_vars.add(src.port)

        # Add global variable to context
        local_vars = {**run_ctx.variables, **input_data}
        result.input_ports = input_data

        # Render prompt
        try:
            if step_def.role_text or step_def.task_text:
                # No-code flow
                # Choose the first input as upstream if defined
                primary_input = list(input_data.values())[0] if input_data else ""
                messages = self.prompts.render_from_parts(
                    role_text=step_def.role_text,
                    task_text=step_def.task_text,
                    upstream_output=primary_input,
                    extra_variables=local_vars,
                )
            else:
                messages = self.prompts.render(
                    step_def.name,
                    step_def.prompt_version,
                    local_vars,
                )
            result.rendered_prompt = messages
        except FileNotFoundError as e:
            result.status = "error"
            result.error = str(e)
            return result

        req = ProviderRequest(
            model=step_def.model,
            messages=messages,
        )

        t0 = time.perf_counter()
        # Since client.chat_completion is synchronous, we use run_in_executor
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, self.client.chat_completion, req)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        result.output_text = response.content
        result.raw_response = response.raw_json
        result.metrics = StepMetrics(
            latency_ms=latency_ms,
            prompt_tokens=response.usage.get("prompt_tokens")
            if response.usage
            else None,
            completion_tokens=response.usage.get("completion_tokens")
            if response.usage
            else None,
            total_tokens=response.usage.get("total_tokens") if response.usage else None,
            model=step_def.model,
            prompt_version=step_def.prompt_version,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        if response.ok:
            result.status = "success"
            out_data = {}
            if len(step_def.outputs) == 1:
                # Basic direct mapping
                out_name = step_def.outputs[0].name
                out_data[out_name] = response.content
                port_outputs[step_def.id][out_name] = response.content
                self.storage.save_port(
                    run_ctx.run_id, step_def.id, out_name, response.content
                )
                if self.event_bus:
                    self.event_bus.publish(
                        port_emitted(
                            run_ctx.run_id, step_def.id, out_name, response.content
                        )
                    )
            elif len(step_def.outputs) > 1:
                # Expect JSON
                try:
                    parsed = json.loads(response.content)
                    if not isinstance(parsed, dict):
                        raise ValueError("Model output not a JSON object")

                    for out_port in step_def.outputs:
                        val = parsed.get(out_port.name, "")
                        # Store in port outputs cache
                        if not isinstance(val, str):
                            val = json.dumps(val)
                        out_data[out_port.name] = val
                        port_outputs[step_def.id][out_port.name] = val
                        self.storage.save_port(
                            run_ctx.run_id, step_def.id, out_port.name, val
                        )
                        if self.event_bus:
                            self.event_bus.publish(
                                port_emitted(
                                    run_ctx.run_id, step_def.id, out_port.name, val
                                )
                            )
                except (json.JSONDecodeError, ValueError) as e:
                    result.status = "error"
                    result.error = (
                        "Multi-output extraction failed "
                        f"(invalid JSON expected by {len(step_def.outputs)} ports): {e}"
                    )
            result.output_ports = out_data
        else:
            result.status = "error"
            result.error = response.error

        return result
