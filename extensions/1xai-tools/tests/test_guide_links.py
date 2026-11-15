# SPDX-License-Identifier: MPL-2.0
"""Nút "Hướng dẫn ↗" của mọi hộp thoại trỏ tới bài có thật trong docs/web-guides (nguồn của 1xag.com/office/*)."""
import ast
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GUIDES = REPO / "docs" / "web-guides"
SOURCE = (HERE.parent / "onex_tools.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def _value(name):
    return next(ast.literal_eval(n.value) for n in TREE.body if isinstance(n, ast.Assign)
                and any(getattr(t, "id", "") == name for t in n.targets))


def _guide_url():
    fn = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "guide_url")
    scope = {"GUIDE_BASE": _value("GUIDE_BASE")}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "onex_tools.py", "exec"), scope)
    return scope["guide_url"]


def _front_matter(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---", f"{path}: thiếu front matter"
    end = lines.index("---", 1)
    return dict(line.split(": ", 1) for line in lines[1:end])


class GuideLinkTests(unittest.TestCase):
    def test_urls_follow_the_hub_layout(self):
        url = _guide_url()
        self.assertEqual(url("nd30", "vi"), "https://1xag.com/office/nd30")
        self.assertEqual(url("nd30", "en"), "https://1xag.com/office/en/nd30")
        self.assertEqual(url("", "vi"), "https://1xag.com/office")
        self.assertEqual(url("", "en"), "https://1xag.com/office/en")

    def test_every_topic_has_a_guide_in_both_languages(self):
        for topic in sorted(set(_value("GUIDE_TOPICS").values())):
            for lang in ("vi", "en"):
                with self.subTest(topic=topic, lang=lang):
                    self.assertTrue((GUIDES / lang / f"{topic}.md").is_file())

    def test_guides_have_the_front_matter_the_hub_needs(self):
        for path in sorted(GUIDES.glob("*/*.md")):
            with self.subTest(path=path.name):
                meta = _front_matter(path)
                for key in ("title", "description", "headline", "lead", "order"):
                    self.assertIn(key, meta)
                self.assertLessEqual(len(meta["title"]), 60)
                self.assertLessEqual(len(meta["description"]), 155)

    def test_no_guide_without_a_twin(self):
        vi = {p.name for p in (GUIDES / "vi").glob("*.md")}
        en = {p.name for p in (GUIDES / "en").glob("*.md")}
        self.assertEqual(vi, en)


if __name__ == "__main__":
    unittest.main()
