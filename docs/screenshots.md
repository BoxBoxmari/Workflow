# UI Screenshot Guidance

To ensure consistent and high-quality visual documentation for the Workflow MVP, please follow these guidelines when capturing screenshots.

## Recommended Screenshots

Capture the following views to demonstrate the full range of the Modern UI:

1. **Main Workspace (Design View)**:
    - Show the Flow Canvas with a multi-step workflow.
    - Sidebar cards should be visible.
    - Use **Dark Mode** for the primary hero screenshot.
2. **Results View**:
    - Trigger a workflow run.
    - Show the Result Drawer open to the **Output** or **Metrics** tab.
    - Ensure the **Progress Bar** (active) is visible in the top bar.
3. **Appearance Toggle**:
    - A side-by-side or sequential comparison of the **Dark** vs. **Light** mode for the main shell.
4. **Inspector & Validation**:
    - Show the Inspector panel with a validation warning (e.g., "Invalid model catalog ID").
    - Prefer a step that includes source selection so the combo format `Title (step_id)` is visible.
    - If the source is workflow root input, ensure it is rendered as **Workflow input**.
5. **Sidebar Interactions**:
    - Show selection highlighting on workflow cards and recent run cards.

## Technical Specifications

- **Dimensions**: Default window size **1400x900**.
- **Aspect Ratio**: 16:10 preferred.
- **Format**: PNG (lossless) or WebP.
- **Redaction**:
  - ⚠️ **CRITICAL**: Before capturing, ensure no real API keys or sensitive project names are visible in the workspace.
  - Redact any private file paths showing standard user directories (e.g., `/Users/Admin/...`).
- **Framing**: Capture the full application window (including title bar if desired for context) or just the client area.

## Capture Process

1. Start the app: `python main.py`.
2. Load the `example_workflow` from `config/workflows.json`.
3. Resize to standard 1400x900.
4. Switch between tabs and modes to capture the specific features.
