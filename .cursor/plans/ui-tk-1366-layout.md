# Plan: UI Tkinter 1366×768 layout fix

## WBS

1. Intake & framing — 1366×768 RUN button disappeared, Individual file list cut off.
2. Root cause — Left column had five grid rows with no scroll; total height > 768px.
3. Design decision — Scrollable content + single sticky Run/Cancel bar.
4. Implementation — `_init_left_panel`: row 0 = Canvas + Scrollbar + content_frame; row 1 = ctrl_frame (RUN, Cancel). `_init_left_panel_content(content)` holds Paths, Options, Tax, Command Preview only.
5. Verification — Tests pass, lint clean, manual check at 1366×768.

## Integrated decisions

- Left panel: two grid rows — scroll area (row 0), sticky bar (row 1).
- Run/Cancel live only in `ctrl_frame`; no duplicate in content.
- Design tokens: `quality_audit/ui/styles.py` (COLORS, FONTS, SPACING, PADDING_SECTION); `reference.md`, `BRAND_KPMG.md` for handoff and min resolution 1366×768.

## Action plan (done)

- [x] styles.py: typography, 8pt grid, semantic colors.
- [x] tk_cli_gui.py: scrollable left content, sticky Run/Cancel.
- [x] reference.md, BRAND_KPMG.md: min resolution, checklist.

## Verification checklist

- [x] `python -m pytest tests/test_audit_service_integration.py tests/test_batch_processing.py -q --tb=short` → 9 passed.
- [x] `python -m flake8 quality_audit/ui/tk_cli_gui.py quality_audit/ui/styles.py` → no errors.
- [ ] Manual: run GUI at 1366×768, confirm RUN visible and Individual list not cut off (optional).

## Risk / rollback

- If scroll feels wrong: revert `_init_left_panel` to single column without canvas; restore Run/Cancel inside content (old layout).
- No API/schema changes; GUI-only.

## Open questions

- None. Optional: add pytest-based GUI smoke test or 1366×768 screenshot to CI.
