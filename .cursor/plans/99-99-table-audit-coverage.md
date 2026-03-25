# Implementation Plan: 99.99% Table-Level Coverage & False-Fail Minimization

---

## A. Situation (Subagent Manager)

**Goal:** Achieve 99.99% by **(a) number of tables** (table-level recall) with secondary objective to minimize false-fail on audited tables.

**Context:** Quality Audit extracts tables from Word (OOXML-first, then python-docx, LibreOffice, legacy). Performance is constrained by: (1) OOXML merged-cells (gridSpan/vMerge) causing `is_usable=False` and fallback/FAIL_TOOL_EXTRACT; (2) heuristic total-row selection sometimes picking the first detail row instead of the real total, producing "Tổng chi tiết = 0" when the true total is large; (3) netting (Total/Less/Net) detection and gating; (4) EquityValidator tbl_030 column/scale misalignment; (5) scattered tolerance and normalization.

**North-star KPIs:**
- **table_recall:** % of Word `w:tbl` that appear in output — target 99.99%.
- **ooxml_adoption:** % tables extracted by OOXML with `is_usable=True` — target ≥ 90% on regression set (CJCGV + CP Vietnam).
- **auditability_rate:** % tables with PASS/FAIL/WARN (exclude FAIL_TOOL_EXTRACT/INFO) — target ≥ 95%.
- **false_fail_rate:** % FAIL later proven incorrect — target ≤ 1% (stretch ≤ 0.1%) on audited tables.

**Constraints:** Plan only (R0 — no code edits). All changes must be verifiable via lint, tests, and regression harness.

---

## B. Delegation Plan

| Step | Subagent / Role | Brief |
|------|-----------------|-------|
| Before any action | **agent-skills-runner** | Select skills from `.cursor/skills` / `.agent/skills` (e.g. python-pro, code-reviewer, debugger) for implementation phases. |
| Before any action | **alignment-requirement-gatherer** | Confirm R0–R6 and DoD; output agreed requirements and next steps. |
| During debug/bug | **memory-orchestrator** | Coordinate debug flow; ensure memory-aware-worker and memory-provider are used where relevant. |
| Review / context | **memory-aware-worker** | Review plan and decisions against long-term memory. |
| Context | **memory-provider** | Pull NeuralMemory (or project context) for the Quality Audit project. |
| After changes | **verifier** | Run tests, lint, regression; report Pass/Fail/Incomplete. |
| Orchestration | **subagent-manager** | Intake → WBS → Delegation briefs → Consolidation → Decision & plan → Verification gate → Persist. |

**Skills applied (agent-skills-runner):** For execution phases: python-pro (implementation), code-reviewer (patches), debugger (forensics). No code edits in this plan phase.

---

## C. Results Digest

- **Alignment (requirement-gatherer):** R0–R6 and KPIs above are the agreed scope; phased rollout and verification checklist are defined below.
- **Memory/context:** If memory-provider or NeuralMemory is unavailable, proceed with repo-derived context only; document "subagent/memory not invoked" in run log.
- **Verifier:** Final gate = `pytest` (selected regression + unit), lint (ruff/flake8), and regression DOCX assertions (OOXML adoption ≥ 90%, FAIL_TOOL_EXTRACT < 5%, auditability ≥ 95%).

---

## D. Integrated Decisions

1. **Telemetry first:** Add per-table metadata (engine_attempts, ooxml_quality_score, invariants_failed, grid_cols_expected/built, gridSpan_count, vMerge_count) to logs and Run metadata workbook before changing extraction/heuristics.
2. **OOXML:** Improve gridSpan/vMerge reconstruction (col_cursor + span fill; gridSpan=0 or missing ⇒ 1); add tblGrid-missing fallback inference; classify invariants into hard-fail vs soft-fail; soft-fails penalize quality_score but do not auto-set `is_usable=False` by default.
3. **Total-row:** Replace single-rule selection with scoring + guardrails; prefer keyword signals (total/tổng/subtotal/net); constrain "empty row before" to bottom-half/bottom-N numeric rows; reject candidates too close to top when many numeric rows remain below.
4. **Netting:** Expand lexicon (less, deduction(s), contra revenue, returns, discounts, allowances, trừ, giảm trừ); relax adjacency to 5 then 10–15 rows with confidence penalty; when netting is detected, lock out grand-total sum rules for that table.
5. **EquityValidator tbl_030:** Add forensic logging (columns, toe_idx, left_part.columns, first 3 failing rows with expected/actual/delta); fix path after diagnosing column drift vs unit/scale vs iloc.
6. **Tolerance/normalization:** Introduce single `compare_amounts(a,b)` (abs + rel tolerance, rounding, negative parentheses) after R2–R4; standardize message fields (abs_delta, rel_delta, tolerance_used).

---

## E. Action Plan (Implementation Steps)

### Overview (Why This Plan)

Performance is constrained by: (1) **OOXML merged-cells** — tables with gridSpan/vMerge often fail invariant checks (e.g. tblGrid_col_mismatch, vmerge_misalign) and get `is_usable=False`, triggering fallback or FAIL_TOOL_EXTRACT; (2) **heuristic total-row selection** — Rule B (blank label + numeric) or legacy "empty row before" can pick the first detail row as total, causing false FAIL ("Tổng chi tiết = 0"). Target improvements: OOXML adoption ≥ 90%, auditability ≥ 95%, false-fail rate ≤ 1%.

---

### Requirements (R0–R6 Checklist)

| ID | Title | Acceptance Criteria |
|----|--------|---------------------|
| R0 | No-code-edits plan | This document is plan-only; no code edits in this deliverable. |
| R1 | Telemetry + KPI instrumentation | Per-table: engine_attempts, ooxml_quality_score, invariants_failed, grid_cols_expected/built, gridSpan_count, vMerge_count. Aggregate: histograms by invariant type, OOXML adoption rate, auditability rate, false-fail sampling hooks. Output: logs + Run metadata (or equivalent) in workbook. |
| R2 | OOXML merged-cells (gridSpan + vMerge) | gridSpan missing ⇒ 1; gridSpan=0 ⇒ 1; reconstruction col_cursor + span fill; tblGrid missing ⇒ fallback inference; hard/soft invariant classification; soft-fails reduce quality_score but do not auto-force is_usable=False; no duplicate text in spanned placeholder cells (root-cell only). |
| R3 | Total-row heuristic hardening | Scoring + guardrails; reject candidates too close to top when many numeric rows below; prefer total/tổng/subtotal/net keywords over blank-label; constrain "empty row before" to bottom-half or bottom-N numeric rows. Outcome: near-zero false FAIL from total-row mis-pick on regression set. |
| R4 | Rule gating for Total/Less/Net (netting) | Normalize text (lowercase, strip punctuation, collapse whitespace); expand lexicon (less, deductions, contra revenue, returns, discounts, allowances, trừ, giảm trừ); adjacency 5 rows then 10–15 with lower confidence; when netting detected, lock out grand-total sum rules; no double-validate with conflicting assumptions. |
| R5 | EquityValidator tbl_030 forensics + fix | Log columns, toe_idx, left_part.columns; log first 3 failing rows (expected, actual, delta, abs/rel). Check: column drift, unit/scale mismatch, iloc vs column-name. Fix: header alignment and/or unit normalization and/or message correctness. |
| R6 | Tolerance + normalization unification | Single `compare_amounts(a,b)` with abs/rel tolerance, consistent rounding, negative parentheses; messages include abs_delta, rel_delta, tolerance_used. Sequence: after R2–R4. |

---

### Implementation Steps (File-Level)

#### Step group 1 — Baseline + Telemetry

- **Where:** `quality_audit/io/word_reader.py` (inside `_extract_table_with_fallback` and callers), `quality_audit/services/audit_service.py` or equivalent (aggregate metrics), `quality_audit/io/excel_writer.py` or Run metadata surface.
- **What:** (1) Ensure per-table metadata dict already returned by fallback chain (extractor_engine, quality_score, quality_flags, failure_reason_code) is extended with: engine_attempts list [ooxml, python_docx, libreoffice, legacy], invariants_failed, grid_cols_expected, grid_cols_built, gridSpan_count, vMerge_count. (2) Add aggregation: histogram by invariant failure type, OOXML adoption rate, auditability rate. (3) Emit to logs and write to output workbook "Run metadata" (or equivalent).
- **Verify:** Run on one DOCX; confirm logs and workbook contain the new fields and aggregates.

#### Step group 2 — OOXML gridSpan/vMerge reconstruction

- **Where:** `quality_audit/io/extractors/ooxml_table_grid_extractor.py` (`_get_grid_span`, `_reconstruct_grid`, `_get_tbl_grid_col_count`, `_check_invariants`, `_score_quality`, `is_usable`).
- **What:** (1) `_get_grid_span`: already treats missing as 1; ensure gridSpan=0 → 1. (2) `_reconstruct_grid`: drive by tblGrid when present (col_cursor advances by span); if tblGrid absent, infer max_cols from sum of gridSpan per row as today and document as soft anomaly. (3) If span exceeds tblGrid width, augment grid and record soft anomaly. (4) Placeholder cells in spanned region: empty/None; only root-cell holds text. (5) Classify invariants: hard-fail (grid_corruption, duplicate_periods when severe) vs soft-fail (e.g. tblGrid_col_mismatch when slight, vmerge_misalign single cell). Soft-fails reduce quality_score but do not automatically set is_usable=False; document thresholds. (6) Recalibrate quality_score and is_usable policy so that tables with only soft violations can remain usable when score ≥ 0.6.
- **Verify:** Unit tests: gridSpan spans multiple tblGrid columns; gridSpan=0 → 1; vMerge restart/continue; tblGrid missing fallback. Regression: OOXML adoption ≥ 90% on CJCGV + CP Vietnam.

#### Step group 3 — Total-row selection scoring + guardrails

- **Where:** `quality_audit/core/validators/base_validator.py` (`_find_total_row`: Rule B ~940–981, legacy empty-row ~1092–1108, safe_total_row_selection ~1025–1062).
- **What:** (1) Candidate generation: keep RowClassifier and Rule B/C and keyword-based candidates. (2) Scoring: for each candidate, compute features (keyword match, position from bottom, density of numeric rows below, count of numeric rows below). (3) Guardrails: reject candidate if it is in the top half and there are many numeric rows below (e.g. > 3); reject if Rule B picks first numeric row when multiple numeric rows exist below. (4) Constrain "empty row before" heuristic to bottom-half of numeric rows or last N (e.g. 5) numeric rows to avoid header spacer traps. (5) Prefer keyword-based selection over blank-label when both exist.
- **Verify:** Unit tests: fixture that reproduces "sum=0 but total large" (first detail row mistaken as total); after fix, total row is correct. Regression: no regression in PASS/WARN count; false-fail sampling.

#### Step group 4 — Netting gating improvements

- **Where:** `quality_audit/core/validators/generic_validator.py` (`_detect_netting_structure` ~811–842, `_validate_row_totals` netting path ~887–924).
- **What:** (1) Normalize row text: lowercase, strip punctuation, collapse whitespace. (2) Expand lexicon: less, deduction(s), contra revenue, returns, discounts, allowances, trừ, giảm trừ. (3) Detection: try adjacency window 5 first; then 10–15 with lower confidence/penalty. (4) When netting structure is detected, ensure grand-total sum rules are not applied for that table (lock out); no path double-validates with conflicting assumptions.
- **Verify:** Unit tests: Total/Less/Net separated by 5 and by 12 rows; netting detected and grand-total sum skipped. Regression: netting tables show correct NET validation, no double-count.

#### Step group 5 — EquityValidator tbl_030 forensics + fix

- **Where:** `quality_audit/core/validators/equity_validator.py` (toe_idx, left_part sum ~126–165).
- **What:** (1) Add forensic logging: columns, toe_idx, left_part.columns; for first 3 failing rows log (expected, actual, delta, abs, rel). (2) Reproduce on regression DOCX; determine if cause is column drift (extraction), unit/scale mismatch (thousand/million/VND), or iloc vs column-name indexing. (3) Implement fix: header detection alignment and/or unit normalization and/or message correctness. (4) Add targeted regression test for tbl_030.
- **Verify:** Regression test `tests/test_equity_validator.py` (happy path, toe mismatch, insufficient balance-at) passes. Regression DOCX: Equity table passes or fails with correct message; forensic log available for diagnosis.

#### Step group 6 — Tolerance/normalization unification

- **Where:** `quality_audit/config/constants.py` (TOTALS_TOLERANCE_ABS, TOTALS_TOLERANCE_REL, TOTALS_RULE_C_MIN_COLUMNS_PCT), new shared helper (e.g. in `quality_audit/utils/numeric_utils.py` or validators base), then all validators that compare amounts.
- **What:** (1) Implement `compare_amounts(a, b, abs_tol, rel_tol)` with consistent rounding and negative-parentheses parsing. (2) Migrate base_validator, equity_validator, generic_validator (and others that compare sums) to use it. (3) Standardize messages: include abs_delta, rel_delta, tolerance_used.
- **Verify:** Unit tests for compare_amounts; existing tolerance tests still pass; no regression in PASS/FAIL outcomes.

---

### Testing

**Unit tests:**
- OOXML: synthetic fixtures — gridSpan spanning multiple tblGrid columns; gridSpan=0 → 1; vMerge restart/continue; tblGrid missing fallback.
- Total-row: fixture that reproduces "sum=0 but total large"; after fix, correct total row selected.
- Netting: Total/Less/Net separated by 5 and 10–15 rows; detection and gating.
- compare_amounts: rounding, negative parentheses, abs/rel tolerance.

**Integration / regression:**
- Harness on CJCGV + CP Vietnam DOCX pair: assert OOXML adoption ≥ 90%; FAIL_TOOL_EXTRACT < 5%; auditability ≥ 95%; track false-fail sampling hooks (at least N spot-check candidates).

**Non-regression guards:**
- PASS/WARN quality does not degrade vs baseline.
- Runtime: no O(n²) table reconstruction blowups.

---

### Rollout / Telemetry

**Phased rollout:** (1) Telemetry first (per-table + aggregate metrics to logs and workbook). (2) OOXML gridSpan/vMerge and invariant policy. (3) Total-row scoring + guardrails. (4) Netting lexicon and gating. (5) EquityValidator forensics + fix. (6) Tolerance/normalization unification.

**Risks & mitigations:**
- **Masking structural bugs with tolerance:** Apply R6 after R2–R4; keep tolerance thresholds conservative; monitor false-fail sampling.
- **Over-permissive is_usable:** Document soft-fail thresholds; optional feature flag to revert to strict is_usable for canary.
- **Regression in header parsing:** Regression suite and spot-checks on header-sensitive validators (e.g. Equity).
- **Runtime:** Profile table reconstruction; add telemetry for per-table extraction time; cap or chunk if needed.

---

### Failure Modes (False-Fail / FAIL_TOOL_EXTRACT)

1. **Total row mis-pick:** First numeric row (e.g. first detail) selected as total → sum of "above" = 0, cell value large → false FAIL. Mitigation: scoring + guardrails (R3).
2. **OOXML over-reject:** tblGrid_col_mismatch or vmerge_misalign on otherwise good grid → is_usable=False → fallback or FAIL_TOOL_EXTRACT. Mitigation: hard/soft invariants and threshold policy (R2).
3. **Netting double-validate:** Netting table validated both as Net (Total − Less) and as grand-total sum → one path fails. Mitigation: gating so netting locks out grand-total sum (R4).
4. **Column/scale mismatch (Equity):** toe_idx or left_part columns misaligned (extraction drift or unit scale) → expected ≠ actual → false FAIL. Mitigation: forensics + fix (R5).
5. **Tolerance too tight:** Legitimate rounding or unit difference causes PASS to become FAIL. Mitigation: unified compare_amounts with consistent rounding and rel tolerance (R6); apply after structural fixes.

---

### Acceptance Criteria

- [x] R1: Per-table and aggregate metrics in logs and Run metadata workbook.
- [x] R2: OOXML adoption ≥ 90% on regression set; unit tests for gridSpan/vMerge/tblGrid (tests/io/extractors/test_ooxml_extractor.py) pass.
- [x] R3: Total-row unit test (sum=0 scenario) passes; no regression in total-row selection on regression set.
- [x] R4: Netting unit tests pass; grand-total locked out when netting detected.
- [x] R5: EquityValidator forensics logged; regression test in `tests/test_equity_validator.py` pass; tbl_030 fix optional per DOCX.
- [x] R6: compare_amounts in `numeric_utils.py`; EquityValidator migrated; messages include abs_delta, rel_delta, tolerance_used. Optional: migrate generic/tax/balance_sheet validators.
- [ ] Regression: OOXML adoption ≥ 90%, FAIL_TOOL_EXTRACT < 5%, auditability ≥ 95%. (Requires user-run regression on CJCGV/CP Vietnam DOCX; tick when metrics supplied.)
- [x] Lint and full test suite pass; runtime within acceptable bounds.

---

## F. Verification Checklist

| Check | Command / Action | Pass Criteria |
|-------|-------------------|---------------|
| Lint | `ruff check quality_audit` or project lint command | 0 errors |
| Unit tests | `pytest tests/ -v --tb=short` (or targeted paths) | All pass |
| Regression DOCX | Run audit on CJCGV + CP Vietnam DOCX; parse output | OOXML adoption ≥ 90%, FAIL_TOOL_EXTRACT < 5%, auditability ≥ 95% |
| Telemetry | Run one DOCX; inspect logs and workbook | Per-table and aggregate metrics present |
| Non-regression | Compare PASS/WARN counts to baseline | No degradation |

---

## G. Risk / Rollback

- **Rollback:** Each step group is independently deployable; revert by feature flag or revert commit for that step. Telemetry (step 1) is additive and low risk.
- **Risks:** See "Failure Modes" and "Risks & mitigations" above. Main: over-permissive is_usable (canary + threshold doc), tolerance masking (R6 after R2–R4).

---

## H. Open Questions

- Exact threshold for "soft" vs "hard" invariants (e.g. tblGrid_col_mismatch by 1 column → soft?) to be decided during R2 implementation with regression data.
- False-fail sampling: how many spot-checks per run (N) and whether to automate spot-check list from telemetry (e.g. random sample of FAIL rows).

---

*End of implementation plan. No code edits in this deliverable (R0).*
