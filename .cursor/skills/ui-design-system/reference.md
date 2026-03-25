# UI Design System — Reference

Extended token structure, spacing grid, breakpoints, and handoff template. Use when defining tokens manually or documenting the system.

---

## 1. Design Token Structure

**Colors**
- Semantic: `primary`, `secondary`, `surface`, `background`, `text`, `textMuted`, `border`, `error`, `warning`, `success`, `info`.
- Scale per semantic (e.g. 50–950 or 100–900) for hover/active/disabled.
- Document hex/rgb and usage (fill, stroke, background, text).

**Typography**
- Scale: e.g. `xs` (12px) through `display` (48–72px); use rem with 16px base.
- Font families: `sans`, `serif`, `mono`; map to actual font stacks.
- Weights: 400 (normal), 500 (medium), 600 (semibold), 700 (bold).
- Line-height and letter-spacing per size; document for devs.

**Spacing (8pt grid)**
- 4, 8, 12, 16, 24, 32, 48, 64, 96, 128 (px or rem).
- Map to names: `space-1` … `space-10` or `xs`/`sm`/`md`/`lg`/`xl`.

**Shadows**
- Levels: subtle, default, raised, overlay; document blur, spread, opacity.

**Animation**
- Duration: e.g. 150ms (micro), 300ms (default), 500ms (macro).
- Easing: linear, ease-in, ease-out, ease-in-out; prefer named curves (e.g. `ease-default`).

---

## 2. Responsive Breakpoints (Example)

| Name | Min width | Typical use   |
|------|-----------|---------------|
| xs   | 0         | default/mobile |
| sm   | 640px     | large phone   |
| md   | 768px     | tablet        |
| lg   | 1024px    | desktop       |
| xl   | 1280px    | wide          |
| 2xl  | 1536px    | max-width     |

Document in tokens and use consistently in layout and component specs.

---

## 3. Component Doc Template

```markdown
## [ComponentName]

**Purpose**: One-line description.

**Variants**: size (sm/md/lg), style (primary/ghost), state (default/hover/active/disabled).

**Tokens**: color, typography, spacing, shadow (list token names).

**Props/API**: prop name, type, default, description.

**Responsive**: How it changes at sm/md/lg (layout, visibility, density).

**Accessibility**: focus, aria, keyboard, contrast note.

**Usage**: Short code or snippet.
```

---

## 4. Developer Handoff Checklist

- [ ] Token file (JSON/CSS/SCSS) with semantic names and values
- [ ] Typography scale and font stack
- [ ] Spacing scale and 8pt grid note
- [ ] Breakpoints and layout rules
- [ ] Component list with variants and props
- [ ] Accessibility requirements (contrast, focus, semantics)
- [ ] Usage examples or Storybook link
- [ ] Changelog or version note for the design system

---

## 5. Script: design_token_generator.py

When present under `scripts/`:

```bash
python scripts/design_token_generator.py [brand_color] [style] [format]
```

- **Styles**: `modern` (clean, high contrast), `classic` (traditional, balanced), `playful` (vibrant, rounded).
- **Formats**: `json` (for JS/CSS-in-JS), `css` (custom properties), `scss` (variables/mixins).
- Use output path in handoff and reference it in component docs.
