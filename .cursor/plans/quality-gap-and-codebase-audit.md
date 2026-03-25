# Quality Gap & Codebase Audit Report

**Workflow:** Subagent (Intake → WBS → Delegation → Consolidation → Verify → Persist)  
**Scope:** So sánh log + Outputs vs Inputs → quality gap; Audit `quality_audit/` core → liên kết với quality gap.  
**Dialectic:** Thesis → Antithesis → Synthesis → Finalization; 3–5 câu hỏi kiểm chứng.

---

## A. Situation (Tình huống)

- **Inputs:** `data/CJCGV-FS2018-EN- v2 .DOCX`, `data/CP Vietnam-FS2018-Consol-EN.docx` (và `test_single_table.docx`).
- **Outputs:** `results/CJCGV-FS2018-EN- v2 _output.xlsx`, `results/CP Vietnam-FS2018-Consol-EN_output.xlsx` (được tham chiếu trong `audit_analysis.json` và `forensic_analysis.json`; file .xlsx có thể nằm ngoài repo hoặc đã tạo ở run trước).
- **Log:** `log.txt` — một run CLI: 3 file, 100 bảng, 3 success, 0 failed; nhiều bảng có `extractor_engine='legacy'`, `quality_score=0.0`, `failure_reason_code='LEGACY_FALLBACK'`.
- **Artifacts đã dùng:** `results/audit_analysis.json`, `results/forensic_analysis.json`, `log.txt`, code trong `quality_audit/` (word_reader, extractors, validators, audit_service, factory, table_type_classifier).

---

## B. Delegation Plan (Kế hoạch ủy thác)

| Bước | Hành động | Subagent / Công cụ |
|------|-----------|---------------------|
| 1 | Chọn skill phù hợp trước mọi sửa code | agent-skills-runner |
| 2 | Điều phối debug / root cause | memory-orchestrator |
| 3 | Review với trí nhớ dài hạn | memory-aware-worker |
| 4 | Lấy context NeuralMemory cho project | memory-provider |
| 5 | Xác minh mọi thay đổi / kết luận | verifier |

**Lưu ý:** Trong môi trường hiện tại không có tool `Task(subagent_type=...)` để gọi trực tiếp các subagent; các bước trên nên được thực hiện thủ công hoặc qua Cursor agent khi có sẵn.

---

## C. Results Digest (Tóm tắt kết quả)

### 1. Quality gap (Input vs Output vs log)

**Nguồn số liệu:** `audit_analysis.json` + `forensic_analysis.json` (đọc từ output xlsx đã được pipeline ghi).

- **Tổng quan:** 99 bảng (48 CJCGV + 51 CP Vietnam): **PASS=52**, **FAIL=9**, **FAIL_TOOL_EXTRACT=19**, **WARN=9**, **INFO=10**.
- **FAIL_TOOL_EXTRACT (19 bảng):** Tất cả có `extractor_engine: "legacy"`, `engine_attempts: "ooxml,python_docx"`, `failure_reason: "FAIL_TOOL_EXTRACT_LOW_QUALITY"`. Nghĩa là OOXML và Python-docx đều không trả về kết quả “usable” (quality_score ≥ 0.6 và không vi phạm hard invariant) → fallback legacy → quality 0, không đủ cho validation đầy đủ.
- **FAIL (9 bảng):** Validation thất bại dù extraction có thể tốt: **COLUMN_TOTAL_VALIDATION** (total row / cột tổng), **EQUITY_VALIDATION**, **TAX_REMAINING_TABLE_GRAND_TOTAL**. Phân bổ theo `total_row_method`: keyword_total_row (2), rule_b_blank_label (4), rule_c_sum_equation (2), UNKNOWN (1).
- **WARN (9 bảng):** Cùng loại rule (COLUMN_TOTAL_VALIDATION, GenericTableValidator_VALIDATION) nhưng đánh dấu cảnh báo.
- **Nguyên nhân quality gap:**
  1. **Extraction:** Một số bảng phức tạp (merged cells, layout đặc biệt) khiến OOXML và Python-docx không đạt ngưỡng 0.6 hoặc vi phạm invariant → legacy → chất lượng thấp, dẫn tới FAIL_TOOL_EXTRACT.
  2. **Validation:** Quy tắc total row / cột tổng / tax / equity không khớp với cách trình bày thực tế trong docx → FAIL/WARN dù extraction tốt.

### 2. Audit codebase `quality_audit/` (core) và liên kết với quality gap

**Luồng chính:**

- **word_reader._extract_table_with_fallback:** Thử lần lượt: **OOXML** → **Python-docx** → **RenderFirst** (nếu soffice có) → **Legacy**. Chỉ khi engine trả về `is_usable and grid` mới dừng; nếu không → legacy với `quality_score=0.0`, `failure_reason_code='LEGACY_FALLBACK'`.
- **OOXMLTableGridExtractor:** `is_usable` = `quality_score >= 0.6` và không hard invariant (empty_grid, row/col_count, duplicate_periods, exception) và không có flag GRID_CORRUPTION/DUPLICATE_PERIODS.
- **PythonDocxExtractor:** Cùng ngưỡng 0.6, trả về ExtractionResult với quality_score và invariant_violations.
- **ValidatorFactory + TableTypeClassifier:** Phân loại bảng (BalanceSheet, IncomeStatement, CashFlow, Equity, Tax, Generic). Bảng footer/signature → SKIPPED_FOOTER_SIGNATURE (validator=None).
- **audit_service:** Đọc docx → extract với fallback → validate từng bảng → ghi observability (extractor_engine, quality_score, failure_reason_code) vào log và report.

**Liên kết quality gap ↔ code:**

| Vấn đề quan sát | Vị trí code / nguyên nhân |
|-----------------|---------------------------|
| 19 bảng FAIL_TOOL_EXTRACT, legacy, quality 0 | `word_reader._extract_table_with_fallback`: OOXML và Python-docx không trả về is_usable → legacy. Nguyên nhân sâu: OOXML/Python-docx với bảng có gridSpan/vMerge phức tạp hoặc layout lệch → quality_score < 0.6 hoặc hard invariant. |
| SKIPPED_FOOTER_SIGNATURE | `ValidatorFactory`: heading bắt đầu "SKIPPED_"; `WordReader._is_footer_or_signature_table` + logic skip trước khi gọi factory. |
| FAIL COLUMN_TOTAL_VALIDATION / total_row_method | `base_validator` / `generic_validator`: chọn total row (keyword_total_row, rule_b_blank_label, rule_c_sum_equation, safe_total_row_selection_no_match). Mismatch với cách trình bày trong docx → FAIL/WARN. |
| FAIL TAX / EQUITY | `tax_validator` / `equity_validator`: rule đặc thù (grand total, remaining table, equity movement). Dữ liệu từ legacy hoặc cấu trúc bảng không chuẩn → FAIL. |

**Performance / Security (tóm tắt):**

- **Performance:** Đọc docx tuần tự; mỗi bảng chạy OOXML → Python-docx → (RenderFirst) → legacy. RenderFirst phụ thuộc soffice (external binary). Không thấy cache kết quả extraction theo table fingerprint; có thể tối ưu nếu cùng file chạy nhiều lần.
- **Security:** `file_handler.validate_path` và `validate_docx_safety` (zip bomb) đã được gọi trong `audit_service.audit_document`; input path được kiểm tra trước khi đọc.

---

## D. Integrated Decisions (Quyết định tích hợp)

1. **Quality gap chủ yếu do hai nhóm:** (1) extraction không đủ tốt (19 bảng fallback legacy), (2) rule validation (total row, tax, equity) không khớp với format thực tế (9 FAIL + 9 WARN).
2. **Ưu tiên xử lý:** Cải thiện OOXML/Python-docx cho bảng có merged cells / layout khó (giảm legacy fallback); sau đó điều chỉnh hoặc mở rộng rule total row và tax/equity để giảm FAIL/WARN sai.
3. **Subagent:** Mọi thay đổi code nên qua agent-skills-runner (skill), memory-orchestrator (debug), memory-provider (context), verifier (xác nhận).

---

## E. Action Plan (Kế hoạch hành động)

1. **Ngắn hạn:**  
   - Ghi lại danh sách 19 bảng FAIL_TOOL_EXTRACT (table_id/heading) từ forensic_analysis; mở vài bảng tương ứng trong docx để phân tích đặc điểm (gridSpan, vMerge, số cột).  
   - Kiểm tra OOXML/Python-docx với các bảng đó: log invariant_violations và quality_flags để biết lý do bị reject.

2. **Trung hạn:**  
   - Cải thiện OOXML/Python-docx: nới lỏng hoặc tách bạch hard vs soft invariant; hoặc điều chỉnh quality_score cho bảng có merged cells nhưng nội dung đọc được.  
   - Cập nhật rule total row (keyword_total_row, rule_b_blank_label, rule_c_sum_equation) hoặc thêm rule mới để phù hợp format CJCGV/CP Vietnam.

3. **Dài hạn:**  
   - Cân nhắc RenderFirst (soffice) ổn định trên môi trường deploy để giảm fallback legacy.  
   - Bổ sung test regression với các bảng đang FAIL_TOOL_EXTRACT/FAIL để tránh tái phạm.

---

## F. Verification Checklist (Kiểm tra xác minh)

| # | Mục | Lệnh / Cách kiểm chứng | Tiêu chí pass |
|---|-----|------------------------|----------------|
| 1 | Pipeline chạy đủ 3 file | `python -m quality_audit.cli data --output-dir results` | Exit 0, Total files 3, Failed 0 |
| 2 | Số bảng và status | Đọc `results/audit_analysis.json` | combined_status khớp với log (PASS/FAIL/FAIL_TOOL_EXTRACT/WARN/INFO) |
| 3 | Legacy fallback có trong log | `grep LEGACY_FALLBACK log.txt` | Số dòng tương ứng 19 bảng FAIL_TOOL_EXTRACT |
| 4 | Output xlsx tồn tại | Kiểm tra `results/*_output.xlsx` | Có file CJCGV và CP Vietnam (hoặc đường dẫn đúng đã cấu hình) |
| 5 | Security: path & zip bomb | Đọc `audit_service.audit_document` | Gọi validate_path và validate_docx_safety trước khi đọc |

---

## G. Risk / Rollback

- **Rủi ro:** Thay đổi ngưỡng quality (0.6) hoặc invariant có thể làm nhiều bảng “pass” extraction nhưng chất lượng grid kém → validation sai.  
- **Rollback:** Giữ nguyên QUALITY_THRESHOLD và hard invariant; chỉ thêm soft flags hoặc cải thiện thuật toán grid reconstruction; mọi thay đổi có test và so sánh audit_analysis trước/sau.

---

## H. Open Questions (Câu hỏi mở)

1. Đường dẫn chính xác của file xlsx output (trong repo hay ngoài)? Nếu ngoài, có cần copy vào `results/` để so sánh diff với input docx không?  
2. Có cần chạy lại pipeline để tạo mới xlsx và so sánh từng ô (sample) với docx để đo độ trung thực extraction không?  
3. Subagent (agent-skills-runner, memory-orchestrator, memory-aware-worker, memory-provider, verifier) được gọi qua cơ chế nào trong Cursor (Task tool hay thủ công)?

---

## Thesis – Antithesis – Synthesis – Finalization

### Thesis (Câu trả lời ban đầu)

**“Quality gap xuất phát từ hai nơi: (1) extraction không đủ tốt cho 19 bảng (OOXML và Python-docx bị reject → legacy, quality 0), (2) rule validation (total row, tax, equity) không khớp với cách trình bày thực tế trong docx (9 FAIL + 9 WARN). Vấn đề nằm ở `quality_audit/io/word_reader.py` (fallback), `quality_audit/io/extractors/ooxml_table_grid_extractor.py` và `python_docx_extractor.py` (ngưỡng 0.6 và invariant), và `quality_audit/core/validators/` (total row selection và rule tax/equity).”**

### Antithesis (Phản biện)

- Có thể quality gap do **input docx** (file hỏng, format lạ) chứ không phải code?  
- Có thể **số liệu trong audit_analysis.json** không tương ứng run hiện tại (file cũ)?  
- Có thể **RenderFirst** không được cài (soffice) nên mọi bảng khó đều rơi legacy, không phải do OOXML/Python-docx yếu?  
- Có thể **FAIL** là do dữ liệu tài chính thật sự sai (lỗi nguồn) chứ không phải rule quá chặt?

### Synthesis (Tổng hợp)

- **Input docx:** Log cho thấy 3 file chạy thành công, 100 bảng; không có lỗi đọc file. Giả định docx hợp lệ; nếu cần có thể kiểm tra thêm một vài file.  
- **Khớp run:** audit_analysis.json và forensic_analysis.json tham chiếu đúng tên output xlsx và row count (48, 51); forensic liệt kê FAIL_TOOL_EXTRACT với engine_attempts "ooxml,python_docx" → khớp với một run đã chạy pipeline.  
- **RenderFirst:** Log có “Render-first skipped: system binaries missing (soffice)” hoặc tương tự; nhiều bảng chỉ thử ooxml + python_docx rồi legacy. Vậy cả hai đều đúng: (1) OOXML/Python-docx không đủ tốt cho 19 bảng đó, (2) không có RenderFirst để cứu → legacy. Cải thiện OOXML/Python-docx vẫn có lợi; bật RenderFirst khi có soffice sẽ giảm thêm legacy.  
- **FAIL do dữ liệu:** Có thể một phần; nhưng forensic_analysis chỉ ra failure_reason (COLUMN_TOTAL_VALIDATION, TAX_REMAINING_TABLE_GRAND_TOTAL, EQUITY_VALIDATION) — đây là rule logic (total row, cột tổng), không phải so sánh số. Kết luận: cả extraction lẫn rule đều góp phần; ưu tiên vẫn là giảm legacy và chỉnh rule cho phù hợp format.

### Finalization (Kết luận cuối)

Giữ nguyên Thesis với bổ sung: (1) RenderFirst không có (soffice) làm tăng số bảng rơi legacy; (2) FAIL/WARN chủ yếu do rule validation (total row / tax / equity), có thể một phần do dữ liệu nguồn nhưng nguyên nhân chính vẫn là logic rule và cách trình bày bảng.

---

## Câu hỏi kiểm chứng và trả lời

1. **“19 bảng FAIL_TOOL_EXTRACT có phải luôn cùng 19 bảng có extractor_engine=legacy trong log không?”**  
   Có. forensic_analysis.fail_tool_extract_inventory liệt kê đúng 19 mục, mỗi mục có extractor_engine=legacy và engine_attempts=ooxml,python_docx; log có nhiều dòng observability với extractor_engine='legacy', failure_reason_code='LEGACY_FALLBACK'. Số lượng và nguồn file (CJCGV vs CP Vietnam) khớp với 19 bảng đó.

2. **“Tại sao OOXML và Python-docx lại bị reject cho những bảng này?”**  
   Trong code: OOXML/Python-docx trả về is_usable=False khi quality_score < 0.6 hoặc có hard invariant (empty_grid, row/col_count mismatch, duplicate_periods, exception). Không có log chi tiết từng bảng (invariant_violations, quality_flags) trong log.txt; cần bật debug hoặc thêm log trong extractors để biết chính xác lý do từng bảng.

3. **“SKIPPED_FOOTER_SIGNATURE có làm sai lệch số bảng PASS/FAIL không?”**  
   Không. Bảng skipped vẫn được ghi vào output với validator_type=None và status INFO; chúng không được tính là PASS hay FAIL validation. Số PASS/FAIL/FAIL_TOOL_EXTRACT/WARN trong audit_analysis là trên 99 bảng (48+51), không trùng với số bảng skipped.

4. **“Có thể giảm FAIL bằng cách nới lỏng rule total row không?”**  
   Có thể. Hiện tại rule (keyword_total_row, rule_b_blank_label, rule_c_sum_equation) có thể quá chặt với một số bảng. Nới lỏng hoặc thêm rule mới (ví dụ theo format CJCGV/CP Vietnam) có thể chuyển một số FAIL thành PASS hoặc WARN; cần test regression để tránh false positive.

5. **“Cấu trúc thư mục quality_audit/core có ảnh hưởng trực tiếp đến quality gap không?”**  
   Có gián tiếp. quality_audit/core chứa validators, factory, routing (table_type_classifier), cache_manager — quyết định loại validator và cách validate. Extraction nằm ở quality_audit/io (word_reader, extractors). Gap extraction (19 bảng) do io; gap validation (9 FAIL, 9 WARN) do core validators và routing. Cấu trúc folder hợp lý (tách io vs core); vấn đề là logic bên trong, không phải cách tổ chức thư mục.

---

## Câu trả lời cuối đã hiệu chỉnh

**Quality gap giữa Input (docx) và Output (xlsx) + log gồm hai nhóm:**

1. **Extraction (19 bảng – FAIL_TOOL_EXTRACT):** OOXML và Python-docx đều không trả về kết quả “usable” (quality_score ≥ 0.6 và không vi phạm hard invariant) cho 19 bảng đó, nên pipeline dùng legacy fallback → quality_score 0. Nguyên nhân nằm ở logic và ngưỡng trong `quality_audit/io/word_reader.py` và `quality_audit/io/extractors/` (OOXMLTableGridExtractor, PythonDocxExtractor). RenderFirst (soffice) không có hoặc không dùng được nên không giảm được số bảng rơi legacy.

2. **Validation (9 FAIL + 9 WARN):** Rule kiểm tra total row và cột tổng (COLUMN_TOTAL_VALIDATION), tax (TAX_REMAINING_TABLE_GRAND_TOTAL) và equity (EQUITY_VALIDATION) không khớp với cách trình bày thực tế trong docx. Vấn đề nằm ở `quality_audit/core/validators/` (base_validator, generic_validator, tax_validator, equity_validator) và cách chọn total row (total_row_method).

**Audit codebase:** Cấu trúc `quality_audit/` (config, core, io, services, utils) rõ ràng; bảo mật (path, zip bomb) đã được kiểm trong audit_service. Cần hành động: (1) cải thiện extraction (OOXML/Python-docx) và/hoặc bật RenderFirst; (2) điều chỉnh hoặc mở rộng rule total row và tax/equity; (3) thêm log/debug cho extractors để phân tích từng bảng FAIL_TOOL_EXTRACT.
