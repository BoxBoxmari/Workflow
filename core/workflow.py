"""
core.workflow — Sequential step runner.

Executes a WorkflowDef step-by-step, calling the provider for each,
persisting results, and supporting real-time progress callbacks for
the UI layer.  Runs on a background thread to avoid blocking tkinter.
"""

from __future__ import annotations

import logging
import threading
import time
import json
from datetime import datetime, timezone
from typing import Callable, Optional, Any

from core.events import (
    EventBus,
    run_finished,
    run_failed,
    step_finished,
    step_started,
    run_started,
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

log = logging.getLogger("workbench.core.workflow")


class WorkflowRunner:
    """Runs a sequential workflow against the Workbench API."""

    def __init__(
        self,
        client: WorkbenchClient,
        prompt_registry: PromptRegistry,
        storage: StorageManager,
        event_bus: Optional[EventBus] = None,
    ):
        self.client = client
        self.prompts = prompt_registry
        self.storage = storage
        self.event_bus = event_bus  # optional — None = no events published
        self._cancel_flag = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
        Execute a workflow synchronously (call from a background thread).


        Parameters
        ----------
        workflow_def : WorkflowDef
            The workflow definition to execute.
        initial_input : str
            Text or ingested content to feed into the first step (legacy or default input).
        initial_variables : dict
            Supplemental variables (e.g., from attachments) to prepopulate context.
        on_step_start : callback(step_def, step_index, total_steps)
            Called before each step starts.
        on_step_complete : callback(step_result, step_index, total_steps)
            Called after each step completes.
        on_run_complete : callback(run_context)
            Called when the entire run finishes.

        Returns
        -------
        RunContext with final status.
        """
        self._cancel_flag.clear()

        # Initialize run context
        run_ctx = RunContext(
            run_id=_generate_run_id(),
            workflow_id=workflow_def.id,
            workflow_name=workflow_def.name,
            workflow_snapshot=workflow_def.to_dict(),
            started_at=datetime.now(timezone.utc).isoformat(),
            status="running",
            run_type="standard",
        )

        # Set initial input variable
        run_ctx.variables["input"] = initial_input
        if initial_variables:
            for k, v in initial_variables.items():
                run_ctx.variables[k] = v

        # Create run directory
        self.storage.create_run(run_ctx)
        self.storage.append_event(
            run_ctx.run_id,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "run_started",
                "message": f"Workflow '{workflow_def.name}' started",
            },
        )
        if on_run_start:
            on_run_start(run_ctx)
        if self.event_bus:
            self.event_bus.publish(run_started(run_ctx.run_id, workflow_def.id))

        enabled_steps = [s for s in workflow_def.steps if s.enabled]
        total = len(enabled_steps)
        # In-memory output cache for upstream injection (step_id → output_text)
        step_outputs: dict[str, str] = {}
        attachment_meta = attachment_meta or {}

        try:
            for idx, step_def in enumerate(enabled_steps):
                if self._cancel_flag.is_set():
                    run_ctx.status = "cancelled"
                    self.storage.append_event(
                        run_ctx.run_id,
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "event_type": "run_cancelled",
                            "message": "Run cancelled by user",
                        },
                    )
                    break

                if on_step_start:
                    on_step_start(step_def, idx, total)
                if self.event_bus:
                    self.event_bus.publish(
                        step_started(run_ctx.run_id, step_def.id, idx, total)
                    )

                step_result = self._execute_step(
                    step_def,
                    run_ctx,
                    enabled_steps,
                    step_outputs,
                    attachment_meta,
                )
                run_ctx.step_results.append(step_def.id)

                # Persist step
                self.storage.save_step(run_ctx.run_id, step_result)
                self.storage.append_event(
                    run_ctx.run_id,
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event_type": "step_completed",
                        "step_id": step_def.id,
                        "status": step_result.status,
                        "latency_ms": step_result.metrics.latency_ms,
                    },
                )

                if on_step_complete:
                    on_step_complete(step_result, idx, total)
                if self.event_bus:
                    self.event_bus.publish(
                        step_finished(
                            run_ctx.run_id,
                            step_result.step_id,
                            step_result.status,
                            idx,
                            total,
                            result=step_result,
                        )
                    )

                # Propagate output to context variables (Gap 1: auto-mapping)
                if step_result.status == "success":
                    output_var = (
                        step_def.output_mapping or step_def.get_auto_output_mapping()
                    )
                    run_ctx.variables[output_var] = step_result.output_text
                    # Also cache in-memory for upstream resolution
                    step_outputs[step_def.id] = step_result.output_text
                else:
                    # On step error: record and stop workflow
                    run_ctx.status = "error"
                    run_ctx.error = (
                        f"Step '{step_def.name}' failed: {step_result.error}"
                    )
                    break

            if run_ctx.status == "running":
                run_ctx.status = "success"

        except Exception as e:
            run_ctx.status = "error"
            run_ctx.error = str(e)
            self.storage.append_event(
                run_ctx.run_id,
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event_type": "run_error",
                    "message": str(e),
                },
            )

        # Finalize
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
            else:
                self.event_bus.publish(run_finished(run_ctx.run_id, run_ctx.status))

        return run_ctx

    def cancel(self) -> None:
        """Signal the runner to stop after the current step."""
        self._cancel_flag.set()

    def run_async(
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
        """Start the workflow on a background thread. Returns the thread."""
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

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _execute_step(
        self,
        step_def: StepDef,
        run_ctx: RunContext,
        enabled_steps: list[StepDef],
        step_outputs: dict[str, str],  # in-memory: step_id → output_text
        attachment_meta: dict[str, dict[str, Any]],
    ) -> StepResult:
        """Execute a single workflow step."""
        result = StepResult(
            step_id=step_def.id,
            step_name=step_def.name,
            status="running",
        )

        # --- Resolve input variable (Gap 1: auto-mapping) ---
        input_var = step_def.input_mapping or None
        upstream_output = ""

        step_idx = next(
            (i for i, s in enumerate(enabled_steps) if s.id == step_def.id), None
        )
        prev_step = enabled_steps[step_idx - 1] if step_idx and step_idx > 0 else None

        if not input_var:
            # Auto-generate: match previous step's auto-output key
            input_var = step_def.get_auto_input_mapping(prev_step)

        # Resolve upstream_output for no-code inject (Gap 2)
        if step_def.depends_on:
            # Explicit dependencies: use first available dep output
            for dep_id in step_def.depends_on:
                if dep_id in step_outputs:
                    upstream_output = step_outputs[dep_id]
                    break
        elif prev_step:
            # Sequential workflow fallback
            upstream_output = step_outputs.get(prev_step.id, "")

        # Resolve input_text from run_ctx variables (legacy) or upstream cache
        input_text = run_ctx.variables.get(input_var, upstream_output)
        result.input_text = input_text
        emitted_attachment_vars: set[str] = set()
        if (
            input_var
            and input_var in attachment_meta
            and isinstance(input_text, str)
            and input_text.strip()
        ):
            meta = attachment_meta[input_var]
            consumed_event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "attachment_consumed_by_step",
                "run_id": run_ctx.run_id,
                "step_id": step_def.id,
                "variable_name": input_var,
                "source_file_sha256": meta.get("sha256", ""),
                "slot_id": meta.get("slot_id"),
            }
            self.storage.append_event(run_ctx.run_id, consumed_event)
            if self.event_bus:
                self.event_bus.publish(
                    attachment_consumed_by_step(
                        run_id=run_ctx.run_id,
                        step_id=step_def.id,
                        variable_name=input_var,
                        source_file_sha256=meta.get("sha256", ""),
                        slot_id=meta.get("slot_id"),
                    )
                )
            emitted_attachment_vars.add(input_var)

        # --- Render prompt (Gap 2: no-code path vs legacy) ---
        try:
            if step_def.role_text or step_def.task_text:
                # No-code path: assemble from role + task, auto-inject upstream
                messages = self.prompts.render_from_parts(
                    role_text=step_def.role_text,
                    task_text=step_def.task_text,
                    upstream_output=upstream_output or input_text,
                    extra_variables={**run_ctx.variables},
                )
            else:
                # Legacy path: render from .txt file on disk
                messages = self.prompts.render(
                    step_def.name,
                    step_def.prompt_version,
                    {**run_ctx.variables, "input": input_text},
                )
            result.rendered_prompt = messages
            rendered_blob = json.dumps(messages, ensure_ascii=False)
            for variable_name, meta in attachment_meta.items():
                if variable_name in emitted_attachment_vars:
                    continue
                variable_value = run_ctx.variables.get(variable_name)
                if (
                    isinstance(variable_value, str)
                    and variable_value.strip()
                    and variable_value in rendered_blob
                ):
                    consumed_event = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event_type": "attachment_consumed_by_step",
                        "run_id": run_ctx.run_id,
                        "step_id": step_def.id,
                        "variable_name": variable_name,
                        "source_file_sha256": meta.get("sha256", ""),
                        "slot_id": meta.get("slot_id"),
                    }
                    self.storage.append_event(run_ctx.run_id, consumed_event)
                    if self.event_bus:
                        self.event_bus.publish(
                            attachment_consumed_by_step(
                                run_id=run_ctx.run_id,
                                step_id=step_def.id,
                                variable_name=variable_name,
                                source_file_sha256=meta.get("sha256", ""),
                                slot_id=meta.get("slot_id"),
                            )
                        )
                    emitted_attachment_vars.add(variable_name)
        except FileNotFoundError as e:
            result.status = "error"
            result.error = str(e)
            return result

        # Call provider
        req = ProviderRequest(
            model=step_def.model,
            messages=messages,
        )

        t0 = time.perf_counter()
        response = self.client.chat_completion(req)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # Populate result
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
        else:
            result.status = "error"
            result.error = response.error

        return result
