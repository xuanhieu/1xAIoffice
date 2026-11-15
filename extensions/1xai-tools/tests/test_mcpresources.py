# SPDX-License-Identifier: MPL-2.0
"""Kiểm lớp resource: địa chỉ 1x://, Markdown và CSV. Không cần UNO."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))

from vn1x import mcpresources as res


class UriTests(unittest.TestCase):
    def test_a_text_document_and_a_sheet_round_trip(self):
        self.assertEqual(res.parse(res.doc_uri("doc1")), ("doc", "doc1", None))
        self.assertEqual(res.parse(res.sheet_uri("doc2", "Sheet1")), ("sheet", "doc2", "Sheet1"))

    def test_a_sheet_name_with_a_slash_survives(self):
        """Người Việt hay đặt tên trang kiểu "Quý 1/2026"; cắt bừa dấu gạch chéo là hỏng."""
        self.assertEqual(res.parse(res.sheet_uri("d", "Quý 1/2026")), ("sheet", "d", "Quý 1/2026"))

    def test_a_foreign_address_is_refused(self):
        for bad in ("https://example.com", "1x://", "1x://doc/", "1x://sheet/d", "1x://khac/d", 5, None):
            with self.subTest(bad=bad):
                with self.assertRaises(res.ResourceError):
                    res.parse(bad)


class DescriptorTests(unittest.TestCase):
    DOCS = [{"id": "doc1", "title": "Tờ trình", "kind": "doc"},
            {"id": "doc2", "title": "Sổ lương", "kind": "sheet", "sheets": ["Sheet1", "Quý 1"]}]

    def test_one_resource_per_text_document_and_one_per_sheet(self):
        out = res.descriptors(self.DOCS)
        self.assertEqual([d["uri"] for d in out],
                         ["1x://doc/doc1", "1x://sheet/doc2/Sheet1", "1x://sheet/doc2/Quý 1"])

    def test_the_media_type_says_what_the_assistant_will_get(self):
        out = res.descriptors(self.DOCS)
        self.assertEqual(out[0]["mimeType"], res.MARKDOWN)
        self.assertEqual(out[1]["mimeType"], res.CSV_TYPE)

    def test_a_document_without_an_id_is_skipped_instead_of_crashing(self):
        self.assertEqual(res.descriptors([{"title": "không mã"}]), [])

    def test_no_documents_open_is_an_empty_list(self):
        self.assertEqual(res.descriptors([]), [])
        self.assertEqual(res.descriptors(None), [])


class MarkdownTests(unittest.TestCase):
    def test_headings_become_hashes_at_the_right_level(self):
        out = res.to_markdown([("Heading 1", "Chương I"), ("Heading 2", "Mục 1"), ("Standard", "Nội dung.")])
        self.assertEqual(out, "# Chương I\n\n## Mục 1\n\nNội dung.")

    def test_vietnamese_style_names_count_as_headings_too(self):
        self.assertEqual(res.heading_level("Tiêu đề 2"), 2)

    def test_an_ordinary_paragraph_is_left_alone(self):
        self.assertEqual(res.heading_level("Standard"), 0)
        self.assertEqual(res.to_markdown([("Standard", "Kính gửi: UBND tỉnh")]), "Kính gửi: UBND tỉnh")

    def test_empty_paragraphs_do_not_become_empty_headings(self):
        self.assertEqual(res.to_markdown([("Heading 1", "   "), ("Standard", "A")]), "A")

    def test_nothing_is_guessed_beyond_headings(self):
        """Đoán in đậm hay bảng mà đoán sai thì trợ lý đọc ra một tài liệu khác bản người dùng đang nhìn."""
        out = res.to_markdown([("Standard", "- một gạch đầu dòng"), ("Standard", "Giá: 1.000.000 đồng")])
        self.assertEqual(out, "- một gạch đầu dòng\n\nGiá: 1.000.000 đồng")


class CsvTests(unittest.TestCase):
    def test_a_comma_inside_a_cell_is_quoted(self):
        self.assertEqual(res.to_csv([["Hà Nội, Việt Nam", "x"]]), '"Hà Nội, Việt Nam",x')

    def test_a_quote_inside_a_cell_is_doubled(self):
        self.assertEqual(res.to_csv([['ông "A"']]), '"ông ""A"""')

    def test_empty_cells_stay_empty(self):
        self.assertEqual(res.to_csv([["a", None, ""]]), "a,,")

    def test_no_rows_is_an_empty_string(self):
        self.assertEqual(res.to_csv([]), "")


class ContentsTests(unittest.TestCase):
    def test_the_reply_carries_the_media_type_of_the_address(self):
        self.assertEqual(res.contents("1x://doc/d", "# A")[0]["mimeType"], res.MARKDOWN)
        self.assertEqual(res.contents("1x://sheet/d/S", "a,b")[0]["mimeType"], res.CSV_TYPE)
