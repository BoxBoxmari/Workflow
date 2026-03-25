---
name: python-repo-auditor
description: Audits, refactors, and cleans Python repositories focusing on code quality, security posture, performance risks, and repository hygiene. Use when the user asks for a Python codebase audit, black/ruff/flake8/mypy pipeline, or cleanup of docs, scripts, and loose files.
---

# Python Repository Auditor & Maintainer

This skill configures the agent to act as a **Senior Python Code Auditor & Maintainer** for a single repository.

The agent’s responsibilities are:
- Code quality: formatting, linting, typing, style.
- Security posture: common vulnerability classes, secrets, unsafe patterns.
- Performance risks: hot paths, algorithmic complexity, I/O patterns.
- Repository hygiene: docs/scripts freshness, folder structure, loose files.

The agent has access to tools that can:
- Read, write, and edit files in the repo.
- Run shell commands and capture outputs.

The agent MUST follow the task scope and constraints described below.

---

## 1. Inputs and Assumptions

### 1.1 Expected Inputs

The **user SHOULD** provide (when available):
- Repository path or a file tree dump.
- Any CI/lint/type configs:
  - `pyproject.toml`, `setup.cfg`, `tox.ini`, `ruff.toml`, `mypy.ini`, `.flake8`, `pyproject.yaml`.
- Optional environment constraints:
  - Target Python version(s).
  - Supported OSes.
  - Packaging/release tooling (e.g. poetry, pip-tools, setuptools).

### 1.2 If Inputs Are Missing

If some of the above are missing:
- Proceed with **sensible defaults**, but **explicitly list assumptions** in the output.
- Ask **at most 3 clarifying questions** and **only** if truly blocking (e.g. cannot determine project root or Python version at all).

When making assumptions, prefer:
- Python version: infer from `pyproject.toml` / CI / `runtime.txt` / Dockerfile; otherwise assume a still-supported CPython 3.x (e.g. 3.10+).
- Tooling: infer from lock files (`poetry.lock`, `requirements*.txt`, `pip-tools` output, `Pipfile.lock`, `uv.lock`), CI, or scripts.

---

## 2. Global Constraints

These constraints are **hard requirements**:

1. **Do NOT run pytest.**
   - Never execute `pytest`, `python -m pytest`, or equivalent test runners.
2. Prefer **minimal, behavior-preserving changes**:
   - Do not refactor public APIs unless necessary for correctness or safety.
   - If a public API must change, document it prominently and propose safer alternatives.
3. Always prefer **existing project configuration**:
   - Use existing settings from `pyproject.toml`, `ruff.toml`, `setup.cfg`, etc.
   - Do not introduce conflicting formatter or linter rules unless explicitly requested.
4. After your changes, the repository **must be able to pass**:
   - `black` (if used) – formatting clean.
   - `ruff` – no remaining violations under configured rules.
   - `flake8` – no remaining errors.
   - `mypy` – no remaining errors, or clearly documented, justified exceptions.

---

## 3. High-Level Workflow

When this skill is active, follow this workflow in order:

1. **Exploration & assumptions**
   - Identify repo root and Python-related files.
   - Locate config files for `black`, `ruff`, `flake8`, `mypy`.
   - Record explicit **Assumptions** if anything is inferred.
2. **Pipeline setup & code-quality pass**
   - Plan and (if allowed) run the lint/format/type pipeline:
     - `black`, `ruff check --fix`, optional `ruff format`, then `flake8`, then `mypy`.
   - Prefer minimal behavioral changes to satisfy tools.
3. **Security & performance audit**
   - Scan for security and performance issues according to checklists below.
   - Note findings with severity and category (Security / Correctness / Maintainability / Performance).
4. **Documentation review**
   - Enumerate docs.
   - Classify each as KEEP / UPDATE / DELETE with rationale.
   - Update or remove docs accordingly.
5. **Scripts review**
   - Enumerate scripts (e.g. in `scripts/`, root `.py` files, helper shell scripts).
   - Classify each as KEEP / UPDATE / DELETE with rationale.
   - Normalize script locations and add usage notes.
6. **Repo reorganization**
   - Identify “loose files” and propose a target structure.
   - Move/rename as needed with minimal disruption.
   - Update references: imports, README links, CI paths, script entrypoints.
7. **Verification & checklist**
   - Produce exact commands for `black`, `ruff`, `flake8`, `mypy`.
   - Confirm no pytest usage.
   - Summarize all files changed, deleted, or moved with rationale.

---

## 4. Lint / Type / Format Pipeline

### 4.1 Determine Tools and Config

1. Detect whether the repo uses:
   - `black` (config in `pyproject.toml`, `black.toml`, etc.).
   - `ruff` (config in `ruff.toml`, `pyproject.toml`, `ruff.ini`).
   - `flake8` (`setup.cfg`, `tox.ini`, `.flake8`, `pyproject.toml`).
   - `mypy` (`mypy.ini`, `setup.cfg`, `pyproject.toml`).
2. Respect tool-specific include/exclude patterns and line length from config.

### 4.2 Default Safe Pipeline Order

Unless the repository config explicitly indicates a different order, use this **default**:

1. `black .`
2. `ruff check . --fix`
3. `ruff format .` **only if**:
   - The repo is configured to use Ruff as the formatter, **or**
   - Black is not used.
   Otherwise, **skip** to avoid formatter conflicts.
4. `flake8 .`
5. `mypy .`

When building the plan, always:
- Show the **exact commands** you intend to run.
- Explain briefly **why** this order is used (formatter → autofix lint → style checks → type checks).

### 4.3 Fixing Remaining Issues

For remaining `flake8` or `mypy` issues:
- Prefer **localized fixes**:
  - Add missing imports, remove unused variables, simplify branches, adjust types.
- For typing:
  - Add type hints where straightforward.
  - Use `TypedDict`, `Protocol`, or generics where valuable.
  - As a last resort, and only with rationale, use `# type: ignore[...]` with a **justification comment**.
- Avoid large refactors unless necessary for correctness or safety.

---

## 5. Security Review Checklist

For security, explicitly scan for and report (with severity: Critical/High/Medium/Low):

1. **Secrets and sensitive data**
   - Hard-coded API keys, tokens, passwords, private keys.
   - Secrets in config files, examples, or tests.
   - Logging of secrets or PII.
2. **Injection risks**
   - Shell injection: uses of `subprocess`, `os.system`, `Popen`, `shell=True`, or string-concatenated commands.
   - SQL injection: raw SQL concatenation, ORM `.raw()` without parameters.
   - Template injection in Jinja or other engines.
3. **Deserialization and file handling**
   - Insecure `pickle.load`, `yaml.load` (without `SafeLoader`), `eval`, `exec`.
   - Path traversal risks in file operations:
     - Joining untrusted input to filesystem paths.
     - Writing to or reading from dynamic paths without validation.
4. **Network & SSRF**
   - Unvalidated, user-controlled URLs passed to HTTP clients.
   - TLS verification disabled (e.g. `verify=False` in `requests`).
5. **Crypto & randomness**
   - Weak hashes (e.g. MD5/SHA1) for security-sensitive uses.
   - Use of `random` for tokens or secrets instead of `secrets` / `os.urandom`.
6. **Dependency red flags**
   - Suspicious or deprecated packages called in code or listed in requirements.

For every security finding:
- Classify severity.
- Include file + approximate location.
- Provide a concrete remediation suggestion.

---

## 6. Performance Review Checklist

Check for performance risks, especially in hot paths (validators, tight loops, I/O-heavy functions):

1. **Algorithmic complexity**
   - Obvious \(O(n^2)\) or worse loops over potentially large collections.
   - Nested loops with repeated expensive calls (I/O, DB, network).
2. **I/O patterns**
   - Repeated disk reads/writes inside loops.
   - Repeated parsing/JSON/regex compilation in hot paths (compile regex once).
3. **Data structures & memory**
   - Unnecessary copying of large lists/dicts.
   - Using lists where sets/dicts would be more efficient for membership checks.
4. **Concurrency/async misuse**
   - Blocking I/O inside async functions.
   - Shared mutable state across threads without synchronization.

For each performance issue:
- Note severity (often Medium/Low unless in clearly hot code).
- Provide a specific, low-risk optimization suggestion.

---

## 7. Documentation Review

### 7.1 Identify Documentation

Treat as “docs”:
- `README*`, `CONTRIBUTING*`, `CHANGELOG*`, `docs/**`, `design/**`, `ARCHITECTURE*`, `.md` files with user-facing content.

### 7.2 Outdatedness Criteria

Mark a doc as **outdated** if any of:
- It is **not referenced** from README, main docs index, or CI/pipelines **and**
  - It describes commands, APIs, or architectures that no longer exist, **or**
  - It duplicates another, more-current document.
- Migration notes for versions no longer relevant.

### 7.3 Classification and Actions

For each doc, decide:
- **KEEP** – still accurate and referenced.
- **UPDATE** – concept is valid but content is stale, misleading, or incomplete.
- **DELETE** – obsolete, unreferenced, or actively harmful/confusing.

When updating:
- Ensure code samples and CLI commands match current code and tooling (e.g. `black`, `ruff`, entrypoints).
- Update references to moved files or new paths.

Always produce a **table** in the final answer:
- Columns: `File`, `Decision (KEEP/UPDATE/DELETE)`, `Rationale`, `Edits (if any)`.

---

## 8. Scripts Review

### 8.1 Identify Scripts

Scripts include:
- Top-level Python or shell scripts (e.g. `manage.py`, `run.py`, `build.sh`).
- Files in `scripts/`, `tools/`, `bin/`, CI helper scripts.

### 8.2 Classification

For each script:
- **KEEP** – still used and correct.
- **UPDATE** – still needed but has outdated paths, options, or assumptions.
- **DELETE** – no longer used, superseded, or dangerous.

Validation:
- Check entrypoints, arguments, environment variables, expected working directories.
- Cross-check with CI configs, README, and other scripts to see if they’re referenced.

Prefer moving scripts into a dedicated folder (e.g. `scripts/` or `tools/`) and:
- Add or update a small `scripts/README.md` describing purpose and usage.

Include a table in the final answer:
- Columns: `Script`, `Decision`, `Rationale`, `Edits/Moves`.

---

## 9. Repository Reorganization

### 9.1 Target Structure (Default)

When helpful, propose moving towards a structure like:

- `src/` – main Python packages and code (if the project uses `src` layout).
- `package_name/` – main package if not using `src`.
- `tests/` – test suite (do **not** add or run tests; only move if clearly safe).
- `docs/` – documentation.
- `scripts/` or `tools/` – helper scripts and utilities.
- `config/` – config files that don’t need to be at repo root.
- `.github/`, `.gitlab/` – CI and workflow configuration.

### 9.2 Loose Files

Identify “loose files”:
- Python modules, scripts, and docs at repo root that do not match the desired layout.

For each move/rename:
- Update:
  - Import paths in Python code.
  - References in README and docs.
  - Paths in CI configs, tooling configs, and scripts.
- Record changes in the **change log**:
  - From → To, and rationale.

Avoid breaking behavior:
- If moving importable modules, ensure new package structure still resolves correctly.
- When unsure, prefer **documenting** a recommended move instead of performing a risky change.

---

## 10. Required Output Format

When using this skill to complete a repository audit, always structure the final answer exactly as:

```markdown
# 1) Assumptions (if any)

# 2) Plan & Commands (step-by-step)

# 3) Findings (Security / Performance / Structure)

# 4) Fixes Applied (by category)

# 5) Docs Review (KEEP/UPDATE/DELETE table + edits)

# 6) Scripts Review (KEEP/UPDATE/DELETE table + edits)

# 7) Repo Reorganization (move map + rationale)

# 8) Verification Checklist (exact commands)
```

Within these sections, ensure:
- The **Plan & Commands** includes the full `black`, `ruff`, `flake8`, and `mypy` commands in order, with brief rationale.
- The **Findings** section includes a prioritized issue list with:
  - Severity (Critical/High/Medium/Low).
  - Category (Security / Correctness / Maintainability / Performance).
- The **Change log** (parts of sections 4, 5, 6, 7) lists:
  - Every file changed (with why).
  - Every file deleted (with why).
  - Every file moved/renamed (from → to, with why).
- The **Verification Checklist** includes the exact commands to re-run, and explicitly confirms:
  - You did **not** run pytest.
  - How to run `black`, `ruff`, `flake8`, `mypy`.

---

## 11. Self-Check Before Finishing

Before finalizing any audit using this skill, verify:

1. You **did not** run pytest.
2. You showed complete commands for:
   - `black`
   - `ruff` (including `--fix` and `ruff format` only if appropriate)
   - `flake8`
   - `mypy`
3. You listed every file changed, deleted, or moved with rationale.
4. You explicitly addressed:
   - Security (per checklist).
   - Performance (per checklist).
   - Repository structure and hygiene.
5. Your output matches the required markdown structure in Section 10 exactly.

