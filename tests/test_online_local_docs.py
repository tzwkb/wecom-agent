import tempfile
import unittest
from pathlib import Path

from online import local_docs


class OnlineLocalDocsTests(unittest.TestCase):
    def test_read_local_doc_by_path_returns_content_and_staleness_notice(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.md"
            path.write_text("# Plan\ncontent", encoding="utf-8")

            result = local_docs.read_path(path)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["source"], "local-cache-fallback")
            self.assertEqual(result["freshness"], "local file; may be stale vs online document")
            self.assertIn("# Plan", result["content"])
            self.assertIsNone(result["visual"])

    def test_search_reads_matching_cached_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stale = root / "old" / "meeting-notes.txt"
            fresh = root / "new" / "meeting-notes.txt"
            stale.parent.mkdir()
            fresh.parent.mkdir()
            stale.write_text("old", encoding="utf-8")
            fresh.write_text("fresh", encoding="utf-8")
            fresh.touch()

            result = local_docs.search("meeting", roots=[root], max_results=2)

            self.assertEqual(result["count"], 2)
            self.assertEqual(result["files"][0]["name"], "meeting-notes.txt")
            self.assertIn(result["files"][0]["content"], {"old", "fresh"})
            self.assertEqual(result["files"][0]["source"], "local-cache-fallback")

    def test_search_reports_no_local_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = local_docs.search("missing", roots=[tmp])

            self.assertEqual(result["status"], "not_found")
            self.assertEqual(result["count"], 0)
            self.assertIn("not downloaded", result["message"])

    def test_image_returns_visual_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "screenshot.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\n")

            result = local_docs.read_path(path)

            self.assertEqual(result["status"], "visual")
            self.assertIsNone(result["content"])
            self.assertIn("VISUAL", result["visual"])


if __name__ == "__main__":
    unittest.main()
