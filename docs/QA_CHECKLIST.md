# QA Checklist — Alignment Baseline & Regression

This checklist is the canonical manual verification set for the alignment release.
Baseline matrix: `docs/plans/alignment-regression-matrix.md`

## 1) Baseline Snapshot (Automated)

- [x] Run `python -m pytest -q`
- [x] Record baseline result in regression matrix
  - Baseline captured: `236 passed in 55.50s`
- [x] Run targeted no-regression smoke for Wave 7
  - `python -m pytest tests/ui/test_no_regression_smoke.py -q` -> `1 passed`
- [x] Run Wave 7 targeted suite
  - `python -m pytest tests/core tests/runtime tests/state tests/ui -q` -> `20 passed`

## 2) Feature Flag Verification

- [ ] Open the application and navigate to the left sidebar.
- [ ] Ensure the **Graph Runtime (Beta)** switch is visible at the bottom of the sidebar.
- [ ] Toggle the switch ON and OFF; verify no crash and no hung UI.
- [ ] Close and reopen the app; verify toggle initializes safely for MVP default state.

## 3) Legacy Regression (Graph Runtime OFF)

- [ ] Ensure **Graph Runtime (Beta)** is OFF.
- [ ] Load a legacy sequential workflow (example: `BA Document Review`).
- [ ] Configure required step inputs/outputs.
- [ ] Attach required files (if any).
- [ ] Click **Run Workflow**.
- [ ] Verify execution path remains legacy sequential runner.
- [ ] Verify run history persists `input_text`/`output_text` without data loss.
- [ ] Verify Cancel stops execution gracefully.

## 4) Graph Execution (Graph Runtime ON)

- [ ] Ensure **Graph Runtime (Beta)** is ON.
- [ ] Generate examples if missing: run `python generate_examples.py`.
- [ ] Load graph workflow example (example: `examples/graph_fanout.json`).
- [ ] Verify cards show graph metadata (graph badges, port counts, topology hints).
- [ ] Select a downstream node and verify upstream dependencies are visually indicated.
- [ ] Run workflow and confirm branch execution + join behavior are stable.
- [ ] Verify Result Drawer maps port-based outputs correctly to downstream consumers.

## 5) Attachment Mapping Flow

- [ ] Create or edit attachment slots for relevant steps.
- [ ] Verify slot identity uses `step_id::slot_id` and survives edit/apply cycles.
- [ ] Bind local files to slots and save workflow.
- [ ] Reload workflow and verify bindings remain intact.
- [ ] Run workflow and verify runtime resolves slot bindings correctly.

## 6) Run History Reload Integrity

- [ ] Open Recent Runs and load a successful graph run.
- [ ] Verify graph result payload (ports/events where applicable) rehydrates without crash.
- [ ] Open a successful legacy run.
- [ ] Verify legacy result payload rehydrates correctly.

## 7) Inspector Render & Authoring UX

- [ ] Open inspector for graph step and verify join strategy options are contract-safe.
- [ ] Verify execution mode rendering is consistent with step-level source-of-truth.
- [ ] Verify source picker displays `Title (step_id)` for graph steps.
- [ ] Verify choosing `-- No source --` persists as empty source selection (not label text).
- [ ] Verify `ROOT_SOURCE_IDS` render as **Workflow input** in picker and source lines.

## 8) Sign-off

- [ ] All sections above completed.
- [ ] Differences vs baseline documented in `docs/plans/alignment-regression-matrix.md`.
- [ ] Any failed check has linked fix task and rerun evidence.
