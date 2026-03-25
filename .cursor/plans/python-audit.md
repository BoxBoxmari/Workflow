# Plan: Python Repository Audit & Maintenance

**Topic:** python-audit  
**Last updated:** 2025-02-08

## WBS (Workstreams)

| # | Workstream | Owner | Output | Verify |
|---|------------|--------|--------|--------|
| 1 | Lint/format/type pipeline | Verifier | black, ruff, flake8, mypy | Commands pass |
| 2 | Security & performance scan | Security/Perf | Findings table | No Critical/High unmitigated |
| 3 | Docs review | Docs & ADR Writer | KEEP/UPDATE/DELETE table | Examples match code |
| 4 | Scripts review + move | — | scripts/ README, moves | Entrypoints valid |
| 5 | Repo reorganization | — | Move map, README/CI refs | No broken refs |
| 6 | Verification checklist | Verifier | Exact commands | Re-run and confirm |

## Decisions

- Use repo config (pyproject.toml, .flake8); no pytest.
- Black only (no ruff format); Ruff check --fix only.
- Move root scripts to scripts/; planning/debug docs to docs/; update refs.
- Path validation for soffice/docx (S2) deferred to follow-up.

## Action Plan (prioritized)

1. P0: Re-run mypy to completion; fix errors or document exceptions.
2. P1: Update docs (API, ARCHITECTURE, IT-DEPENDENCIES, scripts/README).
3. P1: Move verify_p0_columns.py, extract_gold_set.py → scripts/; update refs.
4. P2: Move ACTION_PLAN_*, EPIC_*, QUALITY_AUDIT_CONTEXT_SUMMARY.md → docs/ (optional).
5. P2: Add path validation for soffice (S2) in follow-up.
6. P3: Document .flake8 line length 200 vs Black 88 or align.

## Verification Checklist

```bash
black .
ruff check . --fix
flake8 .
mypy .
```

- **Pass criteria:** All exit 0; mypy at most notes (no errors).
- **Edge cases:** New Python files under same config; CI runs same commands.

## Risk / Rollback

- **Risks:** Script moves may break CI or local habits.
- **Rollback:** Revert moves and formatting via git.

## References

- Full report: `AUDIT_REPORT_PYTHON_MAINTENANCE.md` (repo root).
- Subagent protocol: `.cursor/agents/subagent-manager.md`.
