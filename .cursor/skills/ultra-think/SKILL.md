---
name: ultra-think
description: Performs deep analysis and problem solving using multi-dimensional thinking (technical, business, user, system). Use when the user requests thorough analysis, architectural or strategic decisions, complex problem solving, or explicit "ultra-think" / "deep analysis".
---

# Deep Analysis and Problem Solving

Analyze problems and questions from multiple angles, generate several solution options with trade-offs, then provide structured recommendations and a clear rationale.

## When to Use

- User asks for "ultra-think", "deep analysis", or thorough reasoning
- Architectural or technology decisions (e.g. migrate vs improve, stack choice)
- Complex problem solving (scaling, cost, compatibility, design)
- Strategic or product decisions needing trade-off analysis
- When the problem has many stakeholders, constraints, or unknowns

## The Process

1. **Parse the problem**: Extract the core challenge from the user’s input; identify stakeholders, constraints, implicit requirements, and unknowns; question assumptions.
2. **Multi-dimensional analysis**: Analyze from **technical** (feasibility, scale, performance, security, debt), **business** (value, ROI, time-to-market, risk/reward), **user** (needs, UX, edge cases, journeys), and **system** (integration, dependencies, coupling, emergent behavior).
3. **Generate 3–5 solutions**: For each option: pros/cons, complexity, resources, risks, long-term impact; include conventional and creative or hybrid options.
4. **Deep dive**: For the most promising options: implementation outline, pitfalls and mitigations, phased/MVP approach, second- and third-order effects, failure modes and recovery.
5. **Cross-domain**: Draw parallels from other domains; apply patterns from other contexts; consider analogies and combinations.
6. **Challenge and refine**: Stress-test each option; play devil’s advocate; surface weaknesses, "what if" scenarios, and unintended consequences.
7. **Synthesize**: Combine insights; identify key decision factors and critical trade-offs; summarize novel insights.
8. **Structured output**: Present using the [output structure](#output-structure) below.
9. **Meta-analysis**: Note uncertainty, biases, limitations, and confidence levels; suggest further expertise or research if needed.

## Output Structure

Use this structure for the final response:

```markdown
## Problem Analysis
- Core challenge
- Key constraints
- Critical success factors

## Solution Options
### Option 1: [Name]
- Description | Pros/Cons | Implementation approach | Risk assessment

### Option 2: [Name]
[Same structure]

[Option 3, 4, 5 as needed]

## Recommendation
- Recommended approach and rationale
- Implementation roadmap
- Success metrics
- Risk mitigation plan

## Alternative Perspectives
- Contrarian view
- Future considerations
- Areas for further research
```

## Key Principles

- **First principles**: Break down to fundamental truths.
- **Systems thinking**: Consider interconnections and feedback loops.
- **Probabilistic thinking**: Work with uncertainties and ranges.
- **Inversion**: Consider what to avoid, not only what to do.
- **Second-order thinking**: Consider consequences of consequences.

## Output Expectations

- Substantial analysis (typically 2–4 pages of insights when appropriate).
- Multiple viable options with clear trade-offs.
- Clear reasoning and acknowledgment of uncertainty.
- Actionable recommendations and, where useful, novel perspectives.

## Reference

- **reference.md**: Full step-by-step checklist, extended output template, and usage examples. Read when applying the full process or validating structure.
