# Senior Backend — Reference

API design patterns, database optimization, security practices, commands, and troubleshooting. Use when designing APIs, tuning the database, or implementing security.

---

## 1. API Design Patterns

- **REST**: Resource-based URLs; GET/POST/PUT/PATCH/DELETE; HTTP status codes; consistent error shape (e.g. `{ code, message, details }`).
- **GraphQL**: Schema-first; resolvers thin; avoid N+1 (DataLoader/batching); pagination (cursor or offset) and limits.
- **Versioning**: URL path (e.g. `/v1/`) or header; deprecate with notice; avoid breaking changes without version bump.
- **Errors**: 4xx client, 5xx server; no stack traces in production; log details server-side.
- **Pagination**: Cursor-based for large lists; document `limit`/`offset` or `first`/`after`; set max page size.
- **Auth**: Prefer stateless (JWT) or standard (OAuth2); tokens in header or cookie; document scope/permissions.
- **Anti-patterns**: God endpoints; inconsistent naming; missing validation; leaking internals; no rate limiting on public APIs.

---

## 2. Database Optimization Guide

- **Schema**: Normalize where it helps; denormalize for read-heavy paths; use appropriate types and constraints.
- **Indexes**: Index columns in WHERE/JOIN/ORDER BY; avoid over-indexing writes; use EXPLAIN/ANALYZE to verify.
- **Queries**: Prefer parameterized queries; batch where possible; avoid N+1 (eager load, DataLoader, or batch queries).
- **Migrations**: Versioned, reversible when possible; run in order; test on copy of prod data.
- **Connection pooling**: Use pool with sensible min/max; timeouts and health checks; no connection leak in handlers.
- **Tool**: Run `database_migration_tool.py` for analysis and recommendations; use output to drive changes.

---

## 3. Backend Security Practices

- **Input**: Validate and sanitize all inputs; reject invalid early; use allowlists where possible.
- **SQL/NoSQL**: Parameterized/prepared statements only; no string concatenation for queries.
- **Auth**: Strong passwords (policy + hashing e.g. bcrypt/argon2); secure session/token storage; HTTPS only.
- **Secrets**: Env or secret manager only; never in code or logs; rotate regularly.
- **Headers**: Security headers (CORS, CSP, HSTS, etc.); consistent and locked down for production.
- **Dependencies**: Audit and update; pin versions; address known CVEs promptly.
- **Logging**: No secrets or PII in logs; structured logs; level and retention appropriate for production.

---

## 4. Common Commands

```bash
# Development
npm run dev
npm run build
npm run test
npm run lint

# Database / migrations (when scripts exist)
python scripts/database_migration_tool.py .
python scripts/api_scaffolder.py . [options]

# Load testing
python scripts/api_load_tester.py [arguments] [options]

# Deployment (context only)
docker build -t app:latest .
docker-compose up -d
kubectl apply -f k8s/
```

---

## 5. Troubleshooting

- **Script not found**: Confirm scripts under `scripts/` and run from repo root; if missing, apply patterns from this reference manually.
- **DB performance**: Use EXPLAIN/ANALYZE; check indexes and N+1; run migration tool if available; review connection pool and timeouts.
- **Auth issues**: Verify token validation, expiry, and scope; check CORS and cookie settings; ensure HTTPS in production.
- **Security**: Validate all inputs; audit dependencies; ensure no secrets in code or logs; follow reference.md security section.

---

## 6. Resources

- **This file (reference.md)**: API patterns, DB optimization, security, commands, troubleshooting.
- **Project docs**: README, ADRs, API specs, and runbooks for project-specific rules.
- **Scripts**: `api_scaffolder.py`, `database_migration_tool.py`, `api_load_tester.py` — run when present and use output to guide implementation.
