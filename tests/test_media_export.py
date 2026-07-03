import tempfile
import unittest
from pathlib import Path

from decrypt.media_export import copy_unique


class MediaExportTests(unittest.TestCase):
    def test_copy_unique_keeps_files_with_the_same_basename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src1 = root / "cache-a" / "2026" / "report.pdf"
            src2 = root / "cache-b" / "2026" / "report.pdf"
            dst = root / "out"
            src1.parent.mkdir(parents=True)
            src2.parent.mkdir(parents=True)
            src1.write_text("one", encoding="utf-8")
            src2.write_text("two", encoding="utf-8")

            first = copy_unique(src1, dst)
            second = copy_unique(src2, dst)

            self.assertNotEqual(first, second)
            self.assertEqual(first.name, "report.pdf")
            self.assertTrue(second.name.startswith("report_"))
            self.assertEqual(sorted(p.read_text(encoding="utf-8") for p in dst.iterdir()), ["one", "two"])


if __name__ == "__main__":
    unittest.main()
