# Code Reviewer — Reference

Extended checklist, standards, antipatterns, and troubleshooting for the code-reviewer skill. Use when you need detailed criteria or examples.

---

## 1. Code Review Checklist (Detailed)

- **Logic**: Correct behavior; edge cases and null/empty inputs handled; no off-by-one or race conditions where relevant.
- **Security**: No hardcoded secrets; inputs validated and sanitized; SQL/NoSQL/commands parameterized; auth and authorization enforced; sensitive data not logged.
- **Style**: Follows project conventions (linter/formatter); consistent naming; no dead or commented-out code.
- **Structure**: Single responsibility; functions/classes at reasonable size; clear separation of concerns; no unnecessary coupling.
- **Error handling**: Errors caught and handled; messages safe for logs; failures degrade gracefully where appropriate.
- **Tests**: New/changed behavior covered; tests deterministic; no flaky or overspecified tests.
- **Performance**: No obvious N+1, heavy loops, or large allocations in hot paths; caching and I/O usage appropriate.
- **Documentation**: Public APIs and non-obvious behavior documented; ADRs or design notes updated when relevant.

---

## 2. Coding Standards (Summary)

- **Code quality**: Prefer established patterns; avoid duplication; document non-obvious decisions.
- **Performance**: Measure before optimizing; cache where it helps; optimize critical paths; monitor in production.
- **Security**: Validate all inputs; use parameterized queries; implement auth correctly; keep dependencies updated.
- **Maintainability**: Clear names; small, focused units; helpful comments; keep complexity low.

Apply language- and framework-specific style (e.g. ESLint/Prettier, Black/ruff, gofmt) as configured in the project.

---

## 3. Common Antipatterns

- **God objects/modules**: One type or file doing too much — suggest splitting by responsibility.
- **Copy-paste duplication**: Same logic in multiple places — suggest extraction and reuse.
- **Missing validation**: User or external input used without validation or sanitization — flag as security/maintainability risk.
- **Silent failures**: Swallowing errors or returning without signaling failure — request explicit handling and logging.
- **Exposed secrets**: API keys, tokens, or passwords in code or logs — critical; must be removed and moved to config/secrets.
- **Brittle tests**: Tests that depend on order, time, or environment in a way that causes flakiness — suggest deterministic, isolated tests.
- **Over-engineering**: Unnecessary abstraction or indirection for current requirements — suggest simpler design.

---

## 4. Development Workflow (For Reviewers)

- **Setup**: Ensure deps installed (`npm install` / `pip install -r requirements.txt`), env configured (e.g. `.env` from `.env.example`).
- **Quality checks**: Run linter, formatter, and type checks; run `code_quality_checker` if present; use output in review.
- **Tests**: Run full test suite (or relevant subset); treat failures as blocking for merge unless explicitly documented.
- **Scripts**: Use `pr_analyzer.py`, `code_quality_checker.py`, and `review_report_generator.py` when available to support findings; do not describe script internals unless debugging.

---

## 5. Common Commands (Reference)

```bash
# Development
npm run dev
npm run build
npm run test
npm run lint

# Analysis (when scripts exist)
python scripts/code_quality_checker.py .
python scripts/review_report_generator.py --analyze

# Deployment (for context only; not part of review)
docker build -t app:latest .
docker-compose up -d
kubectl apply -f k8s/
```

---

## 6. Troubleshooting

- **Script not found**: Confirm scripts live under `scripts/` and the command is run from repo root; if missing, review manually using this checklist and reference.
- **Conflicting standards**: Prefer project config (e.g. `.eslintrc`, `pyproject.toml`) over generic advice; note conflicts in feedback.
- **Large or ambiguous diff**: Use PR analyzer if available; otherwise break review by module or commit and report per area.

---

## 7. Resources

- **This file (reference.md)**: Checklist, standards, antipatterns, workflow, commands, troubleshooting.
- **Project docs**: README, CONTRIBUTING, ADRs, and architecture docs for project-specific rules.
- **Scripts**: `scripts/pr_analyzer.py`, `scripts/code_quality_checker.py`, `scripts/review_report_generator.py` — run them when present and use output in the review.
