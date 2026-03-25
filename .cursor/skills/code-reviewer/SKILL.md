---
name: code-reviewer
description: Comprehensive code review for TypeScript, JavaScript, Python, Swift, Kotlin, Go. Includes automated analysis, best-practice checks, security scanning, and review checklist generation. Use when reviewing pull requests, providing code feedback, identifying issues, or enforcing code quality standards.
---

# Code Reviewer

Review code for quality, security, and maintainability across TypeScript, JavaScript, Python, Swift, Kotlin, and Go. Apply when reviewing pull requests, giving code feedback, or ensuring quality standards.

## When to Use

- Reviewing pull requests or staged changes
- User asks for code review or feedback
- Enforcing code quality or security before merge
- Generating or running review checklists and reports

## Quick Workflow

1. Inspect changes: run `git diff` (or use PR context) and focus on modified files.
2. Run automated checks when scripts exist (see [Scripts](#scripts)).
3. Apply the [Review checklist](#review-checklist) and produce feedback in the [Feedback format](#feedback-format).
4. For detailed patterns and antipatterns, see [reference.md](reference.md).

## Review Checklist

- **Correctness**: Logic correct, edge cases and error paths handled.
- **Security**: No exposed secrets or API keys; input validated; parameterized queries / safe APIs; auth and permissions correct.
- **Readability**: Simple, clear code; consistent naming; no unnecessary duplication.
- **Maintainability**: Functions focused, reasonable size; dependencies and side effects clear.
- **Testing**: Changes covered by tests; tests stable and meaningful.
- **Performance**: No obvious bottlenecks; appropriate use of caching and I/O.

## Feedback Format

Organize feedback by priority:

- **Critical** (must fix before merge): correctness, security, data integrity.
- **Warnings** (should fix): style, maintainability, missing tests, performance.
- **Suggestions** (consider): readability, minor improvements, optional refactors.

Include concrete examples or code snippets for fixes when useful.

## Scripts

If the project provides these under `scripts/`, run them as part of the review when relevant:

**PR Analyzer** — analyze PR scope and changed files:
```bash
python scripts/pr_analyzer.py <project-path> [options]
```

**Code Quality Checker** — static analysis and quality metrics:
```bash
python scripts/code_quality_checker.py <target-path> [--verbose]
```

**Review Report Generator** — generate a structured review report:
```bash
python scripts/review_report_generator.py [arguments] [options]
```

Use script output to populate findings and the review checklist; do not report script internals unless debugging.

## Tech Stack (Scope)

Languages in scope: TypeScript, JavaScript, Python, Go, Swift, Kotlin.  
Context may include: React, Next.js, Node/Express, REST/GraphQL, PostgreSQL/Prisma, Docker/Kubernetes, GitHub Actions/CircleCI, AWS/GCP/Azure. Apply language- and framework-specific best practices when reviewing.

## Reference

- **reference.md**: Code review checklist, coding standards, common antipatterns, troubleshooting, and extended guidance. Read when you need detailed criteria or examples.
