## User Defined Namespaces
- [Leave blank - user populates]

## Patterns

### Attachments UI (simple vs advanced)

- **Simple mode**: `ui/inspector_panel.py::_refresh_att_badge` và `ui/flow_canvas.py::_build_modal_content` hiển thị tối giản phần tệp đính kèm (tiêu đề, trạng thái, 1 nút “Đính kèm tệp/Thay tệp”). Nếu step chưa có `AttachmentSlot` thì tự tạo 1 slot ngầm định (label “Tệp đính kèm”) và bind theo `slot_key = "{step_id}::{slot_id}"`.
- **Advanced mode**: vẫn giữ UI cấu hình chi tiết `AttachmentSlot` (label/variable/accepted types/required, apply/remove slot).

### Type-checking (mypy) – monkey-patch Tkinter và union stacks

- **Tkinter monkey-patch**: Khi cần gán/patch phương thức trên `_tk.Misc`, dùng `setattr(cast(Any, _tk.Misc), "...", fn)` để tránh lỗi `mypy` kiểu `method-assign`/`attr-defined` trong `ui/app.py`.
- **DFS stack mixed types**: Nếu một stack chứa vừa marker `str` vừa tuple `(node, path)`, annotate kiểu union rõ ràng (ví dụ `list[tuple[str, list[str]] | str]`) để tránh lỗi `mypy` khi `append` trong `core/config_validation.py`.

