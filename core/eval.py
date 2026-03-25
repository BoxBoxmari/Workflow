"""
core.eval — Model and prompt comparison logic.

Provides two comparison modes:
  1. Model comparison: same input + same prompt → N models
  2. Prompt comparison: same input + same model → N prompt versions

Each comparison produces a list of StepResult objects for
side-by-side review.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from core.models import (
    ProviderRequest,
    RunContext,
    StepDef,
    StepMetrics,
    StepResult,
    _generate_run_id,
)
from core.prompts import PromptRegistry
from core.provider import WorkbenchClient
from core.storage import StorageManager


def compare_models(
    client: WorkbenchClient,
    prompt_registry: PromptRegistry,
    storage: StorageManager,
    step_def: StepDef,
    input_text: str,
    models: list[str],
    variables: Optional[dict[str, str]] = None,
) -> tuple[RunContext, list[StepResult]]:
    """
    Run the same step with the same prompt against multiple models.

    Returns (RunContext, list of StepResult — one per model).
    """
    variables = variables or {}
    variables["input"] = input_text

    run_ctx = RunContext(
        run_id=_generate_run_id(),
        workflow_id=f"compare_models_{step_def.id}",
        workflow_name=f"Model Comparison: {step_def.name}",
        started_at=datetime.now(timezone.utc).isoformat(),
        status="running",
        run_type="comparison",
    )
    storage.create_run(run_ctx)

    results: list[StepResult] = []

    for model in models:
        result = _run_single_step(
            client=client,
            prompt_registry=prompt_registry,
            step_name=step_def.name,
            prompt_version=step_def.prompt_version,
            model=model,
            variables=variables,
        )
        results.append(result)
        storage.save_step(run_ctx.run_id, result)
        run_ctx.step_results.append(result.step_id)

    run_ctx.status = (
        "success" if all(r.status == "success" for r in results) else "error"
    )
    run_ctx.finished_at = datetime.now(timezone.utc).isoformat()
    storage.save_run(run_ctx)
    storage.update_index(run_ctx)

    return run_ctx, results


def compare_prompts(
    client: WorkbenchClient,
    prompt_registry: PromptRegistry,
    storage: StorageManager,
    step_def: StepDef,
    input_text: str,
    prompt_versions: list[str],
    variables: Optional[dict[str, str]] = None,
) -> tuple[RunContext, list[StepResult]]:
    """
    Run the same step with the same model using multiple prompt versions.

    Returns (RunContext, list of StepResult — one per prompt version).
    """
    variables = variables or {}
    variables["input"] = input_text

    run_ctx = RunContext(
        run_id=_generate_run_id(),
        workflow_id=f"compare_prompts_{step_def.id}",
        workflow_name=f"Prompt Comparison: {step_def.name}",
        started_at=datetime.now(timezone.utc).isoformat(),
        status="running",
        run_type="comparison",
    )
    storage.create_run(run_ctx)

    results: list[StepResult] = []

    for version in prompt_versions:
        result = _run_single_step(
            client=client,
            prompt_registry=prompt_registry,
            step_name=step_def.name,
            prompt_version=version,
            model=step_def.model,
            variables=variables,
        )
        results.append(result)
        storage.save_step(run_ctx.run_id, result)
        run_ctx.step_results.append(result.step_id)

    run_ctx.status = (
        "success" if all(r.status == "success" for r in results) else "error"
    )
    run_ctx.finished_at = datetime.now(timezone.utc).isoformat()
    storage.save_run(run_ctx)
    storage.update_index(run_ctx)

    return run_ctx, results


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _run_single_step(
    client: WorkbenchClient,
    prompt_registry: PromptRegistry,
    step_name: str,
    prompt_version: str,
    model: str,
    variables: dict[str, str],
) -> StepResult:
    """Execute a single step with the given model and prompt version."""
    result = StepResult(
        step_id=f"{step_name}_{model}_v{prompt_version}",
        step_name=step_name,
        input_text=variables.get("input", ""),
        status="running",
    )

    # Render prompt
    try:
        messages = prompt_registry.render(step_name, prompt_version, variables)
        result.rendered_prompt = messages
    except FileNotFoundError as e:
        result.status = "error"
        result.error = str(e)
        return result

    # Call provider
    req = ProviderRequest(model=model, messages=messages)
    t0 = time.perf_counter()
    response = client.chat_completion(req)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    result.output_text = response.content
    result.raw_response = response.raw_json
    result.metrics = StepMetrics(
        latency_ms=latency_ms,
        prompt_tokens=response.usage.get("prompt_tokens") if response.usage else None,
        completion_tokens=response.usage.get("completion_tokens")
        if response.usage
        else None,
        total_tokens=response.usage.get("total_tokens") if response.usage else None,
        model=model,
        prompt_version=prompt_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    if response.ok:
        result.status = "success"
    else:
        result.status = "error"
        result.error = response.error

    return result
