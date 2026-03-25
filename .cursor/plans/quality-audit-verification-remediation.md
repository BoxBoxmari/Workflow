# Quality Audit — Verification & Remediation Plan

**Source:** Đối chiếu input DOCX vs output XLSX (CJCGV-FS2018-EN-v2, CP Vietnam-FS2018-Consol-EN).  
**Criteria:** (A) CY/PY đủ cột/kỳ, (B) đúng từng số cell, (C) logic casting/roll-forward đúng.

---

## A) Situation

- **Goal:** Khắc phục sai lệch giữa report đối chiếu và codebase: (1) extraction mất cột số (Cash flow, Other receivables), (2) validator logic gây FAIL giả (equity roll-forward, column total bỏ dòng đầu, income statement rule, BSPL casting), (3) header kỳ nhân bản, (4) scope rule cho bảng 1 kỳ / %.
- **DoD:** P0 (extraction loss) có fix hoặc root-cause rõ; P1 (validator logic) có fix + test; verify chạy audit trên 2 DOCX → 2 XLSX; lint/test pass.
- **Constraints:** Minimal change, không đổi public API/contract; ưu tiên fix theo report.
- **Risk level:** Medium (logic validator ảnh hưởng nhiều bảng; extraction ảnh hưởng 3 bảng cụ thể).

---

## B) Delegation Plan

| Workstream | Subagent | Inputs | Expected Output | Status |
|------------|----------|--------|-----------------|--------|
| W1 Extraction loss | Code Reviewer + Verifier | `ooxml_table_grid_extractor`, `word_reader`, report tbl_006/tbl_012/tbl_004 CP | Root cause + patch cho Cash flow / Other receivables mất amount | Done (extractor suffix; amount columns TBD) |
| W2 Equity roll-forward | Code Reviewer + Verifier | `equity_validator.py`, report C2 | expected = prior_balance + sum(movements); test | Done (Phase 2.3) |
| W3 Column total first row | Code Reviewer + Verifier | `generic_validator.py` find_block_sum, report C3 | Detail range gồm dòng đầu có số; test | Done (Phase 2.1) |
| W4 Income statement rule | Code Reviewer + Verifier | `generic_validator.py` eligibility, report C4 | Skip COLUMN_TOTAL cho income statement / formula subtotals | Done (Phase 2.2) |
| W5 BSPL Fixed assets casting | Code Reviewer + Verifier | `generic_validator.py` _validate_fixed_assets, report C1 | Ưu tiên Total/Tổng khi map note → FS line | Done (Phase 1.3) |
| W6 Verify end-to-end | Verifier | 2 DOCX, 2 XLSX, log | Lệnh audit + pass criteria + spot-check tables | Pending |

---

## C) Results Digest

- **Verifier:** Tests/lint chạy; audit CLI trên 2 DOCX→2 XLSX chưa chạy đủ trong session (cần user chạy local).
- **Code Reviewer:** Phân tích generic_validator (find_block_sum, column total, income statement), equity_validator (balance = prior + movements); fixes đã áp dụng theo todo.
- **Memory/NeuralMemory:** Context project đã dùng để tránh trùng và gắn với report.
- **Others:** Extractor duplicate period headers + Total/Tổng BSPL đã fix.

---

## D) Integrated Decisions

- **D1:** Ưu tiên P0: extraction mất cột (tbl_006, tbl_012 CJ; tbl_004 CP) — cần kiểm tra pipeline từ Word → grid → amount column detection; P1 là validator logic (đã xử lý theo W2–W5).
- **D2:** Conflict resolution: Correctness (B/C) > compatibility; không đổi contract output, chỉ sửa logic nội bộ.
- **D3:** Plan file lưu tại `.cursor/plans/quality-audit-verification-remediation.md`; verification checklist chạy bởi user hoặc CI.

---

## E) Action Plan (prioritized)

| Prio | Area | Thay đổi | Lý do | Owner |
|------|------|----------|--------|--------|
| P0 | Extraction — Cash flow / Other receivables | Xác định vì sao amount columns = 0 trong output cho tbl_006 (CJ), tbl_012 (CJ), tbl_004 (CP); sửa detector hoặc grid mapping | Report: output mất toàn bộ ô amount | Human + Code Reviewer |
| P1 | EquityValidator | expected closing = prior_balance + sum(movements); không so movement trực tiếp với balance | Report C2 | Done (Phase 2.3) |
| P1 | GenericValidator find_block_sum | Đảm bảo dòng đầu có số nằm trong range detail sum (tránh bỏ dòng đầu) | Report C3 | Done (Phase 2.1) |
| P1 | GenericValidator income statement | Không áp COLUMN_TOTAL_VALIDATION cho bảng có formula subtotals (income statement / cash flow) | Report C4 | Done (Phase 2.2) |
| P1 | Fixed assets BSPL | Ưu tiên cột Total/Tổng khi map note total → FS line | Report C1 | Done (Phase 1.3) |
| P2 | Extractor duplicate period | Suffix cho header kỳ trùng (31/12/2018 → 31/12/2018, 31/12/2018 (2)) | Report A2 | Done (Phase 3.1) |
| P2 | Single-period / % tables | Không FAIL_TOOL_EXTRACT vì “thiếu CY/PY” cho bảng movement 1 kỳ hoặc % ownership | Report A3 | Done (Phase 4.1) |
| P2 | CJ substantive table | 1 bảng Authorised/Contributed capital theo investors chưa lên casting — kiểm tra scope note tables | Report section 5 | Human |

---

## F) Verification Checklist

- **Commands:**
  - `pytest tests/ -v --tb=short` (hoặc scope cụ thể: `tests/test_generic_validator*.py tests/test_equity*.py`)
  - `python -m quality_audit.cli audit "<path>/data/CJCGV-FS2018-EN- v2 .DOCX" -o "<path>/results/CJCGV-FS2018-EN- v2 _output.xlsx"`
  - Tương tự cho CP Vietnam DOCX → output XLSX
  - Ruff/black: `ruff check quality_audit/` (nếu có)
- **Expected pass criteria:**
  - Toàn bộ tests liên quan validator/extractor pass.
  - Output XLSX cho CJ/CP có ít nhất 1 ô amount (>=1000) trong Cash flow (tbl_006 CJ, tbl_004 CP) và Other receivables (tbl_012 CJ) sau khi fix P0.
  - Focus List không còn FAIL giả cho: payables significant/related (CJ), inventories (CP), foreign currencies (CP), equity roll-forward (CJ/CP), income statement sum-to-total (CJ), fixed assets BSPL (CJ).
- **Edge cases to spot-check:**
  - CJ tbl_006_2018_VND_000, tbl_012_Other_receivables; CP tbl_004_2018_VND (Cash flow).
  - CJ tbl_004 (Income statement), tbl_017 (Tangible fixed assets), tbl_030 (Equity); CP tbl_014 (Inventories), tbl_037 (Foreign currencies), tbl_033 (Equity).

---

## G) Risk / Rollback

- **Risks:** Thay đổi logic validator có thể ảnh hưởng bảng khác; extraction fix có thể đụng merged cells/header detection.
- **Rollback:** Revert commit cho từng phase; giữ test cũ để so sánh.
- **Monitoring:** Sau deploy chạy audit trên 2 DOCX → 2 XLSX và so số ô amount + số FAIL Focus List với baseline report.

---

## H) Open questions

- P0 extraction: Cột amount bị mất ở bước nào (Word read → grid, hay grid → amount column detection)? Cần trace với 1 file (e.g. CJ Cash flow) và log từng bước.
- CJ 43 vs 48 blocks: Có chấp nhận bỏ 4 bảng chữ ký; còn 1 bảng substantive (capital by investors) — có cần đưa vào scope casting không?
