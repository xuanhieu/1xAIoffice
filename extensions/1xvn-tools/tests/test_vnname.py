# SPDX-License-Identifier: MPL-2.0
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x.vnname import salutation, sort_key, split_name  # noqa: E402


class SplitTests(unittest.TestCase):
    def test_four_syllables(self):
        self.assertEqual(split_name("Nguyễn Thị Ánh Nguyệt"), ("Nguyễn", "Thị Ánh", "Nguyệt"))

    def test_two_and_three_syllables(self):
        self.assertEqual(split_name("Trần Hưng"), ("Trần", "", "Hưng"))
        self.assertEqual(split_name("Lê Văn Tám"), ("Lê", "Văn", "Tám"))

    def test_one_syllable_is_the_given_name(self):
        self.assertEqual(split_name("Hiếu"), ("", "", "Hiếu"))

    def test_empty_and_spaces(self):
        self.assertEqual(split_name(""), ("", "", ""))
        self.assertEqual(split_name("   Phạm   Xuân   Hiếu  "), ("Phạm", "Xuân", "Hiếu"))


class SortTests(unittest.TestCase):
    def ordered(self, names):
        return sorted(names, key=sort_key)

    def test_sorts_by_given_name_first(self):
        self.assertEqual(self.ordered(["Trần Bình", "Nguyễn An", "Lê Cường"]),
                         ["Nguyễn An", "Trần Bình", "Lê Cường"])

    def test_vietnamese_letter_order(self):
        # đ đứng sau d, ă và â đứng sau a: thứ tự này khác hẳn sắp theo Unicode.
        self.assertEqual(self.ordered(["Lê Đông", "Lê Dung", "Lê An", "Lê Âu", "Lê Ăn"]),
                         ["Lê An", "Lê Ăn", "Lê Âu", "Lê Dung", "Lê Đông"])

    def test_tone_order(self):
        self.assertEqual(self.ordered(["Lê Má", "Lê Mạ", "Lê Ma", "Lê Mã", "Lê Mả", "Lê Mà"]),
                         ["Lê Ma", "Lê Mà", "Lê Mả", "Lê Mã", "Lê Má", "Lê Mạ"])

    def test_same_given_name_falls_back_to_middle_then_surname(self):
        self.assertEqual(self.ordered(["Vũ Thị Hoa", "Vũ Anh Hoa", "Bùi Anh Hoa"]),
                         ["Bùi Anh Hoa", "Vũ Anh Hoa", "Vũ Thị Hoa"])

    def test_case_does_not_matter(self):
        self.assertEqual(sort_key("Lê Hoa"), sort_key("lê hoa"))

    def test_empty_name(self):
        self.assertEqual(sort_key(""), "")


class SalutationTests(unittest.TestCase):
    def test_male_and_female_spellings(self):
        for value in ("Nam", "nam", "M", "male", "Ông", "1"):
            with self.subTest(value=value):
                self.assertEqual(salutation(value, "Nguyễn Văn A"), "Ông Nguyễn Văn A")
        for value in ("Nữ", "nu", "F", "female", "Bà", "0"):
            with self.subTest(value=value):
                self.assertEqual(salutation(value, "Trần Thị B"), "Bà Trần Thị B")

    def test_unknown_gender_does_not_guess(self):
        self.assertEqual(salutation("", "Lê C"), "Ông/Bà Lê C")
        self.assertEqual(salutation("khác", "Lê C"), "Ông/Bà Lê C")

    def test_without_a_name(self):
        self.assertEqual(salutation("Nam"), "Ông")

    def test_custom_titles(self):
        self.assertEqual(salutation("Nam", "A", male="Anh", female="Chị"), "Anh A")


if __name__ == "__main__":
    unittest.main()
