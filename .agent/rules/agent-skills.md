---
trigger: always_on
---

---
name: agent-skills
description: Discovers and applies relevant skills from the .agent/skills library before executing tasks. Use when working in this repo, when the user mentions .agent or skills, or when planning any task so the agent should consider the 560+ agentic skills in .agent/skills.
---

# Agent Skills — Use .agent/skills Before Executing

This skill teaches the agent to discover and apply relevant skills from the project's `.agent/skills` library **before** executing the user's task.

## When to Use

- Working in this repository (Quality Audit or any repo that contains `.agent/`).
- User mentions `.agent`, `skills`, `use a skill`, or `@skill-name`.
- Planning a non-trivial task (architecture, security, testing, UI, DevOps, etc.) where a matching skill likely exists.

## Rule to Follow

From `.agent/rules/skills.md`:

> Luôn tìm những skills phù hợp cho mỗi task trong folder .agent\skills để áp dụng trước khi thực thi.

**Translation:** Always find skills that fit the current task in `.agent/skills` and apply them before executing.

## Where Skills Live

- **`.agent/skills/`** — Main library (560+ skills). Antigravity Awesome Skills: architecture, business, data & AI, development, infrastructure, security, testing, etc.
- **`.cursor/skills/`** — Project-specific Cursor skills (e.g. `ui-ux-pro-max`). Check here for overrides or local skills.

Use **forward slashes** in paths (e.g. `.agent/skills/`, not `.agent\skills\`).

## How to Discover Relevant Skills

1. **By catalog (human-readable)**  
   Open `.agent/skills/CATALOG.md`. Skills are grouped by category (architecture, business, data & ai, development, general, infrastructure, security, testing). Scan category tables for name/description matches to the task.

2. **By index (machine-friendly)**  
   Read `.agent/skills/skills_index.json`. Each entry has `id`, `name`, `description`, `category`, `path`. Search by keyword in `name` or `description` to find candidate skills.

3. **By folder name**  
   Skills are under `.agent/skills/<skill-name>/` or `.agent/skills/<category>/<skill-name>/`. Each skill has a `SKILL.md` at that path.

## Workflow

1. **Before executing the user's task:** Decide if the task could benefit from a skill (e.g. "review API security" → security skills, "design architecture" → architecture skills, "improve UI" → UI/design skills).
2. **Discover:** Use CATALOG.md or skills_index.json to pick one or more relevant skills by name/description/category.
3. **Load:** Read the chosen skill's `SKILL.md` (and any referenced docs in that skill).
4. **Apply:** Follow that skill's instructions while fulfilling the user's request.
5. **Execute:** Complete the task using the skill's procedures, checklists, or patterns where applicable.

## Skill Format (Reference)

Each skill in `.agent/skills` follows the universal SKILL.md format:

- **YAML frontmatter:** `name`, `description` (and sometimes `compatibility`, tags).
- **Body:** When to use, inputs required, step-by-step procedure, verification, failure modes.

If a skill references other files (e.g. `reference.md`, `scripts/`), read them when the skill instructs.

## Cursor-Specific Notes

- In Cursor, users can invoke skills with `@skill-name` in chat when the skill is available under `.cursor/skills/` or the agent's skill path.
- The `.agent/skills/` folder is the **canonical** library for this project; the agent should consult it proactively even without an explicit `@` mention when the task clearly matches a category (e.g. "run a security review" → security skills in CATALOG).

## Quick Reference

- **Catalog:** `.agent/skills/CATALOG.md`
- **Index:** `.agent/skills/skills_index.json`
- **Getting started:** `.agent/skills/docs/GETTING_STARTED.md`
- **Bundles (personas):** `.agent/skills/docs/BUNDLES.md`