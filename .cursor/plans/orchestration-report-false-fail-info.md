# Báo cáo điều phối (Subagent Manager) — False FAIL / False INFO

## A) Situation

- **Goal:** Giảm false FAIL và false INFO khi extract đúng nhưng validate/routing sai (GenericTableValidator/COLUMN_TOTAL_VALIDATION, evidence gate, EquityValidator).
- **DoD:** (1) False FAIL do COLUMN_TOTAL giảm rõ (shortlist chuyển trạng thái); (2) False INFO "0 assertion" có policy + metrics; (3) Equity không FAIL computed=0 do missing parse; (4) Feature flags; (5) Unit tests + smoke notes.
- **Constraints:** Không thêm lib; thay đổi tối thiểu; feature-flag; backward compatible; log truy vết table_id → classifier → validator → rule.
- **Risk level:** Trung bình (chỉ validator/config, không auth/tiền; rollback bằng flag).

## B) Delegation Plan

| Workstream | Subagent | Inputs | Expected Output | Status |
|------------|----------|--------|-----------------|--------|
| Fix A (gate + flags) | Verifier | feature_flags.py, generic_validator.py | ruff + pytest pass | Done |
| Locate root causes | (explore) | codebase search | file/symbol list | Done |
| Policy "0 assertion" | — | base_validator, generic_validator | flag + enum + log | Pending |
| Equity NO_EVIDENCE | — | EquityValidator | mapping + guards | Pending |
| Tests + smoke | Verifier | fixtures, 2 DOCX | unit pass, smoke notes | Pending |

*(Tool Task(subagent_type=...) không có; Verifier thực tế = ruff + pytest; delegation qua brief + checklist.)*

## C) Results Digest

- **Verifier:** `ruff check` + `pytest tests/test_generic_validator*.py tests/test_scrum8_fixes.py` — 30 passed, All checks passed.
- **Code Reviewer:** (chưa gọi riêng; thay đổi đã theo minimal-change + guard).
- **Security Reviewer:** Không áp dụng (không chạm auth/secrets).
- **Docs & ADR Writer:** Plan file + orchestration report cập nhật.

## D) Integrated Decisions

- Eligibility gate chạy khi `run_column_totals` và `enable_generic_total_gate=True`; gate fail → INFO với `no_assertion_reason=ELIGIBILITY_GATE`, không FAIL.
- Cả hai flag mặc định False; bật qua config khi chạy audit.
- `table_context` có thể None → dùng `(table_context or {}).get("table_id", "")` khi log.

## E) Action Plan (prioritized)

| Prio | File/Area | Thay đổi | Lý do | Thực thi |
|------|-----------|----------|-------|----------|
| P0 | feature_flags.py, generic_validator.py | Cờ + eligibility gate | Giảm false FAIL COLUMN_TOTAL | Done |
| P1 | base_validator / generic_validator | Policy "0 assertion" + enum reason + log | Giảm false INFO | Pending |
| P1 | base_validator | Total row selection khi tighten_total_row_keywords | Tránh pick line item | Pending |
| P2 | EquityValidator | Mapping + NO_EVIDENCE khi components missing | Tránh FAIL computed=0 | Pending |
| P2 | tests/ | Unit fixtures (note no total, table with Total, equity missing) | Regression guard | Pending |
| P3 | Smoke | 2 DOCX, so sánh PASS/FAIL/INFO | DoD shortlist | Pending (cần XLSX) |

## F) Verification Checklist

- **Commands:** `ruff check quality_audit/config/feature_flags.py quality_audit/core/validators/generic_validator.py`; `pytest tests/test_generic_validator.py tests/test_generic_validator_evidence.py tests/test_scrum8_fixes.py -q --tb=short`.
- **Expected pass criteria:** Ruff All checks passed; pytest 30 passed.
- **Edge cases to spot-check:** Khi bật `enable_generic_total_gate=True`, bảng không đủ detail hoặc không có total keyword → INFO, log `generic_total_gate: skip COLUMN_TOTAL` với table_id, reason, detail_count.

*(Đã chạy: ruff + pytest — PASS.)*

## G) Risk / Rollback

- **Risks:** Bật gate mặc định có thể tăng INFO cho bảng biên; total row selection chặt có thể skip bảng hợp lệ.
- **Rollback steps:** Set `enable_generic_total_gate=False`, `tighten_total_row_keywords=False` trong config hoặc feature_flags.
- **Monitoring:** Log `generic_total_gate: skip COLUMN_TOTAL` để theo dõi tỷ lệ gate fail.

## H) Open Questions

- Đường dẫn 2 XLSX output (sau khi chạy `scripts/run_regression_2docs.py` với 2 DOCX) để lập shortlist và so sánh trước/sau.
- Chọn policy P1 (PASS when 0 assertion) hay P2 (INFO_NOT_APPLICABLE) cho "0 assertion executed"; flag `treat_no_assertion_as_pass`.
