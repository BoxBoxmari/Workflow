---
name: cursor-project-config
description: Works with Cursor project configuration under .cursor/ (rules, skills, workspace). Use when editing or adding rules, managing skills, understanding .cursor structure, or when the user mentions .cursor, Cursor rules, or Cursor skills.
---

# Cursor Project Config — .cursor/ Structure and Usage

This skill guides the agent when working with the project's `.cursor/` folder: rules, skills, and workspace.

## When to Use

- User asks about or references `.cursor/`, Cursor rules, or Cursor skills.
- Task involves adding, editing, or understanding project rules or skills.
- Need to know where rules/skills live or how they are applied.

## .cursor/ Structure (This Repo)

```
.cursor/
├── Quality Audit.code-workspace   # VS Code/Cursor workspace
├── agents/                         # Subagent definitions (personas/protocols)
│   ├── agent-skills-runner.md
│   └── verifier.md
├── commands/                      # One-shot workflow commands (invoke full procedure)
│   └── subagent-workflow.md       # Runs Subagent Manager 7-step orchestration
├── rules/                         # Project rules (MDC)
│   ├── code-reviewer.mdc
│   └── python.mdc
└── skills/                        # Project Cursor skills
    ├── agent-skills/
    │   └── SKILL.md
    ├── create-subagent/
    │   └── SKILL.md
    ├── cursor-project-config/
    │   └── SKILL.md
    └── ui-ux-pro-max/
        ├── SKILL.md
        └── scripts/
```

- **agents/** — Subagent `.md` files. Define role, responsibilities, output format; invoked by name or @file.
- **commands/** — Command `.md` files. One-shot prompts that run a full workflow (e.g. Subagent Manager 7-step orchestration). Use when the user wants to trigger a repeatable procedure with a single invocation.
- **rules/** — `.mdc` rule files. Loaded by Cursor; apply to matching globs (e.g. `**/*` or `**/*.py`).
- **skills/** — Skill directories, each with `SKILL.md`. Skills are discovered by description and applied when relevant.

Use **forward slashes** in paths (e.g. `.cursor/skills/`, not `.cursor\skills\`).

## Rules vs Skills vs Subagents

| | Rules | Skills | Subagents |
|---|--------|--------|-----------|
| **Location** | `.cursor/rules/*.mdc` | `.cursor/skills/<name>/SKILL.md` | `.cursor/agents/*.md` |
| **Role** | Persistent constraints (style, security, workflow) | Task-specific procedures and knowledge | Agent personas/protocols (role, output format) |
| **When applied** | By glob + priority in rule file | When description matches the user request or task | When user invokes or @file references the subagent |
| **Create/edit** | Use create-rule skill or edit `.mdc` directly | Use create-skill skill or add folder + `SKILL.md` | Use create-subagent skill or add `.md` in `agents/` |

Do not create or modify files under `~/.cursor/skills-cursor/`; that directory is for Cursor's built-in skills only.

## Adding or Changing Rules

1. **New rule**: Prefer the **create-rule** skill (if available) so the agent follows the rule format and placement.
2. **Edit existing**: Open the right `.cursor/rules/<name>.mdc`, change content and globs/priority as needed.
3. **Scope**: Use globs in the rule file to limit where the rule applies (e.g. `**/*.py`, `**/tests/**`).

## Adding or Changing Skills

1. **New skill**: Use the **create-skill** skill (if available) to get the right structure and description.
2. **Manual**: Create `.cursor/skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`) and body (instructions, examples).
3. **Discovery**: The `description` field is used to decide when to apply the skill; include clear trigger terms and “Use when…” phrasing.

## Quick Reference

- **List rules**: `ls .cursor/rules/` or read rule files to see globs and content.
- **List skills**: `ls .cursor/skills/`; each subfolder is one skill.
- **Read a skill**: Open `.cursor/skills/<skill-name>/SKILL.md`.
- **Workspace**: `.cursor/Quality Audit.code-workspace` — treat as workspace config; avoid overwriting unless the user asks.

## Related

- **create-rule** — Use when the user wants to add or refine a Cursor rule.
- **create-skill** — Use when the user wants to add or refine a Cursor skill.
- **create-subagent** — Use when the user wants to create or edit a subagent under `.cursor/agents/`.
- **agent-skills** — Use when the task should consider skills under `.agent/skills` (this repo’s agent skills library).
