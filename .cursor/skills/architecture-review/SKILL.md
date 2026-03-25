---
name: architecture-review
description: Comprehensive architecture review with design patterns analysis and improvement recommendations. Use when reviewing system architecture, analyzing design patterns, evaluating dependencies, assessing scalability, or planning architectural improvements.
---

# Architecture Review

Perform comprehensive system architecture analysis and improvement planning.

## When to Use

- User requests architecture review, design pattern analysis, or system structure assessment
- Evaluating architectural decisions before major refactoring
- Assessing scalability, maintainability, or technical debt
- Planning architectural improvements or migrations
- Reviewing module boundaries, dependencies, or data flow

## Scope Arguments

Use arguments to focus the review:

- `[scope]` - Specific module, component, or directory path to review
- `--modules` - Focus on module boundaries and organization
- `--patterns` - Analyze design patterns and anti-patterns
- `--dependencies` - Deep dependency analysis and coupling assessment
- `--security` - Security architecture and trust boundaries review

If no argument provided, perform full architecture review.

## Current Architecture Context

Before starting, gather context:

```bash
# Project structure
find . -name "*.js" -o -name "*.ts" -o -name "*.py" -o -name "*.go" | head -20

# Package dependencies
[ -f package.json ] && cat package.json | grep -A 50 '"dependencies"' || \
[ -f requirements.txt ] && head -20 requirements.txt || \
[ -f go.mod ] && head -20 go.mod

# Testing framework
find . -name "*.test.*" -o -name "*spec.*" | head -5

# Documentation
find . -name "README*" -o -name "ARCHITECTURE*" -o -name "DESIGN*" | head -10
```

## Review Framework

### 1. System Structure Assessment

- **Component Hierarchy**: Map major components and their relationships
- **Architectural Patterns**: Identify patterns (MVC, microservices, layered, etc.)
- **Module Boundaries**: Assess module organization and separation of concerns
- **Layered Design**: Evaluate layer separation (presentation, business, data)

**Analysis Steps**:
1. Identify entry points (main files, API routes, CLI commands)
2. Map component dependencies and call graphs
3. Assess module cohesion and coupling
4. Document architectural patterns in use

### 2. Design Pattern Evaluation

- **Implemented Patterns**: Identify existing patterns (Factory, Strategy, Observer, etc.)
- **Pattern Consistency**: Check if patterns are applied consistently
- **Anti-Patterns**: Detect god objects, spaghetti code, circular dependencies
- **Pattern Effectiveness**: Evaluate if patterns solve intended problems

**Common Patterns to Check**:
- Creational: Factory, Builder, Singleton
- Structural: Adapter, Decorator, Facade
- Behavioral: Strategy, Observer, Command
- Architectural: MVC, Repository, Service Layer

### 3. Dependency Architecture

- **Coupling Levels**: Measure coupling between modules/components
- **Circular Dependencies**: Detect and document circular references
- **Dependency Injection**: Evaluate DI usage and container setup
- **Architectural Boundaries**: Assess if boundaries are respected

**Analysis Commands**:
```bash
# Find circular dependencies (example for Node.js)
npx madge --circular src/

# Dependency graph
npx depcheck --json

# Import analysis
grep -r "import\|require" --include="*.js" --include="*.ts" src/ | head -50
```

### 4. Data Flow Analysis

- **Information Flow**: Trace data from input to output
- **State Management**: Evaluate state handling (global, local, shared)
- **Data Persistence**: Assess storage strategies and data access patterns
- **Transformation Patterns**: Review data transformation and validation

**Key Questions**:
- How does data flow through the system?
- Where is state stored and managed?
- Are data transformations clear and testable?
- Is there proper separation between read and write operations?

### 5. Scalability & Performance

- **Scaling Capabilities**: Assess horizontal vs vertical scaling readiness
- **Caching Strategies**: Evaluate caching layers and invalidation
- **Bottlenecks**: Identify potential performance bottlenecks
- **Resource Management**: Review connection pooling, memory management

**Assessment Areas**:
- Database query patterns and indexing
- API rate limiting and throttling
- Caching layers (application, database, CDN)
- Async processing and queue management
- Resource pooling and connection management

### 6. Security Architecture

- **Trust Boundaries**: Map security boundaries and trust zones
- **Authentication Patterns**: Review auth mechanisms and token handling
- **Authorization Flows**: Assess access control and permission checks
- **Data Protection**: Evaluate encryption, sanitization, and validation

**Security Checklist**:
- Input validation at boundaries
- Authentication and session management
- Authorization and access control
- Data encryption (at rest and in transit)
- Secrets management
- Error handling without information leakage

## Advanced Analysis

### Component Testability
- Are components easily testable in isolation?
- Are dependencies mockable?
- Is there proper separation of concerns?

### Configuration Management
- How is configuration handled?
- Are environment-specific configs properly separated?
- Is sensitive configuration secured?

### Error Handling Patterns
- Consistent error handling approach?
- Proper error propagation and logging?
- User-friendly error messages?

### Monitoring Integration
- Are there proper logging and monitoring hooks?
- Is observability built into the architecture?
- Can issues be traced across components?

### Extensibility Assessment
- How easy is it to add new features?
- Are extension points well-defined?
- Is the architecture open for extension but closed for modification?

## Quality Assessment

### Code Organization
- Clear directory structure
- Consistent naming conventions
- Logical grouping of related code

### Documentation Adequacy
- Architecture documentation exists and is current
- API documentation is complete
- Code comments explain "why" not "what"

### Team Communication Patterns
- Clear ownership boundaries
- Well-defined interfaces between teams
- Effective communication mechanisms

### Technical Debt Evaluation
- Identify areas of high technical debt
- Assess impact on velocity and quality
- Prioritize debt reduction efforts

## Output Format

Structure findings as:

```markdown
# Architecture Review Report

## Executive Summary
[2-3 sentence overview of architecture health and key findings]

## System Structure
- **Architecture Pattern**: [identified pattern]
- **Component Hierarchy**: [major components]
- **Module Organization**: [assessment]

## Design Patterns
- **Implemented Patterns**: [list]
- **Anti-Patterns Found**: [list with locations]
- **Recommendations**: [specific improvements]

## Dependency Analysis
- **Coupling Assessment**: [high/medium/low coupling areas]
- **Circular Dependencies**: [if any]
- **Boundary Violations**: [if any]

## Data Flow
- **Information Flow**: [description]
- **State Management**: [approach and assessment]
- **Data Persistence**: [strategies]

## Scalability Assessment
- **Current Capabilities**: [assessment]
- **Bottlenecks**: [identified issues]
- **Scaling Recommendations**: [specific actions]

## Security Architecture
- **Trust Boundaries**: [mapped boundaries]
- **Security Posture**: [overall assessment]
- **Vulnerabilities**: [if any]

## Recommendations
### High Priority
1. [Specific recommendation with rationale]
2. [Specific recommendation with rationale]

### Medium Priority
1. [Specific recommendation]
2. [Specific recommendation]

### Implementation Roadmap
- **Phase 1** (Immediate): [quick wins]
- **Phase 2** (Short-term): [important improvements]
- **Phase 3** (Long-term): [architectural evolution]
```

## Best Practices

- **Be Specific**: Reference actual files, functions, and line numbers
- **Prioritize**: Focus on high-impact improvements first
- **Be Actionable**: Provide concrete steps, not just observations
- **Consider Trade-offs**: Acknowledge when architectural decisions involve trade-offs
- **Reference Standards**: Cite relevant architectural principles (SOLID, DDD, etc.)

## Tools and Commands

Use these tools for analysis:

```bash
# Dependency analysis
npx madge --image deps.svg src/
npx depcheck

# Code complexity
npx complexity-report src/

# Architecture visualization
npx dependency-cruiser --output-type dot src/ | dot -T svg > arch.svg

# Find large files (potential god objects)
find src/ -type f -exec wc -l {} + | sort -rn | head -20
```
