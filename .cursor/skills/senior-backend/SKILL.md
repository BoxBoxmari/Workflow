---
name: senior-backend
description: Backend development for scalable systems using Node.js, Express, Go, Python, Postgres, GraphQL, and REST. Includes API scaffolding, database optimization, security, and performance tuning. Use when designing APIs, optimizing queries, implementing business logic, handling auth, or reviewing backend code.
---

# Senior Backend

Toolkit for building and maintaining scalable backends: API design, database optimization, security, and performance.

## When to Use

- Designing or implementing REST/GraphQL APIs
- Optimizing database queries, migrations, or schema
- Implementing business logic, auth, or authorization
- Reviewing or refactoring backend code
- Running API load tests or migration checks

## Quick Workflow

1. **Scaffold**: Use API scaffolder when starting or extending an API surface.
2. **Database**: Use migration tool for schema changes and optimization checks.
3. **Validate**: Use load tester for performance and stability before release.
4. For patterns and security, see [reference.md](reference.md).

## Scripts

When the project provides these under `scripts/`, run them as needed:

**API Scaffolder** — generate API structure and endpoints:
```bash
python scripts/api_scaffolder.py <project-path> [options]
```

**Database Migration Tool** — migrations and DB optimization analysis:
```bash
python scripts/database_migration_tool.py <target-path> [--verbose]
```

**API Load Tester** — load and stress testing for APIs:
```bash
python scripts/api_load_tester.py [arguments] [options]
```

Use script output to guide implementation; do not report script internals unless debugging.

## Core Capabilities

- **API design**: REST/GraphQL conventions, versioning, errors, pagination; contract-first when appropriate.
- **Database**: Postgres (or project DB); schema design, indexes, migrations, connection pooling; avoid N+1 and heavy queries.
- **Security**: Input validation, parameterized queries, auth (e.g. JWT/OAuth), authorization, secrets in env; no credentials in code.
- **Performance**: Measure first; cache where useful; optimize hot paths; use async/connection pooling; monitor in production.
- **Maintainability**: Clear structure, consistent naming, tests, and docs for APIs and critical logic.

## Tech Stack (Scope)

**Backend**: Node.js, Express, Go, Python (FastAPI/Flask/Django).  
**APIs**: REST, GraphQL.  
**Database**: PostgreSQL, Prisma/ORMs, migrations.  
**DevOps/Cloud**: Docker, Kubernetes, Terraform, GitHub Actions, AWS/GCP/Azure.  

Apply language- and framework-specific best practices; prefer project conventions over generic advice.

## Best Practices Summary

- **Code quality**: Follow project patterns; write tests; document API and non-obvious logic.
- **Performance**: Measure before optimizing; use caching and connection pooling; optimize critical paths.
- **Security**: Validate inputs; parameterized queries; proper auth/authz; dependencies updated.
- **Maintainability**: Clear code; consistent naming; small, focused modules.

## Reference

- **reference.md**: API design patterns, database optimization guide, backend security practices, common commands, troubleshooting. Read when designing APIs, tuning DB, or implementing security.
