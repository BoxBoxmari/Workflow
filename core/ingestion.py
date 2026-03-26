"""
core.ingestion — File parsing and normalization.

Ingests local files into plain-text content for use as workflow input.
Three tiers of support:
  Tier 1 (reliable):     txt, json, xml, csv   — full content via stdlib
  Tier 2 (best-effort):  docx, xlsx, pptx      — text via zip+xml parsing
  Tier 3 (limited):      pdf                    — not supported, returns warning
"""

from __future__ import annotations

import csv
import json
import re
import defusedxml.ElementTree as ET
import zipfile
from pathlib import Path

from core.models import IngestResult


# Maximum content size to load (bytes) — guard against very large files
_MAX_CONTENT_BYTES = 100 * 1024  # 100 KB of text


def ingest_file(filepath: str | Path) -> IngestResult:
    """
    Ingest a local file and return normalized text content.

    Dispatches by file extension.  Returns IngestResult with content,
    metadata, and any warnings about fidelity limitations.
    """
    # Normalize path to resolve symlinks and redundant ".." components.
    # This is a correctness measure for consistent metadata, not a security
    # barrier — in a local desktop app the user selects their own files.
    path = Path(filepath).resolve()

    if not path.is_file():
        return IngestResult(error=f"File not found: {path}")

    ext = path.suffix.lower()
    metadata = {
        "filename": path.name,
        "type": ext,
        "size_bytes": path.stat().st_size,
    }

    # Extension dispatch
    parsers = {
        ".txt": _parse_txt,
        ".json": _parse_json,
        ".xml": _parse_xml,
        ".csv": _parse_csv,
        ".docx": _parse_docx,
        ".xlsx": _parse_xlsx,
        ".pptx": _parse_pptx,
        ".pdf": _parse_pdf,
    }

    parser = parsers.get(ext)
    if parser is None:
        return IngestResult(
            metadata=metadata,
            error=f"Unsupported file type: {ext}",
        )

    try:
        result = parser(path)
        result.metadata.update(metadata)
        if result.content:
            result.content = _normalize_content(result.content)
        # Truncate if too large
        if len(result.content) > _MAX_CONTENT_BYTES:
            result.content = result.content[:_MAX_CONTENT_BYTES]
            result.warnings.append(
                f"Content truncated to {_MAX_CONTENT_BYTES // 1024}KB"
            )
        return result
    except Exception as e:
        return IngestResult(
            metadata=metadata,
            error=f"Failed to parse {path.name}: {e}",
        )


def _normalize_content(content: str) -> str:
    content = content.strip()
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content


# ---------------------------------------------------------------------------
# Tier 1 — Reliable (stdlib)
# ---------------------------------------------------------------------------


def _parse_txt(path: Path) -> IngestResult:
    """Read plain text with encoding fallback."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            content = path.read_text(encoding=encoding)
            return IngestResult(content=content)
        except (UnicodeDecodeError, ValueError):
            continue
    return IngestResult(error="Unable to decode text file")


def _parse_json(path: Path) -> IngestResult:
    """Parse JSON and return pretty-printed string."""
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    content = json.dumps(data, indent=2, ensure_ascii=False)
    return IngestResult(content=content)


def _parse_xml(path: Path) -> IngestResult:
    """Extract all text content from XML elements."""
    tree = ET.parse(str(path))
    root = tree.getroot()
    texts = []
    for elem in root.iter():
        if elem.text and elem.text.strip():
            texts.append(elem.text.strip())
        if elem.tail and elem.tail.strip():
            texts.append(elem.tail.strip())
    content = "\n".join(texts)
    return IngestResult(content=content)


def _parse_csv(path: Path) -> IngestResult:
    """Read CSV and convert to a readable table string."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return IngestResult(content="(empty CSV)")

    # Format as pipe-separated table
    lines = []
    for row in rows:
        lines.append(" | ".join(row))
    content = "\n".join(lines)
    return IngestResult(content=content)


# ---------------------------------------------------------------------------
# Tier 2 — Best-effort (stdlib zip + xml parsing)
# ---------------------------------------------------------------------------

# OOXML namespaces
_DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_XLSX_NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_PPTX_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def _parse_docx(path: Path) -> IngestResult:
    """Extract paragraph text from a .docx file via zip + xml."""
    warnings = [
        "DOCX: best-effort plain text extraction. "
        "Images, tables, headers/footers, and styles are not preserved."
    ]
    texts = []
    with zipfile.ZipFile(str(path), "r") as zf:
        if "word/document.xml" not in zf.namelist():
            return IngestResult(
                warnings=warnings,
                error="word/document.xml not found in archive",
            )
        with zf.open("word/document.xml") as doc:
            tree = ET.parse(doc)
            root = tree.getroot()
            for para in root.iter(f"{{{_DOCX_NS['w']}}}p"):
                para_text = []
                for run in para.iter(f"{{{_DOCX_NS['w']}}}t"):
                    if run.text:
                        para_text.append(run.text)
                line = "".join(para_text).strip()
                if line:
                    texts.append(line)

    content = "\n".join(texts)
    return IngestResult(content=content, warnings=warnings)


def _parse_xlsx(path: Path) -> IngestResult:
    """Extract cell values from first sheet of a .xlsx file via zip + xml."""
    warnings = [
        "XLSX: best-effort text extraction from first sheet only. "
        "Formulas, charts, multiple sheets, merged cells, and date formats not supported."
    ]

    shared_strings: list[str] = []
    cell_values: list[list[str]] = []

    with zipfile.ZipFile(str(path), "r") as zf:
        # Parse shared strings
        if "xl/sharedStrings.xml" in zf.namelist():
            with zf.open("xl/sharedStrings.xml") as ss:
                tree = ET.parse(ss)
                root = tree.getroot()
                ns = _XLSX_NS["s"]
                for si in root.iter(f"{{{ns}}}si"):
                    parts = []
                    for t in si.iter(f"{{{ns}}}t"):
                        if t.text:
                            parts.append(t.text)
                    shared_strings.append("".join(parts))

        # Parse first worksheet
        sheet_path = "xl/worksheets/sheet1.xml"
        if sheet_path not in zf.namelist():
            return IngestResult(
                warnings=warnings,
                error="xl/worksheets/sheet1.xml not found",
            )

        with zf.open(sheet_path) as ws:
            tree = ET.parse(ws)
            root = tree.getroot()
            ns = _XLSX_NS["s"]
            for row_elem in root.iter(f"{{{ns}}}row"):
                row_vals = []
                for cell in row_elem.iter(f"{{{ns}}}c"):
                    cell_type = cell.get("t", "")
                    value_elem = cell.find(f"{{{ns}}}v")
                    if value_elem is not None and value_elem.text:
                        if cell_type == "s":
                            # Shared string reference
                            idx = int(value_elem.text)
                            if idx < len(shared_strings):
                                row_vals.append(shared_strings[idx])
                            else:
                                row_vals.append(value_elem.text)
                        else:
                            row_vals.append(value_elem.text)
                    else:
                        row_vals.append("")
                if any(v for v in row_vals):
                    cell_values.append(row_vals)

    lines = [" | ".join(row) for row in cell_values]
    content = "\n".join(lines)
    return IngestResult(content=content, warnings=warnings)


def _parse_pptx(path: Path) -> IngestResult:
    """Extract text frames from all slides of a .pptx file."""
    warnings = [
        "PPTX: best-effort text extraction only. "
        "Shapes, images, animations, and speaker notes not preserved."
    ]
    slide_texts: list[str] = []

    with zipfile.ZipFile(str(path), "r") as zf:
        slide_files = sorted(
            [
                n
                for n in zf.namelist()
                if n.startswith("ppt/slides/slide") and n.endswith(".xml")
            ]
        )
        if not slide_files:
            return IngestResult(
                warnings=warnings,
                error="No slides found in pptx archive",
            )

        for slide_file in slide_files:
            with zf.open(slide_file) as sf:
                tree = ET.parse(sf)
                root = tree.getroot()
                ns_a = _PPTX_NS["a"]
                texts = []
                for para in root.iter(f"{{{ns_a}}}p"):
                    para_text = []
                    for run in para.iter(f"{{{ns_a}}}r"):
                        t = run.find(f"{{{ns_a}}}t")
                        if t is not None and t.text:
                            para_text.append(t.text)
                    line = "".join(para_text).strip()
                    if line:
                        texts.append(line)

                slide_name = Path(slide_file).stem
                if texts:
                    slide_texts.append(f"--- {slide_name} ---\n" + "\n".join(texts))

    content = "\n\n".join(slide_texts)
    return IngestResult(content=content, warnings=warnings)


# ---------------------------------------------------------------------------
# Tier 3 — Limited
# ---------------------------------------------------------------------------


def _parse_pdf(path: Path) -> IngestResult:
    """PDF is not supported in MVP."""
    return IngestResult(
        warnings=[
            "PDF ingestion is not supported in this MVP. "
            "Please convert to .txt or .docx externally."
        ],
        error="PDF format not supported",
    )
