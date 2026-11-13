# SPDX-License-Identifier: MPL-2.0
import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x.nd30 import (  # noqa: E402
    Nd30Error, build, format_date_line, format_number, format_symbol, recipients_lines)

BASE = {
    "type": "to_trinh", "parent_org": "UBND tỉnh Đà Nẵng", "org": "Sở Khoa học và Công nghệ", "org_abbr": "skhcn",
    "number": 5, "place": "Đà Nẵng", "date": datetime.date(2026, 1, 5), "summary": "Về việc phê duyệt kế hoạch năm 2026",
    "body": ["Đoạn một.", "Đoạn hai."], "authority": "KT.", "authority_title": "Giám đốc",
    "signer_title": "Phó Giám đốc", "signer_name": "Nguyễn Văn A",
    "recipients": ["UBND tỉnh", "Lãnh đạo Sở"], "archive_unit": "VP", "archive_copies": 2,
}


class FormatTests(unittest.TestCase):
    def test_number(self):
        self.assertEqual(format_number(5), "05")
        self.assertEqual(format_number(12), "12")
        with self.assertRaises(Nd30Error):
            format_number(0)

    def test_date_padding_rule(self):
        # Ngày < 10 và tháng 1, 2 có số 0; tháng 3–12 không.
        self.assertEqual(format_date_line("Hà Nội", datetime.date(2026, 1, 5)), "Hà Nội, ngày 05 tháng 01 năm 2026")
        self.assertEqual(format_date_line("Hà Nội", datetime.date(2026, 2, 28)), "Hà Nội, ngày 28 tháng 02 năm 2026")
        self.assertEqual(format_date_line("Hà Nội", datetime.date(2026, 3, 9)), "Hà Nội, ngày 09 tháng 3 năm 2026")
        self.assertEqual(format_date_line("Hà Nội", datetime.date(2026, 11, 13)), "Hà Nội, ngày 13 tháng 11 năm 2026")
        with self.assertRaises(Nd30Error):
            format_date_line(" ", datetime.date(2026, 1, 1))

    def test_symbol(self):
        self.assertEqual(format_symbol("to_trinh", "ubnd"), "TTr-UBND")
        self.assertEqual(format_symbol("quyet_dinh", "UBND"), "QĐ-UBND")
        self.assertEqual(format_symbol("cong_van", "ubnd", "vp"), "UBND-VP")
        with self.assertRaises(Nd30Error):
            format_symbol("to_trinh", "")
        with self.assertRaises(Nd30Error):
            format_symbol("nghi_quyet_la", "UBND")

    def test_recipients(self):
        self.assertEqual(recipients_lines(["Như trên", "Lãnh đạo;"], "VP", 2),
                         ["- Như trên;", "- Lãnh đạo;", "- Lưu: VT, VP, 02b."])
        self.assertEqual(recipients_lines([], ""), ["- Lưu: VT."])


class BuildTests(unittest.TestCase):
    def test_to_trinh(self):
        b = build(BASE)
        self.assertEqual([x["text"] for x in b["left"]],
                         ["UBND TỈNH ĐÀ NẴNG", "SỞ KHOA HỌC VÀ CÔNG NGHỆ", "Số: 05/TTr-SKHCN"])
        self.assertTrue(b["left"][1]["bold"])
        self.assertEqual(b["right"][0]["text"], "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM")
        self.assertEqual(b["right"][2]["text"], "Đà Nẵng, ngày 05 tháng 01 năm 2026")
        self.assertTrue(b["right"][2]["italic"])
        self.assertEqual([x["text"] for x in b["title"]], ["TỜ TRÌNH", "Về việc phê duyệt kế hoạch năm 2026"])
        self.assertEqual(b["sign"][0]["text"], "KT. GIÁM ĐỐC")
        self.assertEqual(b["sign"][1]["text"], "PHÓ GIÁM ĐỐC")
        self.assertEqual(b["sign"][-1]["text"], "Nguyễn Văn A")
        self.assertEqual(b["receivers"][-1]["text"], "- Lưu: VT, VP, 02b.")
        self.assertEqual(b["page"]["margin_left_mm"], 30)

    def test_cong_van(self):
        b = build(dict(BASE, type="cong_van", unit_abbr="VP", recipient_to="UBND các huyện"))
        self.assertEqual(b["left"][2]["text"], "Số: 05/SKHCN-VP")
        self.assertEqual(b["left"][3]["text"], "V/v Về việc phê duyệt kế hoạch năm 2026")
        self.assertEqual(b["title"][0]["text"], "Kính gửi: UBND các huyện")

    def test_required(self):
        for key in ("org", "summary", "signer_name"):
            with self.subTest(key=key), self.assertRaises(Nd30Error):
                build(dict(BASE, **{key: " "}))
        with self.assertRaises(Nd30Error):
            build(dict(BASE, authority="XX."))


if __name__ == "__main__":
    unittest.main()
