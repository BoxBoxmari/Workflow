# Immediately Plan — Workflow MVP UI/UX Refactor + Technical Stabilization (Final, Local-First Only)

## 1) Mục tiêu thực thi ngay

Refactor sản phẩm từ mô hình UI phân mảnh hiện tại sang **single-workspace workflow workbench** với các đặc tính sau:

- dễ hiểu với user non-tech,
- vẫn đủ trực quan để thấy workflow step-by-step,
- hỗ trợ quan sát prompt, input, output, file attachment, run status,
- biểu diễn được sequential flow và structured branching,
- không cần drag-and-drop,
- không đổi framework,
- không phá compatibility với config, prompt, history hiện tại,
- mọi persistence đều **local-first**, không có bất kỳ database setup bên ngoài nào.

Song song với refactor UI, bổ sung ngay một lớp **stability + control** để tránh:

- callback rối,
- file config corrupt,
- state reload đè draft,
- UI và runtime dính cứng vào nhau,
- refactor xong nhưng không kiểm soát được behavior.

---

## 2) Hard constraints

### 2.1. Local-first only
Tất cả dữ liệu, trạng thái và chỉ mục phục vụ app phải nằm **cục bộ trên máy**.

### 2.2. Không có DB setup bên ngoài
Không được dùng bất kỳ hạ tầng database hay service nào cần cài đặt, khởi chạy hoặc cấu hình riêng ngoài app.

**Không được phép:**
- PostgreSQL
- MySQL
- MariaDB
- MongoDB
- Redis
- Supabase
- Neon
- Elasticsearch
- Vector DB riêng
- bất kỳ database server/container/service chạy nền ngoài app

### 2.3. Chỉ cho phép embedded local storage
Nếu cần khả năng query/index ở mức cao hơn file JSON/CSV, chỉ được dùng **local embedded file-based engine** nằm trong app process.

Điều đó có nghĩa là:
- **được phép**: JSON, JSONL, CSV, TXT, in-memory cache, SQLite local file
- **không được phép**: bất kỳ DB nào cần setup infra riêng

### 2.4. Source of truth vẫn là file-based
Nguồn dữ liệu chính phải tiếp tục là file-based storage hiện tại. Bất kỳ lớp index/query nào nếu xuất hiện sau này cũng chỉ là **local embedded sidecar**, không phải source of truth.

---

## 3) Quyết định kiến trúc

### Quyết định 1 — Không big-bang rewrite
Áp dụng **strangler refactor**:

- giữ `core/` gần như nguyên trạng trong pha đầu,
- dựng workspace UI mới song song,
- cho workspace mới làm màn hình mặc định,
- các panel cũ chỉ giữ như legacy fallback trong giai đoạn chuyển tiếp.

### Quyết định 2 — Giữ tkinter
Không đổi sang web, không đổi framework.

Lý do:
- đúng mục tiêu local MVP,
- đúng tinh thần low-tech / non-code,
- không phát sinh migration không cần thiết.

### Quyết định 3 — Tách UI refactor khỏi runtime semantics upgrade
**Phase đầu**:
- đổi UI shell,
- flow cards,
- inspector,
- result drawer,
- structured branch visualization,
- runtime vẫn **sequential**.

**Phase sau**:
- thêm execution planner đọc `depends_on`,
- nâng runner lên **topological sequential execution**,
- chưa làm parallel thật.

### Quyết định 4 — Refactor UI phải đi kèm technical enablers ngay
Không chỉ thay giao diện. Phải làm ngay các nền kỹ thuật sau:
- UI event bus,
- atomic write,
- schema migration,
- enum hóa state/status,
- view-model layer,
- dirty-state guard,
- theme system.

Nếu không thêm lớp này, UI mới sẽ nhanh chóng biến thành một phiên bản khác của `app.py` hiện tại: to, rối, khó bảo trì.

---

## 4) Giữ gì, thay gì, thêm gì

### 4.1. Giữ lại
Các phần giữ làm nền:

- `core/config_service.py`
- `core/storage.py`
- `core/prompts.py`
- `core/ingestion.py`
- `core/provider.py`
- `core/config_validation.py`

Giữ run history storage hiện có:
- `run.json`
- `steps/*.json`
- `events.jsonl`
- `index.csv`

Các phần này đủ tốt cho:
- recent runs sidebar,
- result drawer,
- history replay,
- run inspection.

### 4.2. Hạ vai trò / legacy only
Các module UI cũ không còn là interaction model chính:

- `ui/workflow_panel.py`
- `ui/detail_panel.py`
- `ui/design_studio.py`
- `ui/history_panel.py`
- `ui/workflow_editor.py`

Chúng chỉ tồn tại tạm thời để giảm rủi ro chuyển đổi.

### 4.3. Refactor mạnh
- `ui/app.py`

`App` chỉ nên còn:
- bootstrap service,
- tạo root window,
- khởi tạo theme,
- khởi tạo controller,
- mount workspace shell.

### 4.4. Tạo mới
#### UI shell và orchestration
- `ui/workspace_shell.py`
- `ui/sidebar_panel.py`
- `ui/flow_canvas.py`
- `ui/inspector_panel.py`
- `ui/result_drawer.py`
- `ui/workspace_controller.py`
- `ui/workspace_state.py`
- `ui/viewmodels.py`
- `ui/theme.py`

#### Core model/control
- `core/workflow_graph.py`
- `core/workflow_layout.py`
- `core/events.py`
- `core/io_utils.py`
- `core/migrations.py`
- `core/enums.py`
- `core/commands.py`
- `core/execution_plan.py` *(phase sau)*

#### Optional soon-after, vẫn local-only
- `state/session.json`
- local embedded run index (`runs/index.db` hoặc `runs/index.sqlite3`) **nếu thật sự cần tối ưu history/search**

Lưu ý: local embedded run index chỉ là **file local trong máy**, không phải DB setup bên ngoài, không phải source of truth, và không phải dependency bắt buộc cho phase đầu.

---

## 5) Target architecture

### 5.1. Single workspace layout
#### Top bar
- workflow name
- save
- run
- run from selected step
- mode toggle: `Simple / Advanced`
- view toggle: `Design / Results`

#### Left sidebar
- workflow list
- create/duplicate workflow
- recent runs
- open run results

#### Center canvas
- flow cards theo trục dọc
- support structured branch lanes
- inline status / output preview

#### Right inspector
- edit step đang chọn
- prompt
- input/output
- files needed
- dependency / lane settings theo ngôn ngữ thân thiện

#### Bottom drawer
- full input
- full output
- raw response
- metrics
- event log

### 5.2. Controller-centered architecture
`WorkspaceController` là nơi điều phối trung tâm:
- workflow selection
- step selection
- dirty state
- drafts
- run state
- history selection
- inline preview
- UI event dispatch
- undo/redo stack
- sync giữa canvas và inspector

UI panels không được nói chuyện trực tiếp với `ConfigService` theo kiểu tự phát như hiện tại.

### 5.3. View-model layer bắt buộc
Không render trực tiếp từ `WorkflowDef`.

Phải có lớp trung gian:
- `FlowNodeViewModel`
- `FlowEdgeViewModel`
- `StepInspectorViewModel`

Nguồn dữ liệu:
- `core/workflow_graph.py` build graph từ workflow
- `core/workflow_layout.py` tính lane, depth, merge markers
- `ui/viewmodels.py` map sang dữ liệu render

---

## 6) Data model và compatibility

### 6.1. Giữ nguyên nghĩa của `StepDef.name`
`name` vẫn là **prompt template key**. Không đổi.

### 6.2. Mở rộng `StepDef`
Bổ sung tối thiểu:

```python
title: str = ""
purpose: str = ""
ui: dict[str, Any] = field(default_factory=dict)
```

Ý nghĩa:
- `title`: tên hiển thị cho user
- `purpose`: mô tả ngắn
- `ui`: metadata UI như `lane`, `collapsed`, `branch_group`, `color_tag`

### 6.3. Không lưu freeform coordinates
Không lưu `x`, `y`.

Chỉ lưu:
- `ui.lane`
- `ui.branch_group`
- `ui.collapsed`

### 6.4. Schema version + migration layer
Thêm top-level:
- `schema_version`

Thiết lập:
- version 1 = format hiện tại
- version 2 = thêm `title`, `purpose`, `ui`, normalize `depends_on`, attachment defaults

Load pipeline:
1. parse raw
2. detect version
3. migrate lên current
4. normalize defaults
5. validate

### 6.5. Normalize vấn đề `depends_on`
Phải chuẩn hóa ngay:
- `null` -> `[]`
- string đơn -> `[string]` nếu có legacy case
- missing -> `[]`

Đây là điều kiện bắt buộc để branch visualization và execution planner không lỗi ngầm.

---

## 7) Branching model

### 7.1. Phase hiện tại
Branch chỉ cần **hiển thị có cấu trúc**, runtime vẫn sequential.

Nguồn logic:
- `depends_on` cho edge
- `ui.lane` cho placement
- thứ tự `workflow.steps` vẫn được giữ ổn định khi save

### 7.2. Không drag-and-drop
Chỉ hỗ trợ button-driven editing:
- Add below
- Add branch
- Move up
- Move down
- Move lane left
- Move lane right
- Merge after selected

### 7.3. Merge step
Merge step là step có:

- `depends_on = [branch_leaf_a, branch_leaf_b, ...]`

Không tạo node type đặc biệt ở runtime phase đầu.

---

## 8) Runtime plan

### 8.1. Runtime hiện tại
`core/workflow.py` giữ execution kiểu sequential.

Không đổi runner ở đợt đầu.

### 8.2. Runtime phase sau
Thêm `core/execution_plan.py` để:
- build dependency graph
- validate missing deps
- detect cycle
- mark merge points
- sinh topological order
- tính reachable steps cho run-from-step

### 8.3. Compatibility rule khi lên planner
1. Step có `depends_on` rõ  
   → dùng explicit dependencies

2. Step không có `depends_on`  
   → fallback theo list order semantics hiện tại

3. Workflow branch mode mới  
   → phải set dependency rõ

### 8.4. Chưa làm
Không làm ở đợt này:
- parallel execution
- asyncio hóa app
- concurrent provider calls per branch

---

## 9) Storage strategy cuối cùng

### 9.1. Source of truth
Nguồn dữ liệu chính vẫn là file-based local storage:
- `workflows.json`
- `config/prompts/*.txt`
- `runs/<run_id>/run.json`
- `runs/<run_id>/steps/*.json`
- `runs/<run_id>/events.jsonl`
- `state/session.json` *(khi thêm session persistence)*

### 9.2. Optimization layer chỉ là local embedded sidecar
Nếu sau này history/search/filter chậm rõ rệt, có thể thêm **local embedded run index**:
- `runs/index.db`
- hoặc `runs/index.sqlite3`

Điều kiện:
- chỉ là file local trong máy,
- không cần cài DB server,
- không cần setup infra,
- không phải source of truth,
- chỉ dùng cho index/query convenience.

### 9.3. Fallback bảo thủ nếu muốn tránh mọi khái niệm “DB”
Có thể giữ hoàn toàn file-based bằng:
- `runs/index.json`
- hoặc `runs/index.csv`
- cộng với in-memory cache khi app mở

Kết luận storage:
- **phase đầu không bắt buộc phải có local embedded index**
- **phase đầu đủ dùng với file-based + in-memory cache**
- local embedded index chỉ là tối ưu tùy chọn, vẫn nằm hoàn toàn trong local-only constraint

---

## 10) File attachment plan

### 10.1. Giữ attachment slot ở step definition
`attachments: list[AttachmentSlot]` vẫn nằm trong `StepDef`.

### 10.2. Không lưu file binding runtime vào `workflows.json`
Path file runtime là session data, không phải design config.

### 10.3. Session binding
#### P0
- chỉ giữ trong `WorkspaceState`

#### P1
- lưu vào `state/session.json` hoặc `state/recent_bindings.json`

### 10.4. UI hiển thị file theo step
Mỗi step hiển thị:
- required / optional
- attached / missing
- attach / replace / remove
- preview ingestion summary

Không dùng bảng attachment toàn cục làm interaction model nữa.

---

## 11) Prompt editing plan

### 11.1. Prompt editor chính
Prompt editing chính nằm trong:
- inspector
- hoặc full editor như secondary action

Không dùng `DesignStudioPanel` làm entrypoint chỉnh prompt nữa.

### 11.2. Prompt versioning
Giữ nguyên file system:
- `config/prompts/{step_name}_v{version}.txt`

### 11.3. Tách rõ 3 lớp tên
- `step.id` = runtime identity
- `step.name` = prompt template key
- `step.title` = user-facing title

---

## 12) State management plan

### 12.1. Tạo `WorkspaceState` mới
Không vá tiếp `DesignerState`.

Tối thiểu có:

```python
selected_workflow_id: str | None
selected_step_id: str | None
selected_run_id: str | None
mode: WorkspaceMode
view: WorkspaceView
workflow_drafts: dict[str, WorkflowDef]
prompt_drafts: dict[str, str]
run_step_results: dict[str, StepResult]
attachment_bindings: dict[str, str]
drawer_tab: DrawerTab
is_dirty: bool
is_running: bool
external_change_detected: bool
undo_stack: list[Command]
redo_stack: list[Command]
```

### 12.2. Chuẩn hóa state/status bằng `StrEnum`
Tạo `core/enums.py` với:
- `RunStatus`
- `StepStatus`
- `WorkspaceMode`
- `WorkspaceView`
- `DrawerTab`

Serialization vẫn dùng `.value`.

---

## 13) Technical enablers bắt buộc đi cùng refactor

### 13.1. UI event bus
Chuẩn hóa thread handoff qua queue.

Thiết kế:
- background worker đẩy event vào queue
- main thread poll queue theo chu kỳ bằng `root.after`
- chỉ `WorkspaceController` xử lý dispatch/update UI

Event types tối thiểu:
- `RunStarted`
- `StepStarted`
- `StepFinished`
- `RunFinished`
- `RunFailed`
- `ConfigReloaded`
- `HistoryLoaded`

### 13.2. Atomic write
Tạo `core/io_utils.py`:
- `atomic_write_text()`
- `atomic_write_json()`

Áp dụng cho:
- `workflows.json`
- `index.csv`
- `run.json`
- `steps/*.json`
- `events.jsonl` nếu cần append-safe strategy riêng

Optional:
- tạo `.bak` cho config quan trọng

### 13.3. Dirty-state guard + debounced watcher
Watcher không được auto reload bừa.

Rule:
- nếu `is_dirty == True` → không reload ngay
- chỉ set `external_change_detected = True`
- UI hiển thị thông báo nhẹ: “Config changed on disk. Reload?”
- auto reload chỉ diễn ra khi:
  - không dirty
  - hoặc vừa save xong
  - hoặc user chủ động reload

### 13.4. Centralized ttk theme
Tạo `ui/theme.py` với:
- spacing tokens
- font tokens
- card style
- badge style
- state colors
- selected/focus style

Mọi panel dùng style name, không patch widget rời rạc.

### 13.5. Undo/redo command stack
Tạo `core/commands.py`.

Mỗi thao tác chỉnh workflow là command có:
- `do()`
- `undo()`
- `label`

Áp dụng cho:
- add/delete step
- duplicate
- change title/purpose
- move lane
- merge branch
- attach/remove file binding
- change prompt draft

---

## 14) Logging, caching, local index, tests — immediate roadmap sau khi workspace nền đứng vững

Các mục này không cần block Phase 0, nhưng phải nằm trong immediate roadmap, không đẩy thành “someday”.

### 14.1. Structured logging
Thiết lập logger namespace:
- `workbench.ui`
- `workbench.core`
- `workbench.storage`
- `workbench.workflow`

Log các event chính:
- workflow loaded
- step selected
- run started
- run finished
- config reloaded
- migration applied

### 14.2. Prompt/layout cache
Dùng cache cho:
- load prompt
- build workflow graph
- compute layout

Không cache provider output.

### 14.3. Local embedded run index (optional optimization only)
Giữ file-based storage là source of truth:
- `runs/<run_id>/run.json`
- `steps/*.json`
- `events.jsonl`

Nếu cần tối ưu history/search/filter/compare sau này, có thể thêm:
- `runs/index.db` hoặc `runs/index.sqlite3`

Mục đích:
- recent run load nhanh
- filter/search run tốt hơn
- compare step/run nhanh hơn
- thống kê basic latency/error

Nếu muốn cực kỳ bảo thủ, có thể thay bằng:
- `runs/index.json`
- hoặc `runs/index.csv`
- cộng với in-memory cache

### 14.4. Golden-file tests
Tạo test cho:
- migration
- graph/layout snapshot
- workflow dry-run semantics

Đây là lớp test quan trọng nhất để refactor UI mà không gãy behavior.

### 14.5. Session state
Chuẩn bị:
- `state/session.json`

Có thể lưu:
- workflow đang mở
- step đang chọn
- drawer tab
- mode
- recent file bindings

---

## 15) Phase plan thực thi

### Phase 0 — Stabilization groundwork
Làm ngay trước khi dựng workspace mới.

1. Thêm `schema_version`, migration, normalize defaults
2. Mở rộng `StepDef` với `title`, `purpose`, `ui`
3. Chuẩn hóa `depends_on`
4. Tạo `core/enums.py`
5. Tạo `core/io_utils.py` cho atomic write
6. Tạo `core/events.py`
7. Tạo `ui/theme.py`
8. Tách orchestration khỏi `ui/app.py`
9. Tạo `ui/workspace_state.py`
10. Viết `WorkflowDef -> ViewModel adapter`

**Done của Phase 0**:
- config cũ vẫn load được
- save không còn ghi thẳng non-atomic
- app có controller/state/theme/event bus nền
- chưa cần workspace hoàn chỉnh

### Phase 1 — Single workspace shell
1. Dựng `workspace_shell`
2. Dựng sidebar
3. Dựng flow canvas khung
4. Dựng inspector
5. Dựng result drawer
6. Cho workspace mới làm default entrypoint

**Done của Phase 1**:
- user mở app thấy một workspace chính
- có thể chọn workflow, chọn step, xem inspector
- chưa cần branch đầy đủ

### Phase 2 — Flow card interaction
1. Step cards
2. Select step
3. Add below
4. Duplicate
5. Delete
6. Prompt preview
7. File chips
8. Undo/redo cho thao tác cơ bản

**Done của Phase 2**:
- workflow edit cơ bản thực hiện được hoàn toàn trong workspace mới

### Phase 3 — Structured branching
1. Lane rendering
2. Add branch
3. Move lane
4. Merge after selected
5. Connector đơn giản
6. Graph/layout snapshot tests

**Done của Phase 3**:
- user nhìn được flow dạng nhánh
- save/load branch metadata ổn
- runtime vẫn sequential nhưng UI branch nhất quán

### Phase 4 — Run observability
1. Event bus gắn với runner
2. Active step highlight
3. Inline output preview
4. Step error inline
5. Drawer raw/metrics/log
6. History replay

**Done của Phase 4**:
- user run workflow và theo dõi kết quả trong cùng workspace

### Phase 5 — Execution planner + local indexing optimization
1. `core/execution_plan.py`
2. topological sequential order
3. run-from-step
4. local embedded run index nếu thực sự cần
5. structured logging mở rộng
6. session persistence

**Done của Phase 5**:
- branch-aware execution semantics bắt đầu đúng hơn
- history/search mượt hơn rõ rệt khi cần tối ưu
- vẫn không có bất kỳ DB setup bên ngoài nào

---

## 16) Module map cuối cùng

### Tạo mới ngay
- `ui/workspace_shell.py`
- `ui/workspace_controller.py`
- `ui/workspace_state.py`
- `ui/sidebar_panel.py`
- `ui/flow_canvas.py`
- `ui/inspector_panel.py`
- `ui/result_drawer.py`
- `ui/viewmodels.py`
- `ui/theme.py`
- `core/workflow_graph.py`
- `core/workflow_layout.py`
- `core/events.py`
- `core/io_utils.py`
- `core/migrations.py`
- `core/enums.py`
- `core/commands.py`

### Tạo sau nhưng đã nằm trong immediate roadmap
- `core/execution_plan.py`
- `state/session.json`
- local embedded run index file *(optional, only if needed)*

### Refactor mạnh
- `ui/app.py`

### Tái sử dụng có chỉnh sửa
- `core/config_service.py`
- `core/storage.py`
- `core/models.py`
- `core/config_validation.py`

### Legacy only
- `ui/design_studio.py`
- `ui/workflow_panel.py`
- `ui/detail_panel.py`
- `ui/history_panel.py`
- `ui/workflow_editor.py`

---

## 17) Rủi ro kỹ thuật và khóa rủi ro

### Rủi ro 1 — Gãy prompt compatibility
Khóa:
- giữ `name` là prompt key
- thêm `title` riêng

### Rủi ro 2 — UI branch vượt quá runtime thật
Khóa:
- branch view chỉ là structured flow view
- không claim parallel execution
- docs và label phải trung thực

### Rủi ro 3 — Config reload đè draft
Khóa:
- dirty-state guard
- debounce watcher
- explicit reload flow

### Rủi ro 4 — Controller thành god object lần 2
Khóa:
- event bus
- command stack
- view-model layer
- panel không thao tác service trực tiếp

### Rủi ro 5 — Tkinter canvas quá phức tạp
Khóa:
- không làm freeform canvas
- dùng scrollable frame + lane containers
- connector đơn giản

### Rủi ro 6 — History/search chậm khi run data tăng
Khóa:
- phase đầu dùng file-based + in-memory cache
- chỉ thêm local embedded index khi có nhu cầu thực
- không dùng bất kỳ DB setup bên ngoài nào

---

## 18) Acceptance criteria

Plan này được coi là đạt nếu:

1. Một workflow có thể:
   - mở
   - chỉnh
   - save
   - run
   - replay history  
   trong **một workspace chính**

2. User nhìn từng step card là hiểu:
   - step làm gì
   - đọc input từ đâu
   - ghi output ra đâu
   - có cần file không
   - đang draft/running/done/error

3. `workflows.json` cũ vẫn load được

4. Prompt files cũ vẫn load/save được

5. Run history cũ vẫn mở được

6. Branch view hiển thị được mà không cần drag-and-drop

7. Runtime phase đầu vẫn chạy ổn với workflow cũ

8. Save config/run artifacts an toàn hơn, không ghi thẳng kiểu dễ corrupt

9. UI không còn phụ thuộc vào callback phân tán từ background thread

10. Có nền kỹ thuật đủ sạch để phase execution planner không biến thành rewrite lần hai

11. Toàn bộ persistence vẫn local-first, không phát sinh bất kỳ DB setup ngoài app

---

## 19) Kết luận chốt

Immediately Plan cuối cùng được chốt như sau:

- **Strangler refactor, không big-bang**
- **Giữ Python + tkinter**
- **Single workspace là kiến trúc UI đích**
- **Thêm `title`, `purpose`, `ui` vào `StepDef`**
- **Giữ `name` là prompt key**
- **Structured branching dùng `depends_on + ui.lane`**
- **Phase đầu chỉ đổi UI + interaction model, runtime vẫn sequential**
- **Bắt buộc làm cùng lúc các technical enablers:**
  - UI event bus
  - atomic write
  - schema migration
  - StrEnum state model
  - view-model layer
  - dirty-state guard
  - centralized theme
  - undo/redo command stack
- **Ngay sau khi workspace ổn định, đưa vào nếu cần:**
  - execution planner
  - structured logging
  - prompt/layout cache
  - golden-file tests
  - session state
  - local embedded run index optimization
- **Mọi thứ liên quan đến persistence/index/query đều phải local-only; không có bất kỳ DB setup bên ngoài nào**

Đây là bản plan đủ chặt để đi thẳng vào implementation mà không bị trôi sang redesign mơ hồ, technical debt mới, hay phát sinh hạ tầng trái với mục tiêu MVP local-first.
