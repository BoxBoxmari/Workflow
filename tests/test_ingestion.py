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


if __name__ == "__main__":
    unittest.main()
