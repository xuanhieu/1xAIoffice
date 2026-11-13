# SPDX-License-Identifier: MPL-2.0
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x.guides import guide_files, pick_language, thumbnail_png  # noqa: E402


class GuideTests(unittest.TestCase):
    def test_language(self):
        self.assertEqual(pick_language("vi"), "vi")
        self.assertEqual(pick_language("vi-VN"), "vi")
        self.assertEqual(pick_language("en-US"), "en")
        self.assertEqual(pick_language(""), "en")

    def test_order_and_filters(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / "vi"
            folder.mkdir()
            for n in ("b.pdf", "c.pptx", "a.xlsx", "d.docx", "notes.txt"):
                (folder / n).write_text("x")
            got = [(p.name, f) for p, f in guide_files(d, "vi")]
            self.assertEqual([g[0] for g in got], ["d.docx", "a.xlsx", "c.pptx"])
            self.assertEqual(got[0][1], "MS Word 2007 XML")
            self.assertEqual(guide_files(d, "en"), [])
            (folder / "thumbs").mkdir()
            (folder / "thumbs" / "d.docx.png").write_bytes(b"png")
            self.assertEqual(thumbnail_png(folder / "d.docx"), b"png")
            self.assertIsNone(thumbnail_png(folder / "a.xlsx"))


if __name__ == "__main__":
    unittest.main()
