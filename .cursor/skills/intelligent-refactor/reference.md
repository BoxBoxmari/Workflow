# Intelligent Refactor — Reference

Full 17-step checklist with detailed instructions. Use when executing a full refactoring or validating the process.

---

## 1. Pre-Refactoring Analysis

- [ ] Identify code to refactor and reasons (readability, performance, maintainability, bugs)
- [ ] Understand current functionality and behavior completely
- [ ] Review existing tests and documentation
- [ ] Identify all dependencies and usage points (grep, call graph, or IDE tools)

---

## 2. Test Coverage Verification

- [ ] Ensure comprehensive test coverage exists for code being refactored
- [ ] If tests missing, write them BEFORE starting refactoring
- [ ] Run all tests to establish baseline (all passing)
- [ ] Document current behavior with additional tests if needed

---

## 3. Refactoring Strategy

- [ ] Define clear goals (performance, readability, maintainability, specific issues)
- [ ] Choose techniques:
  - Extract Method/Function
  - Extract Class/Component
  - Rename Variable/Method
  - Move Method/Field
  - Replace Conditional with Polymorphism
  - Eliminate Dead Code
- [ ] Plan in small, incremental steps (one technique at a time)

---

## 4. Environment Setup

- [ ] Create branch: `git checkout -b refactor/<name>` (use argument or descriptive name)
- [ ] Ensure all tests pass before starting
- [ ] Set up tooling if needed (profilers, analyzers, linters)

---

## 5. Incremental Refactoring

- [ ] Make small, focused changes one at a time
- [ ] Run tests after each change to ensure nothing breaks
- [ ] Commit working changes frequently with descriptive messages
- [ ] Use IDE refactoring tools when available for safety

---

## 6. Code Quality Improvements

- [ ] Improve naming conventions for clarity
- [ ] Eliminate duplication (DRY principle)
- [ ] Simplify complex conditional logic
- [ ] Reduce method/function length and complexity
- [ ] Improve separation of concerns

---

## 7. Performance Optimizations

- [ ] Identify and eliminate bottlenecks
- [ ] Optimize algorithms and data structures
- [ ] Reduce unnecessary computations
- [ ] Improve memory usage patterns

---

## 8. Design Pattern Application

- [ ] Apply appropriate design patterns where beneficial
- [ ] Improve abstraction and encapsulation
- [ ] Enhance modularity and reusability
- [ ] Reduce coupling between components

---

## 9. Error Handling Improvement

- [ ] Standardize error handling approaches
- [ ] Improve error messages and logging
- [ ] Add proper exception handling
- [ ] Enhance resilience and fault tolerance

---

## 10. Documentation Updates

- [ ] Update code comments to reflect changes
- [ ] Revise API documentation if interfaces changed
- [ ] Update inline documentation and examples
- [ ] Ensure comments are accurate and helpful

---

## 11. Testing Enhancements

- [ ] Add tests for any new code paths created
- [ ] Improve existing test quality and coverage
- [ ] Remove or update obsolete tests
- [ ] Ensure tests are meaningful and effective

---

## 12. Static Analysis

- [ ] Run linting tools to catch style and potential issues
- [ ] Use static analysis tools to identify problems
- [ ] Check for security vulnerabilities
- [ ] Verify code complexity metrics

---

## 13. Performance Verification

- [ ] Run performance benchmarks if applicable
- [ ] Compare before/after metrics
- [ ] Ensure refactoring didn't degrade performance
- [ ] Document any performance improvements

---

## 14. Integration Testing

- [ ] Run full test suite to ensure no regressions
- [ ] Test integration with dependent systems
- [ ] Verify all functionality works as expected
- [ ] Test edge cases and error scenarios

---

## 15. Code Review Preparation

- [ ] Review all changes for quality and consistency
- [ ] Ensure refactoring goals were achieved
- [ ] Prepare clear explanation of changes made
- [ ] Document benefits and rationale

---

## 16. Documentation of Changes

- [ ] Create summary of refactoring changes
- [ ] Document any breaking changes or new patterns
- [ ] Update project documentation if needed
- [ ] Explain benefits and reasoning for future reference

---

## 17. Deployment Considerations

- [ ] Plan deployment strategy for refactored code
- [ ] Consider feature flags for gradual rollout
- [ ] Prepare rollback procedures
- [ ] Set up monitoring for refactored components

---

## Reminders

- **Preserve external behavior**: Refactoring should not change what the code does, only how it's structured.
- **Test-first**: Always ensure tests exist and pass before refactoring.
- **Incremental**: Small steps, test frequently, commit working state.
- **Safety over speed**: Prioritize correctness and maintainability.
