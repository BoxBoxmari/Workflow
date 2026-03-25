---
name: code-quality-review
description: Runs a full code quality review covering security, performance, and architecture. Use when the user requests a code review, quality audit, or analysis of a file path, commit range, or the full repo.
---

# Code Quality Review

Run a structured code quality review: security, performance, architecture, tests, and docs. Use a file path, commit hash, or `--full` for the whole repo.

## When to Use

- User asks for a code review, quality audit, or quality analysis
- Reviewing a specific file, commit(s), or the full repository
- Before merge or release to surface issues and recommendations

## Input

- **file-path**: Review one file or directory.
- **commit-hash**: Review changes in a commit or range (e.g. `HEAD~5..HEAD`).
- **--full**: Review the whole repository (structure, config, main code paths).

If no argument is given, use recent changes (e.g. `git diff --stat HEAD~5`) and repo context.

## Current State (Check First)

- **Git**: `git status --porcelain`; `git diff --stat HEAD~5`; `git log --oneline -5`.
- **Build**: Run the project build (e.g. `npm run build`) if defined; note success or failure.
- **Config**: Identify primary language/framework and config files (package.json, requirements.txt, Cargo.toml, etc.).
- **Docs**: Skim README and key docs for context.

## Review Steps

1. **Repository**: Structure, language/framework, config files, README and docs.
2. **Code quality**: Smells, anti-patterns, potential bugs; style and naming; unused/dead code; error handling and logging.
3. **Security**: Common vulnerabilities (injection, XSS, etc.); hardcoded secrets; auth/authz; input validation and sanitization.
4. **Performance**: Bottlenecks; inefficient algorithms or queries; memory and leaks; bundle size and optimization.
5. **Architecture**: Organization, separation of concerns, abstraction, modularity; dependencies and coupling; scalability and maintainability.
6. **Testing**: Coverage and quality; gaps; test structure; suggested scenarios.
7. **Documentation**: Comments, API docs, README/setup; gaps and improvements.
8. **Recommendations**: Prioritize by severity (critical, high, medium, low); actionable items with file paths and line numbers where applicable; summary and next steps.

Be constructive; give specific examples with file paths and line numbers when possible.

## Output

- **Findings**: Grouped by area (security, performance, architecture, etc.); each with severity, location, and brief description.
- **Recommendations**: Specific, actionable; suggest tools or practices where useful.
- **Summary**: Prioritized next steps and overall assessment.

## Reference

- **reference.md**: Full step-by-step checklist and output template. Read when running a full review or validating structure.
