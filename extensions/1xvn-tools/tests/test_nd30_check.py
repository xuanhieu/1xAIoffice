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


class SpacingTests(unittest.TestCase):
    """Phụ lục I mục 6đ: giãn dòng từ dòng đơn tới 1,5 lines; khoảng cách đoạn TỐI THIỂU 6pt."""

    def body(self, **extra):
        base = {"text": "Một đoạn nội dung.", "size": 14, "font": "Times New Roman", "adjust": 2,
                "indent_mm": 12.7, "line_percent": 100, "space_after_pt": 6}
        return [dict(base, **extra)]

    def keys(self, paragraphs):
        return {issue.key for issue in nd30_check.check_body(paragraphs)}

    def test_single_spacing_and_six_points_are_fine(self):
        self.assertEqual(self.keys(self.body()), set())

    def test_one_and_a_half_lines_is_the_most_the_decree_allows(self):
        self.assertEqual(self.keys(self.body(line_percent=150)), set())
        self.assertIn("body_line_spacing", self.keys(self.body(line_percent=200)))

    def test_less_than_single_spacing_is_wrong_too(self):
        self.assertIn("body_line_spacing", self.keys(self.body(line_percent=90)))

    def test_paragraph_spacing_has_only_a_minimum(self):
        """Nghị định chỉ nói "tối thiểu 6pt", nên 12pt hay 18pt đều đúng; báo oan là lỗi của bộ kiểm."""
        self.assertEqual(self.keys(self.body(space_after_pt=6)), set())
        self.assertEqual(self.keys(self.body(space_after_pt=18)), set())
        self.assertIn("body_space_after", self.keys(self.body(space_after_pt=0)))

    def test_one_well_spaced_paragraph_is_enough(self):
        """Đoạn cuối thường không có khoảng cách dưới; chỉ cần văn bản có chỗ đạt là được."""
        paragraphs = self.body() + self.body(space_after_pt=0)
        self.assertNotIn("body_space_after", self.keys(paragraphs))

    def test_a_document_that_sets_spacing_another_way_is_not_accused(self):
        """Đặt khoảng cách dòng cố định theo mm thì không quy ra "dòng" được; im lặng còn hơn báo bừa."""
        self.assertEqual(self.keys(self.body(line_percent=None)), set())

    def test_the_message_names_the_number_it_found(self):
        issues = nd30_check.check_body(self.body(line_percent=200))
        self.assertIn("200", issues[0].message)


class NumberFormatTests(unittest.TestCase):
    """Số trong lời nhắn phải đọc ra đúng con số ấy."""

    def test_round_numbers_keep_their_zeros(self):
        """Bản cũ bỏ cả số 0 cuối của số nguyên: lề 20 mm hiện thành "2 mm", khổ A4 210 mm thành "21 mm"."""
        for value, want in ((210, "210"), (297, "297"), (20, "20"), (30, "30"), (100, "100"), (150, "150")):
            with self.subTest(value=value):
                self.assertEqual(nd30_check._mm(value), want)

    def test_decimals_drop_the_padding_but_keep_the_digit(self):
        self.assertEqual(nd30_check._mm(12.7), "12.7")
        self.assertEqual(nd30_check._mm(13.0), "13")

    def test_the_page_size_message_shows_the_real_width(self):
        issues = nd30_check.check_page({"width_mm": 216, "height_mm": 279, "margin_top_mm": 20,
                                        "margin_bottom_mm": 20, "margin_left_mm": 30, "margin_right_mm": 15,
                                        "font": "Times New Roman"})
        message = next(i.message for i in issues if i.key == "page_size")
        self.assertIn("216", message)
        self.assertIn("210", message)      # khổ A4 mà NĐ30 yêu cầu


class RoundingTests(unittest.TestCase):
    """Writer giữ lề bằng twip, nên 15 mm đọc ra có thể là 14,99 mm."""

    def page(self, **extra):
        base = {"width_mm": 210, "height_mm": 297, "margin_top_mm": 20, "margin_bottom_mm": 20,
                "margin_left_mm": 30, "margin_right_mm": 15, "font": "Times New Roman"}
        return dict(base, **extra)

    def keys(self, page):
        return {issue.key for issue in nd30_check.check_page(page)}

    def test_a_margin_a_hair_under_the_limit_is_not_an_error(self):
        """Chính văn bản app dựng ra từng bị báo sai lề phải vì chuyện này."""
        self.assertEqual(self.keys(self.page(margin_right_mm=14.99)), set())
        self.assertEqual(self.keys(self.page(margin_left_mm=29.99)), set())

    def test_a_page_size_a_hair_off_is_not_an_error(self):
        self.assertEqual(self.keys(self.page(width_mm=209.99, height_mm=296.99)), set())

    def test_a_margin_that_is_really_wrong_is_still_caught(self):
        self.assertIn("margin_right_mm", self.keys(self.page(margin_right_mm=10)))
        self.assertIn("margin_left_mm", self.keys(self.page(margin_left_mm=25)))

    def test_the_slack_is_far_smaller_than_the_steps_the_decree_uses(self):
        """Các mốc của NĐ30 cách nhau 5 mm; dung sai 0,05 mm không thể nuốt mất một mức nào."""
        self.assertLess(nd30_check.ROUNDING_MM, 0.5)

    def test_font_sizes_keep_the_exact_comparison(self):
        """Dung sai chỉ dành cho số đo milimét; cỡ chữ 12,9 pt vẫn là sai."""
        issues = nd30_check.check_body([{"text": "a", "size": 12.9, "font": "Times New Roman",
                                         "adjust": 2, "indent_mm": 12.7}])
        self.assertIn("body_size", {i.key for i in issues})
