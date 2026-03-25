# Epic Tickets — Async Multi-Input / Multi-Output Graph Upgrade for Workflow MVP

## Goal
Bẻ kế hoạch nâng cấp async graph thành backlog có thể thực thi theo từng epic và ticket, với dependency rõ, acceptance criteria rõ, và ưu tiên bảo toàn stability cho codebase hiện tại.

## Delivery Principles
- Không chạm sâu vào legacy path nếu chưa có test bao phủ.
- Không triển khai UI graph phức tạp trước runtime correctness.
- Mỗi epic phải để lại một trạng thái repo vẫn chạy được.
- Các thay đổi có nguy cơ gãy compatibility phải có regression test cùng đợt.

## Epic E1 — Main-thread Event Reduction Foundation
### Goal
Ổn định luồng cập nhật UI trước khi tăng concurrency.

### Why this epic exists
Codebase hiện có `EventBus`, nhưng background runner vẫn đang là nguồn mutation UI/state trực tiếp. Nếu giữ nguyên pattern này rồi thêm async graph runtime, nguy cơ race condition và trạng thái UI không deterministic sẽ tăng mạnh.

### Tickets
#### E1-T1 Audit runtime-to-UI update path
- Scope
  - rà soát `ui/app.py`, `ui/workspace_controller.py`, `core/workflow.py`, `core/events.py`
  - xác định toàn bộ điểm background callback đang tác động trực tiếp vào UI/state
- Deliverables
  - sơ đồ call path hiện tại
  - danh sách mutation points cần thay thế
- Acceptance criteria
  - có inventory đầy đủ các đường update runtime -> UI
  - có quyết định rõ path nào bị deprecate

#### E1-T2 Add main-thread event pump
- Scope
  - thêm polling loop bằng `root.after(...)` trong `ui/app.py`
  - dispatch event bus về controller trên UI thread
- Deliverables
  - event pump chạy ổn định khi app mở
- Acceptance criteria
  - event từ background runner được nhận trên main thread
  - không có update widget trực tiếp từ worker thread trong path mới

#### E1-T3 Refactor workspace controller to state reducer
- Scope
  - gom logic xử lý event về `WorkspaceController`
  - tách reduce state khỏi execute runtime
- Deliverables
  - reducer functions cho run lifecycle events
- Acceptance criteria
  - state thay đổi thông qua reducer rõ ràng
  - UI render từ state thay vì callback side effect

#### E1-T4 Regression tests for legacy execution UI updates
- Scope
  - test event pump
  - test run legacy qua UI shell
- Deliverables
  - regression test cho path cũ
- Acceptance criteria
  - legacy run vẫn hiển thị status đúng
  - app không phát sinh lỗi cross-thread UI update trong smoke flow

### Epic acceptance criteria
- main-thread event reduction hoạt động
- legacy runner vẫn chạy được
- codebase sẵn sàng cho concurrency mà không tăng risk UI race

## Epic E2 — Schema v3 Port-Based Contracts Inside StepDef
### Goal
Mở rộng schema để hỗ trợ multi-input / multi-output mà không phá editor model hiện tại.

### Tickets
#### E2-T1 Extend `StepDef` with graph contracts
- Scope
  - sửa `core/models.py`
  - thêm `execution_mode`, `InputPortDef`, `OutputPortDef`, `SourceRef`
- Deliverables
  - dataclasses/models mới
- Acceptance criteria
  - `StepDef` parse được cả legacy fields và graph fields
  - default values an toàn cho workflow cũ

#### E2-T2 Extend `StepResult` without replacing it
- Scope
  - thêm `input_ports`, `output_ports`, `node_events` vào `StepResult`
- Deliverables
  - result contract tương thích ngược
- Acceptance criteria
  - result object cũ vẫn deserialize được
  - UI cũ không vỡ khi field mới chưa có dữ liệu

#### E2-T3 Add schema versioning and migrations
- Scope
  - `core/migrations.py`
  - `core/config_service.py`
- Deliverables
  - load/save v2 và v3
  - migration helper v2 -> v3
- Acceptance criteria
  - workflow v2 vẫn load được
  - workflow v3 save/load round-trip không mất dữ liệu

#### E2-T4 Add command helpers for nested port mutations
- Scope
  - `core/commands.py`
  - hỗ trợ add/remove/update input port, output port, source binding
- Deliverables
  - command objects mới cho editor
- Acceptance criteria
  - undo/redo hoạt động với thay đổi graph schema cơ bản

### Epic acceptance criteria
- schema v3 tồn tại và dùng được
- workflow legacy không bị buộc migrate
- editor model `WorkflowDef.steps` vẫn giữ nguyên

## Epic E3 — Graph-Aware Validation Layer
### Goal
Chặn cấu hình graph sai trước khi runtime chạy.

### Tickets
#### E3-T1 Build graph extraction helpers
- Scope
  - helper chuyển `steps` graph-mode thành predecessor graph
  - helper map port bindings
- Deliverables
  - module helper dùng chung cho validation và runtime
- Acceptance criteria
  - build được predecessor map chính xác từ `inputs[*].sources[*]`

#### E3-T2 Implement graph validation rules
- Scope
  - cập nhật `core/config_validation.py`
- Deliverables
  - validate source step tồn tại
  - validate source port tồn tại
  - validate unique input/output port names
  - validate join strategy
  - validate required inputs satisfiable
  - validate DAG acyclic
- Acceptance criteria
  - các lỗi graph sai được report rõ và đúng vị trí

#### E3-T3 Separate legacy and graph validation paths
- Scope
  - giữ nguyên validation hiện tại cho `execution_mode = legacy`
  - route graph steps qua validation mới
- Deliverables
  - dual validation path rõ ràng
- Acceptance criteria
  - workflow cũ không đổi behavior validation
  - workflow graph nhận error/warning đúng chuẩn

#### E3-T4 Test matrix for invalid graph configs
- Scope
  - cycle
  - missing step
  - missing port
  - duplicate port name
  - unsatisfied required input
  - invalid join strategy
- Deliverables
  - negative tests
- Acceptance criteria
  - coverage đủ cho các lỗi cấu hình trọng yếu

### Epic acceptance criteria
- graph config sai bị chặn trước khi run
- validation message đủ rõ để sửa cấu hình

## Epic E4 — AsyncGraphRunner Runtime
### Goal
Tạo runtime graph bất đồng bộ mới mà không làm lẫn với legacy runner.

### Tickets
#### E4-T1 Create `core/async_graph_runner.py`
- Scope
  - skeleton runner mới
  - interface tương thích với run orchestration hiện tại ở mức cần thiết
- Deliverables
  - class `AsyncGraphRunner`
- Acceptance criteria
  - runner khởi tạo được với workflow graph hợp lệ

#### E4-T2 Implement readiness scheduler
- Scope
  - build predecessor graph
  - tích hợp scheduler readiness
  - release downstream node khi upstream xong
- Deliverables
  - runtime scheduling core
- Acceptance criteria
  - fan-out chạy được
  - fan-in unlock đúng khi đủ điều kiện

#### E4-T3 Implement bounded concurrency and cancellation
- Scope
  - concurrency limit
  - cancel signal
  - cleanup path
- Deliverables
  - graph run có thể cancel an toàn
- Acceptance criteria
  - cancel không treo app
  - task đang chạy được mark trạng thái nhất quán

#### E4-T4 Implement join strategies
- Scope
  - `first`
  - `concat`
  - `json_map`
- Deliverables
  - join engine cho input ports
- Acceptance criteria
  - output ghép đúng theo thứ tự deterministic
  - lỗi join có message rõ

#### E4-T5 Implement multi-output extraction
- Scope
  - single-output map thẳng
  - multi-output parse JSON object
- Deliverables
  - output extraction layer
- Acceptance criteria
  - node nhiều output trả đúng port payloads
  - parse lỗi thì fail fast

#### E4-T6 Publish graph runtime events
- Scope
  - `node_ready`
  - `node_started`
  - `port_emitted`
  - `node_finished`
  - `node_blocked`
  - `run_finished`
- Deliverables
  - event emission đầy đủ
- Acceptance criteria
  - UI/state layer nhận đủ event để render graph run

#### E4-T7 Runtime integration tests
- Scope
  - happy path fan-out/fan-in
  - partial failure
  - blocked downstream
  - cancellation
- Deliverables
  - integration tests cho runner mới
- Acceptance criteria
  - runner mới pass test matrix tối thiểu

### Epic acceptance criteria
- có graph runner riêng chạy được MVP DAG
- legacy runner không bị sửa semantics

## Epic E5 — Storage and History Compatibility
### Goal
Mở rộng persistence cho graph runs mà không làm vỡ history hiện tại.

### Tickets
#### E5-T1 Extend run manifest with engine metadata
- Scope
  - thêm `engine_type`, `schema_version`, graph summary nếu cần
- Deliverables
  - manifest format mới tương thích ngược
- Acceptance criteria
  - run manifest cho legacy và graph đều đọc được

#### E5-T2 Add node and port artifact persistence
- Scope
  - `core/storage.py`
  - save/load `nodes/*.json` và `ports/*.json`
- Deliverables
  - graph artifact persistence
- Acceptance criteria
  - graph run lưu được node results và port payloads

#### E5-T3 Extend event log structure
- Scope
  - enrich `events.jsonl`
- Deliverables
  - event log chứa đủ ngữ nghĩa cho replay/debug
- Acceptance criteria
  - replay/history path đọc được event graph quan trọng

#### E5-T4 Add storage adapter for history reopen
- Scope
  - normalize legacy run và graph run về viewmodel chung
- Deliverables
  - history load adapter
- Acceptance criteria
  - user mở lại được cả run cũ và run graph mới

#### E5-T5 Regression tests for legacy history
- Scope
  - reopen old run folder
  - render old result drawer path
- Deliverables
  - regression coverage
- Acceptance criteria
  - history cũ không bị gãy sau nâng cấp storage

### Epic acceptance criteria
- graph runs được lưu và mở lại được
- legacy history vẫn ổn định

## Epic E6 — Inspector Panel and Result Drawer Upgrade
### Goal
Cho phép người dùng cấu hình và quan sát multi-input / multi-output rõ ràng trong UI.

### Tickets
#### E6-T1 Add execution mode control in inspector
- Scope
  - `legacy` / `graph`
  - mode-specific form rendering
- Deliverables
  - execution mode selector
- Acceptance criteria
  - đổi mode không làm hỏng step đang edit

#### E6-T2 Build input ports editor
- Scope
  - add/remove input port
  - edit name, required, join strategy
  - manage sources
- Deliverables
  - input port editor UI
- Acceptance criteria
  - có thể cấu hình ít nhất 2 input ports và nhiều sources cho một port

#### E6-T3 Build output ports editor
- Scope
  - add/remove output port
  - edit name, kind, exposed
- Deliverables
  - output port editor UI
- Acceptance criteria
  - có thể cấu hình ít nhất 2 output ports

#### E6-T4 Upgrade result drawer for graph results
- Scope
  - render Summary
  - render Inputs
  - render Outputs
  - render Events
  - render Provenance
- Deliverables
  - result drawer mới cho graph path
- Acceptance criteria
  - reviewer nhìn rõ output nào đi từ đâu tới đâu

#### E6-T5 Add compatibility rendering for legacy results
- Scope
  - giữ path hiển thị đơn giản cho legacy result
- Deliverables
  - backward-compatible UI rendering
- Acceptance criteria
  - workflow cũ vẫn đọc dễ, không bị “quá tải UI” bởi field graph mới

#### E6-T6 UI smoke and interaction tests
- Scope
  - inspector rendering
  - result drawer rendering
  - basic command interactions
- Deliverables
  - smoke tests
- Acceptance criteria
  - UI không crash khi step thiếu một phần graph metadata

### Epic acceptance criteria
- user cấu hình được graph step cơ bản từ UI
- reviewer đọc được results nhiều input/output một cách rõ ràng

## Epic E7 — Flow Canvas Enrichment for Graph Awareness
### Goal
Làm cho canvas hiện tại thể hiện được graph semantics đủ dùng mà chưa cần full graph editor.

### Tickets
#### E7-T1 Extend flow node viewmodels
- Scope
  - port counts
  - execution mode
  - join indicators
  - status badges
- Deliverables
  - viewmodel mới cho node card
- Acceptance criteria
  - card có đủ metadata chính để phân biệt legacy và graph

#### E7-T2 Add graph badges and summaries to step cards
- Scope
  - `ui/flow_canvas.py`
- Deliverables
  - hiển thị số input/output ports
  - merge/join badge
  - runtime status badge
- Acceptance criteria
  - người dùng nhìn danh sách step là hiểu được step nào có branch/join

#### E7-T3 Highlight selected node provenance
- Scope
  - khi chọn step, flow canvas và result drawer đồng bộ ngữ nghĩa
- Deliverables
  - selected-state UX tốt hơn
- Acceptance criteria
  - reviewer điều hướng graph run dễ hơn

#### E7-T4 Visual regression tests
- Scope
  - render card cho legacy step
  - render card cho graph step
- Deliverables
  - snapshot/smoke tests nếu khả thi
- Acceptance criteria
  - canvas không bị vỡ layout với metadata mới

### Epic acceptance criteria
- flow canvas đủ sức truyền đạt graph semantics ở mức MVP
- chưa cần full connector-based editor

## Epic E8 — End-to-End Hardening and Release Gate
### Goal
Chốt chất lượng và chuẩn bị enable graph path an toàn.

### Tickets
#### E8-T1 Build sample graph workflows
- Scope
  - một workflow fan-out/fan-in đơn giản
  - một workflow multi-output step
- Deliverables
  - sample configs cho manual QA và demo
- Acceptance criteria
  - sample workflows chạy được ổn định

#### E8-T2 Full regression pack
- Scope
  - legacy sequential workflows
  - graph workflows
  - history reopen
  - cancel flow
- Deliverables
  - release regression checklist
- Acceptance criteria
  - không có regression blocker ở path legacy

#### E8-T3 Feature flag / safe enable strategy
- Scope
  - graph mode enable path
  - fallback behavior nếu graph runner fail init
- Deliverables
  - guardrail config hoặc UI flag
- Acceptance criteria
  - có thể disable graph path mà legacy vẫn chạy bình thường

#### E8-T4 Release documentation
- Scope
  - migration notes
  - known limits
  - QA checklist
- Deliverables
  - docs cho internal handoff
- Acceptance criteria
  - dev và QA có đủ hướng dẫn để kiểm thử và rollback

### Epic acceptance criteria
- graph path đủ ổn định để bật trong MVP
- legacy path vẫn là fallback đáng tin cậy

## Recommended Delivery Order
1. E1 — Main-thread Event Reduction Foundation
2. E2 — Schema v3 Port-Based Contracts Inside StepDef
3. E3 — Graph-Aware Validation Layer
4. E4 — AsyncGraphRunner Runtime
5. E5 — Storage and History Compatibility
6. E6 — Inspector Panel and Result Drawer Upgrade
7. E7 — Flow Canvas Enrichment for Graph Awareness
8. E8 — End-to-End Hardening and Release Gate

## Suggested Release Slices
### Slice A — Safe foundation
- E1
- E2
- E3

### Slice B — Runnable graph core
- E4
- E5

### Slice C — Usable UI
- E6
- E7

### Slice D — Release hardening
- E8

## Exit Definition
Backlog này được xem là hoàn tất khi:
- legacy workflow chạy và reopen history bình thường
- graph workflow fan-out/fan-in chạy được end-to-end
- multi-input / multi-output được cấu hình từ UI cơ bản
- validation chặn được graph sai trước runtime
- cancel/failure path không làm app treo hoặc state sai
