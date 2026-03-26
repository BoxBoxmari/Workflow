# User Manual — Workflow MVP Validation Workbench

This guide explains how to use the AI Workflow Validation Workbench to test, compare, and audit sequential AI workflows locally.

## 1. Setup & Launch

Before using the tool, ensure you have:

1. **Python 3.10+** and the `requests` library installed.
2. **Provider Config**: Create `config/provider.json` with provider endpoint settings (`base_url`, `api_version`, `timeout`). API credentials are loaded from OS Credential Manager (`keyring`) or environment variables.
3. **Launch**: Execute `python main.py` from the root directory.

## 2. Core Workflow Operations

### Loading a Workflow

- By default, the tool scans `config/workflows.json`.
- Selecting a workflow from the **Workflow Panel** (left) will populate the step sequence in the main list.

### Running a Workflow

- Click the **[Run]** button to execute steps sequentially.
- **Note**: Since you cannot call the Workbench API currently, runs will fail at the first API step. You can still use the UI to inspect local history and ingested files.

## 3. Comparing Models & Prompts

The **Compare** menu allows side-by-side evaluation:

- **Compare Models**: Select a step, then choose multiple models (e.g., `gpt-4o`, `gpt-4-turbo`) to see how outputs differ for the same input and prompt.
- **Compare Prompts**: Test different versions of a prompt template (e.g., `v1` vs `v2`) on the same model and input.

## 4. File Ingestion for Testing

Use the **Select File** button to load external data into the workflow input:

- **Supported (Tier 1)**: `.txt`, `.json`, `.xml`, `.csv`. These are normalized with high fidelity.
- **Best-effort (Tier 2)**: `.docx`, `.xlsx`, `.pptx`. The tool extracts raw text using standard library parsing. Formatting and images are ignored.
- The normalized content appears in the **Input** tab of the Detail Panel.

## 5. Inspection & Traceability

After a run (or when loading from history), use the **Detail Panel** (center) tabs:

- **Input**: The text sent to the model.
- **Prompt**: The final rendered prompt including system instructions and variables.
- **Output**: The plain text response from the AI.
- **Raw**: The full JSON payload from the Workbench API provider.
- **Metrics**: Latency, token usage, and status metadata.

## 6. History & Audit

- All runs are saved locally to the `runs/` directory.
- Use the **History Panel** (bottom) to browse past results.
- Clicking a run in the history list reloads all step data and artifacts for back-testing or stakeholder review.

### Attachment audit events

When attachment slots are used, the run event log (`runs/<run_id>/events.jsonl`) now emits two explicit event types:

- `attachment_ingested`
  - `run_id`, `step_id`, `slot_id`, `variable_name`
  - `file_path`, `size_bytes`, `sha256`
  - `status` (`ok` or `error`) and optional `error`
- `attachment_consumed_by_step`
  - `run_id`, `step_id`, `variable_name`, `source_file_sha256`
  - optional `slot_id`

This allows you to trace both:

1. when an attachment was successfully (or unsuccessfully) ingested, and
2. which step actually consumed the ingested attachment variable at execution time.

### Attachment management in UI

- Both **Simple mode** (Flow Canvas modal) and **Advanced mode** (Inspector attachments) support selecting **multiple files** in one action.
- First selected file is bound to the current slot; additional files are auto-bound by creating new slots on the same step.
- A **Delete file** action is available in both modes and removes the physical file binding from the slot.

### Events tab behavior

- The **Events** tab now hydrates events for:
  - live runs while steps complete, and
  - historical runs loaded from Run History.
- If events exist in `runs/<run_id>/events.jsonl`, step results will no longer show false `"No events recorded"` for those steps.

## 7. Configuration & Customization

- **Workflows**: Modify `config/workflows.json` to define step names, models, and variable mappings.
- **Prompts**: Add `.txt` files to `config/prompts/` using the naming convention `{step_name}_v{version}.txt`.
- **Prompt cleanup on save**: When a workflow is deleted and you save, prompt files that are no longer referenced by any workflow are automatically removed from `config/prompts/`.
- **Formatting**: Prompts support `$variable` substitution using standard Python string templates.
