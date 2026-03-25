# Plan: Audit observability, tbl_031, soffice, legacy extractor, role/evidence

## WBS (Work Breakdown Structure)

| ID | Workstream | Owner | Output | Verify |
|----|------------|-------|--------|--------|
| W1 | Log table_id in column_roles | Code | table_context["table_id"] in audit_service, passed to validators | Log line contains table_id |
| W2 | Observability: Validated vs Skipped | Code | validation_status in log + observability_payload; SKIPPED_* → Skipped | test_footer_artifacts, test observability sheet |
| W3 | tbl_031 (CP Vietnam) manual check | Human | Decision: real equity table vs footer; if real, fix skip | Manual + regression test |
| W4 | Soffice / RenderFirst env | Docs/Script | Install/verify soffice; when RenderFirst used | Doc or script run |
| W5 | Legacy extractor quality_score=0 | Analysis | When/why 0; fallback improvements | Doc + optional code |
| W6 | Role/evidence for % and special columns | Analysis | Avoid NO_EVIDENCE when all cols excluded | Doc + optional role fix |

## Decisions

- **D1:** table_id injected in table_context in `audit_service._validate_single_table` and passed to validators so column_roles logs show it.
- **D2:** validation_status = "Skipped" when rule_id in (SKIPPED_FOOTER_SIGNATURE, SKIPPED_NO_NUMERIC_EVIDENCE), else "Validated"; used in logger and observability_payload.
- **D3:** Report sheet name is "Run metadata" (excel_writer); tests use `telemetry=service.telemetry` and `wb["Run metadata"]`.

## Action Plan (prioritized)

| Pri | Area | Change | Rationale | Executor |
|-----|------|--------|-----------|----------|
| P0 | audit_service | table_context with table_id; validation_status | Tasks 1–2 | Done |
| P0 | test_audit_service_observability | telemetry + "Run metadata" | Fix test | Done |
| P1 | Verify | Run test_audit_service_observability + test_audit_service_integration | Gate | Verifier |
| P2 | Manual | tbl_031 CP Vietnam: real table vs footer | Task 3 | Human |
| P2 | Doc/script | Soffice + RenderFirst | Task 4 | Docs |
| P3 | Analysis | quality_score=0 legacy extractor | Task 5 | Analysis |
| P3 | Analysis | Role/evidence % and special numeric | Task 6 | Analysis |

## Verification Checklist

- **Commands:**  
  `python -m pytest tests/test_audit_service_observability_and_skipped.py -v`  
  `python -m pytest tests/test_audit_service_integration.py -v`  
  `ruff check quality_audit/services/audit_service.py tests/test_audit_service_observability_and_skipped.py`
- **Expected:** All tests pass; ruff 0 errors.
- **Edge cases:** Footer tables show "Skipped" in log and observability; validated tables show "Validated"; telemetry sheet "Run metadata" present when telemetry provided.

## Risk / Rollback

- **Risks:** Integration tests may be slow (timeout in CI); tbl_031 fix may require skip-rule change.
- **Rollback:** Revert commits in audit_service.py and test file; observability/telemetry sheet name is backward compatible.
- **Monitoring:** Logs and Run metadata sheet for validation_status.

## Context-fix slice (column_roles table_id/heading)

- **Problem:** `infer_column_roles` was always called with `context={}`, so logs lacked `table_id`/`heading`.
- **Solution:** Base validator exposes `_get_roles_context()` from `_current_table_context`; each concrete validator sets/clears `_current_table_context` in validate(); all five call sites in base_validator pass `context=roles_ctx` into `infer_column_roles` / `infer_column_roles_and_exclude`.
- **Files:** base_validator.py (5 call sites), generic/tax/balance_sheet/cash_flow/income_statement/equity_validator.py (set + finally clear).
- **Verification (done):** Ruff on all modified validators: pass. Pytest: test_audit_service_observability_and_skipped + test_audit_service_integration — 7 passed.

## Open questions

- tbl_031: need CP Vietnam sample to confirm table type.
- Soffice: path/version on Windows for RenderFirst.
- quality_score=0: which extractor and which inputs produce 0 (need codebase grep).
