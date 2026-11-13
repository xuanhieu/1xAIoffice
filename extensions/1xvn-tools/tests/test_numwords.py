# SPDX-License-Identifier: MPL-2.0
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x.numwords import (  # noqa: E402
    NumberWordsError, integer_to_words, money_to_words, number_to_words, parse_number_text)

CASES = {
    0: "không",
    5: "năm",
    10: "mười",
    11: "mười một",
    14: "mười bốn",
    15: "mười lăm",
    20: "hai mươi",
    21: "hai mươi mốt",
    24: "hai mươi bốn",
    25: "hai mươi lăm",
    55: "năm mươi lăm",
    100: "một trăm",
    101: "một trăm lẻ một",
    105: "một trăm lẻ năm",
    110: "một trăm mười",
    115: "một trăm mười lăm",
    121: "một trăm hai mươi mốt",
    1000: "một nghìn",
    1001: "một nghìn không trăm lẻ một",
    1010: "một nghìn không trăm mười",
    1100: "một nghìn một trăm",
    10500: "mười nghìn năm trăm",
    21000: "hai mươi mốt nghìn",
    1000000: "một triệu",
    1000001: "một triệu không trăm lẻ một",
    1205000: "một triệu hai trăm lẻ năm nghìn",
    2000000000: "hai tỷ",
    1234567891: "một tỷ hai trăm ba mươi bốn triệu năm trăm sáu mươi bảy nghìn tám trăm chín mươi mốt",
    1000000000000: "một nghìn tỷ",
    -15: "âm mười lăm",
}


class IntegerTests(unittest.TestCase):
    def test_cases(self):
        for n, want in CASES.items():
            with self.subTest(n=n):
                self.assertEqual(integer_to_words(n), want)

    def test_options(self):
        self.assertEqual(integer_to_words(105, le="linh"), "một trăm linh năm")
        self.assertEqual(integer_to_words(24, tu=True), "hai mươi tư")
        self.assertEqual(integer_to_words(14, tu=True), "mười bốn")
        self.assertEqual(integer_to_words(3000, nghin="ngàn"), "ba ngàn")

    def test_too_large(self):
        with self.assertRaises(NumberWordsError):
            integer_to_words(10 ** 18)
        self.assertTrue(integer_to_words(10 ** 18 - 1).startswith("chín trăm chín mươi chín triệu tỷ"))


class NumberTests(unittest.TestCase):
    def test_decimals(self):
        self.assertEqual(number_to_words("3.5"), "ba phẩy năm")
        self.assertEqual(number_to_words("3.25"), "ba phẩy hai mươi lăm")
        self.assertEqual(number_to_words("0.05"), "không phẩy không năm")
        self.assertEqual(number_to_words("12.50"), "mười hai phẩy năm")
        self.assertEqual(number_to_words(-2.5), "âm hai phẩy năm")

    def test_capitalize_and_errors(self):
        self.assertEqual(number_to_words(21, capitalize=True), "Hai mươi mốt")
        for bad in ("abc", "", None, float("inf"), True):
            with self.subTest(bad=bad), self.assertRaises(NumberWordsError):
                number_to_words(bad)


class ParseTests(unittest.TestCase):
    def test_parse(self):
        cases = {"1.250.000": "1250000", "1.250.000,5": "1250000.5", "1,250,000.5": "1250000.5",
                 "3,5": "3.5", "3.5": "3.5", "12 500": "12500", "-7": "-7", "1.500": "1500", "0,750": "0.750",
                 "250.000đ": "250000", "2,25": "2.25"}
        for text, want in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_number_text(text), want)

    def test_parse_errors(self):
        for bad in ("", "abc", "1.2.3,4,5", None):
            with self.subTest(bad=bad), self.assertRaises(NumberWordsError):
                parse_number_text(bad)


class MoneyTests(unittest.TestCase):
    def test_money(self):
        self.assertEqual(money_to_words(1250000), "Một triệu hai trăm năm mươi nghìn đồng")
        self.assertEqual(money_to_words("15000.6"), "Mười lăm nghìn không trăm lẻ một đồng")
        self.assertEqual(money_to_words(2000000, even_suffix="chẵn"), "Hai triệu đồng chẵn")
        self.assertEqual(money_to_words(2000500, even_suffix="chẵn"), "Hai triệu năm trăm đồng")
        self.assertEqual(money_to_words(100, currency="USD"), "Một trăm USD")


if __name__ == "__main__":
    unittest.main()
