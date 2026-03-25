# Release Notes: Graph Execution Engine (Beta)

## Overview

We are thrilled to announce the Beta release of the **Graph Execution Engine**! Traditionally, our Workflow MVP operated on a strict sequential execution model. While effective for simple pipelines, it struggled with complex scenarios like fan-out parallel processing or resolving multiple upstream dependencies locally.

This release introduces an Opt-In graph-aware runtime that maps explicit input and output ports across your workflow definitions conceptually solving non-linear orchestration dynamically.

## Key Features

- **Topological Execution**: Steps define `depends_on` relationships. The `AsyncGraphRunner` evaluates this topology and executes independent branches concurrently via Thread Pools.
- **Port-Based I/O**: Shift away from monolithic `input_text` string manipulation. Steps can now receive multiple inputs (e.g., `[Document, Context]`) and produce multiple discrete outputs.
- **Visual Node Enrichment**: Flow Canvas natively identifies components containing multiple ports or serving as graph junctions via dedicated `[ Branch ]` and `[ Merge ]` badges.
- **Dynamic Inspector**: Legacy users experience no interruption. The inspector dynamically rebuilds interface elements corresponding to the internal graph state transparently.
- **Backward Compatibility**: A global feature flag gracefully defaults the application to legacy environments when disabled. Existing workflows will not break and can be migrated piece-meal.

## Known Limitations (MVP Scope)

- **Nested Graphs**: Currently, we do not support encapsulating sub-graphs mathematically. All orchestration operates on a single flat 1D canvas hierarchy.
- **Cycles**: Cyclic dependencies are explicitly guarded against during execution plan generation.
- **Visual Spaghetti**: As we enforce a strict 1D Vertical Canvas layout, highly convoluted graphs might become challenging to trace linearly without clicking on nodes to flash their provenance borders.

## Migration Guide

1. Launch the application.
2. At the bottom of the sidebar, toggle **Graph Runtime (Beta)**.
3. Migrate individual Steps iteratively using the Inspector Panel's advanced menu by setting **Execution Model** to `Graph`.
4. Configure explicit Input variables and target their source `Step ID` and `Source Variable Name`.

---

## Alignment Release Update (2026-03-21)

This alignment pass stabilized the planned graph/runtime surfaces without
changing the external MVP behavior contract.

### What was stabilized in this pass

- Canonical graph contract synchronization (join strategy + execution mode).
- Schema v3 migration and persistence roundtrip hardening.
- Runtime graph semantics stability for root inputs, joins, and multi-output.
- Non-technical authoring UX adapter flow (graph-mode inspector paths).
- Attachment-slot authoring path stabilized for step-bound slots.
- Run history hydration integrity repaired for legacy/corrupted payload shapes.
- Wave 7 UI polish: reduced redundant drawer text re-render on unchanged content.
- Inspector attachment slots: **Workflow input** root source in source picker
  (maps to `__input__`), friendly source lines, slot edit form (Apply/Delete),
  and `update_attachment_slot` tests for `accepted_types` normalization and
  `step_id::slot_id` binding-key stability.
- Flow canvas attachment modal: full slot authoring path (add, edit label,
  edit variable name, edit required, edit accepted types, bind/unbind file,
  remove slot) wired through existing controller APIs.

### Verification evidence

- `python -m pytest tests/ui/test_no_regression_smoke.py -q` -> `1 passed`
- `python -m pytest tests/core tests/runtime tests/state tests/ui -q` -> `20 passed`

### Notes

- Active UI surface for graph cards is `ui/flow_canvas.py`; release alignment
  changes were applied on active surfaces (`ui/flow_canvas.py`,
  `ui/inspector_panel.py`, `ui/result_drawer.py`, and controller flows).
