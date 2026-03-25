---
name: ui-design-system
description: UI design system toolkit for Senior UI Designer including design token generation, component documentation, responsive design calculations, and developer handoff tools. Use for creating design systems, maintaining visual consistency, and facilitating design-dev collaboration.
---

# UI Design System

Toolkit for creating and maintaining scalable design systems: tokens, components, responsive rules, accessibility, and handoff docs.

## When to Use

- Creating or evolving a design system
- Defining or documenting design tokens (colors, typography, spacing)
- Designing component architecture or documentation
- Calculating responsive breakpoints and layout
- Ensuring accessibility and preparing developer handoff

## Core Capabilities

- **Design tokens**: Colors, typography, spacing, shadows, animation; export to JSON/CSS/SCSS.
- **Component system**: Structure, variants, and documentation patterns.
- **Responsive design**: Breakpoints and layout calculations.
- **Accessibility**: Contrast, focus, semantics; WCAG-oriented checks.
- **Developer handoff**: Specs, tokens, and usage notes for implementation.

## Design Token Generator

When the project provides `scripts/design_token_generator.py`, use it to generate tokens from a brand color.

**Run**:
```bash
python scripts/design_token_generator.py [brand_color] [style] [format]
```

- **brand_color**: Hex (e.g. `#3B82F6`) or name; optional if script has defaults.
- **style**: `modern` | `classic` | `playful` — affects palette and typography feel.
- **format**: `json` | `css` | `scss` — output format.

**Output typically includes**: color palette, typography scale, 8pt spacing grid, shadows, animation tokens, responsive breakpoints. Use the generated file path in handoff docs and component specs.

If the script is missing, define tokens manually (see [reference.md](reference.md)) and suggest adding the script for consistency.

## Token Conventions (When Defining Manually)

- **Colors**: Semantic names (e.g. `primary`, `surface`, `text`, `border`) plus scale (50–950 or 1–5); document hex and usage.
- **Typography**: Scale (e.g. 12–72px or 0.75–4.5rem); font families and weights; line-height and letter-spacing per size.
- **Spacing**: Prefer 8pt grid (4, 8, 12, 16, 24, 32, 48, 64); map to CSS variables or SCSS.
- **Breakpoints**: Document min-widths and use in layout/component rules (e.g. sm/md/lg/xl).

## Component Documentation

For each component: name, purpose, variants (e.g. size, state), props/API, tokens used, responsive behavior, accessibility notes, and code/usage snippet. Keep a single source of truth (e.g. Storybook + markdown or reference.md).

## Accessibility

- Contrast: text/background meets WCAG AA (4.5:1 body, 3:1 large).
- Focus: visible focus states; logical tab order.
- Semantics: headings, landmarks, labels; no structure by visual style only.
- Document a11y requirements in handoff and component docs.

## Developer Handoff

Deliver: token file (JSON/CSS/SCSS), component list with props and variants, responsive rules, a11y checklist, and usage examples. Prefer linked docs (e.g. reference.md) over long inline text.

## Reference

- **reference.md**: Token structure details, spacing grid, breakpoint patterns, and handoff template. Read when defining tokens manually or documenting the system.
