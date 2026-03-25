"""Tests for core.ingestion — file parsing by type."""

import json
import tempfile
import unittest

from core.ingestion import ingest_file


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
