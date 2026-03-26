# Bulk Attach Flow Design

## Overview

A dedicated flow for large batch file uploads, separate from the existing quick-attach mechanism. This addresses the UX need for uploading many files (20-100+) without hitting the quick-attach hard limits (`_MAX_FILES_PER_ATTACH_ACTION=5`, `_MAX_ATTACHMENT_SLOTS_PER_STEP=12`).

## Goals

- Allow users to upload 20-100+ files in one operation
- Provide a clear, non-blocking UX for batch processing
- Maintain the existing quick-attach behavior (unchanged)
- Support validation, deduplication, and progress reporting
- Enable "apply to step" workflow with preview and confirmation

## Non-Goals

- Replace quick-attach (quick-attach remains for 1-5 files)
- Automatic slot creation beyond reasonable limits
- Background/async upload (initial version is synchronous)

## User Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  User clicks    │────▶│  Bulk Attach     │────▶│  File Selection │
│ "Bulk attach..."│     │  Modal Opens     │     │  (multi-select) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  User reviews   │◀────│  Validation &    │◀────│  Files analyzed │
│  and confirms   │     │  Deduplication   │     │  (MIME/sig)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│  Apply to Step  │────▶│  Slots created   │
│  (with mapping) │     │  (respects max)  │
└─────────────────┘     └──────────────────┘
```

## UI Components

### Entry Points

1. **Flow Canvas**: "+" button on step card → "Bulk attach..." option
2. **Inspector Panel**: Attachment section → "Bulk attach files..." link
3. **Context Menu**: Right-click step → "Bulk attach files..."

### Bulk Attach Modal

**Title**: "Bulk Attach Files to {step_title}"

**Sections**:

1. **File Selection Area**
   - Drop zone or "Select files..." button
   - Shows: "Selected: 42 files (15 MB total)"
   - Validation preview: "✓ 40 files ready, ⚠ 2 warnings, ✗ 0 errors"

2. **Validation Results Table**
   - Columns: Filename | Type | Size | Status | Action
   - Status icons: ✓ (ready), ⚠ (warning), ✗ (error)
   - Actions: "View warning", "Remove", "Keep anyway"

3. **Deduplication Notice**
   - "3 files already attached to this step (shown as duplicates)"
   - Options: "Skip duplicates", "Rename and keep", "Replace existing"

4. **Mapping Options**
   - "Map to:" Dropdown: [One slot per file | Single combined slot | Custom...]
   - "Variable naming:" [Use filename | Use index | Custom prefix]

5. **Action Bar**
   - Primary: "Apply to Step" (disabled if >12 slots would be created)
   - Secondary: "Cancel", "Save as Draft" (for later)

## ViewModels

### `BulkAttachItemVM`

Represents a single file in the bulk attach session.

```python
@dataclass
class BulkAttachItemVM:
    # Source
    source_path: Path
    original_filename: str
    
    # Validation
    ingest_result: Optional[IngestResult]  # Populated after analysis
    status: Literal["pending", "analyzing", "ready", "warning", "error", "duplicate"]
    
    # Metadata
    detected_mime: Optional[str]
    detected_signature: Optional[str]
    size_bytes: int
    
    # User decisions
    selected: bool = True  # User can uncheck to exclude
    action_on_duplicate: Literal["skip", "rename", "replace"] = "skip"
    custom_variable_name: Optional[str] = None
    
    # Display
    display_name: str = ""  # May be truncated for UI
    warning_message: Optional[str] = None
```

### `BulkAttachSessionVM`

Manages the entire bulk attach session state.

```python
@dataclass
class BulkAttachSessionVM:
    # Session context
    target_step_id: str
    target_step_title: str
    workflow_id: str
    
    # Items
    items: list[BulkAttachItemVM] = field(default_factory=list)
    
    # Aggregates
    total_count: int = 0
    ready_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    duplicate_count: int = 0
    total_size_bytes: int = 0
    
    # Settings
    mapping_mode: Literal["one_per_file", "combined", "custom"] = "one_per_file"
    naming_mode: Literal["filename", "index", "custom"] = "filename"
    custom_prefix: str = ""
    duplicate_policy: Literal["skip", "rename", "replace"] = "skip"
    
    # Constraints
    max_slots_per_step: int = 12  # Respect existing limit
    available_slots: int = 12  # Calculated: max - current
    
    @property
    def would_exceed_limit(self) -> bool:
        selected_count = sum(1 for i in self.items if i.selected)
        return selected_count > self.available_slots
    
    @property
    def can_apply(self) -> bool:
        return self.ready_count > 0 and not self.would_exceed_limit
```

### `BulkApplyResult`

Result of applying bulk attach to a step.

```python
@dataclass
class BulkApplyResult:
    success: bool
    step_id: str
    
    # What was created
    created_slots: list[str]  # List of slot IDs
    created_count: int
    
    # What was skipped
    skipped_duplicates: list[str]  # Filenames
    skipped_errors: list[str]  # Filenames with errors
    skipped_limit: list[str]  # Filenames that exceeded slot limit
    
    # Events
    events_emitted: list[dict]  # attachment_ingested events
    
    # Errors
    error_message: Optional[str] = None
```

## Controller Integration

### New Methods in `WorkspaceController`

```python
def start_bulk_attach_session(self, step_id: str) -> BulkAttachSessionVM:
    """Initialize a new bulk attach session for a step."""
    
def analyze_bulk_files(
    self, 
    session: BulkAttachSessionVM, 
    file_paths: list[Path]
) -> BulkAttachSessionVM:
    """Analyze selected files (MIME, signature, duplicates)."""
    
def update_bulk_item_selection(
    self,
    session: BulkAttachSessionVM,
    item_index: int,
    selected: bool
) -> BulkAttachSessionVM:
    """Toggle selection of a specific item."""
    
def apply_bulk_attach(
    self,
    session: BulkAttachSessionVM
) -> BulkApplyResult:
    """Apply selected files to step, creating slots and bindings."""
```

## Validation Pipeline

1. **File-level validation** (per file):
   - MIME type detection (via `ingest_file` with validation_mode="warn")
   - Signature validation
   - Size check (warn if >100KB, will be truncated)
   - Extension consistency check

2. **Session-level validation**:
   - Duplicate detection (same filename already attached to step)
   - Slot limit check (respects `_MAX_ATTACHMENT_SLOTS_PER_STEP`)
   - Total size warning (if >10MB total)

## Slot Creation Strategy

### Mode: One Slot Per File (default)

Each selected file becomes one attachment slot.

- Variable naming: `{filename}` or `{prefix}_{index}`
- Respects slot limit: shows warning if `selected_count > available_slots`
- UI shows: "This will create 8 new slots (4 remaining after)"

### Mode: Combined Slot

All files combined into a single slot with delimited content.

- Useful for: Many small text files (logs, snippets)
- Variable naming: `bulk_attachments` or custom
- Content format: `\n--- {filename} ---\n{content}\n`

### Mode: Custom Mapping

Advanced: user specifies variable name per file or group.

## Event Emission

When bulk apply succeeds:

```python
# Per file (only successfully attached)
event = {
    "event_type": "attachment_ingested",
    "run_id": None,  # Not during run
    "step_id": step_id,
    "slot_id": new_slot_id,
    "variable_name": variable_name,
    "file_path": str(path),
    "size_bytes": size,
    "sha256": hash,
    "status": "ok",
    "ingest_quality": "good|truncated|binary",
    "warnings_count": len(ingest_result.warnings),
    "source": "bulk_attach"  # Distinguish from quick-attach
}
```

## Error Handling

| Scenario | UX Response |
|----------|-------------|
| File fails MIME validation | Show in table with ⚠, allow "Keep anyway" |
| Binary file renamed as .txt | Warning + "This may not be readable" |
| Duplicate filename | Options: Skip, Rename (add suffix), Replace |
| Would exceed slot limit | Disable "Apply", show: "Please select max {n} files" |
| IO error during read | Error row, "Retry" or "Skip" |

## Future Enhancements (v2)

- Background/async processing for 100+ files
- Drag-and-drop folder upload
- Preview panel for text files
- Auto-suggest variable names based on content analysis
- Save bulk attach sessions as templates

## Implementation Phases

### Phase 1: Core Structure
- [ ] Create `BulkAttachSessionVM`, `BulkAttachItemVM`, `BulkApplyResult`
- [ ] Add controller methods (stubs)
- [ ] Create modal UI shell

### Phase 2: File Selection & Analysis
- [ ] File dialog multi-select
- [ ] Integrate `ingest_file` for validation
- [ ] Duplicate detection logic

### Phase 3: UI Polish
- [ ] Validation results table
- [ ] Slot limit indicators
- [ ] Apply/Cancel flow

### Phase 4: Integration
- [ ] Hook into flow canvas "+" menu
- [ ] Hook into inspector panel
- [ ] Add context menu entry

## Related Files

- `core/ingestion.py` - MIME/signature validation (already enhanced)
- `core/models.py` - Data classes
- `ui/workspace_controller.py` - Controller integration point
- `ui/bulk_attach_modal.py` (new) - Modal implementation
- `ui/flow_canvas.py` - Entry point
- `ui/inspector_panel.py` - Entry point
