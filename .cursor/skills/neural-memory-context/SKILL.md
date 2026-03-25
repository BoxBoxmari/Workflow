---
name: neural-memory-context
description: Retrieves long-term project context from NeuralMemory (CLI or HTTP) and prepends it to the current task. Use proactively before complex reasoning, debugging, or design tasks that depend on historical decisions, fixes, or insights.
---

# NeuralMemory Context Skill

## Mục tiêu

Skill này giúp agent:
- Lấy **context dài hạn** từ NeuralMemory cho **project hiện tại** (codebase đang mở).
- Biến context đó thành một block văn bản ngắn gọn, dễ tiêm vào prompt.
- **Prepend** block này lên đầu câu trả lời hoặc lên đầu yêu cầu gửi tiếp cho subagent khác.

> Ý tưởng: NeuralMemory là “bộ nhớ dài hạn toàn cục”, còn skill này là cầu nối giữa Cursor và NeuralMemory.

---

## Chế độ hoạt động

Skill hỗ trợ **2 chế độ**, tùy cách bạn đã cài NeuralMemory:

1. **CLI mode** – dùng lệnh `nmem` (không có server HTTP).
2. **HTTP server mode** – gọi API của `neural_memory.server` qua HTTP.

Agent có thể chọn 1 trong 2 tùy môi trường của user.

---

## Bước 0 – Xác định project và query

Trước khi gọi NeuralMemory, luôn xác định:

1. **Tên project**:
   - Nếu user đã nói rõ (ví dụ: `"Quality Audit"`, `"work"`), dùng đúng chuỗi đó.
   - Nếu không:
     - Lấy tên thư mục repo hiện tại (ví dụ: `Quality Audit`) làm project name hợp lý, **rồi xác nhận nhanh với user** nếu có thể.

2. **Query** (tùy trường hợp):
   - Với lệnh `context` đơn thuần, có thể **không cần query**, chỉ lấy context mới nhất.
   - Nếu user đang hỏi về 1 chủ đề cụ thể (vd: “auth bug”, “FastAPI decision”), có thể dùng chính câu hỏi của user làm query cho HTTP mode (nếu API hỗ trợ).

---

## Chế độ 1 – CLI (`nmem context`)

### Khi nào dùng

Sử dụng khi:
- User đã cài NeuralMemory CLI (`nmem`) global.
- Không (hoặc chưa) bật server HTTP `neural_memory.server`.

### Cách thực thi

1. Hỏi hoặc suy ra `PROJECT_NAME` như ở bước 0.
2. Chạy lệnh qua Bash tool:

```bash
nmem context --project "<PROJECT_NAME>" --limit 10 --json
```

3. Nhận JSON trả về, trích từng memory quan trọng:
   - `type` (fact/decision/insight/todo/context/…),
   - `text` hoặc `content`,
   - `created_at`, `priority` hoặc `project` nếu có.

4. Biến thành block text gọn:

```text
[NeuralMemory Context - project "<PROJECT_NAME>"]

1) <type>: <tóm tắt nội dung> (thời gian/ưu tiên nếu có)
2) ...
```

5. **Prepend** block này vào trước:
   - phần reasoning/câu trả lời của chính agent, hoặc
   - phần prompt khi agent chuẩn bị “nhờ” subagent khác (bằng cách chèn block này lên đầu nội dung bạn gửi cho subagent).

### Xử lý lỗi

Nếu lệnh `nmem` lỗi (không cài, sai project, JSON hỏng, v.v.):

```text
[NeuralMemory Context] Không thể lấy context từ CLI (nmem) cho project "<PROJECT_NAME>".
```

Sau đó tiếp tục thực hiện task với thông tin đang có (không được bịa nội dung NeuralMemory).

---

## Chế độ 2 – HTTP server (`neural_memory.server`)

### Khi nào dùng

Sử dụng khi:

- User đã chạy:

```bash
uvicorn neural_memory.server:app --host 127.0.0.1 --port 8000
```

- Bạn có thể gọi HTTP tới `http://127.0.0.1:8000`.

### Cách thực thi (gợi ý)

1. Hỏi hoặc suy ra `PROJECT_NAME` như ở bước 0.
2. Tùy API thực tế của server (user có thể tùy chỉnh), mẫu payload đề xuất:

```bash
curl -s -X POST "http://127.0.0.1:8000/memory/query" \
     -H "Content-Type: application/json" \
     -d "{\"query\": \"<USER_QUESTION_HOẶC_KEYWORD>\", \"limit\": 10, \"project\": \"<PROJECT_NAME>\"}"
```

3. JSON trả về được parse tương tự CLI mode:
   - lấy danh sách memories,
   - format thành block:

```text
[NeuralMemory HTTP Context - project "<PROJECT_NAME>"]

1) <type>: <tóm tắt nội dung> (thời gian nếu có)
2) ...
```

4. Prepend block này giống hệt CLI mode.

### Xử lý lỗi

Nếu request HTTP thất bại (timeout, connection refused, JSON không hợp lệ, endpoint khác schema…):

```text
[NeuralMemory HTTP Context] Không thể kết nối server tại http://127.0.0.1:8000 cho project "<PROJECT_NAME>".
```

Rồi tiếp tục task mà **không bịa** nội dung “memory”.

---

## Cách agent nên sử dụng skill này

### 1. Khi là “orchestrator” (pattern 1)

Nếu bạn đang đóng vai **orchestrator**:

1. Trước khi giao task cho subagent, hãy:
   - Áp dụng skill `neural-memory-context` cho project tương ứng để lấy block context.
2. Sau đó khi bạn “giao việc” cho subagent (dù là bằng lời trong prompt), luôn đặt block context đó ở đầu:

```text
[NeuralMemory Context - project "<PROJECT_NAME>"]
1) ...

--- Task dành cho subagent X ---
...
```

Subagent không cần biết NeuralMemory là gì; nó chỉ thấy thêm phần context ở trên.

### 2. Khi là “memory-aware worker” (pattern 2)

Nếu bạn là subagent/agent có nhiệm vụ chính (review code, debug, thiết kế kiến trúc…) và muốn tự mình dùng trí nhớ dài hạn:

1. Ngay khi nhận task mới:
   - Áp dụng skill `neural-memory-context` với project hiện tại.
2. Dùng block context đó để:
   - định hình giả thuyết,  
   - tránh lặp lại quyết định đã có,  
   - ưu tiên các thông tin từng gây bug, quyết định quan trọng, insight.
3. Khi trả lời user, có thể giữ lại block context (nếu hữu ích) hoặc chỉ dùng nội bộ tùy yêu cầu.

### 3. Khi làm “Memory subagent” (pattern 3)

Nếu bạn được thiết kế chuyên cho việc “cung cấp trí nhớ” cho các agent/subagent khác:

1. Nhận yêu cầu kiểu: “hãy đưa context NeuralMemory cho project X về chủ đề Y”.
2. Áp dụng skill này:
   - chạy CLI/HTTP như trên,
   - tóm tắt thành block chuẩn.
3. Trả về **chỉ block context** cho caller, không phân tích thêm.

Caller sau đó sẽ ghép block đó vào prompt của nó.

---

## Lưu ý bảo mật

- Tin rằng NeuralMemory đã được cấu hình với:
  - `nmem check` và `--redact` cho nội dung nhạy cảm.
- Không tự ý thêm secret/API key vào log hoặc output.
- Khi export/báo cáo, nếu cần, khuyến nghị user dùng:

```bash
nmem brain export --exclude-sensitive -o safe.json
```

---

## Tóm tắt cho agent

1. Xác định `PROJECT_NAME`.
2. Chọn CLI (`nmem context`) hoặc HTTP (`/memory/query`) tùy môi trường user.
3. Parse JSON → tạo block `[NeuralMemory Context - project "…"]`.
4. Prepend block đó lên đầu prompt/câu trả lời hoặc khi giao task cho subagent.
5. Không bịa nội dung NeuralMemory nếu lệnh/API lỗi; chỉ ghi rõ là “không lấy được context”.

