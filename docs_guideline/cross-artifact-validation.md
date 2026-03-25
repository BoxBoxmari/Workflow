# Cross-Artifact Validation — Workflow MVP Validation Workbench

## Purpose
Ensure all artifacts describe the same product, the same scope, and the same implementation direction.

## Governing Principle
No artifact is allowed to silently redefine the product.
All documents, tickets, and implementation checks must refer to the same Workflow MVP baseline.

## Core Consistency Rules
### Rule 1 — Same product domain
All artifacts must describe the AI Workflow Validation Workbench.
They must not drift into another domain such as financial audit, spreadsheet reconciliation, or document quality scoring unless the product scope is formally changed.

### Rule 2 — Same environment constraints
All artifacts must preserve the same baseline constraints:
- local MVP
- standard-library-first
- `tkinter` / `ttk` primary UI
- local file persistence only
- no database
- sequential workflow only

### Rule 3 — Same capability map
Artifacts must remain consistent about the product’s core capabilities:
- model comparison
- prompt comparison
- sequential workflow execution
- practical file ingestion
- trace inspection and run history

### Rule 4 — Same support boundaries
Artifacts must not contradict each other on file ingestion fidelity.
If one document marks PDF support as limited, no other artifact may describe it as fully supported.

### Rule 5 — Same architecture intent
If `tech-plan` and `architecture-validation` define modular boundaries, tickets and execution steps must not bypass them.

## Validation Matrix
Use this matrix when reviewing artifact drift.

| Source artifact | Must align with | Validation focus |
|---|---|---|
| epic-brief | prd-validation, core-flows | product purpose and scope |
| prd-validation | tech-plan, implementation-validation | acceptance criteria and testability |
| core-flows | tech-plan, execute | runtime behavior and UI flow |
| tech-plan | architecture-validation, ticket-breakdown | module boundaries and implementation path |
| ticket-breakdown | execute | delivery order and scope |
| implementation-validation | prd-validation, tech-plan | test coverage and behavior proof |
| revise-requirements | all artifacts | controlled scope change |

## Drift Signals
An artifact set is drifting if any of the following appears:
- the product domain changes across documents
- one document assumes a database while another forbids it
- one document assumes web UI while another assumes desktop UI
- tickets require modules not justified by the tech plan
- tests validate behavior not described in the PRD
- implementation validation ignores key stakeholder-visible flows

## Required Review Questions
Before accepting a new artifact or major code change, confirm:
1. Does this still describe the same Workflow MVP product?
2. Does it preserve the agreed constraints?
3. Does it map to an existing requirement?
4. Does it introduce hidden scope expansion?
5. Do tests and implementation expectations still line up?

## Acceptance Rule
If artifacts disagree, do not treat the newest one as automatically correct.
Resolve the mismatch explicitly and update the affected documents in order.

## Rejection Rule
Reject any artifact set that causes the product to drift away from the Workflow MVP baseline without an approved requirement revision.
