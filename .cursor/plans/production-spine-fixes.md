# Production Spine Fixes — Plan & Verification

## A) Situation

- **Goal:** Chốt production cho audit tool bằng cách xử lý triệt để 3 gap: (A) data-loss/mất cột số, (B) SKIP sai bảng dữ liệu thật (đặc biệt vốn/cổ phần), (C) false FAIL do heuristic (đặc biệt cộng nhầm cột Code/Note/Ref). Hard-stop: **false FAIL due-to-Code = 0**.
- **DoD:** (1) false FAIL due-to-Code = 0 trên golden set; (2) Bảng vốn/cổ phần không bị SKIP sai; (3) Cash Flow/thiếu numeric chuyển sang NO_EVIDENCE/EXTRACT_ERROR có evidence rõ; (4) Output có evidence tối thiểu (cột nào/dòng nào).
- **Constraints:** Không thêm dependency; không OCR/PDF mới; không refactor kiến trúc lớn; single-process; dùng runner hiện có (`quality_audit/cli.py` + `main.py`) để tạo `*_output.xlsx` và log.

---

## B) WBS (Work Breakdown)

| ID   | Workstream                         | Status   |
|------|------------------------------------|----------|
| P0-1 | Spine fix 1: Column Typing Core   | Done     |
| P0-2 | Spine fix 2: Evidence Gating      | Done     |
| P0-3 | Spine fix 3: Skip Classifier 2-phase | Done   |
| P1   | Regression & verification         | Done     |
| P2   | Persist plan & docs               | Done     |

---

## C) Integrated Decisions

- **Quyết định 1:** Thực hiện đúng thứ tự Spine fix 1 -> 2 -> 3. Spine fix 1 là nền tảng (role-based exclude) để đạt hard-stop.
- **Quyết định 2:** Điểm tích hợp Column Typing: module `quality_audit/utils/column_roles.py` với `infer_column_roles(df, header_row, context) -> (roles, confidences, evidence)`. Mọi nơi dùng code-column exclude chuyển sang role-based (ROLE_CODE luôn bị loại khỏi sum/compare/CY-PY).
- **Quyết định 3:** Evidence Gating đặt trước khi validator tính toán. Nếu không có ROLE_NUMERIC đủ tự tin => NO_EVIDENCE; extraction quality = 0 hoặc known-bad => EXTRACT_ERROR; không "silent skip".
- **Quyết định 4:** Skip Classifier 2-phase: Phase 1 — positive evidence (footer/signature); Phase 2 — negative evidence (currency, year, financial row labels). Chỉ SKIP khi phase_1 mạnh và phase_2 yếu; nếu mơ hồ => KHÔNG SKIP.

---

## D) Action Plan (reference)

- **Spine 1:** `infer_column_roles` trong `quality_audit/utils/column_roles.py`; tích hợp vào base_validator, generic_validator, table_normalizer; ROLE_CODE exclude toàn cục.
- **Spine 2:** Gate reason constants trong `quality_audit/config/constants.py`; gate trong generic_validator và base_validator với gate_decision + evidence.
- **Spine 3:** `quality_audit/utils/skip_classifier.py`; tích hợp trong word_reader, generic_validator._should_skip_table, audit_service.

---

## E) Verification Checklist

- **Commands:**
  - `pytest tests/ -v --tb=short` (scope: validators, column_detector, table_normalizer, test_code_detection, test_generic_validator_code_column_and_netting).
  - `python -m quality_audit.cli <path_to_folder_with_3_golden_docx> --output-dir results --log-level INFO`; kiểm tra `results/*_output.xlsx` và log.
  - `python -m ruff check quality_audit/`
- **Pass criteria:**
  - Toàn bộ test liên quan pass; không regress.
  - Trên 3 golden docs: không còn FAIL do cột Code bị cộng; bảng share capital/equity không có rule_id SKIPPED_FOOTER_SIGNATURE khi là bảng dữ liệu thật; bảng thiếu numeric/Cash Flow → status NO_EVIDENCE hoặc EXTRACT_ERROR với evidence trong output.
- **Edge cases:** Bảng chỉ có Code + Label + 2 cột năm; cột Note/Ref; header "Code" với giá trị số; footer thật vs bảng vốn cổ phần có số.

---

## F) Risk / Rollback

- **Risks:** (1) Column role heuristic quá chặt → bảng đang PASS thành NO_EVIDENCE; giảm bằng ngưỡng numeric_density và header hint an toàn. (2) Skip classifier thiếu từ khóa negative → vẫn SKIP nhầm; bổ sung từ khóa vốn/cổ phần và golden.
- **Rollback:** Feature flag trong `quality_audit/config/feature_flags.py` cho spine_fix_2 / spine_fix_3 nếu cần; spine_fix_1 (exclude ROLE_CODE) mặc định ON. Revert commit từng spine nếu cần.
- **Monitoring:** Log gate_decision, column_roles, skip decision + evidence; theo dõi phân bố status (PASS/FAIL/NO_EVIDENCE/EXTRACT_ERROR/SKIPPED_*).
