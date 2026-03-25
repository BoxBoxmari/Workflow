# Tech Plan — Async Multi-Input / Multi-Output Graph Upgrade for Workflow MVP

## Objective
Nâng cấp Workflow MVP từ execution model tuyến tính sang mô hình DAG bất đồng bộ có hỗ trợ nhiều đầu vào, nhiều đầu ra và fan-out / fan-in, nhưng vẫn giữ được độ an toàn cho MVP và không làm gãy các flow legacy đang ổn định.

Mục tiêu không phải là viết lại toàn bộ engine. Mục tiêu là cấy thêm một runtime path mới vào codebase hiện tại theo cách có thể kiểm soát, có rollback, có compatibility path, và có blast radius thấp.

## Current-State Conclusion
Codebase hiện tại không chỉ thiếu đa luồng. Nó đang bị khóa vào hợp đồng dữ liệu và runtime tuyến tính.

### Verified current behavior
- `core/workflow.py` là sequential runner thực sự: duyệt `enabled_steps` theo thứ tự và trả về đúng một `StepResult` cho mỗi step.
- `core/models.py` đang khóa `StepDef` vào mô hình scalar:
  - `input_mapping: str`
  - `output_mapping: str`
  - `depends_on: list[str]`
- `core/config_validation.py` validate theo chuỗi biến input/output tuyến tính, chưa validate graph theo port.
- `ui/inspector_panel.py` chỉ hỗ trợ một input variable và một output variable.
- `ui/result_drawer.py` chỉ render một `input_text` và một `output_text`.
- `ui/workspace_state.py` lưu `run_step_results: dict[str, StepResult]`, nghĩa là runtime state vẫn step-centric.
- `core/workflow_graph.py` và `core/execution_plan.py` đã có graph/topology cho planning và layout, nhưng chưa phải runtime scheduler.
- `core/events.py` đã có `EventBus` thread-safe, nhưng UI hiện tại chưa dùng `root.after(...)` làm main-thread event reduction path.

## Architectural Direction
Hướng đúng cho MVP là **dual-runner architecture**.

### Keep
- `WorkflowRunner` hiện tại tiếp tục là legacy sequential runner.
- `WorkflowDef.steps` tiếp tục là container chính cho editor/UI.
- `input_mapping`, `output_mapping`, `depends_on` tiếp tục được giữ lại cho legacy path và migration.
- `StepResult` tiếp tục là result object chính, nhưng được mở rộng.

### Add
- `execution_mode` trong `StepDef` để phân biệt `legacy` và `graph`.
- cấu trúc port-based mới bên trong `StepDef`:
  - `inputs: list[InputPortDef]`
  - `outputs: list[OutputPortDef]`
- `AsyncGraphRunner` mới cho graph runtime.
- event reduction qua main thread cho UI.
- graph-aware validation cho schema v3.

### Explicit non-direction
- Không vá `core/workflow.py` thành hybrid runner.
- Không rewrite editor model từ `steps` sang `nodes` ở đợt đầu.
- Không đưa Prefect, LangGraph, Airflow hoặc framework orchestration khác vào runtime.
- Không làm graph canvas thật trước khi runtime, validation và inspector ổn định.

## Design Principles
- Compatibility first: flow legacy phải tiếp tục chạy.
- Runtime correctness trước UI richness.
- Port-based semantics chỉ áp dụng cho graph path.
- Main-thread UI state mutation là rule cứng.
- Persistence mở rộng song song, không thay thế big-bang.
- Testability cao hơn cleverness.

## Proposed Module Changes

### Core runtime and contracts
- `core/models.py`
  - mở rộng `StepDef`
  - thêm `SourceRef`, `InputPortDef`, `OutputPortDef`
  - mở rộng `StepResult`
- `core/workflow.py`
  - giữ nguyên legacy runner, chỉ cleanup nếu cần
- `core/async_graph_runner.py`
  - file mới cho graph execution runtime
- `core/config_validation.py`
  - thêm graph-aware validation path
- `core/migrations.py`
  - thêm migration v2 -> v3
- `core/config_service.py`
  - load/save schema v3
- `core/events.py`
  - mở rộng event schema cho graph runtime
- `core/storage.py`
  - lưu graph artifacts song song với legacy artifacts

### UI and state
- `ui/app.py`
  - thêm event pump bằng `root.after(...)`
- `ui/workspace_controller.py`
  - subscribe event bus và reduce vào state
- `ui/workspace_state.py`
  - mở rộng runtime state cho node/port/event
- `ui/inspector_panel.py`
  - chuyển từ scalar mapping sang port editor
- `ui/result_drawer.py`
  - hiển thị Inputs / Outputs / Events / Provenance
- `ui/flow_canvas.py`
  - trước mắt thêm badge và metadata graph, chưa làm graph canvas hoàn chỉnh
- `core/commands.py`
  - thêm command cho port definitions và port bindings

## Schema Strategy
Không đổi top-level editor shape. Vẫn giữ:

```json
{
  "workflow_id": "wf_async_01",
  "name": "Workflow Async Demo",
  "steps": []
}
```

### StepDef v3 extension
```json
{
  "id": "s2",
  "name": "Aggregate Review",
  "execution_mode": "graph",
  "model": "gpt-4.1",
  "prompt_version": "v3",
  "input_mapping": "review_input",
  "output_mapping": "review_output",
  "depends_on": ["s1a", "s1b"],
  "inputs": [
    {
      "name": "drafts",
      "required": true,
      "join_strategy": "concat",
      "sources": [
        {"step_id": "s1a", "port": "draft"},
        {"step_id": "s1b", "port": "draft"}
      ]
    }
  ],
  "outputs": [
    {"name": "review_summary", "kind": "text", "exposed": true},
    {"name": "risk_flags", "kind": "json", "exposed": true}
  ],
  "enabled": true
}
```

### Compatibility rules
- `execution_mode = legacy`:
  - source of truth vẫn là `input_mapping`, `output_mapping`, `depends_on`
  - `inputs` và `outputs` có thể rỗng
- `execution_mode = graph`:
  - source of truth là `inputs` và `outputs`
  - các field scalar cũ chỉ còn vai trò compatibility metadata hoặc migration residue

## Execution Model

### Legacy path
- `WorkflowRunner` tiếp tục chạy tuần tự.
- Không thay semantics hiện tại ngoài bug fix nhỏ hoặc event emission cleanup.

### Graph path
- `AsyncGraphRunner` là runtime mới.
- Chỉ hỗ trợ DAG, không loops, không dynamic graph mutation, không distributed execution.

### Readiness and scheduling
Graph runtime sử dụng predecessor graph để xác định node ready.

Luồng xử lý:
1. validate graph v3
2. build predecessor map từ `inputs[*].sources[*]`
3. prepare scheduler
4. lấy các node ready ban đầu
5. dispatch node execution với bounded concurrency
6. khi node xong, emit outputs theo port
7. mark node done
8. unlock downstream nodes đủ điều kiện
9. tiếp tục tới khi graph kết thúc hoặc run bị cancel

### Why scheduler is not embedded into legacy runner
- semantics của graph khác hoàn toàn step-linear runner
- fan-in, fan-out và blocked propagation sẽ làm `core/workflow.py` trở thành file đa trách nhiệm và khó test
- dual-runner dễ rollback và dễ kiểm soát compatibility hơn

## Async and Threading Strategy

### Main rule
UI thread không được nhận mutation trực tiếp từ background runner.

### Proposed threading model
- Main thread:
  - Tkinter / CustomTkinter UI
  - event pump
  - state reduction
- Worker thread:
  - sở hữu event loop cho graph runtime
  - chạy provider calls và IO-bound orchestration

### Event flow
1. runner publish event vào `EventBus`
2. `ui/app.py` dùng `root.after(...)` để poll queue
3. `WorkspaceController` reduce event vào `WorkspaceState`
4. UI render từ state

### Why this is mandatory
Nếu tăng concurrency khi runner vẫn callback trực tiếp vào controller/state, xác suất race, UI refresh lệch và trạng thái không deterministic sẽ tăng mạnh.

## Join and Fan-in Semantics
MVP không nên cho reducer tùy ý. Chỉ hỗ trợ một tập semantics nhỏ nhưng rõ.

### Supported join strategies
- `first`
  - lấy giá trị từ source đầu tiên thỏa điều kiện
- `concat`
  - nối các source theo thứ tự định nghĩa
- `json_map`
  - gói các source vào object theo alias/key

### Rules
- thứ tự source phải deterministic theo cấu hình workflow
- input port có thể `required` hoặc optional
- join failure phải cho ra `blocked` hoặc `error` có lý do rõ

## Multi-Output Semantics

### Single-output node
- model/provider output map thẳng vào port duy nhất

### Multi-output node
- runner yêu cầu output dạng JSON object
- validate keys so với declared output ports
- nếu parse fail hoặc thiếu required keys thì node fail rõ ràng

### Exposed outputs
`OutputPortDef.exposed` quyết định output đó có được show rõ trong UI/result drawer hay chỉ dùng nội bộ cho downstream steps.

## Persistence Strategy
Không big-bang rewrite storage hiện tại.

### Keep legacy artifacts
- `runs/index.csv`
- `runs/<run_id>/run.json`
- `runs/<run_id>/events.jsonl`
- `runs/<run_id>/steps/step_XX.json`

### Add graph artifacts
- `runs/<run_id>/nodes/<step_id>.json`
- `runs/<run_id>/ports/<step_id>__<port>.json`
- mở rộng `events.jsonl` để ghi node/port events

### Why not replace step persistence immediately
- run history hiện tại đang dựa trên format cũ
- result drawer và reopen history path đang dựa trên `StepResult`
- migration full sang node store ở đợt đầu sẽ tăng blast radius không cần thiết

## Event Model
Event model mới cần giàu ngữ nghĩa hơn step started/finished.

### Required graph events
- `run_started`
- `node_ready`
- `node_started`
- `port_emitted`
- `node_finished`
- `node_blocked`
- `run_cancelled`
- `run_finished`

### Event payload requirements
- `run_id`
- `step_id`
- `event_type`
- `timestamp`
- `status`
- `port_name` nếu là event port-level
- `summary` ngắn cho UI
- `error` hoặc `blocked_reason` nếu có

## UI Strategy

### Phase-appropriate UI
Không làm graph canvas full ngay.

### Inspector panel
Từ:
- Input Variable
- Output Variable

Sang:
- execution mode
- input ports list
- từng input port có:
  - name
  - required
  - join strategy
  - sources
- output ports list
- exposed/internal metadata

### Result drawer
Từ:
- Input
- Output

Sang:
- Summary
- Inputs
- Outputs
- Events
- Provenance
- Raw
- Metrics

### Flow canvas
Trong MVP phase đầu:
- vẫn là card/list UI
- thêm badge:
  - `legacy` / `graph`
  - số input ports
  - số output ports
  - merge/join indicator
  - runtime status

Graph canvas thực sự là backlog sau.

## Validation Strategy

### Legacy validation
Giữ nguyên path cũ.

### Graph validation
Phải có đường validate riêng cho `execution_mode = graph`.

#### Validation rules
- source step tồn tại
- source port tồn tại
- target input port hợp lệ
- output port names unique trong step
- input port names unique trong step
- graph acyclic
- required inputs satisfiable
- join strategy hợp lệ
- không cho binding self-loop nếu không có rule đặc biệt

### Validation outcome
- blocking errors: không cho run
- non-blocking warnings: cho run nhưng hiển thị rõ trong UI

## Migration Strategy

### Versioning
- thêm schema version mới: `v3`
- hỗ trợ load cả `v2` và `v3`

### Migration behavior
- workflow v2 load vào app thì mặc định `execution_mode = legacy`
- port definitions không tự bịa nếu chưa có đủ dữ liệu
- migration helper chỉ tạo scaffold tối thiểu nếu người dùng chuyển một step sang graph mode

### Rollback posture
- workflow legacy không cần migrate để tiếp tục chạy
- nếu graph path lỗi, có thể disable path này mà không phá flow cũ

## Rollout Plan

## Phase 1 — UI-thread handoff stabilization
### Scope
- `ui/app.py`
- `ui/workspace_controller.py`
- `core/events.py`
- state update path

### Deliverable
- event pump main-thread hoạt động
- background runner không còn là nguồn mutation UI trực tiếp

### Exit criteria
- run legacy vẫn hoạt động
- không có cross-thread UI update trực tiếp trong run path chính

## Phase 2 — Schema v3 introduction
### Scope
- `core/models.py`
- `core/migrations.py`
- `core/config_service.py`

### Deliverable
- load/save được workflow v3
- `StepDef` có thể mang port definitions
- flow legacy vẫn không đổi hành vi

### Exit criteria
- test load/save pass cho cả v2 và v3
- editor vẫn mở được workflow cũ

## Phase 3 — Graph-aware validation
### Scope
- `core/config_validation.py`
- helper graph validation modules nếu cần

### Deliverable
- validate DAG graph path theo port
- lỗi/warning có message rõ

### Exit criteria
- phát hiện được cycle, missing source, invalid port, unsatisfied required input

## Phase 4 — AsyncGraphRunner
### Scope
- `core/async_graph_runner.py`
- event publishing
- cancellation path
- bounded concurrency

### Deliverable
- chạy được fan-out và fan-in cơ bản
- event model đầy đủ

### Exit criteria
- sample workflows chạy đúng join strategy
- cancel path không làm treo UI

## Phase 5 — Persistence extension
### Scope
- `core/storage.py`
- graph artifacts
- reopen history compatibility

### Deliverable
- lưu được node outputs và port outputs
- event log phục vụ replay/debug

### Exit criteria
- reopen run graph path được trong UI
- legacy history không vỡ

## Phase 6 — Inspector and result UI
### Scope
- `ui/inspector_panel.py`
- `ui/result_drawer.py`
- `ui/workspace_state.py`
- `core/commands.py`

### Deliverable
- chỉnh được input/output ports
- xem được join/provenance/events

### Exit criteria
- user cấu hình được multi-input / multi-output workflow từ UI cơ bản
- kết quả hiển thị đủ rõ để review

## Phase 7 — Flow canvas enrichment
### Scope
- `ui/flow_canvas.py`
- viewmodels

### Deliverable
- card/list thể hiện tốt graph metadata
- chưa cần full connector canvas

### Exit criteria
- người dùng nhìn được branch/join và port counts mà không cần mở inspector mọi lúc

## Testing Strategy

### Unit tests
- schema migration v2 -> v3
- graph validation
- join strategies
- output parsing cho multi-output nodes
- event reduction
- graph storage serialization

### Integration tests
- graph run fan-out -> independent nodes -> fan-in
- partial failure -> blocked downstream
- cancel run giữa chừng
- reopen history cho run graph

### UI smoke tests
- app boot
- event pump hoạt động
- inspector render port editor
- result drawer render multi-port data

### Regression tests
- sequential workflow cũ vẫn pass end-to-end
- run history cũ vẫn mở được
- command undo/redo không hỏng với step legacy

## Risks

### R1. UI race conditions
Nguyên nhân: background thread mutate UI state trực tiếp.

Giảm thiểu:
- main-thread event reduction
- cấm direct callback mutation trong run path mới

### R2. Schema drift giữa legacy và graph path
Nguyên nhân: hai mô hình cùng tồn tại nhưng thiếu source of truth rõ ràng.

Giảm thiểu:
- `execution_mode` rõ
- quy định field nào là source of truth theo mode
- migration rules rõ ràng

### R3. Join semantics khó hiểu với người dùng
Nguyên nhân: multi-input dễ tạo ambiguity.

Giảm thiểu:
- chỉ hỗ trợ 3 join strategy cho MVP
- UI giải thích ngắn và rõ
- preview input composition nếu cần

### R4. Multi-output parse lỗi
Nguyên nhân: model/provider không trả JSON đúng format.

Giảm thiểu:
- output contract rõ
- validate chặt
- fail fast với message rõ

### R5. History format bị phân mảnh
Nguyên nhân: tồn tại cả legacy step artifacts và graph artifacts.

Giảm thiểu:
- run manifest có `engine_type`
- storage adapter đọc theo engine type
- result drawer normalize viewmodel trước khi render

## Non-Goals for This MVP Upgrade
- loop/retry graph phức tạp
- conditional dynamic routing runtime
- distributed executor
- external queue/job scheduler
- database persistence
- collaborative multi-user editing
- production orchestration features
- full visual graph editor với drag connector

## Success Criteria
Bản nâng cấp được xem là đạt khi:
- workflow legacy hiện tại vẫn chạy mà không cần migrate
- có thể cấu hình một workflow graph có fan-out và fan-in đơn giản
- một step graph có thể nhận nhiều inputs và phát ra nhiều outputs
- UI thể hiện rõ input ports, output ports và join strategy
- history vẫn mở lại được cho cả legacy run và graph run
- cancel/failure không làm treo app hoặc làm hỏng state
- validation chặn được cấu hình graph sai trước khi chạy

## Final Recommendation
Triển khai theo thứ tự:
1. UI-thread handoff
2. schema v3
3. graph validation
4. `AsyncGraphRunner`
5. persistence extension
6. inspector/result UI
7. flow canvas enrichment

Đây là đường nâng cấp hợp lý nhất cho codebase hiện tại vì nó giải quyết đúng execution model mà vẫn giữ được tính ổn định của MVP.
