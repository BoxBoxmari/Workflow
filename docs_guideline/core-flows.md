# Core Flows — Workflow MVP Validation Workbench

## Overview
This document defines the main user and system flows for the Workflow MVP.

The workbench supports five primary validation flows:
1. Single-step model comparison
2. Single-step prompt comparison
3. End-to-end sequential workflow execution
4. File ingestion and normalization review
5. Run history and trace inspection

## Flow 1 — Model Comparison
### User goal
Compare multiple models against the same task input to choose the best model for a workflow step.

### Entry points
- Playground view
- Experiment / Compare view

### Steps
1. User selects a task or prompt template.
2. User selects one or more models.
3. User provides text input or a normalized file artifact.
4. System runs the same logical task for each selected model.
5. System records output, latency, token usage if available, and errors.
6. UI shows side-by-side comparison.

### Outputs
- Per-model output text
- Latency and status comparison
- Usage metrics where returned by provider
- Local persisted experiment record

### Acceptance criteria
- Same task definition is reused across compared models.
- Comparison result is persisted locally.
- Missing metrics are shown as unavailable, not fabricated.

## Flow 2 — Prompt Comparison
### User goal
Compare prompt versions on the same task while keeping model and input constant.

### Steps
1. User selects a task and one model.
2. User selects two or more prompt versions.
3. User provides the same input for all variants.
4. System renders each prompt version.
5. System runs each rendered prompt.
6. UI shows outputs and metrics side by side.

### Acceptance criteria
- Rendered prompt used for each run can be inspected.
- Prompt identity and version are persisted with results.
- Comparison is reproducible from local artifacts.

## Flow 3 — Sequential Workflow Execution
### User goal
Run a defined workflow step by step and inspect how outputs pass between steps.

### Steps
1. User chooses a workflow definition.
2. User provides initial input values and optional file.
3. System resolves workflow configuration.
4. System runs step 1.
5. System persists step result.
6. System maps step 1 output into step 2 input.
7. System repeats until all enabled steps complete or a blocking failure occurs.
8. UI shows overall status and per-step details.

### Step contract
Each step should expose:
- `id`
- `name`
- `model`
- `prompt_version`
- `input_mapping`
- `output_mapping`
- `enabled`

### Acceptance criteria
- Only sequential execution is supported.
- Each step can be inspected independently.
- Failures are visible and do not silently disappear.
- Step outputs are mapped explicitly into subsequent steps.

## Flow 4 — File Ingestion and Normalization Review
### User goal
Upload a practical file, inspect extracted content, and decide whether it is usable for prompt-driven evaluation.

### Supported levels
#### Reliable support
- `txt`
- `json`
- `xml`
- `csv`

#### Basic best-effort support
- `docx`
- `xlsx`
- `pptx`

#### Limited support
- `pdf`

### Steps
1. User selects a file.
2. System detects file type.
3. System routes to the appropriate ingestion handler.
4. Handler extracts text and lightweight structure.
5. UI shows normalized preview and metadata.
6. User may send normalized content into a prompt or workflow.

### Acceptance criteria
- Unsupported or low-fidelity cases are labeled clearly.
- Normalized output is inspectable before model submission.
- Source file reference is preserved in run artifacts.

## Flow 5 — Run History and Trace Inspection
### User goal
Inspect what happened in previous runs without rerunning the workflow.

### Steps
1. User opens run history.
2. System loads `runs/index.csv` and local manifests.
3. User selects a run.
4. UI shows workflow summary and step timeline.
5. User opens input, rendered prompt, output, raw response, and metrics.

### Acceptance criteria
- Runs are discoverable from local storage.
- Trace view uses persisted artifacts, not live reconstruction.
- Missing artifacts or corrupted runs are reported clearly.

## Flow 6 — Fallback UX When `tkinter` Is Unavailable
### Goal
Provide a minimum viable fallback path if desktop widgets are unavailable on the environment.

### Fallback path
1. System detects that `tkinter` cannot be initialized.
2. System presents a local HTML report / fallback viewer path.
3. User can still review run artifacts and comparison output.

### Notes
- This is a fallback, not the primary UX.
- It should not become a hidden web-app architecture.
