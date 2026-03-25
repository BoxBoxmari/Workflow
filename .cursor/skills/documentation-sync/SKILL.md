---
name: documentation-sync
description: Updates and synchronizes project documentation with implementation status, API changes, and synchronized content. Use when updating docs after implementation, syncing specs with code, validating documentation accuracy, or when the user requests documentation updates.
---

# Documentation Update & Synchronization

Update project documentation systematically: sync implementation status, API changes, and content across docs, specs, and project files.

## When to Use

- After implementing features or completing a phase
- When syncing documentation with code changes
- Validating documentation accuracy against implementation
- Updating API docs, architecture docs, or project status
- User requests documentation updates or synchronization

## Input

- **doc-type**: Focus on a specific type (implementation, api, architecture, etc.).
- **--implementation**: Update implementation status and phase docs.
- **--api**: Update API documentation.
- **--architecture**: Update architecture and design docs.
- **--sync**: Synchronize all docs with current code state.
- **--validate**: Check documentation accuracy and completeness.

If no argument, sync all documentation based on current state.

## Current State (Check First)

- **Documentation structure**: List markdown files (e.g. `find . -name "*.md"`); identify specs/, docs/, README, CLAUDE.md.
- **Status indicators**: Count status markers (✅, ⚠️, ❌) in docs/specs.
- **Recent changes**: Recent commits affecting markdown files.
- **Project progress**: Review CLAUDE.md and README.md for current status.

## Documentation Analysis

1. **Review current status**: Check `specs/implementation_status.md` for overall status; review phase implementation plans (`specs/phase{N}_implementation_plan.md`); review implementation specs; review `specs/testing_plan.md`; examine CLAUDE.md and README.md.
2. **Analyze implementation**: Review what was implemented; review test results and coverage; identify new best practices; note challenges and solutions; cross-reference docs with implementation/test results.

## Documentation Updates

1. **Phase implementation docs**: Mark completed tasks (✅); update percentages; add implementation notes; document deviations with justification; add lessons learned/best practices; document complex components; add troubleshooting tips.
2. **Implementation status**: Update phase completion percentages; update component status; add implementation notes and decisions; document best practices; note challenges and solutions.
3. **Implementation specs**: Mark completed items (✅ or strikethrough, preserve originals); add implementation details; add file/class references; update guidance based on experience.
4. **CLAUDE.md / README.md**: Add best practices; update project status; add implementation guidance; document known issues/limitations; update usage examples.
5. **Testing docs**: Add test file details; include test running instructions; document coverage; explain testing approach for complex components.

## Formatting and Structure

- **Consistent style**: Clear headings, code examples where helpful, consistent status indicators (✅, ⚠️, ❌), proper Markdown.
- **Completeness**: Cover implemented features, include usage examples, document API changes, include troubleshooting.

## Guidelines

- **DO NOT CREATE** new specification files; only update existing files in `specs/`.
- **Maintain consistency**: Style, formatting, status indicators.
- **Cross-reference**: Link related sections.
- **Document practices**: Best practices and lessons learned.
- **Update progress**: Status updates and completion percentages.
- **Reflect reality**: Documentation must match actual implementation.

## Output Summary

After completion, provide:
1. Files updated
2. Major changes
3. Updated completion percentages
4. New best practices documented
5. Overall project status after updates

## Reference

- **reference.md**: Full checklist for analysis, updates, formatting, and validation. Read when running a full sync or validating structure.
