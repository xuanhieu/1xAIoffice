# SPDX-License-Identifier: MPL-2.0
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import aicontext  # noqa: E402


class TrimTests(unittest.TestCase):
    def test_short_text_is_untouched(self):
        self.assertEqual(aicontext.trim("Xin chào", 100), ("Xin chào", False))

    def test_cuts_at_a_paragraph_boundary(self):
        first = "Đoạn một dài vừa đủ để giữ lại."
        body, cut = aicontext.trim(first + "\n\n" + "x" * 80, 60)
        self.assertTrue(cut)
        self.assertEqual(body, first)

    def test_cuts_at_a_sentence_when_there_is_no_paragraph(self):
        first = "Câu một dài vừa đủ để được giữ lại hết."   # 39 ký tự, quá nửa ngân sách 60
        body, cut = aicontext.trim(first + " Câu hai dài hơn nhiều so với phần còn lại.", 60)
        self.assertTrue(cut)
        self.assertEqual(body, first)

    def test_hard_cut_when_the_only_boundary_is_too_early(self):
        # Ranh giới ở quá sớm thì cắt ở đó sẽ mất phần lớn nội dung, nên cắt thẳng theo ngân sách.
        body, cut = aicontext.trim("A.\n\n" + "x" * 80, 40)
        self.assertEqual((len(body), cut), (40, True))

    def test_hard_cut_when_nothing_else_fits(self):
        body, cut = aicontext.trim("x" * 100, 20)
        self.assertEqual((len(body), cut), (20, True))


class BuildTests(unittest.TestCase):
    def test_selection_wins_over_whole_document(self):
        messages, note = aicontext.build("Hỏi gì đó", selection="Phần chọn", document="Cả tài liệu")
        self.assertIn("Phần chọn", messages[1]["content"])
        self.assertNotIn("Cả tài liệu", messages[1]["content"])
        self.assertIn("vùng đang chọn", note)

    def test_falls_back_to_the_document(self):
        messages, note = aicontext.build("Hỏi", selection="   ", document="Nội dung")
        self.assertIn("Nội dung", messages[1]["content"])
        self.assertIn("cả tài liệu", note)

    def test_system_message_tells_the_model_not_to_invent(self):
        messages, _ = aicontext.build("Hỏi", document="Nội dung")
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("không bịa", messages[0]["content"])

    def test_question_is_included(self):
        messages, _ = aicontext.build("Đây là văn bản gì?", document="TỜ TRÌNH")
        self.assertIn("Đây là văn bản gì?", messages[1]["content"])

    def test_note_says_when_the_text_was_cut(self):
        _, note = aicontext.build("Hỏi", document="x" * 100, budget=30)
        self.assertIn("đã cắt bớt", note)

    def test_refuses_empty_question_or_document(self):
        with self.assertRaises(ValueError):
            aicontext.build("   ", document="Nội dung")
        with self.assertRaises(ValueError):
            aicontext.build("Hỏi", document="   ")


if __name__ == "__main__":
    unittest.main()
