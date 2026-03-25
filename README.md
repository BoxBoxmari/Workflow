# Workflow MVP Validation Workbench

A local Python desktop application for sequential AI workflow execution, model/prompt comparison, and stakeholder review.

## Overview

This application is designed as a Validation Workbench for business analysts, solution architects, and developers to validate AI workflow directions before building a production system. It allows users to:

- Load sequential workflow definitions
- Run steps against the configured Workbench API
- Ingest local files (txt, json, xml, csv, docx, xlsx, pptx) as input
- Compare models and prompts directly against the same input
- Retain a full local history of runs, metrics, and step output

## Prerequisites

- Python 3.10+
- `customtkinter` (Modern UI framework)
- `tkinter` (Underlying engine, usually included with Python)

## Installation

1. Clone or download this repository.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   source .venv/bin/activate  # macOS/Linux
   ```
3. Install all dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Security

### API Key Storage

API credentials (`subscription_key`, `charge_code`) are stored using the **OS Credential Manager** (Windows Credential Vault) via the `keyring` library — not in plain text files.

To configure credentials securely:

```python
from config.secure_credentials import SecureCredentialStore
SecureCredentialStore.set_api_key("your-subscription-key")
SecureCredentialStore.set_charge_code("your-charge-code")
```

**Alternative:** Set environment variables for development or CI:

```
WORKBENCH_SUBSCRIPTION_KEY=your-key
WORKBENCH_CHARGE_CODE=your-code
```

> ⚠️ The application will still read credentials from `config/provider.json` as a deprecated fallback, but will log a warning. Migrate to the secure store for production use.

## Provider Configuration

`config/provider.json` — only `base_url`, `api_version`, and `timeout` are required here. Credentials should use the secure store instead:

```json
{
  "base_url": "https://api.workbench.kpmg/genai/azure/openai",
  "api_version": "2024-06-01",
  "timeout": 300
}
```

## Usage

```bash
python main.py
```

### Key Capabilities (Modern UI)

- **Workflow Sidebar (Left):** Modern card-based navigation for workflows and run history. Select a card to view drafts or past results.
- **Top Bar:** Run/Stop control, workflow title, indeterminate progress bar during execution, and **Appearance Mode** toggle (Dark, Light, System).
- **Inspector Panel (Right):** Detailed configuration for steps, variables, and model selection. Includes validation warnings.
- **Result Drawer (Bottom):** Tabbed interface (Output, Input, Raw, Metrics, Log) for inspecting step execution details.
- **Flow Canvas (Center):** Visual step cards for designing the sequential workflow.

## Graph Mode Workflows

While the application defaults to simple sequential workflows, you can enable **Graph Mode** to execute complex Directed Acyclic Graphs (DAGs) with fan-out, fan-in, and multi-output capabilities.

### Enabling Graph Runtime

To use graph features, enable the **"Enable Graph Runtime"** toggle located at the bottom of the left sidebar. This switches the execution engine to support parallel processing and advanced port routing.

### Configuring Graph Steps

Once enabled, selecting a step reveals advanced options in the Inspector Panel (Right):

- **Input Ports**: Define explicit named inputs. You can map multiple upstream sources (e.g., `step_id.port_name`) to a single input port using **Join Strategies** (`concat`, `array`, `dict`, `last`).
- **Output Ports**: Define explicit named outputs, specifying their `kind` (e.g., text, json) and whether they are `exposed`.

### Sample Workflows

Check the default workflows dropdown for built-in examples (from `config/workflows.json`) that demonstrate:

1. **Parallel Document Analysis**: Fan-out splitting
2. **Multi-Source Summary**: Fan-in merging
3. **Structured Output Extraction**: Multiple output ports from a single step

### Limitations

- The graph must be a Directed Acyclic Graph (DAG) — loops/cycles are not supported.
- Dynamic graph structure mutations during runtime are not permitted.
- Legacy workflows execute sequentially even when the Graph Runtime is enabled.

## Architecture

Standard-library-first application — no database, no web framework, local-file persistence only.

- `ui/`: Modern **CustomTkinter** desktop interface; `WorkspaceController` mediates all state via a thread-safe `WorkspaceState`.
- `core/`: Provider API client, workflow runner, file ingestion, thread-safe storage.
- `config/`: Model presets, workflow definitions, prompt templates, secure credential module.
- `runs/`: Output directory — execution artifacts and run history.

### Key Design Decisions

| Decision                              | Rationale                                               |
| ------------------------------------- | ------------------------------------------------------- |
| `StorageWriteQueue` background writer | Prevents UI blocking and race conditions on `index.csv` |
| Atomic temp-file writes + retry       | Survives Windows file-lock from Excel/Notepad           |
| Watchdog event-driven config watcher  | Replaces CPU-polling; fires only on actual file change  |
| Append-first CSV index                | O(1) for new runs; full rewrite only on updates         |

## Running Tests

```bash
python -m pytest tests/ -v
```

Skip Tkinter-dependent UI tests in CI:

```bash
python -m pytest tests/ --ignore=tests/test_ui_smoke.py -v
```

## Development Scripts

- `generate_examples.py`: tạo workflow mẫu graph trong thư mục `examples/`.
  Dùng khi cần kiểm thử/manual QA cho fan-out và multi-output.

```bash
python generate_examples.py
```
