---
name: brainstorming
description: Use before any creative work—features, components, new functionality, or behavior changes. Explores user intent, requirements, and design through dialogue before implementation. Use when starting a feature, adding components, or changing behavior to align on intent and design first.
---

# Brainstorming Ideas Into Designs

Turn ideas into concrete designs and specs through dialogue. Use this skill **before** implementation: understand intent and constraints, explore approaches, then present and validate the design in small steps.

## When to Use

- Before creating features, building components, or adding functionality
- Before modifying existing behavior or architecture
- When the user’s request is vague or needs clarification
- When you need to align on requirements and design before coding

## The Process

### 1. Understanding the Idea

- **Context first**: Check project state (relevant files, docs, recent commits).
- **One question at a time**: Do not ask multiple questions in one message; if a topic needs more depth, split into separate questions.
- **Prefer multiple choice** when possible; open-ended is fine when needed.
- **Focus on**: purpose, constraints, and success criteria.

### 2. Exploring Approaches

- Propose **2–3 approaches** with clear trade-offs.
- Present options conversationally; **lead with your recommended option** and explain why.
- Be ready to refine or drop options based on user feedback.

### 3. Presenting the Design

- Once the idea is clear, present the design in **sections of 200–300 words**.
- **Check after each section**: “Does this look right so far?” and adjust if not.
- Cover: architecture, components, data flow, error handling, testing (as relevant).
- Go back and clarify whenever something is unclear.

## Key Principles

- **One question at a time** — Avoid overwhelming the user.
- **Multiple choice preferred** — Easier to answer when it fits.
- **YAGNI** — Remove unnecessary features from designs.
- **Explore alternatives** — Propose 2–3 approaches before settling.
- **Incremental validation** — Validate each section before moving on.
- **Be flexible** — Clarify and revise when something doesn’t make sense.

## After the Design

- **Document**: Write the validated design to `docs/plans/YYYY-MM-DD-<topic>-design.md`. Use clear, concise prose (e.g. elements-of-style or similar skill if available).
- **Commit**: Commit the design document to git.
- **Implementation handoff**: Ask “Ready to set up for implementation?” If yes, use git worktrees and a detailed implementation plan (e.g. writing-plans or project-specific planning) to proceed; do not start coding until the user confirms.

## Reference

- **reference.md**: Doc path and naming, commit message pattern, implementation handoff checklist. Read when documenting or handing off.
