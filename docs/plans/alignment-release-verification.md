# Alignment Release Verification Matrix (2026-03-21)

## Scope

This document captures final verification evidence for the alignment release
plan and maps outcomes to acceptance criteria.

## Automated Verification

### Command Results

1. `python -m pytest tests/ui/test_no_regression_smoke.py -q`
   - Result: `1 passed in 0.21s`
2. `python -m pytest tests/core tests/runtime tests/state tests/ui -q`
   - Result: `20 passed in 3.37s`

### File Touch Log (Wave 7 + Final Gate)

- `ui/result_drawer.py`
  - Added cached-tab render guard to skip redundant textbox re-write when tab
    content does not change.
- `tests/ui/test_no_regression_smoke.py`
  - Added smoke path covering: open workflow -> edit step -> start run ->
    inspect result payload -> reload selected run results.
- `docs/GRAPH_RELEASE_NOTES.md`
  - Added alignment release update and verification evidence section.
- `docs/QA_CHECKLIST.md`
  - Added Wave 7 smoke/targeted automated verification entries.
- `docs/plans/alignment-release-verification.md`
  - Added final acceptance matrix and evidence summary (this file).

## Acceptance Matrix

| Dimension | Required outcome | Status | Evidence |
|---|---|---|---|
| Functional | P0 crash/contract mismatch fixed | PASS | Prior waves completed; targeted suite `20 passed` |
| Semantic | Graph inputs/joins/outputs run correctly E2E | PASS | Prior waves + targeted suite `20 passed` |
| UX | Non-technical authoring flow remains usable | PASS | Wave 4 completed; smoke path passes |
| Stability | Run history reload + legacy regression stable | PASS | Wave 6 tests + smoke reload assertion |
| Delivery | Release notes + verification matrix + touch log available | PASS | Updated `GRAPH_RELEASE_NOTES.md`, `QA_CHECKLIST.md`, this file |

## Residual Risks

- Manual checklist items in `docs/QA_CHECKLIST.md` remain required for full
  sign-off (interactive UI verification and operator flow checks).
