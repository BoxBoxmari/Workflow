---
name: senior-frontend
description: Comprehensive frontend development for modern, performant web applications using React, Next.js, TypeScript, and Tailwind CSS. Use PROACTIVELY for component scaffolding, performance optimization, bundle analysis, and UI best practices. Use when developing frontend features, optimizing performance, implementing UI/UX designs, managing state, or reviewing frontend code.
---

# Senior Frontend

Complete toolkit for senior frontend development with modern tools and best practices.

## Quick Start

### Core Capabilities

Three main capability areas (scripts are optional; implement or use when present):

```bash
# Component Generator
python scripts/component_generator.py <project-path> [options]

# Bundle Analyzer
python scripts/bundle_analyzer.py <target-path> [--verbose]

# Frontend Scaffolder
python scripts/frontend_scaffolder.py [arguments] [options]
```

## 1. Component Generator

- **Purpose**: Automated component scaffolding with best practices.
- **Features**: Configurable templates, quality checks, consistent structure.
- **Usage**: `python scripts/component_generator.py <project-path> [options]`

## 2. Bundle Analyzer

- **Purpose**: Analysis and optimization of frontend bundles.
- **Features**: Deep analysis, performance metrics, recommendations, automated fixes where safe.
- **Usage**: `python scripts/bundle_analyzer.py <target-path> [--verbose]`

## 3. Frontend Scaffolder

- **Purpose**: Project or feature scaffolding with production-grade defaults.
- **Features**: Custom configurations, integration-ready output, expert-level automation.
- **Usage**: `python scripts/frontend_scaffolder.py [arguments] [options]`

## Reference Documentation

When present in the skill or project, use:

- **React patterns**: `references/react_patterns.md` — patterns, examples, best practices, anti-patterns.
- **Next.js optimization**: `references/nextjs_optimization_guide.md` — step-by-step optimization, tool integration, performance tuning, troubleshooting.
- **Frontend best practices**: `references/frontend_best_practices.md` — stack details, configuration, security, scalability.

## Tech Stack

- **Frontend**: React, Next.js, TypeScript, Tailwind CSS; React Native, Flutter when relevant.
- **Backend/API**: Node.js, Express, GraphQL, REST.
- **Data**: PostgreSQL, Prisma, NeonDB, Supabase.
- **DevOps/Cloud**: Docker, Kubernetes, Terraform, GitHub Actions, CircleCI, AWS, GCP, Azure.

## Development Workflow

1. **Setup**: `npm install` (or `pip install -r requirements.txt`); copy `.env.example` to `.env`.
2. **Quality**: Run `python scripts/bundle_analyzer.py .` when available; review and apply recommendations.
3. **Implementation**: Follow patterns in the reference docs above.

## Best Practices Summary

- **Code quality**: Follow established patterns, write tests, document decisions, review regularly.
- **Performance**: Measure before optimizing, use appropriate caching, optimize critical paths, monitor in production.
- **Security**: Validate inputs, use parameterized queries, implement proper auth, keep dependencies updated.
- **Maintainability**: Clear code, consistent naming, helpful comments, keep it simple.

## Common Commands

```bash
npm run dev
npm run build
npm run test
npm run lint
docker build -t app:latest .
docker-compose up -d
kubectl apply -f k8s/
```

## Troubleshooting

Check `references/frontend_best_practices.md` for detailed troubleshooting. Review script output, reference docs, and error logs when issues arise.

## Resources

- Pattern reference: `references/react_patterns.md`
- Next.js optimization: `references/nextjs_optimization_guide.md`
- Best practices: `references/frontend_best_practices.md`
- Scripts: `scripts/` directory (when present)
