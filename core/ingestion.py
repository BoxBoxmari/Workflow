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
from typing import Optional

from core.models import IngestResult


# Maximum content size to load (bytes) — guard against very large files
_MAX_CONTENT_BYTES = 100 * 1024  # 100 KB of text

# Default validation mode for ingestion
_DEFAULT_VALIDATION_MODE = "warn"  # "off", "warn", "strict"

# Magic byte signatures for common file types
# Format: (signature_bytes, offset, signature_name, file_type_category)
_SIGNATURES = [
    # ZIP-based formats (OOXML, etc.)
    (b"PK\x03\x04", 0, "ZIP", "zip"),
    (b"PK\x05\x06", 0, "ZIP_EMPTY", "zip"),  # Empty zip
    (b"PK\x07\x08", 0, "ZIP_SPANNED", "zip"),  # Spanned zip
    # PDF
    (b"%PDF-", 0, "PDF", "binary"),
    # Common image formats (for detection, not parsing)
    (b"\x89PNG\r\n\x1a\n", 0, "PNG", "binary"),
    (b"\xff\xd8\xff", 0, "JPEG", "binary"),
    (b"GIF87a", 0, "GIF", "binary"),
    (b"GIF89a", 0, "GIF", "binary"),
    # Executable formats
    (b"MZ", 0, "EXE", "binary"),  # Windows executable
    (b"\x7fELF", 0, "ELF", "binary"),  # Linux executable
    # UTF BOMs (text markers)
    (b"\xef\xbb\xbf", 0, "UTF8_BOM", "text"),  # UTF-8 BOM
    (b"\xff\xfe", 0, "UTF16_LE_BOM", "text"),  # UTF-16 LE BOM
    (b"\xfe\xff", 0, "UTF16_BE_BOM", "text"),  # UTF-16 BE BOM
]

# Extension to expected signature mapping
_EXTENSION_SIGNATURE_EXPECTATIONS = {
    ".docx": ("zip", "OOXML document"),
    ".xlsx": ("zip", "OOXML spreadsheet"),
    ".pptx": ("zip", "OOXML presentation"),
    ".pdf": ("binary", "PDF document"),
    ".txt": ("text", "Plain text"),
    ".json": ("text", "JSON"),
    ".xml": ("text", "XML"),
    ".csv": ("text", "CSV"),
}


def _detect_signature(path: Path) -> tuple[Optional[str], Optional[str], bool]:
    """
    Detect file signature from magic bytes.

    Returns:
        (signature_name, signature_type, is_text_file)
        - signature_name: Name of detected signature or None
        - signature_type: "text", "binary", "zip", or "unknown"
        - is_text_file: Whether the file appears to be text (based on encoding detection)
    """
    try:
        # Read first 16 bytes for signature detection
        with open(path, "rb") as f:
            header = f.read(16)
    except Exception:
        return (None, None, False)

    if not header:
        return (None, "unknown", True)  # Empty file treated as text (safe default)

    # Check for known signatures
    for sig_bytes, offset, sig_name, sig_type in _SIGNATURES:
        if len(header) >= offset + len(sig_bytes):
            if header[offset:offset + len(sig_bytes)] == sig_bytes:
                return (sig_name, sig_type, sig_type == "text")

    # No magic signature found - try to detect if it's text by checking for binary content
    try:
        # Attempt to decode as UTF-8 (allowing some error tolerance)
        with open(path, "rb") as f:
            sample = f.read(4096)  # Sample first 4KB
        sample.decode("utf-8", errors="strict")
        return ("TEXT_UTF8", "text", True)
    except UnicodeDecodeError:
        # Contains binary data
        return ("BINARY_DATA", "binary", False)
    except Exception:
        return (None, "unknown", False)


def _validate_signature(
    path: Path,
    ext: str,
    detected_sig: Optional[str],
    detected_type: Optional[str],
    validation_mode: str = "warn",
) -> tuple[list[str], list[str], bool]:
    """
    Validate that detected signature matches expected signature for extension.

    Args:
        validation_mode: "warn" adds issues to warnings; "strict" adds to errors

    Returns:
        (validation_warnings, validation_errors, signature_ok)
    """
    warnings: list[str] = []
    errors: list[str] = []
    signature_ok = True

    # Get expectations for this extension
    expected = _EXTENSION_SIGNATURE_EXPECTATIONS.get(ext)
    if expected is None:
        # Unknown extension - warn but don't block
        msg = f"Unknown file type: {ext}. Proceeding with best-effort parsing."
        if validation_mode == "strict":
            errors.append(msg)
        else:
            warnings.append(msg)
        return (warnings, errors, signature_ok)

    expected_type, expected_desc = expected

    # Helper to add issue based on mode
    def add_issue(msg: str) -> None:
        nonlocal signature_ok
        signature_ok = False
        if validation_mode == "strict":
            errors.append(msg)
        else:
            warnings.append(msg)

    # Special case: ZIP-based formats need ZIP signature
    if expected_type == "zip":
        if detected_type != "zip":
            add_issue(
                f"File extension claims {expected_desc} but content is not a valid ZIP archive."
            )
        else:
            # Additional check: OOXML files need specific internal structure
            if not _is_valid_ooxml(path):
                add_issue(
                    "File appears to be ZIP but missing required "
                    f"{expected_desc} internal structure."
                )

    # Special case: PDF should be binary with PDF signature
    elif expected_type == "binary" and ext == ".pdf":
        if detected_sig != "PDF":
            add_issue(
                "File extension is .pdf but content does not appear "
                "to be a valid PDF document."
            )

    # Text formats should have text signature (or no signature is OK if content is text)
    elif expected_type == "text":
        if detected_type == "binary":
            add_issue(
                f"File extension claims {expected_desc} but content appears to be binary data."
            )

    return (warnings, errors, signature_ok)


def _is_valid_ooxml(path: Path) -> bool:
    """Check if a ZIP file has the internal structure of a valid OOXML document."""
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            namelist = zf.namelist()
            # Check for required OOXML structure
            # [Content_Types].xml must exist
            if "[Content_Types].xml" not in namelist:
                return False
            # Check for relationships
            if "_rels/.rels" not in namelist:
                return False
            return True
    except Exception:
        return False


def ingest_file(
    filepath: str | Path, validation_mode: str = _DEFAULT_VALIDATION_MODE
) -> IngestResult:
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

    # Detect MIME/signature before parsing (RISK-002 hardening)
    detected_sig, detected_type, _ = _detect_signature(path)

    # Validate signature against declared extension
    val_warnings, val_errors, sig_ok = _validate_signature(
        path, ext, detected_sig, detected_type, validation_mode
    )

    # Apply validation mode policy
    if validation_mode == "strict":
        if val_errors:
            return IngestResult(
                metadata=metadata,
                error=f"Signature validation failed for {path.name}: {'; '.join(val_errors)}",
                detected_signature=detected_sig,
                detected_mime=detected_type,
                signature_ok=sig_ok,
                signature_type=detected_type or "unknown",
                validation_mode=validation_mode,
                validation_warnings=val_warnings,
                validation_errors=val_errors,
            )
    # In "warn" mode, continue but capture warnings

    try:
        result = parser(path)
        result.metadata.update(metadata)

        # Enrich result with MIME/signature validation metadata
        result.detected_signature = detected_sig
        result.detected_mime = detected_type
        result.signature_ok = sig_ok
        result.signature_type = detected_type or "unknown"
        result.validation_mode = validation_mode
        result.validation_warnings = val_warnings
        result.validation_errors = val_errors

        # Add parser warnings to combined warnings
        if val_warnings:
            result.warnings.extend(val_warnings)

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
            detected_signature=detected_sig,
            detected_mime=detected_type,
            signature_ok=sig_ok,
            signature_type=detected_type or "unknown",
            validation_mode=validation_mode,
            validation_warnings=val_warnings,
            validation_errors=val_errors,
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
