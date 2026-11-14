# SPDX-License-Identifier: MPL-2.0
import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import nd30  # noqa: E402
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


class DialogValidateTests(unittest.TestCase):
    RAW = {"type": "to_trinh", "org": "Sở Khoa học và Công nghệ", "org_abbr": "SKHCN", "number": "5",
           "place": "Đà Nẵng", "date": "05/01/2026", "summary": "Về việc A", "authority": "",
           "signer_name": "Nguyễn Văn A", "body": "Đoạn một.\n\nĐoạn hai.", "recipients": "Như trên\n"}

    def test_ok(self):
        from vn1x.nd30_dialog import validate
        fields, problem = validate(self.RAW, "vi")
        self.assertIsNone(problem)
        self.assertEqual(fields["number"], 5)
        self.assertEqual(fields["date"], datetime.date(2026, 1, 5))
        self.assertEqual(fields["body"], ["Đoạn một.", "Đoạn hai."])
        self.assertEqual(fields["recipients"], ["Như trên"])

    def test_problems_point_at_field(self):
        from vn1x.nd30_dialog import validate
        cases = {"summary": " ", "signer_name": "", "org_abbr": "", "number": "abc", "date": "31/02/2026"}
        for key, value in cases.items():
            with self.subTest(key=key):
                fields, problem = validate(dict(self.RAW, **{key: value}), "vi")
                self.assertIsNone(fields)
                self.assertEqual(problem[0], key)
        _, problem = validate(dict(self.RAW, summary=""), "vi")
        self.assertEqual(problem[1], "Vui lòng nhập: Trích yếu")
        _, problem = validate(dict(self.RAW, number="0"), "en")
        self.assertEqual(problem[0], "number")

    def test_empty_date_is_today(self):
        from vn1x.nd30_dialog import validate
        fields, _ = validate(dict(self.RAW, date=""), "vi", today=datetime.date(2026, 11, 13))
        self.assertEqual(fields["date"], datetime.date(2026, 11, 13))


if __name__ == "__main__":
    unittest.main()


class AbbreviationTableTests(unittest.TestCase):
    """Bảng chữ viết tắt phải khớp từng chữ với Phụ lục III Mục I của Nghị định 30/2020/NĐ-CP.

    Chép lại ở đây nguyên văn (xem docs/legal/sources/nd-30-2020-trich-2026-11-15.txt). Sai một chữ viết tắt là
    ra văn bản sai thể thức, mà nhìn bằng mắt thì không thấy — nên để máy giữ.
    """

    PHU_LUC_III = [
        ("Nghị quyết (cá biệt)", "NQ"), ("Quyết định", "QĐ"), ("Chỉ thị", "CT"), ("Quy chế", "QC"),
        ("Quy định", "QyĐ"), ("Thông cáo", "TC"), ("Thông báo", "TB"), ("Hướng dẫn", "HD"),
        ("Chương trình", "CTr"), ("Kế hoạch", "KH"), ("Phương án", "PA"), ("Đề án", "ĐA"),
        ("Dự án", "DA"), ("Báo cáo", "BC"), ("Biên bản", "BB"), ("Tờ trình", "TTr"),
        ("Hợp đồng", "HĐ"), ("Công điện", "CĐ"), ("Bản ghi nhớ", "BGN"), ("Bản thỏa thuận", "BTT"),
        ("Giấy ủy quyền", "GUQ"), ("Giấy mời", "GM"), ("Giấy giới thiệu", "GGT"),
        ("Giấy nghỉ phép", "GNP"), ("Phiếu gửi", "PG"), ("Phiếu chuyển", "PC"), ("Phiếu báo", "PB"),
    ]

    def test_every_type_in_the_decree_is_offered(self):
        have = {(v["name"], v["abbr"]) for v in nd30.DATA["doc_types"].values()}
        for name, abbr in self.PHU_LUC_III:
            with self.subTest(name):
                self.assertIn((name, abbr), have)

    def test_nothing_is_offered_that_the_decree_does_not_list(self):
        """Công văn là ngoại lệ duy nhất: ký hiệu chỉ gồm chữ viết tắt tên cơ quan, nên không có trong bảng."""
        allowed = {name for name, _ in self.PHU_LUC_III} | {"Công văn"}
        for key, value in nd30.DATA["doc_types"].items():
            with self.subTest(key):
                self.assertIn(value["name"], allowed)

    def test_only_cong_van_has_no_type_name_in_the_document(self):
        for key, value in nd30.DATA["doc_types"].items():
            with self.subTest(key):
                self.assertEqual(value["title"], key != "cong_van")

    def test_abbreviations_are_unique(self):
        abbrs = [v["abbr"] for v in nd30.DATA["doc_types"].values() if v["abbr"]]
        self.assertEqual(len(abbrs), len(set(abbrs)))

    def test_the_symbol_of_a_new_type_reads_the_way_the_decree_writes_it(self):
        self.assertEqual(nd30.format_symbol("quy_dinh", "SKHCN"), "QyĐ-SKHCN")
        self.assertEqual(nd30.format_symbol("giay_uy_quyen", "UBND"), "GUQ-UBND")
        self.assertEqual(nd30.format_symbol("cong_van", "SKHCN"), "SKHCN")

    def test_a_document_of_every_type_can_be_built(self):
        for key in nd30.DATA["doc_types"]:
            with self.subTest(key):
                blocks = nd30.build({"type": key, "org": "Sở Khoa học và Công nghệ", "org_abbr": "SKHCN",
                                     "number": 7, "place": "Đà Nẵng", "date": datetime.date(2026, 11, 15),
                                     "summary": "việc thử dựng văn bản", "body": ["Một đoạn."],
                                     "signer_title": "Giám đốc", "signer_name": "Nguyễn Văn A"})
                self.assertTrue(blocks)


class BodyTemplateTests(unittest.TestCase):
    """Khung phần thân dựng sẵn: bảy loại chép lời văn của Nghị định, còn lại là dàn ý thông lệ."""

    DECREE_TYPES = ("nghi_quyet", "quyet_dinh", "cong_dien", "giay_moi",
                    "giay_gioi_thieu", "bien_ban", "giay_nghi_phep")

    def test_the_seven_decree_bodies_keep_the_decree_wording(self):
        """Những cụm từ này là lời văn của chính Nghị định 30, không phải của mình."""
        for key, phrase in (("nghi_quyet", "QUYẾT NGHỊ:"), ("quyet_dinh", "QUYẾT ĐỊNH:"),
                            ("giay_moi", "trân trọng kính mời"), ("giay_gioi_thieu", "trân trọng giới thiệu"),
                            ("bien_ban", "Thư ký (người ghi biên bản)"),
                            ("giay_nghi_phep", "Xét Đơn đề nghị nghỉ phép"), ("cong_dien", "điện:")):
            with self.subTest(key):
                self.assertTrue(any(phrase in line for line in nd30.body_template(key)),
                                f"{key} thiếu cụm {phrase!r}")

    def test_decree_bodies_say_they_come_from_the_decree(self):
        for key in self.DECREE_TYPES:
            with self.subTest(key):
                self.assertIn("Nghị định 30", nd30.template_source(key))

    def test_every_other_template_admits_it_is_only_office_practice(self):
        for key, value in nd30.TEMPLATES["mau"].items():
            if key in self.DECREE_TYPES:
                continue
            with self.subTest(key):
                self.assertIn("KHÔNG phải quy định", value["nguon"])

    def test_a_type_without_a_template_still_gets_the_old_placeholder(self):
        """Hợp đồng, giấy uỷ quyền, bản thỏa thuận: không dựng sẵn điều khoản có hiệu lực pháp lý."""
        for key in ("hop_dong", "giay_uy_quyen", "ban_thoa_thuan", "ban_ghi_nho"):
            with self.subTest(key):
                self.assertEqual(nd30.body_template(key), ["[Nội dung văn bản]"])
                self.assertEqual(nd30.template_source(key), "")

    def test_every_template_names_a_type_that_exists(self):
        for key in nd30.TEMPLATES["mau"]:
            with self.subTest(key):
                self.assertIn(key, nd30.DATA["doc_types"])

    def test_an_empty_body_falls_back_to_the_template(self):
        blocks = build(dict(BASE, type="bien_ban", body=[]))
        text = " ".join(blocks["body"])
        self.assertIn("Thời gian bắt đầu", text)

    def test_what_the_user_typed_always_wins_over_the_template(self):
        blocks = build(dict(BASE, type="bien_ban", body=["Chỉ một dòng của tôi."]))
        text = " ".join(blocks["body"])
        self.assertEqual(text, "Chỉ một dòng của tôi.")
        self.assertNotIn("Thời gian bắt đầu", text)
