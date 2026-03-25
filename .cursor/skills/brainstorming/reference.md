# Brainstorming — Reference

Document path, commit, and implementation handoff. Use when writing the design doc or handing off to implementation.

---

## 1. Design Document

- **Path**: `docs/plans/YYYY-MM-DD-<topic>-design.md`  
  Example: `docs/plans/2025-02-05-auth-redesign-design.md`
- **Content**: Validated design only; clear sections (overview, architecture, components, data flow, error handling, testing); no implementation code unless it illustrates the design.
- **Style**: Clear and concise; use a writing-style skill if available.

---

## 2. Commit

- **Message**: e.g. `docs: add YYYY-MM-DD <topic> design` or `docs(plans): add <topic> design`.
- **Scope**: Design document only; no code changes in the same commit unless the user asks.

---

## 3. Implementation Handoff

- **Trigger**: Ask “Ready to set up for implementation?” after the design is documented and committed.
- **If yes**: Create an isolated workspace (e.g. git worktree) and a detailed implementation plan (tasks, order, acceptance criteria). Do not start coding until the user confirms the plan.
- **Optional skills**: git-worktrees for isolation; writing-plans (or project equivalent) for the implementation plan. Use if present in the environment; otherwise describe steps in plain language.
