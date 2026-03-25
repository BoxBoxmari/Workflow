---
name: docx
description: "Creates, edits, and analyzes .docx files with tracked changes, comments, and formatting preservation. Use when creating Word documents, editing or redlining content, extracting text, converting DOCX to markdown or images, or working with OOXML/document review workflows."
---

# DOCX Creation, Editing, and Analysis

## Overview

.docx files are ZIP archives containing XML and resources. Use the workflow below for reading, creating, or editing.

## Workflow Decision Tree

| Task | Approach |
|------|----------|
| **Read/analyze content** | Text extraction or raw XML (see below) |
| **Create new document** | docx-js workflow |
| **Edit existing – your doc, simple** | Basic OOXML editing |
| **Edit existing – someone else's / legal, academic, business** | **Redlining workflow** (required) |

## Reading and Analyzing

### Text extraction (markdown)

```bash
pandoc --track-changes=all path-to-file.docx -o output.md
# Options: --track-changes=accept | reject | all
```

### Raw XML (comments, structure, media)

- Unpack: `python ooxml/scripts/unpack.py <office_file> <output_directory>`
- Key paths: `word/document.xml`, `word/comments.xml`, `word/media/`
- Tracked changes: `<w:ins>` (insertions), `<w:del>` (deletions)

## Creating a New Document

1. **Read full API**: Read [docx-js.md](docx-js.md) start to finish (no range limits).
2. Create a JS/TS file using Document, Paragraph, TextRun; export with `Packer.toBuffer()`.
3. Dependencies: `npm install docx` (or global `docx`).

## Editing an Existing Document (OOXML)

1. **Read full API**: Read [ooxml.md](ooxml.md) start to finish (no range limits).
2. Unpack: `python ooxml/scripts/unpack.py <office_file> <output_directory>`
3. Write a Python script using the Document library (see ooxml.md “Document Library”).
4. Pack: `python ooxml/scripts/pack.py <input_directory> <output.docx>`

Use high-level Document methods where possible; drop to DOM for complex cases.

## Redlining Workflow (Tracked Changes)

Use for review/legal/academic/business docs. Implement **all** planned changes; batch related edits (3–10 per batch) for easier debugging.

### Principle: Minimal, precise edits

Only mark text that actually changes. Reuse original `<w:r>` and RSID for unchanged text.

**Bad** – replace full sentence:
```python
'<w:del>...</w:del><w:ins><w:r><w:t>The term is 60 days.</w:t></w:r></w:ins>'
```

**Good** – only “30” → “60”:
```python
'<w:r w:rsidR="00AB12CD"><w:t>The term is </w:t></w:r><w:del><w:r><w:delText>30</w:delText></w:r></w:del><w:ins><w:r><w:t>60</w:t></w:r></w:ins><w:r w:rsidR="00AB12CD"><w:t> days.</w:t></w:r>'
```

### Steps

1. **Markdown with track changes**
   ```bash
   pandoc --track-changes=all path-to-file.docx -o current.md
   ```

2. **Plan batches**  
   Group 3–10 related changes by section, type, or proximity. **Do not** use markdown line numbers to locate edits; use section/heading, paragraph IDs, or grep on unique surrounding text in XML.

3. **Read docs and unpack**
   - Read [ooxml.md](ooxml.md) in full; focus on “Document Library” and “Tracked Change Patterns”.
   - Unpack: `python ooxml/scripts/unpack.py <file.docx> <dir>`
   - Use the RSID suggested by the unpack script for new changes.

4. **Implement per batch**
   - Grep `word/document.xml` **immediately before** each script run (line numbers change after edits).
   - Use `get_node` (or equivalent), apply changes, `doc.save()`.
   - Suggested batching: by section, by change type, or by page range.

5. **Pack**
   ```bash
   python ooxml/scripts/pack.py unpacked reviewed-document.docx
   ```

6. **Verify**
   ```bash
   pandoc --track-changes=all reviewed-document.docx -o verification.md
   grep "original phrase" verification.md   # should NOT appear
   grep "replacement phrase" verification.md # should appear
   ```
   Confirm no unintended edits.

## Converting DOCX to Images

1. DOCX → PDF: `soffice --headless --convert-to pdf document.docx`
2. PDF → images: `pdftoppm -jpeg -r 150 document.pdf page`  
   Yields `page-1.jpg`, `page-2.jpg`, …  
   Options: `-r 150` (DPI), `-f N` / `-l N` (first/last page), `-png` for PNG.

## Code Style

- Prefer short, clear code.
- Avoid long variable names and redundant steps.
- Omit unnecessary print/logging.

## Dependencies

| Tool / lib | Install | Purpose |
|------------|--------|--------|
| pandoc | `apt-get install pandoc` | Text extraction, markdown with track changes |
| docx | `npm install -g docx` | Creating new .docx (JS/TS) |
| LibreOffice | `apt-get install libreoffice` | DOCX → PDF |
| poppler-utils | `apt-get install poppler-utils` | pdftoppm (PDF → images) |
| defusedxml | `pip install defusedxml` | Safe XML parsing (Python) |

Unpack/pack scripts assume an `ooxml/scripts/` layout (e.g. `unpack.py`, `pack.py`). If your project uses different paths, adjust the commands accordingly.
