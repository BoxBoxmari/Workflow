## User Defined Namespaces
- [Leave blank - user populates]

## Patterns

### Attachments UI (simple vs advanced)

- **Simple mode**: `ui/inspector_panel.py::_refresh_att_badge` và `ui/flow_canvas.py::_build_modal_content` hiển thị tối giản phần tệp đính kèm (tiêu đề, trạng thái, 1 nút “Đính kèm tệp/Thay tệp”). Nếu step chưa có `AttachmentSlot` thì tự tạo 1 slot ngầm định (label “Tệp đính kèm”) và bind theo `slot_key = "{step_id}::{slot_id}"`.
- **Advanced mode**: vẫn giữ UI cấu hình chi tiết `AttachmentSlot` (label/variable/accepted types/required, apply/remove slot).

### Type-checking (mypy) – monkey-patch Tkinter và union stacks

- **Tkinter monkey-patch**: Khi cần gán/patch phương thức trên `_tk.Misc`, dùng `setattr(cast(Any, _tk.Misc), "...", fn)` để tránh lỗi `mypy` kiểu `method-assign`/`attr-defined` trong `ui/app.py`.
- **DFS stack mixed types**: Nếu một stack chứa vừa marker `str` vừa tuple `(node, path)`, annotate kiểu union rõ ràng (ví dụ `list[tuple[str, list[str]] | str]`) để tránh lỗi `mypy` khi `append` trong `core/config_validation.py`.

### Storage index.csv – append-only + dedupe read-side

- **Append-only writes**: `core/storage.py::_update_index_impl()` luôn append 1 dòng mới vào `index.csv` cho cả run mới lẫn cập nhật trạng thái run cũ (tránh read-modify-write O(N)).
- **Dedupe contract**: `list_runs()` và `compact_index()` dedupe theo `run_id` với “last-write-wins” cho dữ liệu (status/finished_at/step_count…) nhưng **giữ thứ tự theo lần xuất hiện đầu tiên** của mỗi `run_id` để UI history ổn định (cập nhật run không bị nhảy xuống cuối).
- **Windows locking**: append có thể gặp `PermissionError` do file lock; `_append_to_index()` retry với backoff ngắn trước khi raise.

### Ingestion text normalization (AI-suitability)

- **Normalize line endings**: Chuẩn hoá `\r\n` và `\r` về `\n` trước khi truncate/ghi vào workflow input.
- **Collapse excessive blank lines**: Co `\n{3,}` về `\n\n` để giảm nhiễu khi đưa vào LLM/embedding.
- **Trim edges**: `strip()` để loại bỏ whitespace đầu/cuối nội dung.

