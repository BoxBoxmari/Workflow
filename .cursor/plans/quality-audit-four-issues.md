# Plan: Quality Audit – 4 vấn đề (bảng chưa phân loại, NOTE_SUM_TO_TOTAL, IS Formula 30, Tax reconciliation)

## WBS

| # | Workstream | Owner | Output | Verify |
|---|------------|--------|--------|--------|
| 1 | Fix tax reconciliation detail_rows (exclude row 0 "Accounting profit before tax") | Main | audit_service.py: detail_rows = range(1, n-1) when heading contains "reconciliation of effective tax rate" | pytest tests/core/test_audit_engine_phase2.py + golden/cash_flow |
| 2 | Document IS Formula 30 + classifier/assertions (P2) | — | Follow-up: trace IS row source, improve UNKNOWN→assertions | — |

## Quyết định đã chốt

- **Tax reconciliation:** Với bảng "(b) Reconciliation of effective tax rate", total = dòng cuối (n-1), details = chỉ các dòng điều chỉnh thuế (1 .. n-2). Dòng 0 "Accounting (loss)/profit before tax" không được cộng vào sum(details). Đã sửa trong `audit_service.py` bằng điều kiện `table_type == "TAX_NOTE"` và heading chứa `"reconciliation of effective tax rate"` → `detail_rows = list(range(1, n - 1))`.
- **Vấn đề 1 & 3:** Giữ scope P2 (classifier/assertions, IS Formula 30 nguồn dữ liệu); không implement trong phiên này.

## Action Plan (đã thực hiện)

- P0: `quality_audit/services/audit_service.py` — Thêm nhánh cho TAX_NOTE + "reconciliation of effective tax rate" → `detail_rows = list(range(1, n - 1))`; ngược lại giữ `list(range(0, n - 1))`. **Done.**

## Verification Checklist

- **Commands:** `python -m pytest tests/core/test_audit_engine_phase2.py tests/test_quality_audit_golden.py tests/core/test_cash_flow_rules.py -q --tb=short`
- **Expected:** All selected tests pass (no new failures).
- **Edge cases:** Re-run full pipeline với 2 DOCX và kiểm tra bảng "(b) Reconciliation of effective tax rate" không còn FAIL Sum(details)==Total do sai detail_rows.

## Risk / Rollback

- **Risks:** Các TAX_NOTE khác có cấu trúc "row 0 = base, row 1..n-2 = details, row n-1 = total" có thể cần cùng logic; hiện chỉ áp dụng cho heading chứa "reconciliation of effective tax rate".
- **Rollback:** Revert đoạn if/else trong audit_service (detail_rows) về `list(range(0, n - 1))`.
