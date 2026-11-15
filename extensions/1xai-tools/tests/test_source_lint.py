# SPDX-License-Identifier: MPL-2.0
"""Bắt những lỗi chỉ lộ ra khi người dùng bấm thật.

Hộp thoại của extension chỉ chạy được trong app, mà bài kiểm tự động đi đường có kịch bản (bỏ qua hộp thoại). Một
lỗi gán nhiều biến sai số lượng trong _ask_text từng làm hỏng toàn bộ luồng gắn tài khoản AI bằng tay mà không bài
kiểm nào báo. Kiểm này đọc mã nguồn và bắt đúng loại lỗi đó ở mọi tệp Python của extension.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def mismatched_unpacking(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple):
            for target in node.targets:
                if isinstance(target, ast.Tuple) and not any(isinstance(e, ast.Starred) for e in target.elts):
                    if len(target.elts) != len(node.value.elts):
                        yield f"{path.relative_to(ROOT)}:{node.lineno}: {len(target.elts)} biến, {len(node.value.elts)} giá trị"


class SourceLintTests(unittest.TestCase):
    def test_every_multiple_assignment_has_as_many_values_as_names(self):
        found = [msg for path in ROOT.rglob("*.py") if "tests" not in path.parts
                 for msg in mismatched_unpacking(path)]
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
