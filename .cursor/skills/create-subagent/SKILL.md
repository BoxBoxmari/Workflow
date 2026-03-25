---
name: create-subagent
description: Creates Cursor subagent definitions under .cursor/agents/. Use when the user wants to create a subagent, add an agent persona, define a specialized workflow agent, or asks about .cursor/agents/ or subagent format.
---

# Creating Cursor Subagents

This skill guides creating **subagent** definitions for Cursor. Subagents are specialized agent personas or protocols stored under `.cursor/agents/` as Markdown files. They define role, responsibilities, output format, and constraints so the main agent can adopt that behavior when the subagent is invoked or referenced.

## When to Use

- User says "create a subagent", "add a subagent", or "create this subagent".
- User references `.cursor/agents/` or wants a new agent persona/workflow.
- Task is to define a specialized agent (e.g. reviewer, runner, verifier) for the project.

## Where Subagents Live

```
.cursor/
└── agents/
    ├── agent-skills-runner.md
    ├── verifier.md
    └── <your-subagent>.md
```

- **Path**: `.cursor/agents/<name>.md` (use forward slashes in docs).
- **Format**: Single `.md` file per subagent; no subfolder required.

## File Structure

Each subagent file has **YAML frontmatter** and a **Markdown body**.

### Frontmatter (required)

```yaml
---
name: short-name
description: One line: what this subagent does and when to use it.
---
```

| Field         | Rules                                      | Purpose                          |
|---------------|--------------------------------------------|----------------------------------|
| `name`        | Lowercase, hyphens, no spaces, max ~64 chars | Identifier; used in file name    |
| `description` | One concise sentence; include trigger terms | Discovery when to apply subagent |

### Body sections (recommended)

1. **Title** — `# Subagent Name` (match the role).
2. **Role** — One short paragraph: "You are the **X** subagent. Your role is..."
3. **Responsibilities** — Numbered list of what the subagent must do.
4. **Output format** — How the subagent should structure its response (e.g. Summary, Commands run, Passed/Failed).
5. **Constraints** — Bullet list of what the subagent must not do or must always do.

## Template

```markdown
---
name: my-subagent
description: Short description and when to use (e.g. "Use when the user asks for X or mentions Y").
---

# My Subagent Name

You are the **My Subagent Name** subagent. Your role is to [one sentence].

## Responsibilities

1. **First duty** — What to do.
2. **Second duty** — What to do.
3. **Third duty** — What to do.

## Output format

Produce a response that includes:

- **Section A**: ...
- **Section B**: ...
- **Section C**: ...

## Constraints

- Constraint one.
- Constraint two.
```

## Examples (from this repo)

- **agent-skills-runner** — Discovers and applies skills from `.agent/skills` before executing tasks; reports which skills were applied.
- **verifier** — Validates completed work, runs tests, reports Passed/Failed/Incomplete.

## Checklist

- [ ] File created at `.cursor/agents/<name>.md`.
- [ ] Frontmatter has `name` and `description`.
- [ ] Description includes both what the subagent does and when to use it (trigger terms).
- [ ] Body has Role, Responsibilities, Output format, and Constraints.
- [ ] Paths in the file use forward slashes (e.g. `.cursor/agents/`, `.agent/skills/`).
- [ ] Content is concise; keep file under ~150 lines unless the role is complex.

## Rules vs skills vs subagents

| Concept   | Location              | Role |
|----------|------------------------|------|
| **Rules**   | `.cursor/rules/*.mdc`   | Persistent constraints by glob. |
| **Skills**  | `.cursor/skills/<name>/SKILL.md` | Task procedures; applied when description matches. |
| **Subagents** | `.cursor/agents/*.md` | Agent personas/protocols; define role and output format. |

Subagents are referenced by name or by reading the file; they are not auto-loaded by glob like rules. The user or the main agent invokes them (e.g. "use the verifier subagent" or by including `@.cursor/agents/verifier.md`).
