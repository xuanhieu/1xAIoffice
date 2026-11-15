# SPDX-License-Identifier: MPL-2.0
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import changeset  # noqa: E402

OLD = "Kính gửi quý cơ quan, chúng tôi xin trình bày như sau."
NEW = "Kính gửi quý cơ quan, chúng tôi xin trình bày nội dung sau đây."


class BuildTests(unittest.TestCase):
    def test_keeps_real_changes(self):
        changes = changeset.build([("p1", OLD, NEW)])
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].anchor, "p1")

    def test_drops_changes_that_do_nothing(self):
        self.assertEqual(changeset.build([("p1", OLD, OLD), ("p2", OLD, f"  {OLD}  ")]), [])

    def test_mixed(self):
        changes = changeset.build([("p1", OLD, OLD), ("p2", OLD, NEW)])
        self.assertEqual([c.anchor for c in changes], ["p2"])


class SummaryTests(unittest.TestCase):
    def test_counts_words_and_places(self):
        line = changeset.summary(changeset.build([("p1", "một hai ba", "một hai ba bốn")]))
        self.assertIn("1 chỗ", line)
        self.assertIn("3 từ → 4 từ", line)

    def test_several_places(self):
        changes = changeset.build([("p1", "a b", "a b c"), ("p2", "d", "d e")])
        self.assertIn("2 chỗ", changeset.summary(changes))

    def test_nothing_to_do(self):
        self.assertEqual(changeset.summary([]), "Không có gì để sửa.")


class PreviewTests(unittest.TestCase):
    def test_shows_before_and_after(self):
        text = changeset.preview(changeset.build([("p1", OLD, NEW)]))
        self.assertIn("Trước:", text)
        self.assertIn("Sau:", text)
        self.assertIn(OLD, text)
        self.assertIn(NEW, text)

    def test_long_text_is_shortened(self):
        changes = changeset.build([("p1", "x" * 2000, "y" * 2000)])
        text = changeset.preview(changes, limit=100)
        self.assertIn("…", text)
        self.assertLess(len(text), 600)

    def test_numbers_several_places(self):
        text = changeset.preview(changeset.build([("p1", "a", "b"), ("p2", "c", "d")]))
        self.assertIn("[1]", text)
        self.assertIn("[2]", text)

    def test_empty_changeset(self):
        self.assertEqual(changeset.preview([]), "Không có gì để sửa.")


class StaleTests(unittest.TestCase):
    def test_nothing_changed(self):
        changes = changeset.build([("p1", OLD, NEW)])
        self.assertEqual(changeset.stale(changes, {"p1": OLD}), [])

    def test_whitespace_differences_are_harmless(self):
        changes = changeset.build([("p1", OLD, NEW)])
        self.assertEqual(changeset.stale(changes, {"p1": f"  {OLD}\n"}), [])

    def test_edited_anchor_is_reported(self):
        changes = changeset.build([("p1", OLD, NEW)])
        self.assertEqual(changeset.stale(changes, {"p1": "Người dùng vừa gõ lại đoạn này."}), ["p1"])

    def test_missing_anchor_is_reported(self):
        changes = changeset.build([("p1", OLD, NEW)])
        self.assertEqual(changeset.stale(changes, {}), ["p1"])


if __name__ == "__main__":
    unittest.main()
