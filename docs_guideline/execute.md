# Execute — Workflow MVP Validation Workbench

## Purpose
Define the build order for the MVP so the team can implement without losing scope discipline.

## Execution Rules
- Build in small vertical slices.
- Keep each slice runnable.
- Prefer one clear capability at a time over broad unfinished coverage.
- Validate after each phase.
- Do not introduce infrastructure that the next slice does not require.

## Recommended Build Sequence

### Step 1 — Confirm environment baseline
- Verify Python version
- Verify `tkinter` availability using `python -m tkinter`
- Confirm endpoint and environment variables required by the provider
- Confirm local write access to the project workspace

### Step 2 — Scaffold and storage
- Create project folders
- Implement local storage helpers
- Persist a fake sample run to prove artifact structure

### Step 3 — Provider wrapper
- Move the current simple API call into `core/provider.py`
- Normalize response structure
- Add visible error handling path

### Step 4 — Prompt registry
- Add prompt version definitions
- Add renderer for variable substitution
- Prove rendered prompt persistence

### Step 5 — Sequential workflow runner
- Read a workflow definition
- Run steps in order
- Persist step and run artifacts
- Confirm output mapping works

### Step 6 — Evaluation flows
- Add model comparison flow
- Add prompt comparison flow
- Persist comparison results

### Step 7 — File ingestion
- Support reliable types first
- Add Office best-effort support second
- Mark unsupported and limited cases clearly

### Step 8 — Desktop UI
- Build the shell and panels
- Connect to storage and workflow runner
- Add run history and detail tabs
- Add file upload and preview panel

### Step 9 — Validation and polish
- Add unit and smoke tests
- Add a small golden dataset
- Run end-to-end local validation
- Update README and usage notes

## Ready-to-Demo Checklist
Before showing stakeholders, confirm:
- a sample workflow runs end to end
- model comparison works with at least two models
- prompt comparison works with at least two prompt versions
- run history opens correctly
- one reliable file type and one best-effort file type are demonstrated
- errors are visible and understandable

## Stop Conditions
Pause implementation and correct direction if:
- a database becomes necessary to continue
- a web framework becomes the default path
- workflow logic starts branching into a generic orchestration engine
- file support claims exceed what the code can justify
