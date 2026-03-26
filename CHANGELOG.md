# Changelog

## [Unreleased] — 2026-03-26

### Added

- `docs/design/bulk-attach-flow.md` — Dedicated UX/architecture design for large-batch attachment uploads, separated from quick-attach hard limits.

### Changed

- `core/models.py` — Extended `IngestResult` with MIME/signature validation metadata:
  - `detected_mime`, `detected_signature`, `signature_ok`, `signature_type`
  - `validation_mode`, `validation_warnings`, `validation_errors`
  - Added `has_validation_issues` convenience property.
- `core/ingestion.py` — Added stronger file-validation pipeline:
  - Magic-byte signature detection
  - Extension/signature consistency checks
  - OOXML ZIP-structure validation for `.docx/.xlsx/.pptx`
  - Configurable validation mode behavior (`off|warn|strict`) with strict-mode rejection on signature validation errors.
- `docs_guideline/user-manual.md` — Updated attachment section with:
  - MIME/signature validation behavior and validation modes
  - Dedicated bulk-attach UX flow guidance.

### Tests

- `tests/test_ingestion.py` — Added signature-validation regression coverage:
  - spoofed extension detection
  - strict-mode rejection behavior
  - valid OOXML signature acceptance
  - metadata propagation and truncation checks.

### Fixed (Phase 3 Completion)

- `ui/detail_panel.py` — Integrated `sanitize_for_display()` to strip ANSI codes from LLM output before rendering in Tkinter widgets. Raw response tab intentionally left unsanitized.
- `ui/app.py` — Removed `LegacyApp` class (834 lines of dead code); `App` is now the sole entry point. File reduced from 938 to 100 lines.
- `tests/test_ui_smoke.py` — Removed tests referencing `LegacyApp` attributes; replaced with controller/shell/storage presence tests for new architecture.
- `core/config_validation.py` — Added validation for empty `model` and `prompt_version` fields to prevent the class of runtime crash seen with workflow `5c94028a`.
- `tests/test_config_validation.py` — Added `test_validate_workflow_empty_model` and `test_validate_workflow_empty_prompt_version` test cases (2 new tests).

### Security

- LLM output sanitization now **active** at the display boundary — ANSI escape sequences and control characters stripped before Tkinter rendering.

### Added

- `config/secure_credentials.py` — `SecureCredentialStore` class wrapping OS Credential Manager (Windows Vault) via `keyring`, with env-var fallback for CI/dev.
- `core/sanitization.py` — `sanitize_for_display()` and `sanitize_log_output()` functions; strips ANSI escape sequences and C0 control characters from LLM outputs before rendering in Tkinter.
- `core/storage.StorageWriteQueue` — background daemon thread that serialises all `index.csv` writes; eliminates race conditions caused by concurrent Event Bus callbacks.
- `core/storage.StorageManager.compact_index()` — deduplicates `index.csv` rows for periodic maintenance.
- `core/storage.StorageManager._append_to_index()` — O(1) CSV append for new runs (no full rewrite).
- `ui/config_watcher.py` — OS-native event-driven file watcher using `watchdog`; replaces CPU-polling loop.
- `requirements.txt` — standardises dependency installation (`requests`, `watchdog`, `keyring`).

### Changed

- `core/provider.WorkbenchClient.from_config()` — now resolves `subscription_key` and `charge_code` from `SecureCredentialStore` first; only falls back to plaintext `provider.json` values with a deprecation warning.
- `core/ingestion.ingest_file()` — uses `Path.resolve()` for consistent path normalisation.
- `core/io_utils.atomic_write_text()` — exponential backoff retry (0.5s → 1.0s → raise) on `PermissionError`; handles Windows file-lock from Excel/Notepad.
- `core/storage.StorageManager.__init__()` — added `threading.Lock()` mutex and `StorageWriteQueue`.
- `core/storage.StorageManager._write_index_rows()` — atomic write via temp-file + `os.replace()` with Windows retry.
- `core/storage.StorageManager._update_index_impl()` — append-first strategy: O(1) for new runs, full rewrite only on updates.
- `ui/workspace_controller.WorkspaceController.start()` — uses `start_config_watcher()` instead of polling thread.
- `ui/workspace_controller.WorkspaceController.stop()` — uses `stop_config_watcher()` for clean observer shutdown.
- `ui/app.App._build_input_preview()` — refactored into orchestrator + `_build_attachment_context()` + `_build_manual_input_context()` helpers; each under 35 lines.
- `README.md` — updated with secure credential setup, `requirements.txt` install flow, and architecture decision table.

### Fixed

- `config/workflows.json` — removed corrupted draft workflow `5c94028a` (empty `model` and `prompt_version` fields caused runtime crash on load).
- `core/ingestion.py` — removed unused `io`, `os`, `Optional` imports flagged by Ruff linter.

### Security

- API keys removed from direct config-file dependency. `provider.json` can now contain only non-secret connection parameters.
- LLM output sanitised before UI display; raw results preserved in storage for debugging.

---

## [Pre-audit baseline] — 2026-03-18

Initial MVP implementation. See conversation audit report for full issue log.
