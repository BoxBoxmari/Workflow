# Documentation Sync — Reference

Full checklist for documentation analysis, updates, formatting, and validation. Use when running a full sync or validating structure.

---

## 1. Documentation Analysis Checklist

**Current status review**
- [ ] Check `specs/implementation_status.md` for overall project status
- [ ] Review implemented phase document (`specs/phase{N}_implementation_plan.md`)
- [ ] Review `specs/flutter_structurizr_implementation_spec.md` and updated version
- [ ] Review `specs/testing_plan.md` for currency given recent test results
- [ ] Examine CLAUDE.md and README.md for project-wide context
- [ ] Check for new lessons learned or best practices to document

**Implementation and testing analysis**
- [ ] Review what was implemented in the last phase
- [ ] Review testing results and coverage
- [ ] Identify new best practices discovered during implementation
- [ ] Note implementation challenges and solutions
- [ ] Cross-reference docs with implementation/test results for accuracy

---

## 2. Documentation Updates Checklist

**Phase implementation document**
- [ ] Mark completed tasks with ✅ status
- [ ] Update implementation percentages
- [ ] Add detailed notes on implementation approach
- [ ] Document deviations from original plan with justification
- [ ] Add new sections if needed (lessons learned, best practices)
- [ ] Document specific implementation details for complex components
- [ ] Include troubleshooting tips or workflow improvements

**Implementation status document**
- [ ] Update phase completion percentages
- [ ] Add or update component implementation status
- [ ] Add notes on implementation approach and decisions
- [ ] Document best practices discovered
- [ ] Note challenges overcome and solutions implemented

**Implementation specification documents**
- [ ] Mark completed items with ✅ or strikethrough (preserve originals)
- [ ] Add notes on implementation details where appropriate
- [ ] Add references to implemented files and classes
- [ ] Update implementation guidance based on experience

**CLAUDE.md and README.md**
- [ ] Add new best practices
- [ ] Update project status
- [ ] Add new implementation guidance
- [ ] Document known issues or limitations
- [ ] Update usage examples to include new functionality

**Testing documentation**
- [ ] Add details on test files created
- [ ] Include test running instructions
- [ ] Document test coverage
- [ ] Explain testing approach for complex components

---

## 3. Formatting and Structure Checklist

- [ ] Use clear headings and sections
- [ ] Include code examples where helpful
- [ ] Use status indicators consistently (✅, ⚠️, ❌)
- [ ] Maintain proper Markdown formatting
- [ ] Cover all implemented features
- [ ] Include usage examples
- [ ] Document API changes or additions
- [ ] Include troubleshooting guidance for common issues

---

## 4. Validation Checklist

- [ ] Documentation matches actual implementation
- [ ] All status indicators are accurate
- [ ] Completion percentages are updated
- [ ] Cross-references are valid
- [ ] No broken links or missing files referenced
- [ ] Code examples are current and runnable

---

## 5. Output Summary Template

```markdown
## Documentation Update Summary

**Files Updated:**
- [list of files]

**Major Changes:**
- [key changes]

**Updated Completion Percentages:**
- Phase X: [old]% → [new]%
- Overall: [old]% → [new]%

**New Best Practices Documented:**
- [practice 1]
- [practice 2]

**Overall Project Status:**
- [current status summary]
```

---

## 6. Important Constraints

- **DO NOT CREATE** new specification files; only update existing files in `specs/`.
- Always preserve original requirements when marking items complete (use ✅ or strikethrough, don't delete).
- Cross-reference related documentation sections.
- Ensure documentation reflects actual implementation state.
