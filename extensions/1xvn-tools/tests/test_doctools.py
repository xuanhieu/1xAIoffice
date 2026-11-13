# SPDX-License-Identifier: MPL-2.0
"""Bảng công cụ tài liệu dùng chung: tên, lược đồ, kiểm tham số, phân trang."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import doctools  # noqa: E402


class DeclarationTests(unittest.TestCase):
    def test_every_tool_declares_a_schema_and_hints(self):
        for tool in doctools.declarations():
            self.assertTrue(tool["description"], tool["name"])
            self.assertEqual(tool["inputSchema"]["type"], "object")
            self.assertIn("readOnlyHint", tool["annotations"])
            self.assertIn("destructiveHint", tool["annotations"])

    def test_read_only_tools_are_never_marked_destructive(self):
        for tool in doctools.TOOLS:
            if tool["read_only"]:
                self.assertFalse(tool["destructive"], tool["name"])

    def test_replacing_a_paragraph_is_marked_destructive(self):
        self.assertTrue(doctools.BY_NAME["doc.replace"]["destructive"])


class CheckTests(unittest.TestCase):
    def test_unknown_tool(self):
        with self.assertRaises(doctools.ToolError):
            doctools.check("doc.xoa_het", {})

    def test_missing_required_argument(self):
        with self.assertRaises(doctools.ToolError) as caught:
            doctools.check("doc.read", {})
        self.assertIn("doc", str(caught.exception))

    def test_empty_string_counts_as_missing(self):
        with self.assertRaises(doctools.ToolError):
            doctools.check("doc.read", {"doc": ""})

    def test_wrong_type(self):
        with self.assertRaises(doctools.ToolError):
            doctools.check("doc.read", {"doc": "d1", "cursor": "mười"})

    def test_boolean_is_not_an_integer(self):
        with self.assertRaises(doctools.ToolError):
            doctools.check("doc.read", {"doc": "d1", "cursor": True})

    def test_negative_cursor(self):
        with self.assertRaises(doctools.ToolError):
            doctools.check("doc.read", {"doc": "d1", "cursor": -1})

    def test_enum_is_enforced(self):
        with self.assertRaises(doctools.ToolError):
            doctools.check("vn.convert_legacy", {"doc": "d1", "kind": "utf7"})
        self.assertEqual(doctools.check("vn.convert_legacy", {"doc": "d1", "kind": "vni"})["kind"], "vni")

    def test_unknown_argument_is_dropped_not_fatal(self):
        self.assertEqual(doctools.check("doc.read", {"doc": "d1", "bua": 1}), {"doc": "d1"})


class PageTests(unittest.TestCase):
    def test_short_text_has_no_cursor(self):
        self.assertEqual(doctools.page("ngắn"), ("ngắn", None))

    def test_long_text_is_cut_at_a_line_boundary(self):
        text = ("dòng dài vừa phải\n" * 100)
        chunk, nxt = doctools.page(text, limit=100)
        self.assertTrue(chunk.endswith("phải"))
        self.assertIsNotNone(nxt)
        self.assertEqual(text[:nxt], chunk)

    def test_reading_on_with_the_cursor_covers_the_whole_text(self):
        text = "".join(f"đoạn {i}\n" for i in range(200))
        seen, cursor = "", 0
        while True:
            chunk, cursor = doctools.page(text, cursor, limit=120)
            seen += chunk
            if cursor is None:
                break
        self.assertEqual(seen, text)

    def test_cursor_past_the_end(self):
        self.assertEqual(doctools.page("abc", 99), ("", None))


class FakeBackend:
    def docs_list_open(self):
        return "d1: Tờ trình (văn bản, chưa lưu)"

    def doc_read(self, doc, cursor=0):
        return doctools.page("một\nhai\nba\n" * 50, cursor, limit=40)

    def doc_replace(self, doc, anchor, text):
        raise RuntimeError("người dùng đã từ chối")


class CallTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()

    def test_plain_result(self):
        out = doctools.call(self.backend, "docs.list_open", {})
        self.assertNotIn("isError", out)
        self.assertIn("Tờ trình", out["content"][0]["text"])

    def test_paged_result_tells_the_client_how_to_read_on(self):
        out = doctools.call(self.backend, "doc.read", {"doc": "d1"})
        self.assertIn("cursor=", out["content"][0]["text"])

    def test_bad_arguments_come_back_as_an_error_result_not_a_crash(self):
        out = doctools.call(self.backend, "doc.read", {})
        self.assertTrue(out["isError"])

    def test_a_backend_failure_is_reported_not_raised(self):
        out = doctools.call(self.backend, "doc.replace", {"doc": "d1", "anchor": 0, "text": "x"})
        self.assertTrue(out["isError"])
        self.assertIn("từ chối", out["content"][0]["text"])

    def test_a_tool_the_backend_does_not_implement(self):
        out = doctools.call(self.backend, "sheet.read_range", {"doc": "d1", "range": "A1:B2"})
        self.assertTrue(out["isError"])


if __name__ == "__main__":
    unittest.main()
