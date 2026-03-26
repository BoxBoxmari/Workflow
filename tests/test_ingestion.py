"""Tests for core.ingestion — file parsing by type."""

import json
import os
import tempfile
import unittest
import zipfile

from core.ingestion import ingest_file


def _write_temp_zip(path: str, entries: dict[str, str]) -> None:
    # Create an OOXML container (.docx/.xlsx/.pptx) with specified internal files.
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)


class TestIngestionTxt(unittest.TestCase):
    def test_parse_txt(self):
        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write("Hello world\nLine 2")
            f.flush()
            result = ingest_file(f.name)
        self.assertTrue(result.ok)
        self.assertIn("Hello world", result.content)
        self.assertIn("Line 2", result.content)

    def test_txt_normalizes_line_endings_and_excess_blank_lines(self):
        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", delete=False, encoding="utf-8", newline=""
        ) as f:
            f.write("  A\r\n\r\n\r\nB\rC  \r\n\r\n\r\n")
            f.flush()
            result = ingest_file(f.name)
        self.assertTrue(result.ok)
        self.assertEqual(result.content, "A\n\nB\nC")


class TestIngestionJson(unittest.TestCase):
    def test_parse_json(self):
        data = {"key": "value", "num": 42}
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            f.flush()
            result = ingest_file(f.name)
        self.assertTrue(result.ok)
        self.assertIn("key", result.content)
        self.assertIn("42", result.content)


class TestIngestionCsv(unittest.TestCase):
    def test_parse_csv(self):
        with tempfile.NamedTemporaryFile(
            suffix=".csv", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write("name,age\nAlice,30\nBob,25")
            f.flush()
            result = ingest_file(f.name)
        self.assertTrue(result.ok)
        self.assertIn("Alice", result.content)
        self.assertIn("30", result.content)


class TestIngestionXml(unittest.TestCase):
    def test_parse_xml(self):
        xml_content = "<root><item>Hello</item><item>World</item></root>"
        with tempfile.NamedTemporaryFile(
            suffix=".xml", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_content)
            f.flush()
            result = ingest_file(f.name)
        self.assertTrue(result.ok)
        self.assertIn("Hello", result.content)
        self.assertIn("World", result.content)

    def test_parse_xml_blocks_dtd_and_entities(self):
        # Internal DTD + entity reference should be rejected by defusedxml.
        xml_content = """<?xml version="1.0"?>
<!DOCTYPE root [
  <!ENTITY xxe "PWNED">
]>
<root>&xxe;</root>"""
        with tempfile.NamedTemporaryFile(
            suffix=".xml", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_content)
            f.flush()
            result = ingest_file(f.name)

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        self.assertIn("Failed to parse", result.error)


class TestIngestionXXEOOXML(unittest.TestCase):
    def test_parse_docx_blocks_dtd_and_entities(self):
        docx_xml = """<?xml version="1.0"?>
<!DOCTYPE w:document [
  <!ENTITY xxe "PWNED">
]>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p><w:r><w:t>&xxe;</w:t></w:r></w:p>
</w:document>"""

        tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        tmp.close()
        try:
            _write_temp_zip(tmp.name, {"word/document.xml": docx_xml})
            result = ingest_file(tmp.name)
            self.assertFalse(result.ok)
            self.assertIsNotNone(result.error)
            self.assertIn("Failed to parse", result.error)
        finally:
            os.unlink(tmp.name)

    def test_parse_xlsx_blocks_dtd_and_entities(self):
        xlsx_sheet = """<?xml version="1.0"?>
<!DOCTYPE worksheet [
  <!ENTITY xxe "PWNED">
]>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="s"><v>&xxe;</v></c>
    </row>
  </sheetData>
</worksheet>"""

        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp.close()
        try:
            _write_temp_zip(tmp.name, {"xl/worksheets/sheet1.xml": xlsx_sheet})
            result = ingest_file(tmp.name)
            self.assertFalse(result.ok)
            self.assertIsNotNone(result.error)
            self.assertIn("Failed to parse", result.error)
        finally:
            os.unlink(tmp.name)

    def test_parse_pptx_blocks_dtd_and_entities(self):
        pptx_slide = """<?xml version="1.0"?>
<!DOCTYPE p:sld [
  <!ENTITY xxe "PWNED">
]>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:spTree>
    <p:sp>
      <p:txBody>
        <a:p><a:r><a:t>&xxe;</a:t></a:r></a:p>
      </p:txBody>
    </p:sp>
  </p:spTree>
</p:sld>"""

        tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
        tmp.close()
        try:
            _write_temp_zip(tmp.name, {"ppt/slides/slide1.xml": pptx_slide})
            result = ingest_file(tmp.name)
            self.assertFalse(result.ok)
            self.assertIsNotNone(result.error)
            self.assertIn("Failed to parse", result.error)
        finally:
            os.unlink(tmp.name)


class TestIngestionPdf(unittest.TestCase):
    def test_pdf_unsupported(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", mode="wb", delete=False) as f:
            f.write(b"%PDF-1.4 dummy")
            f.flush()
            result = ingest_file(f.name)
        self.assertFalse(result.ok)
        self.assertIn("not supported", result.error)


class TestIngestionUnsupported(unittest.TestCase):
    def test_unknown_extension(self):
        with tempfile.NamedTemporaryFile(suffix=".xyz", mode="w", delete=False) as f:
            f.write("data")
            f.flush()
            result = ingest_file(f.name)
        self.assertFalse(result.ok)
        self.assertIn("Unsupported", result.error)


class TestIngestionMissing(unittest.TestCase):
    def test_file_not_found(self):
        result = ingest_file("/nonexistent/file.txt")
        self.assertFalse(result.ok)
        self.assertIn("not found", result.error)


class TestIngestionSignatureValidation(unittest.TestCase):
    """Tests for MIME/signature validation (RISK-002 hardening)."""

    def test_binary_renamed_as_txt_warns(self):
        """A binary file renamed as .txt should produce validation warning."""
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb", delete=False) as f:
            # Write PNG signature (binary)
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR")
            f.flush()
            result = ingest_file(f.name)
        # Should parse but with warnings
        self.assertTrue(result.ok)  # In warn mode, still ok
        self.assertTrue(result.has_validation_issues)
        self.assertFalse(result.signature_ok)
        self.assertEqual(result.signature_type, "binary")
        self.assertTrue(any("binary data" in w for w in result.validation_warnings))

    def test_off_mode_suppresses_validation_issues(self):
        """validation_mode="off" should skip validation side-effects."""
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb", delete=False) as f:
            # Write PNG signature (binary) but with .txt extension
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR")
            f.flush()
            result = ingest_file(f.name, validation_mode="off")

        self.assertTrue(result.ok)  # off mode should not hard-fail
        self.assertFalse(result.has_validation_issues)
        self.assertTrue(result.signature_ok)
        self.assertEqual(result.validation_warnings, [])
        self.assertEqual(result.validation_errors, [])
        self.assertFalse(any("binary data" in w for w in result.warnings))
        self.assertEqual(result.validation_mode, "off")

    def test_legitimate_txt_passes(self):
        """A real text file should pass validation."""
        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write("Hello, this is a legitimate text file.\nLine 2.\n")
            f.flush()
            result = ingest_file(f.name)
        self.assertTrue(result.ok)
        self.assertFalse(result.has_validation_issues)
        self.assertTrue(result.signature_ok)
        self.assertEqual(result.signature_type, "text")

    def test_ooxml_spoofed_zip_warns(self):
        """A ZIP without OOXML structure renamed as .docx should warn."""
        with tempfile.NamedTemporaryFile(suffix=".docx", mode="wb", delete=False) as f:
            # Create a valid ZIP but without OOXML structure
            import zipfile as zf_module

            with zf_module.ZipFile(f.name, "w") as zf:
                zf.writestr("random.txt", "not an ooxml file")
            result = ingest_file(f.name)
        # Should have warnings about missing OOXML structure
        self.assertTrue(result.has_validation_issues)
        self.assertTrue(
            any("OOXML" in w or "internal structure" in w for w in result.warnings)
        )

    def test_valid_docx_passes(self):
        """A valid OOXML document should pass signature validation."""
        with tempfile.NamedTemporaryFile(suffix=".docx", mode="wb", delete=False) as f:
            # Create a minimal valid OOXML structure
            import zipfile as zf_module

            with zf_module.ZipFile(f.name, "w") as zf:
                zf.writestr("[Content_Types].xml", "<?xml version=\"1.0\"?><Types/>")
                zf.writestr("_rels/.rels", "<?xml version=\"1.0\"?><Relationships/>")
            result = ingest_file(f.name)
        # Valid OOXML structure should pass signature validation
        # Note: result.ok may be False because skeleton docx has no content to parse,
        # but signature validation should succeed (no signature warnings/errors)
        self.assertTrue(result.signature_ok)
        self.assertEqual(result.detected_signature, "ZIP")
        self.assertEqual(result.signature_type, "zip")
        # Should not have validation issues for a valid OOXML structure
        self.assertFalse(result.has_validation_issues)

    def test_content_truncation_warning(self):
        """Files larger than 100KB should produce truncation warning."""
        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", encoding="utf-8", delete=False
        ) as f:
            # Write >100KB of text
            f.write("x" * (100 * 1024 + 1000))
            f.flush()
            result = ingest_file(f.name)
        self.assertTrue(result.ok)
        self.assertTrue(any("truncated" in w for w in result.warnings))
        self.assertEqual(len(result.content), 100 * 1024)  # Truncated to exactly 100KB

    def test_empty_file_treated_as_text(self):
        """Empty files should be treated as text and pass validation."""
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("")  # Empty
            f.flush()
            result = ingest_file(f.name)
        self.assertTrue(result.ok)
        self.assertEqual(result.signature_type, "unknown")

    def test_strict_mode_rejects_spoofed_binary(self):
        """In strict mode, binary renamed as text should be rejected."""
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR")
            f.flush()
            result = ingest_file(f.name, validation_mode="strict")
        # In strict mode, should not be ok
        self.assertFalse(result.ok)
        self.assertTrue(result.has_validation_issues)

    def test_signature_metadata_populated(self):
        """All IngestResult signature fields should be populated correctly."""
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write('{"key": "value"}')
            f.flush()
            result = ingest_file(f.name)
        self.assertTrue(result.ok)
        self.assertIsNotNone(result.detected_mime)
        self.assertIsNotNone(result.detected_signature)
        self.assertTrue(result.signature_ok)
        self.assertEqual(result.validation_mode, "warn")


if __name__ == "__main__":
    unittest.main()
