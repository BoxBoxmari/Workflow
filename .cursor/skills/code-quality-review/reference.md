# Code Quality Review — Reference

Full checklist and output template. Use when running a full review or checking structure.

---

## 1. Review Checklist

**Repository analysis**
- [ ] Repo structure and primary language/framework
- [ ] Config files (package.json, requirements.txt, Cargo.toml, etc.)
- [ ] README and main documentation

**Code quality**
- [ ] Code smells, anti-patterns, potential bugs
- [ ] Consistent style and naming
- [ ] Unused imports, variables, dead code
- [ ] Error handling and logging

**Security**
- [ ] SQL/command injection, XSS, other common vulnerabilities
- [ ] Hardcoded secrets, API keys, passwords
- [ ] Authentication and authorization
- [ ] Input validation and sanitization

**Performance**
- [ ] Bottlenecks (algorithms, I/O, DB)
- [ ] Inefficient queries or loops
- [ ] Memory usage and leaks
- [ ] Bundle size and optimization

**Architecture & design**
- [ ] Organization and separation of concerns
- [ ] Abstraction and modularity
- [ ] Dependencies and coupling
- [ ] Scalability and maintainability

**Testing**
- [ ] Coverage and quality
- [ ] Gaps and critical paths
- [ ] Test structure and organization
- [ ] Additional scenarios to add

**Documentation**
- [ ] Comments and inline docs
- [ ] API documentation
- [ ] README and setup
- [ ] Gaps and improvements

**Recommendations**
- [ ] Prioritize by severity (critical, high, medium, low)
- [ ] Actionable items with file:line where applicable
- [ ] Tools and practices to adopt
- [ ] Summary report and next steps

---

## 2. Output Template

```markdown
## Code Quality Review

**Scope**: [file-path | commit | full repo]

### Findings

#### Security
- **[Severity]** [Description] — `path/to/file.ext:NN`

#### Performance
- **[Severity]** [Description] — `path/to/file.ext:NN`

#### Architecture
- **[Severity]** [Description] — `path/to/file.ext:NN`

[Other areas as needed]

### Recommendations
1. [Action] — [rationale]
2. [Action] — [rationale]

### Summary
- **Critical**: [count] — [one-line summary]
- **High**: [count] — [one-line summary]
- **Next steps**: [prioritized list]
```

---

## 3. Tools and Arguments

- **Read**: Inspect files and configs.
- **Bash**: Run git commands, build, linters, tests as needed.
- **Grep / Glob**: Search codebase for patterns, secrets, or structure.

**Arguments**
- `[file-path]`: Focus review on that file or directory.
- `[commit-hash]`: Focus on changes in that commit or range.
- `--full`: Review entire repository (structure, config, main code paths).
