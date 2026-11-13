# SPDX-License-Identifier: MPL-2.0
import sys
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x.vntext import looks_like_tcvn3, normalize, remove_diacritics, tcvn3_to_unicode  # noqa: E402


class DiacriticTests(unittest.TestCase):
    def test_remove(self):
        self.assertEqual(remove_diacritics("Đường Lê Lợi, Quận 1"), "Duong Le Loi, Quan 1")
        self.assertEqual(remove_diacritics("Nguyễn Thị Ánh Tuyết"), "Nguyen Thi Anh Tuyet")
        self.assertEqual(remove_diacritics("abc 123 – €"), "abc 123 – €")

    def test_normalize(self):
        nfd = unicodedata.normalize("NFD", "Tiếng Việt")
        self.assertNotEqual(nfd, "Tiếng Việt")
        self.assertEqual(normalize(nfd), "Tiếng Việt")


class Tcvn3Tests(unittest.TestCase):
    def test_known_sample(self):
        # Quốc hiệu gõ bằng phông .VnTime, đọc ra như ký tự Windows-1252.
        text, changed = tcvn3_to_unicode("Céng hoµ x· héi chñ nghÜa ViÖt Nam")
        self.assertEqual(text, "Cộng hoà xã hội chủ nghĩa Việt Nam")
        self.assertEqual(changed, 7)

    def test_more_words(self):
        self.assertEqual(tcvn3_to_unicode("§éc lËp - Tù do - H¹nh phóc")[0], "Độc lập - Tự do - Hạnh phúc")
        self.assertEqual(tcvn3_to_unicode("®ång")[0], "đồng")

    def test_upper_font(self):
        self.assertEqual(tcvn3_to_unicode("céng hoµ", upper=True)[0], "CỘNG HOÀ")

    def test_ascii_untouched(self):
        self.assertEqual(tcvn3_to_unicode("Report 2026 (v1.0)"), ("Report 2026 (v1.0)", 0))

    def test_unicode_text_must_not_be_converted(self):
        # Chữ Unicode có dấu trùng vị trí byte với TCVN3 ("ã", "à"...): chỉ chuyển đoạn dùng phông TCVN3 hoặc vùng
        # người dùng chọn. Bộ đoán looks_like_tcvn3 phải từ chối chữ Unicode.
        self.assertNotEqual(tcvn3_to_unicode("Đã là Unicode")[0], "Đã là Unicode")
        self.assertFalse(looks_like_tcvn3("Đã là Unicode"))

    def test_detect(self):
        self.assertTrue(looks_like_tcvn3("Céng hoµ x· héi chñ nghÜa ViÖt Nam"))
        self.assertFalse(looks_like_tcvn3("Cộng hoà xã hội chủ nghĩa Việt Nam"))
        self.assertFalse(looks_like_tcvn3("Hello world"))


if __name__ == "__main__":
    unittest.main()
