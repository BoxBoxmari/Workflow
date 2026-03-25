# Architecture Validation — Workflow MVP Validation Workbench

## Purpose
Validate that implementation decisions remain aligned with the agreed architecture for Workflow MVP.

## Architecture Baseline
The MVP architecture is valid only if it preserves the following structure:
- UI layer is desktop-first and implemented with `tkinter` / `ttk`
- Provider access is encapsulated behind a dedicated module
- Workflow logic is independent from UI widget code
- File ingestion is isolated from runtime orchestration
- Persistence is local-file based, not database based
- Comparison logic is separated from workflow execution logic

## Required Boundaries
### UI boundary
UI modules may:
- collect user input
- trigger runs
- display state and artifacts

UI modules must not:
- embed provider request logic directly
- implement file parsing directly
- own persistence format decisions
- contain business logic that should live in `core/`

### Provider boundary
Provider modules may:
- build request payloads
- call the configured endpoint
- normalize provider response shape

Provider modules must not:
- manage UI state
- decide workflow step order
- persist runs directly except through storage contracts

### Workflow boundary
Workflow modules may:
- resolve ordered steps
- pass outputs into later steps
- coordinate step execution and failure handling

Workflow modules must not:
- define UI layout
- hardcode environment secrets
- directly parse source files

### Storage boundary
Storage modules may:
- write JSON / CSV / JSONL artifacts
- load prior runs
- manage run folder structure

Storage modules must not:
- interpret workflow semantics
- call the provider directly

### Ingestion boundary
Ingestion modules may:
- detect file type
- extract text and lightweight structure
- emit normalized file artifacts

Ingestion modules must not:
- call the provider
- decide experiment comparison logic
- silently overclaim file fidelity

## Validation Checks
The architecture should be considered valid only if the following checks pass:
1. A reviewer can map each major responsibility to one module area.
2. UI code does not hide orchestration logic.
3. Storage remains file-based.
4. Workflow remains sequential.
5. File support does not exceed the documented limits.
6. New dependencies remain justified and exceptional.

## Drift Indicators
Architecture drift is present if any of the following appears:
- a web stack becomes primary
- a database appears in the persistence layer
- UI widgets call provider code directly
- workflow control spreads across unrelated modules
- file parsing logic is duplicated in multiple places
- a plugin framework is introduced before MVP needs it

## Acceptance Decision
### Accept
Architecture is acceptable when the implementation remains small, readable, and consistent with MVP constraints.

### Accept with conditions
Architecture is acceptable with conditions when small local exceptions exist but can be corrected without rework.

### Reject
Architecture must be rejected if the implementation materially expands scope or violates the environment and persistence constraints.
