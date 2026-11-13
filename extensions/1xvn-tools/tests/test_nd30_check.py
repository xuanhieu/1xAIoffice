# SPDX-License-Identifier: MPL-2.0
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import nd30_check  # noqa: E402
from vn1x.nd30 import DATA  # noqa: E402

GOOD_PAGE = {"width_mm": 210, "height_mm": 297, "margin_top_mm": 20, "margin_bottom_mm": 20,
             "margin_left_mm": 30, "margin_right_mm": 15, "font": "Times New Roman"}
GOOD_BODY = [{"text": "Đoạn một.", "size": 14, "font": "Times New Roman", "adjust": 2, "indent_mm": 12.7},
             {"text": "Đoạn hai.", "size": 14, "font": "Times New Roman", "adjust": 2, "indent_mm": 12.7}]
GOOD_TEXTS = [DATA["quoc_hieu"], DATA["tieu_ngu"], "Nơi nhận:", "- Lưu: VT."]


def keys(issues):
    return sorted(i.key for i in issues)


class PageTests(unittest.TestCase):
    def test_good_page_has_no_issue(self):
        self.assertEqual(nd30_check.check_page(GOOD_PAGE), [])

    def test_letter_size_and_margins(self):
        bad = dict(GOOD_PAGE, width_mm=215.9, height_mm=279.4, margin_left_mm=25, margin_right_mm=25)
        self.assertEqual(keys(nd30_check.check_page(bad)), ["margin_left_mm", "margin_right_mm", "page_size"])

    def test_margins_at_the_edge_of_the_range_pass(self):
        self.assertEqual(nd30_check.check_page(dict(GOOD_PAGE, margin_top_mm=25, margin_left_mm=35,
                                                    margin_right_mm=20, margin_bottom_mm=25)), [])

    def test_wrong_font_is_fixable(self):
        issues = nd30_check.check_page(dict(GOOD_PAGE, font="Arial"))
        self.assertEqual(keys(issues), ["font"])
        self.assertTrue(issues[0].fix)
        self.assertIn("Times New Roman", issues[0].message)

    def test_a4_within_one_millimetre_passes(self):
        self.assertEqual(nd30_check.check_page(dict(GOOD_PAGE, width_mm=209.9, height_mm=297.04)), [])


class BodyTests(unittest.TestCase):
    def test_good_body(self):
        self.assertEqual(nd30_check.check_body(GOOD_BODY), [])

    def test_size_font_and_alignment(self):
        bad = [dict(p, size=11, font="Arial", adjust=0) for p in GOOD_BODY]
        self.assertEqual(keys(nd30_check.check_body(bad)), ["body_adjust", "body_font", "body_size"])

    def test_missing_indent(self):
        bad = [dict(p, indent_mm=0) for p in GOOD_BODY]
        self.assertEqual(keys(nd30_check.check_body(bad)), ["body_indent"])

    def test_empty_body_is_not_reported(self):
        self.assertEqual(nd30_check.check_body([{"text": "  ", "size": 9}]), [])


class PartsTests(unittest.TestCase):
    def test_all_parts_present(self):
        self.assertEqual(nd30_check.check_parts(GOOD_TEXTS), [])

    def test_missing_parts(self):
        self.assertEqual(keys(nd30_check.check_parts(["Chỉ có chữ thường"])),
                         ["noi_nhan", "quoc_hieu", "tieu_ngu"])

    def test_extra_spaces_still_match(self):
        self.assertEqual(nd30_check.check_parts([f"  {DATA['quoc_hieu']}  ", DATA["tieu_ngu"], "Nơi  nhận:"]), [])


class WholeDocumentTests(unittest.TestCase):
    def test_clean_document(self):
        self.assertEqual(nd30_check.check({"page": GOOD_PAGE, "body": GOOD_BODY, "texts": GOOD_TEXTS}), [])

    def test_page_fix_matches_the_rules(self):
        fix = nd30_check.page_fix()
        self.assertEqual(nd30_check.check_page(fix), [])
        self.assertEqual(fix["font"], DATA["font"])


if __name__ == "__main__":
    unittest.main()
