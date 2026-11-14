# SPDX-License-Identifier: MPL-2.0
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import csvsafe  # noqa: E402


class OptionsTests(unittest.TestCase):
    def fields(self, **kwargs):
        return csvsafe.filter_options(**kwargs).split(",")

    def test_separator_charset_and_quote(self):
        f = self.fields()
        self.assertEqual(f[0], "44")        # dấu phẩy
        self.assertEqual(f[1], "34")        # dấu nháy kép
        self.assertEqual(f[2], "76")        # UTF-8

    def test_semicolon_and_tab(self):
        self.assertEqual(self.fields(separator=";")[0], "59")
        self.assertEqual(self.fields(separator="\t")[0], "9")

    def test_every_column_is_text(self):
        formats = self.fields()[4]
        self.assertTrue(formats.startswith("1/2/2/2/3/2"))
        self.assertEqual(formats.split("/")[-2:], [str(csvsafe.MAX_COLUMNS), "2"])

    def test_dangerous_options_are_off(self):
        f = self.fields()
        self.assertEqual(len(f), 13)
        self.assertEqual(f[6], "true")      # ô trong dấu bao là chữ
        self.assertEqual(f[7], "false")     # không nhận dạng số đặc biệt
        self.assertEqual(f[12], "false")    # không tính công thức khi mở

    def test_rejects_empty_separator(self):
        with self.assertRaises(ValueError):
            csvsafe.filter_options(separator="")


class GuessTests(unittest.TestCase):
    def test_guesses_common_separators(self):
        self.assertEqual(csvsafe.guess_separator("ho_ten,so_dien_thoai,ma_so"), ",")
        self.assertEqual(csvsafe.guess_separator("ho_ten;so_dien_thoai;ma_so"), ";")
        self.assertEqual(csvsafe.guess_separator("a\tb\tc"), "\t")

    def test_ignores_separators_inside_quotes(self):
        self.assertEqual(csvsafe.guess_separator('"Hà Nội, Việt Nam";"0912";"x"'), ";")

    def test_falls_back_to_comma(self):
        self.assertEqual(csvsafe.guess_separator("chi_mot_cot"), ",")


if __name__ == "__main__":
    unittest.main()


class HeaderGuessTests(unittest.TestCase):
    """Chỉ tô đậm và ghim dòng đầu khi nó thật sự là tiêu đề; đoán sai còn khó chịu hơn không làm gì."""

    def test_text_header_above_numbers_is_a_header(self):
        self.assertTrue(csvsafe.looks_like_header(["Họ tên", "Lương"], ["Nguyễn Văn A", "7500000"]))

    def test_two_rows_of_text_are_not_a_header(self):
        """Danh sách tên thuần chữ: dòng đầu cũng là dữ liệu."""
        self.assertFalse(csvsafe.looks_like_header(["Nguyễn Văn A", "Hà Nội"], ["Trần Thị B", "Huế"]))

    def test_a_number_in_the_first_row_rules_it_out(self):
        self.assertFalse(csvsafe.looks_like_header(["2026", "Lương"], ["Nguyễn Văn A", "7500000"]))

    def test_an_empty_cell_in_the_first_row_rules_it_out(self):
        self.assertFalse(csvsafe.looks_like_header(["Họ tên", ""], ["Nguyễn Văn A", "7500000"]))

    def test_a_file_with_one_row_has_no_header(self):
        self.assertFalse(csvsafe.looks_like_header(["Họ tên", "Lương"], []))

    def test_vietnamese_and_english_number_formats_both_count(self):
        self.assertTrue(csvsafe.looks_like_header(["Mặt hàng", "Giá"], ["Gạo", "1.250.000"]))
        self.assertTrue(csvsafe.looks_like_header(["Mặt hàng", "Giá"], ["Gạo", "1,250,000.50"]))

    def test_a_phone_number_keeps_its_leading_zero_and_still_reads_as_a_number(self):
        """0912… vẫn là số theo nghĩa này; đó là lý do dấu hiệu thứ hai cần cả dòng đầu toàn chữ."""
        self.assertTrue(csvsafe.looks_like_header(["Họ tên", "Điện thoại"], ["Nguyễn Văn A", "0912345678"]))
