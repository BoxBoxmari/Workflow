# Ticket Breakdown — Workflow MVP Validation Workbench

## Goal
Break the MVP into delivery-focused tickets that can be executed incrementally.

## Phase 1 — Foundation
### T1.1 Project scaffold
- Create `main.py`, `core/`, `ui/`, `config/`, `runs/`, `tests/`
- Add `.env.example` if environment variables are needed
- Add minimal README with local run instructions

### T1.2 Configuration baseline
- Define `config/models.json`
- Define `config/workflows.json`
- Establish prompt version file format or simple prompt registry format

### T1.3 Storage baseline
- Implement run folder structure
- Implement `index.csv`
- Implement JSON / JSONL persistence helpers

## Phase 2 — Provider and Prompt Layer
### T2.1 Provider wrapper
- Wrap the existing Workbench-style API call
- Normalize response fields
- Capture status, latency, error, and usage when available

### T2.2 Prompt registry and rendering
- Support named prompt versions
- Render prompt with input variables
- Preserve rendered prompt in run artifacts

### T2.3 Error visibility
- Surface configuration or provider errors clearly
- Avoid silent failures

## Phase 3 — Workflow Runner
### T3.1 Sequential workflow executor
- Read workflow definition
- Execute enabled steps in order
- Map outputs to later steps

### T3.2 Step persistence
- Persist each step result independently
- Add event log entries for lifecycle milestones

### T3.3 Failure handling
- Stop or mark run clearly on blocking failures
- Surface error detail in UI and stored artifacts

## Phase 4 — Evaluation Features
### T4.1 Model comparison
- Compare two or more models on the same task
- Persist experiment summary and detailed results

### T4.2 Prompt comparison
- Compare two or more prompt versions on the same task
- Preserve rendered prompt and outputs for review

### T4.3 Golden examples
- Add a small benchmark / golden dataset for repeatable validation

## Phase 5 — File Ingestion
### T5.1 Reliable file types
- Support TXT, JSON, XML, CSV

### T5.2 Best-effort Office support
- Implement DOCX, XLSX, PPTX extraction using ZIP + XML parsing
- Emit normalized artifacts and fidelity notes

### T5.3 Limited PDF path
- Add limited handling and explicit user warning
- Or document pre-conversion requirement

## Phase 6 — Desktop UI
### T6.1 Application shell
- Main window
- Navigation or primary layout regions
- Run status and progress display

### T6.2 Workflow and detail panes
- Step list
- Detail tabs for input, output, prompt, raw response, metrics

### T6.3 Run history
- Load runs from local storage
- Reopen historical run details

### T6.4 File review pane
- Upload file
- Show normalized preview
- Route normalized content into workflow or comparison flow

## Phase 7 — Validation
### T7.1 Unit tests
- storage
- prompt rendering
- provider wrapper
- ingestion
- workflow chaining
- comparison logic

### T7.2 UI smoke tests
- app initialization
- key widgets
- clean teardown

### T7.3 Integration smoke flow
- one small workflow run end to end using mocked provider behavior

## Deferred backlog
- richer HTML fallback viewer
- advanced workflow branching
- richer result analytics
- multi-user sharing
- database-backed persistence
