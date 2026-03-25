# Tech Plan — Workflow MVP Validation Workbench

## Objective
Define the implementation approach for a local Python MVP that supports workflow validation, prompt/model comparison, and traceable review.

## Architectural Direction
The MVP should use a small modular architecture with explicit boundaries.

### Proposed modules
- `main.py` — application entry point
- `ui/` — `tkinter` / `ttk` screens, layout, and interaction wiring
- `core/provider.py` — wraps the existing Workbench-style API call
- `core/workflow.py` — sequential workflow runner
- `core/prompts.py` — prompt registry, versions, and rendering
- `core/eval.py` — model and prompt comparison logic
- `core/storage.py` — JSON / CSV / JSONL persistence
- `core/ingestion.py` — file-type detection, extraction, normalization
- `config/models.json` — available model presets
- `config/workflows.json` — workflow definitions
- `runs/` — local history and artifacts

## UI Strategy
### Primary stack
- `tkinter`
- `ttk`

### Key widgets
- `ttk.Treeview` for workflow steps and run history
- `ttk.Notebook` for detail tabs
- `ScrolledText` for long prompt/input/output content
- `ttk.Progressbar` for execution state
- `filedialog` for file selection

### Primary UI zones
1. Workflow panel
2. Input / Output / Prompt / Raw tabs
3. Metrics panel
4. Run history panel

## Persistence Strategy
### Directory layout
- `runs/index.csv`
- `runs/<run_id>/run.json`
- `runs/<run_id>/events.jsonl`
- `runs/<run_id>/steps/step_01.json`
- `runs/<run_id>/steps/step_02.json`
- `runs/<run_id>/artifacts/...`

### Purpose
- `index.csv` supports history listing
- `run.json` stores run-level manifest
- `events.jsonl` stores runtime event sequence
- step files store step-specific result details
- artifacts folder stores normalized file content and related assets

## Core Data Contracts
### Workflow definition
```json
{
  "workflow_id": "workflow_01",
  "name": "Sample Workflow",
  "steps": [
    {
      "id": "s1",
      "name": "Extract",
      "model": "gpt-4.1",
      "prompt_version": "v1",
      "input_mapping": {},
      "output_mapping": {"output_text": "extract_text"},
      "enabled": true
    }
  ]
}
```

### Run manifest
```json
{
  "run_id": "20260315_101530",
  "workflow_id": "workflow_01",
  "started_at": "...",
  "ended_at": "...",
  "status": "completed",
  "steps": []
}
```

### Step result
```json
{
  "step_id": "s1",
  "name": "Extract",
  "model": "gpt-4.1",
  "prompt_version": "v1",
  "input_text": "...",
  "rendered_prompt": "...",
  "output_text": "...",
  "latency_ms": 1830,
  "usage": {
    "input_tokens": 1200,
    "output_tokens": 320
  },
  "status": "completed",
  "error": null
}
```

## File Ingestion Plan
### Reliable
- plain text
- JSON
- XML
- CSV

### Best effort
- DOCX via ZIP + XML parsing
- XLSX via ZIP + XML parsing
- PPTX via ZIP + XML parsing

### Limited
- PDF only if a trusted conversion path is available, otherwise limited and clearly labeled

## Implementation Guardrails
- No database
- No web framework
- No branching workflow engine
- No speculative plugin framework
- No heavy dependency footprint without clear justification

## Technical Risks
- `tkinter` may not be available in all Python builds
- file-ingestion fidelity for Office formats is limited
- PDF support may be too weak without conversion
- provider usage metrics may not always be returned
- desktop UI responsiveness can degrade if long-running work blocks the main thread

## Fallback Strategy
If `tkinter` cannot be used:
- generate local HTML report outputs
- open them using `webbrowser`
- keep fallback narrow and artifact-oriented
