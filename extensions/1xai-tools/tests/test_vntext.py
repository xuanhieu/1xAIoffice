# SPDX-License-Identifier: MPL-2.0
import sys
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import vntext  # noqa: E402
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


class TypingTests(unittest.TestCase):
    def test_viqr(self):
        for src, want in (("Tie^'ng Vie^.t", "Tiếng Việt"), ("Ha` No^.i", "Hà Nội"),
                          ("dda^'t nu+o+'c", "đất nước"), ("Ca^`n Tho+", "Cần Thơ"),
                          ("ddo^?i mo+'i", "đổi mới"), ("na(m", "năm")):
            with self.subTest(src=src):
                self.assertEqual(vntext.viqr_to_unicode(src)[0], want)

    def test_viqr_leaves_ordinary_punctuation(self):
        for text in ("I don't know.", "Hello, world.", "A (B) C", "1 + 2 = 3"):
            with self.subTest(text=text):
                self.assertEqual(vntext.viqr_to_unicode(text), (text, 0))

    def test_vni(self):
        for src, want in (("Tie61ng Vie65t", "Tiếng Việt"), ("Ha2 No65i", "Hà Nội"),
                          ("d9a61t nu7o71c", "đất nước"), ("d9u7o72ng", "đường"),
                          ("na8m", "năm"), ("Ca62n Tho7", "Cần Thơ")):
            with self.subTest(src=src):
                self.assertEqual(vntext.vni_to_unicode(src)[0], want)

    def test_tone_must_follow_the_vowel(self):
        # Bộ chuyển chỉ nhận dấu đứng NGAY SAU nguyên âm, không nhận dấu đặt cuối âm tiết.
        self.assertEqual(vntext.vni_to_unicode("nu7o71c")[0], "nước")
        self.assertEqual(vntext.vni_to_unicode("nu7o7c1")[0], "nươc1")

    def test_counts_changes(self):
        self.assertEqual(vntext.vni_to_unicode("Ha2 No65i")[1], 2)
        self.assertEqual(vntext.viqr_to_unicode("Ha` No^.i")[1], 2)

    def test_mark_only_fits_its_vowel(self):
        # "i(" không hợp lệ: dấu á của ă chỉ đi với a, nên giữ nguyên.
        self.assertEqual(vntext.viqr_to_unicode("i(")[0], "i(")
        self.assertEqual(vntext.vni_to_unicode("i8")[0], "i8")

    def test_detects_typing_style(self):
        self.assertTrue(vntext.looks_like_typing("Tie^'ng Vie^.t", vntext.VIQR))
        self.assertFalse(vntext.looks_like_typing("Tiếng Việt", vntext.VIQR))
        self.assertTrue(vntext.looks_like_typing("Ha2 No65i", vntext.VNI))
        self.assertFalse(vntext.looks_like_typing("", vntext.VNI))


class TidyTests(unittest.TestCase):
    def test_collapses_spaces_and_trims_lines(self):
        self.assertEqual(vntext.tidy_spaces("Xin   chào\n   bạn  "), "Xin chào\nbạn")

    def test_punctuation_spacing(self):
        self.assertEqual(vntext.tidy_spaces("Xin chào , bạn ( ở đây ) ."), "Xin chào, bạn (ở đây).")
        self.assertEqual(vntext.tidy_spaces("Hà Nội.Việt Nam"), "Hà Nội. Việt Nam")

    def test_keeps_decimal_comma_and_numbers(self):
        self.assertEqual(vntext.tidy_spaces("1,5 kg và 3.000 đồng"), "1,5 kg và 3.000 đồng")

    def test_replaces_unusual_spaces(self):
        self.assertEqual(vntext.tidy_spaces("Hà\u00a0Nội\u2009rộng"), "Hà Nội rộng")


class NormalizeFullTests(unittest.TestCase):
    def test_nfc_and_spacing_together(self):
        combined = unicodedata.normalize("NFD", "Việt  Nam ,đất")
        self.assertEqual(vntext.normalize_full(combined), "Việt Nam, đất")

    def test_tone_style_left_alone_by_default(self):
        self.assertEqual(vntext.normalize_full("hòa hoà"), "hòa hoà")

    def test_tone_style_applied_when_asked(self):
        self.assertEqual(vntext.normalize_full("hòa hoà", modern_tone=True), "hoà hoà")
        self.assertEqual(vntext.normalize_full("hòa hoà", modern_tone=False), "hòa hòa")


class ToneStyleTests(unittest.TestCase):
    def test_both_directions(self):
        self.assertEqual(vntext.tone_style("hòa thủy hòe", modern=True), "hoà thuỷ hoè")
        self.assertEqual(vntext.tone_style("hoà thuỷ hoè", modern=False), "hòa thủy hòe")

    def test_qu_cluster_is_left_alone(self):
        for text in ("quý", "quỹ", "quả"):
            with self.subTest(text=text):
                self.assertEqual(vntext.tone_style(text, modern=True), text)
                self.assertEqual(vntext.tone_style(text, modern=False), text)

    def test_closed_syllable_is_left_alone(self):
        self.assertEqual(vntext.tone_style("nguyệt", modern=True), "nguyệt")

    def test_words_without_those_vowels_are_untouched(self):
        self.assertEqual(vntext.tone_style("Tiếng Việt số 1", modern=True), "Tiếng Việt số 1")

    def test_word_without_tone_is_untouched(self):
        self.assertEqual(vntext.tone_style("hoa hoe thuy", modern=True), "hoa hoe thuy")


class DetectTests(unittest.TestCase):
    def test_empty_text_is_not_tcvn3(self):
        self.assertFalse(looks_like_tcvn3(""))


if __name__ == "__main__":
    unittest.main()
