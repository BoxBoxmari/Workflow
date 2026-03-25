# Revise Requirements — Workflow MVP Validation Workbench

## Purpose
Define how requirement changes should be handled without destabilizing the MVP.

## Requirement Revision Policy
Changes are allowed, but they must be classified before implementation.

## Revision Categories
### Category A — Clarification
The requirement stays the same in substance, but wording or examples improve.

**Examples**
- clarifying what “best-effort Office support” means
- clarifying what metrics are optional

**Action**
- update the relevant document
- no architecture change unless wording exposed a real gap

### Category B — Scope-preserving enhancement
The product remains the same, but a capability becomes slightly more explicit.

**Examples**
- adding one more reliable file fixture
- adding clearer run history fields
- adding a Help menu in the UI

**Action**
- update docs and ticket list
- validate impact on tests and UI

### Category C — Scope-expanding change
The request adds material complexity and should not be absorbed casually.

**Examples**
- adding branching workflow logic
- adding multi-user collaboration
- adding database persistence
- adding a web UI as primary experience

**Action**
- stop and assess formally
- create a new decision record
- do not silently absorb into MVP

## Requirement Revision Process
1. Identify the changed request.
2. Classify it as clarification, scope-preserving, or scope-expanding.
3. Check which artifacts are affected.
4. Update docs in a controlled order.
5. Only then update implementation or tickets.

## Artifact Update Order
When a valid requirement revision is accepted, update in this order:
1. `epic-brief`
2. `prd-validation`
3. `core-flows`
4. `tech-plan`
5. `architecture-validation`
6. `ticket-breakdown`
7. `execute`
8. `implementation-validation`
9. `cross-artifact-validation`

## Guardrails
- Do not let implementation lead the requirement definition.
- Do not treat a convenient code shortcut as a product decision.
- Do not broaden file support or architecture claims without updating docs.
- Do not absorb environment-breaking changes into MVP silently.

## Decision Questions
Before accepting a requirement revision, ask:
- Does this preserve the MVP nature of the product?
- Does this violate environment constraints?
- Does this add significant architecture complexity?
- Can it be validated within the current test approach?
- Will stakeholders still understand the product clearly?
