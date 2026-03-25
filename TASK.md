# Alignment release — verification trail

## Context

Báo cáo trước nghi ngờ `EventBus.dispatch` truyền `Event` thẳng vào handler dùng `event.get`. Mã hiện tại đã chuẩn hóa payload dict trước khi gọi handler.

## Requirements

- [x] `pytest tests/` pass (bằng chứng dòng lệnh dưới đây)

## Verification Commands

```bash
cd "c:\Users\Admin\Downloads\Compressed\Workflow MVP 1"
python -m pytest tests/ -q --tb=no
```

## Evidence (session)

- Lệnh: `python -m pytest tests/ -q --tb=no -rs`
- Kết quả: **255 passed**, **8 skipped**, **3 subtests passed**, `exit_code: 0` (~37s, máy user).
- Skip: toàn bộ `tests/test_ui_smoke.py` — *No display available; skipping UI smoke tests.*
- Ngày cập nhật bằng chứng: 2026-03-22.

### P0 — bổ sung bằng chứng

- **Event → dict (`EventBus`)**: handler nhận payload dict (đã xác minh trước đó; suite xanh).
- **Cancel cross-thread**: `core/async_graph_runner.py` dùng `threading.Event` cho `_cancel_event`; `cancel()` gọi từ UI thread an toàn khi `asyncio.run` chạy worker.
- **Schema v3 khi save**: `ConfigService.save_workflows` ghi `schema_version: 3` (file + từng workflow). Roundtrip: `tests/core/test_schema_roundtrip.py`. Workflow mới in-memory mặc định `schema_version=3` (khớp `WorkflowDef` / UI); persist vẫn ghi v3.
- **Phạm vi Save**: `WorkspaceController.save()` lấy `list(self.state.workflow_drafts.values())` — validate và lưu **toàn bộ** draft trong workspace, không chỉ workflow đang chọn.

## Exit Criteria

- Toàn bộ tests pass (cho phép skip đã khai báo trong suite).

## Notes

- Lint: chưa có `ruff`/config rõ ở root; không khẳng định lint sạch.
- Các wave alignment trong todo nội bộ chỉ coi là đã xác minh khi có log tương tự.
