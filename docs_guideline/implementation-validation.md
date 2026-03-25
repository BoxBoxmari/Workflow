# Implementation Validation — Workflow MVP Validation Workbench

## Purpose
Define how implementation quality will be validated before stakeholder review.

## Validation Layers

### Layer 1 — Unit validation
Validate module-level behavior.

#### Required unit areas
- `core/storage.py`
- `core/prompts.py`
- `core/provider.py`
- `core/ingestion.py`
- `core/workflow.py`
- `core/eval.py`

#### Minimum checks
- serialization and deserialization behave predictably
- prompt rendering is deterministic for the same inputs
- provider response normalization handles missing usage fields
- ingestion handlers produce normalized artifacts and fidelity notes
- workflow step chaining maps outputs correctly
- comparison functions preserve per-run metadata

### Layer 2 — UI smoke validation
Validate that the desktop app can initialize and display critical surfaces.

#### Required checks
- application can start
- main panels render
- essential widgets exist
- app can close cleanly

### Layer 3 — Integration validation
Validate one representative end-to-end run.

#### Required scenario
1. Load a small workflow definition.
2. Provide text or supported file input.
3. Execute multiple sequential steps.
4. Persist run artifacts.
5. Reopen the run from history.
6. Inspect step details.

### Layer 4 — Manual stakeholder validation
Validate that the MVP is understandable by non-developer reviewers.

#### Review questions
- Can the reviewer follow the step order?
- Can they see which model and prompt version were used?
- Can they inspect input, output, and metrics?
- Can they understand file support limitations?
- Can they identify failures without reading logs manually?

## Test Data Strategy
### Recommended local fixtures
- simple text input
- JSON sample
- CSV sample
- one small DOCX sample
- one small XLSX sample
- one small PPTX sample if feasible
- one limited PDF example labeled as limited-support case

### Golden set
Maintain a small repeatable set of evaluation cases for:
- model comparison
- prompt comparison
- workflow chaining

## Failure Conditions
Implementation validation fails if:
- the application cannot run locally
- run artifacts are not persisted reliably
- the UI cannot expose step-level evidence
- workflow chaining is incorrect or opaque
- file support is overstated relative to actual extraction fidelity
- tests cover only happy path behavior and miss obvious error handling

## Validation Output
Each validation cycle should summarize:
- what passed
- what failed
- what remains limited by design
- what is deferred intentionally
