import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path

from scripts import validate_catalog


class ValidateCatalogTests(unittest.TestCase):
    def run_catalog(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.csv"
            with catalog.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow([
                    "id", "level", "topic", "title", "issuer", "document_number",
                    "published_date", "effective_date", "expiry_date", "status",
                    "evidence_grade", "official_page_url", "official_file_url",
                    "local_path", "sha256", "accessed_at", "needs_ocr", "relation", "notes",
                ])
                writer.writerows(rows)
            old_catalog = validate_catalog.CATALOG
            validate_catalog.CATALOG = catalog
            try:
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    result = validate_catalog.main()
                return result, stderr.getvalue()
            finally:
                validate_catalog.CATALOG = old_catalog

    def test_rejects_extra_csv_column(self):
        row = [
            "ID", "国家", "主题", "标题", "机关", "", "", "", "", "待核验", "C",
            "https://www.gov.cn/a", "", "", "", "2026-08-02", "否", "", "", "extra",
        ]
        result, error = self.run_catalog([row])
        self.assertEqual(result, 1)
        self.assertIn("extra CSV columns", error)

    def test_rejects_empty_required_value(self):
        row = [
            "ID", "国家", "主题", "标题", "机关", "", "", "", "", "待核验", "C",
            "https://www.gov.cn/a", "", "", "", "", "否", "", "",
        ]
        result, error = self.run_catalog([row])
        self.assertEqual(result, 1)
        self.assertIn("empty required field accessed_at", error)

    def test_official_domain_matching_is_boundary_aware(self):
        self.assertTrue(validate_catalog.is_official("https://www.gov.cn/a"))
        self.assertTrue(validate_catalog.is_official("http://www.qdgjj.com/a"))
        self.assertTrue(validate_catalog.is_official("https://www.cqgjj.cn/a"))
        self.assertFalse(validate_catalog.is_official("https://evilgov.cn/a"))
        self.assertFalse(validate_catalog.is_official("https://qdgjj.com.example/a"))
        self.assertFalse(validate_catalog.is_official("https://cqgjj.cn.example/a"))


if __name__ == "__main__":
    unittest.main()