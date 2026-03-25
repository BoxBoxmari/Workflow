# Plan: Render-first dùng binary hệ thống (Poppler, Tesseract, LibreOffice)

## 1. Situation

- **Goal:** Chuyển nhánh render-first sang dùng rõ ràng binary hệ thống (poppler, tesseract, LibreOffice): ưu tiên hoặc bắt buộc dùng system binaries thay vì chỉ Python libs.
- **DoD:** (1) Render-first có thể chạy với Poppler (PDF→image), Tesseract (OCR), LibreOffice (DOCX→PDF) cài trên máy; (2) Có cơ chế ưu tiên "binary-first" (local soffice, pdf2image/poppler) khi cấu hình; (3) Thiếu binary thì báo lỗi rõ ràng; (4) Docs và IT-DEPENDENCIES đã cập nhật.
- **Constraints:** Không dùng Docker; chỉ dùng system binaries (local soffice, Poppler, Tesseract). PyMuPDF vẫn dùng được cho PDF→image. Không thay đổi public API extract; CI có thể chạy không có binary (skip render-first tests hoặc mock).
- **Risk level:** Medium (thay đổi thứ tự fallback, thêm config).

## 2. Work Breakdown Structure (WBS)

| ID | Workstream | Output | Owner | Verify |
|----|------------|--------|--------|--------|
| W1 | Config / env "binary-first" | Env `QA_RENDER_FIRST_USE_SYSTEM_BINARIES=1` hoặc flag; FallbackConverter ưu tiên local soffice khi set | Code | Unit test + doc |
| W2 | TableIsolator: ưu tiên Poppler | Khi binary-first: thử pdf2image (poppler) trước PyMuPDF; hoặc detect pdftoppm | Code | Test render PDF→image |
| W3 | Binary detection helper | Module hoặc hàm `check_poppler()`, `check_tesseract()`, `check_soffice()`; dùng ở startup hoặc extractor init | Code | Test khi thiếu binary |
| W4 | Clear errors khi thiếu binary | Message kiểu "Render-first requires: install Poppler (pdftoppm), Tesseract, LibreOffice (soffice); see docs/IT-DEPENDENCIES.md" | Code | Manual / test |
| W5 | Docs & IT-DEPENDENCIES | Cập nhật IT-DEPENDENCIES + README: binary-first mode, lệnh cài (apt/choco/brew) | Docs | Review |
| W6 | Verification & tests | Lint; test unit render-first (mock binary); regression optional với binary thật | Verifier | CI green |

## 3. Delegation Plan

| Workstream | Subagent | Inputs | Expected Output | Status |
|------------|----------|--------|-----------------|--------|
| W1–W4 | Code Reviewer | goal + files (converter, table_isolator, render_first, ocr) | Review diff, suggest minimal change | Simulated |
| W1–W4 | Verifier | plan + commands | pytest list, lint, pass criteria | Below |
| W5 | Docs & ADR Writer | IT-DEPENDENCIES, README | Doc updates | In plan |
| W6 | Verifier | Full checklist | Commands + pass criteria | Below |

## 4. Integrated Decisions

- **D1:** FallbackConverter chỉ dùng local soffice (Docker đã bỏ). TableIsolator có thể ưu tiên pdf2image (poppler) khi env binary-first nếu cần.
- **D2:** Không dùng Docker; PyMuPDF vẫn dùng cho PDF→image. Tesseract dùng binary qua pytesseract; message lỗi rõ khi thiếu binary.
- **D3:** Binary detection: optional helper (ví dụ `quality_audit/io/extractors/binary_check.py`) gọi `shutil.which("pdftoppm")`, `pytesseract.get_tesseract_version()`, `_find_soffice()`; dùng để log hoặc nâng message lỗi, không block main flow khi tắt binary-first.

## 5. Action Plan (prioritized)

| Prio | File/Area | Thay đổi | Lý do | Thực thi |
|------|-----------|----------|--------|----------|
| P0 | `quality_audit/io/extractors/conversion/converter.py` | `FallbackConverter` chỉ dùng local soffice (không Docker) | Chỉ system binary | Done |
| P0 | `quality_audit/io/extractors/table_isolator.py` | Trong `render_pdf_to_image()`: nếu env binary-first thì thử `pdf2image` (poppler) trước PyMuPDF | Ưu tiên Poppler khi binary-first | Code |
| P1 | `quality_audit/io/extractors/` (mới hoặc trong extractors) | Thêm helper `binary_check.py`: `check_poppler()`, `check_tesseract()`, `check_soffice()` trả bool + message | Message lỗi rõ khi thiếu binary | Code |
| P1 | `quality_audit/io/extractors/render_first_table_extractor.py` | Khi init hoặc khi conversion/structure fail: nếu binary-first và thiếu binary thì set rejection_reason với link tới IT-DEPENDENCIES | UX và debug | Code |
| P2 | `docs/IT-DEPENDENCIES.md` | Bổ sung mục "Binary-first mode": env var, thứ tự ưu tiên, lệnh cài Poppler/Tesseract/LibreOffice | Docs | Docs |
| P2 | `README.md` | Ghi ngắn: render-first có thể dùng system binaries, xem IT-DEPENDENCIES | Docs | Docs |
| P3 | Tests | Unit test: FallbackConverter với mock env ưu tiên local; TableIsolator với mock env poppler-first; test thiếu binary (optional) | Regression | Verifier |

## 6. Verification Checklist

- **Commands:**
  - `pytest quality_audit/io/extractors/ -v -k "render_first or converter or table_isolator" --ignore=tests/regression`
  - `pytest tests/io/extractors/test_render_first_extractor.py tests/io/extractors/test_render_first_structure.py -v`
  - `ruff check quality_audit/io/extractors/`
- **Expected pass criteria:** Tất cả test liên quan pass; lint sạch.
- **Edge cases:** (1) Chạy với `QA_RENDER_FIRST_USE_SYSTEM_BINARIES=1` trên máy không cài poppler/soffice → message rõ, không crash. (2) Chạy với binary cài sẵn → render-first vẫn extract được.

## 7. Risk / Rollback

- **Risks:** Thay đổi thứ tự fallback có thể làm một số môi trường (chỉ có Docker, không có soffice) chuyển sang fail khi bật binary-first; mặc định tắt nên không ảnh hưởng hiện tại.
- **Rollback:** Bỏ đọc env `QA_RENDER_FIRST_USE_SYSTEM_BINARIES` và revert thứ tự trong FallbackConverter + TableIsolator.
- **Monitoring:** Log conversion_mode (local_soffice) và render path (pymupdf / pdf2image) trong telemetry đã có.

## 8. Open questions

- Có cần tên env khác (ví dụ `QA_PREFER_SYSTEM_BINARIES`) hay giữ `QA_RENDER_FIRST_USE_SYSTEM_BINARIES`?
- Có cần script `scripts/check_render_first_binaries.py` in ra trạng thái poppler/tesseract/soffice cho người dùng không?
