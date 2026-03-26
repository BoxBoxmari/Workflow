# Project Todos

## Active

- [ ] Hoàn tất vận hành release: version/tag, release notes, artifact, deploy smoke test, rollback drill, sign-off

## Completed

- [x] One-shot fix REL-001: serialize `events.jsonl` append qua `StorageWriteQueue` + `fsync` + retry lock | Done: 03/26/2026
- [x] One-shot fix SEC-002: bỏ fallback plaintext credentials từ `provider.json`, chỉ nhận secure store/env | Done: 03/26/2026
- [x] One-shot fix REL-003: chuẩn hóa UI messagebox qua adapter `ui/dialogs.py` ở các panel chính | Done: 03/26/2026
- [x] Chạy `python -m pytest tests/ -q --tb=no` — PASS (exit 0), 8 skipped | Done: 03/22/2026
- [x] Rà soát P0 register (schema create, scope save, cancel cross-thread) qua codepath + test suite | Done: 03/24/2026
- [x] Rà soát + xử lý CVE theo gate `python -m pip_audit` (verifier: exit code 0) | Done: 03/24/2026
- [x] Dọn docs/scripts không cần thiết + cập nhật docs vận hành (README/QA/matrix) | Done: 03/24/2026
