# Plan: Giảm false FAIL / false INFO (extract đúng, validate/routing sai)

## Context

- **Mục tiêu:** Giảm false FAIL và false INFO khi extract đúng nhưng validator/routing áp sai rule hoặc chọn sai total row.
- **Triệu chứng:** A1 (FAIL do COLUMN_TOTAL_VALIDATION sai total row), A2 (INFO "Không có assertion nào được thực thi"), B1 (Equity FAIL "Tính=0").
- **Ràng buộc:** Thay đổi tối thiểu, feature-flag, test, log truy vết table_id → classifier → validator → rule.

## WBS (Work Breakdown)

| Phase | Mô tả | Trạng thái |
|-------|--------|------------|
| 1 | Reproduce & Triage: đọc XLSX, shortlist ~10 case | Blocked (no XLSX in repo) |
| 2 | Locate: classifier, GenericTableValidator, evidence gate, EquityValidator | Done (code locations identified) |
| 3 | Fix A: eligibility gate + total-row/detail-row selection | In progress (gate + 2 flags added) |
| 4 | Fix A2: policy "0 assertion", logging, trigger | Pending |
| 5 | Fix B: Equity mapping/guards, NO_EVIDENCE not FAIL | Pending |
| 6 | Observability + unit/smoke tests | Pending |
| 7 | DoD + smoke trước/sau | Pending |

## Decisions

- **Eligibility gate:** Chạy trước COLUMN_TOTAL_VALIDATION khi `enable_generic_total_gate=True`. Gate fail → return INFO với `no_assertion_reason=ELIGIBILITY_GATE`, không FAIL.
- **Feature flags mặc định:** `enable_generic_total_gate=False`, `tighten_total_row_keywords=False` để không đổi hành vi mặc định; bật trong config khi chạy audit.
- **Shortlist:** Khi có 2 file XLSX output, lập shortlist 3–5 false FAIL + 3–5 false INFO + 1–2 Equity; ghi table_id, validator, rule, message.

## Action Plan (đã làm / còn lại)

### Đã làm

1. **feature_flags.py:** Thêm `enable_generic_total_gate` (default False), `tighten_total_row_keywords` (default False).
2. **generic_validator.py:** Thêm eligibility gate sau `generic_evidence_gate`:
   - Điều kiện: `run_column_totals` và `enable_generic_total_gate=True`.
   - Gate: (1) >= 2 detail rows (numeric, non-year); (2) total row label có keyword total/subtotal/grand total/tổng… hoặc bắt đầu "total "/"tổng "; (3) nếu `tighten_total_row_keywords`: loại dòng có profit/income/expense nhưng không có total.
   - Gate fail → `ValidationResult(status="INFO: Rule not applicable (eligibility gate: …)", status_enum="INFO", context={no_assertion_reason, eligibility_gate_reason, detail_count, total_row_label_preview}, assertions_count=0)`.
   - Log: `generic_total_gate: skip COLUMN_TOTAL (table_id=…) reason=… detail_count=… total_label=…`.

### Còn lại

- Policy "0 assertion executed": thêm flag `treat_no_assertion_as_pass`, enum `no_assertion_reason` (NO_EVIDENCE / NOT_APPLICABLE / INTERNAL_GUARD), chuẩn hóa log assertion_count.
- Total row selection (base_validator): khi `tighten_total_row_keywords=True` ưu tiên Grand total > Total > Subtotal; hạ điểm dòng có profit/income/expense không có total.
- EquityValidator: mapping fallback; khi components missing → NO_EVIDENCE, không emit computed=0 rồi FAIL; flag `equity_no_evidence_not_fail`.
- Unit tests: fixtures (bảng note không total, bảng có Total, equity missing components).
- Smoke: chạy 2 DOCX, so sánh PASS/FAIL/INFO trước-sau; xác minh shortlist khi có XLSX.

## Verification Checklist

- [x] `pytest tests/test_generic_validator.py tests/test_generic_validator_evidence.py tests/test_scrum8_fixes.py -q --tb=short` pass (30 passed).
- [x] `ruff check quality_audit/config/feature_flags.py quality_audit/core/validators/generic_validator.py` không lỗi (All checks passed).
- [ ] Khi bật `enable_generic_total_gate=True`: bảng không đủ detail hoặc không có total keyword → INFO, không FAIL.
- [ ] Log có `generic_total_gate: skip COLUMN_TOTAL` với table_id, reason, detail_count khi gate fail.

## Risk / Rollback

- **Rủi ro:** Bật gate mặc định có thể tăng INFO cho bảng “biên”. **Mitigation:** Giữ default OFF; bật từng môi trường.
- **Rollback:** Set `enable_generic_total_gate=False`, `tighten_total_row_keywords=False` trong config hoặc feature_flags.

## Open Questions

- Đường dẫn 2 file XLSX output mới nhất (sau khi chạy pipeline 2 DOCX) để lập shortlist và so sánh trước/sau.
- Chọn policy P1 (PASS when 0 assertion) hay P2 (INFO_NOT_APPLICABLE) cho "0 assertion executed"; cần flag `treat_no_assertion_as_pass`.
