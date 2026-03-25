# Alignment Regression Matrix

Date: 2026-03-24  
Scope: Current production hardening gate

## Baseline Automated Result

- Command: `python -m pytest -q`
- Result: `305 passed, 9 skipped`
- Status: PASS
- Purpose: Reference point for production hardening regression comparison.

## Regression Matrix

|Area|Baseline Status|Current Status|Evidence|Notes|
|---|---|---|---|---|
|Full automated suite (`pytest -q`)|PASS|PASS|`305 passed, 9 skipped`|Updated on current hardening gate|
|Lint (`flake8`)|PASS|PASS|`python -m flake8 .` exit code 0|Verifier gate|
|Type check (`mypy`)|PASS|PASS|`python -m mypy .` exit code 0|Verifier gate|
|Dependency audit (`pip_audit`)|PASS|PASS|`python -m pip_audit` exit code 0|Verifier gate|
|Legacy run (Graph Runtime OFF)|NOT_RUN|PENDING_MANUAL|Manual checklist section 3|Required for final sign-off|
|Graph run semantics (Graph Runtime ON)|NOT_RUN|PENDING_MANUAL|Manual checklist section 4|Required for final sign-off|
|Attachment mapping|NOT_RUN|PENDING_MANUAL|Manual checklist section 5|Required for final sign-off|
|Run history reload|NOT_RUN|PENDING_MANUAL|Manual checklist section 6|Required for final sign-off|
|Inspector render contract|NOT_RUN|PENDING_MANUAL|Manual checklist section 7|Required for final sign-off|

## Update Policy

For each production hardening cycle:

1. Re-run targeted tests for changed modules.
2. Re-run `python -m pytest -q` before release cut.
3. Update `Current Status`, `Evidence`, and `Notes` for affected rows.
4. If any row regresses to FAIL, stop release and open fix before deploy.
