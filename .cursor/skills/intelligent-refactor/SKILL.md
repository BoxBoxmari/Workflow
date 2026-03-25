---
name: intelligent-refactor
description: Refactors code systematically while preserving behavior. Ensures test coverage, applies incremental changes, improves quality and performance, and documents changes. Use when refactoring code, improving code quality, or when the user requests refactoring or code improvements.
---

# Intelligently Refactor and Improve Code Quality

Refactor code systematically: analyze, test, refactor incrementally, verify, and document. Preserve external behavior while improving internal structure.

## When to Use

- User requests refactoring or code improvements
- Code needs quality improvements (readability, maintainability, performance)
- Applying design patterns or reducing complexity
- Before major changes to ensure a solid foundation

## Core Workflow

1. **Pre-refactoring**: Identify what to refactor and why; understand current behavior; review tests and docs; map dependencies.
2. **Test coverage**: Ensure tests exist; write missing tests before refactoring; run tests to establish baseline.
3. **Strategy**: Define goals (performance, readability, maintainability); choose techniques (extract, rename, move, eliminate dead code, etc.); plan incremental steps.
4. **Environment**: Create branch (`git checkout -b refactor/<name>`); ensure tests pass; set up tooling if needed.
5. **Incremental changes**: Small, focused changes; run tests after each; commit frequently with clear messages; use IDE refactoring tools when available.
6. **Quality**: Improve naming; eliminate duplication (DRY); simplify conditionals; reduce length/complexity; improve separation of concerns.
7. **Performance**: Identify bottlenecks; optimize algorithms/data structures; reduce unnecessary work; improve memory usage.
8. **Patterns**: Apply design patterns where beneficial; improve abstraction/encapsulation; enhance modularity/reusability; reduce coupling.
9. **Error handling**: Standardize approaches; improve messages/logging; add exception handling; enhance resilience.
10. **Documentation**: Update comments; revise API docs if interfaces changed; ensure accuracy.
11. **Testing**: Add tests for new paths; improve coverage/quality; remove obsolete tests.
12. **Static analysis**: Run linters; use static analysis tools; check security; verify complexity metrics.
13. **Performance verification**: Run benchmarks; compare before/after; ensure no degradation.
14. **Integration**: Run full test suite; test dependent systems; verify functionality and edge cases.
15. **Review prep**: Review changes; ensure goals met; prepare explanation and rationale.
16. **Documentation**: Summarize changes; document breaking changes or new patterns; update project docs.
17. **Deployment**: Plan strategy; consider feature flags; prepare rollback; set up monitoring.

## Key Principles

- **Preserve behavior**: External behavior must remain unchanged; tests verify this.
- **Test-first**: Write or verify tests before refactoring; use tests as a safety net.
- **Incremental**: Small, focused changes; test after each; commit working state frequently.
- **Safety over speed**: Prioritize correctness; maintain test coverage throughout.
- **Document**: Explain changes, rationale, and benefits for future reference.

## Refactoring Techniques

- Extract Method/Function, Extract Class/Component
- Rename Variable/Method, Move Method/Field
- Replace Conditional with Polymorphism
- Eliminate Dead Code
- Apply design patterns where beneficial

## Reference

- **reference.md**: Full 17-step checklist with detailed instructions. Read when executing a full refactoring or validating the process.
