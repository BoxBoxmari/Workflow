---
name: systematic-bugfix
description: Execute a 9-step evidence-based bugfix workflow: identify code paths and tests, add temporary logging, reproduce and hypothesize, add failing tests, minimal fix, verify, cleanup, full test/lint, then report. Use when debugging a specific bug, fixing a failing test, or when the user asks for a systematic bugfix or root-cause fix.
---

# Systematic Bugfix Workflow

Execute the following steps in order. Do not skip steps. Track progress with the checklist.

## Checklist

```
- [ ] 1. Identify relevant code paths and existing tests
- [ ] 2. Add temporary logging around critical points
- [ ] 3. Run related/reproduction tests; form root-cause hypothesis from logs
- [ ] 4. Add or update tests that reproduce the bug (must fail before fix)
- [ ] 5. Implement minimal fix preserving existing correct behavior
- [ ] 6. Re-run tests and refine until behavior and logs confirm the fix
- [ ] 7. Remove temporary logging; keep only low-noise instrumentation if needed
- [ ] 8. Run full (or feature-related) test suite and lint
- [ ] 9. Report back with required sections
```

---

## Step 1: Identify relevant code paths and existing tests

- Use grep/semantic search to find code that handles the failing behavior or error path.
- Locate existing tests (unit/integration) that cover that area.
- List: entry points, call sites, and test files that should be run.

---

## Step 2: Add temporary logging around critical points

- Add logging at: function entry/exit, branch decisions, and state that might explain the bug.
- Log inputs, key intermediates, and outputs; avoid logging secrets or huge payloads.
- Use a consistent prefix (e.g. `[DEBUG-BUGFIX]`) so it can be removed later.

---

## Step 3: Run related tests and form a root-cause hypothesis

- Run the related test(s) and any reproduction scenario.
- Capture log output and failure messages.
- State a single root-cause hypothesis: "Bug occurs because X when Y."

---

## Step 4: Add or update tests that reproduce the bug

- Add or change a test so it **fails** with the current (buggy) code.
- The test must assert the intended behavior that is currently broken.
- Run the new/updated test and confirm it fails before applying any fix.

---

## Step 5: Implement a minimal fix

- Change only what is necessary to fix the root cause.
- Do not refactor unrelated code or change public APIs unless required.
- Preserve all existing correct behavior.

---

## Step 6: Re-run tests and refine until fix is confirmed

- Re-run the reproduction test(s); they must pass.
- Use logs to confirm the fix (e.g. expected branch taken, correct values).
- If tests still fail or logs contradict the fix, revise the fix and repeat.

---

## Step 7: Remove temporary logging

- Remove all temporary debug logging added in Step 2.
- Keep only long-term, low-noise instrumentation (e.g. structured metrics or error context) if it adds value.

---

## Step 8: Run full (or feature-related) tests and lint

- Run the full test suite, or at least all tests for the affected feature/module.
- Run the project linter (e.g. ruff, flake8, eslint) and fix any new issues.
- Do not consider the workflow complete until tests and lint pass.

---

## Step 9: Report back

Produce a short report with these four sections. Use the exact headings.

### Root cause analysis

- 2–4 sentences: what was wrong, in which component, and under what conditions.

### Files changed and rationale

- List each modified file and one sentence per file explaining why it was changed.

### Tests run and results

- Commands run (e.g. `pytest path/to/test_file.py`, `npm run lint`).
- Result: PASS or FAIL; if FAIL, summarize the failure.

### Remaining risks or edge cases

- 1–3 bullets: other code paths, inputs, or environments that might still be affected or need regression testing.

---

## Anti-patterns

- Do not fix by guessing; the reproduction test must fail before the fix and pass after.
- Do not leave temporary logging in the codebase after Step 7.
- Do not skip the full (or feature) test run and lint before reporting.
