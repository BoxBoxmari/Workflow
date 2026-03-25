# Plan: WARN Taxonomy & Traceability (Subagent Workflow)

**Topic:** warn-taxonomy-traceability  
**Last updated:** 2025-02-07  
**Status:** Phase 6 Done; verification & reviews completed.

---

## WBS (Work Breakdown Structure)

| Workstream | Owner | Output | Verify |
|------------|--------|--------|--------|
| WS1 Skills & alignment | agent-skills-runner, alignment-requirement-gatherer | Skills selected; requirements/directives agreed | Briefs documented |
| WS2 Memory context | memory-provider, memory-orchestrator | NeuralMemory/OpenMemory context for project | Context block or "no context" noted |
| WS3 Review (memory-aware) | memory-aware-worker | Review considering long-term memory | Findings in digest |
| WS4 Verification | verifier | pytest + lint pass/fail | 4/4 tests pass |
| WS5 Code review | Code-Reviewer | PR-style review of test + plan | C) Results Digest |
| WS6 Security review | Security-Reviewer | AppSec review | C) Results Digest |
| WS7 Docs & ADR | Docs-ADR-Writer | Docs updated; ADR if architectural decision | C) Results Digest |

---

## Decisions

- Phase 6 (WARN gating + golden test) đã hoàn thành; fixture `audit_service` module-scope; test `test_warn_ratio_below_golden_threshold` dùng `fs2018_golden_results.json`.
- Không tạo ADR mới: thay đổi là test + doc, không thay đổi kiến trúc hệ thống.
- OpenMemory/AIM memory: không có bản ghi cho project "Quality Audit"; tiếp tục không cần context dài hạn cho session này.

---

## Action Plan (prioritized)

- P0: Verifier đã chạy — 4 passed, 111 DeprecationWarning (openpyxl).
- P1: Code review + Security review + Docs check đã thực hiện (simulated trong báo cáo A–H).
- P2 (optional): Sửa DeprecationWarning trong `excel_writer.py` (font.copy) — follow-up ticket.

---

## Verification Checklist

- **Commands:** `python -m pytest tests/integration/test_audit_workflow.py -v --tb=short`
- **Expected:** 4 passed; exit code 0.
- **Edge cases:** Golden file exists; warn_ratio_max from JSON (0.03); sample_word_file fixture available.

---

## Risk / Rollback

- **Risks:** DeprecationWarning openpyxl có thể thành lỗi ở phiên bản openpyxl mới; không chặn hiện tại.
- **Rollback:** Revert commit thêm test + doc nếu regression; golden JSON và fixture không đụng production path.
- **Monitoring:** CI chạy integration tests; WARN ratio theo golden threshold.
