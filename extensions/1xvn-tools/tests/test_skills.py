# SPDX-License-Identifier: MPL-2.0
"""Skill: đọc front matter, nạp từng phần, và những chỗ phải chặn."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pythonpath"))
from vn1x import skills  # noqa: E402

GOOD = """---
name: thu-nghiem
description: Một skill để thử.
version: 1.2.0
apps: [doc, sheet]
tools: [doc.read, doc.insert]
permissions: {network: [], process: false}
---
# Thân skill

Làm việc A rồi việc B.
"""


class ParseTests(unittest.TestCase):
    def test_front_matter_and_body(self):
        meta, body = skills.parse(GOOD)
        self.assertEqual(meta["name"], "thu-nghiem")
        self.assertEqual(meta["apps"], ["doc", "sheet"])
        self.assertEqual(meta["permissions"], {"network": [], "process": False})
        self.assertTrue(body.startswith("# Thân skill"))

    def test_a_file_without_front_matter_is_refused(self):
        with self.assertRaises(skills.SkillError):
            skills.parse("# Chỉ có thân thôi")

    def test_unclosed_front_matter_is_refused(self):
        with self.assertRaises(skills.SkillError):
            skills.parse("---\nname: a\n")

    def test_a_list_inside_permissions_survives_the_comma(self):
        meta, _ = skills.parse("---\nname: a\ndescription: b\n"
                               "permissions: {network: [api.vidu.vn, b.vn], process: true}\n---\n")
        self.assertEqual(meta["permissions"], {"network": ["api.vidu.vn", "b.vn"], "process": True})


class ValidateTests(unittest.TestCase):
    def meta(self, **extra):
        return dict({"name": "thu-nghiem", "description": "Mô tả."}, **extra)

    def test_defaults_are_the_safe_ones(self):
        out = skills.validate(self.meta())
        self.assertEqual(out["tools"], [])                      # không khai thì không được dùng công cụ nào
        self.assertEqual(out["permissions"], {"network": [], "process": False})
        self.assertEqual(out["apps"], list(skills.APPS))

    def test_a_bad_name_is_refused(self):
        for name in ("Thu Nghiem", "thu_nghiem", "", "a", "../thoat"):
            with self.assertRaises(skills.SkillError, msg=name):
                skills.validate(self.meta(name=name))

    def test_a_missing_description_is_refused(self):
        with self.assertRaises(skills.SkillError):
            skills.validate(self.meta(description="  "))

    def test_an_unknown_app_is_refused(self):
        with self.assertRaises(skills.SkillError):
            skills.validate(self.meta(apps=["doc", "email"]))

    def test_the_name_must_match_the_folder(self):
        with self.assertRaises(skills.SkillError):
            skills.validate(self.meta(), folder_name="ten-khac")


class FolderTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.base = Path(self.dir.name)

    def write(self, name, text=GOOD, folder=None):
        path = self.base / (folder or "skills") / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "SKILL.md").write_text(text, encoding="utf-8")
        return path

    def test_load_a_folder(self):
        path = self.write("thu-nghiem")
        skill = skills.load(path)
        self.assertEqual(skill["version"], "1.2.0")
        self.assertEqual(skill["path"], str(path))

    def test_a_folder_without_skill_md_is_refused(self):
        (self.base / "rong").mkdir()
        with self.assertRaises(skills.SkillError):
            skills.load(self.base / "rong")

    def test_discover_skips_broken_skills_and_says_why(self):
        self.write("thu-nghiem")
        self.write("hong", "khong co front matter")
        found, problems = skills.discover(self.base / "skills")
        self.assertEqual([s["name"] for s in found], ["thu-nghiem"])
        self.assertEqual(len(problems), 1)
        self.assertIn("hong", problems[0])

    def test_a_user_skill_overrides_a_bundled_one_of_the_same_name(self):
        self.write("thu-nghiem")
        self.write("thu-nghiem", GOOD.replace("1.2.0", "9.9.9"), folder="nguoi-dung")
        found, _ = skills.discover(self.base / "skills", self.base / "nguoi-dung")
        self.assertEqual([s["version"] for s in found], ["9.9.9"])

    def test_a_missing_folder_is_not_an_error(self):
        self.assertEqual(skills.discover(self.base / "khong-co"), ([], []))


class LoadingInPartsTests(FolderTests):
    def test_the_model_only_sees_name_and_description(self):
        self.write("thu-nghiem")
        found, _ = skills.discover(self.base / "skills")
        summary = skills.summaries(found)[0]
        self.assertEqual(sorted(summary), ["description", "name"])
        self.assertNotIn("Làm việc A", str(summary))

    def test_summaries_can_be_filtered_by_app(self):
        self.write("thu-nghiem")
        found, _ = skills.discover(self.base / "skills")
        self.assertEqual(skills.summaries(found, app="slide"), [])
        self.assertEqual(len(skills.summaries(found, app="doc")), 1)

    def test_the_body_is_only_read_when_asked_for(self):
        skill = skills.load(self.write("thu-nghiem"))
        self.assertIn("Làm việc A", skills.body(skill))

    def test_a_very_long_body_is_cut(self):
        long = GOOD + ("dài " * 20000)
        skill = skills.load(self.write("thu-nghiem", long))
        self.assertLess(len(skills.body(skill)), skills.MAX_BODY_CHARS + 100)


class ReferenceTests(FolderTests):
    def test_reading_a_reference_file(self):
        path = self.write("thu-nghiem")
        (path / "references").mkdir()
        (path / "references" / "ghi-chu.md").write_text("tham khảo", encoding="utf-8")
        self.assertEqual(skills.reference(skills.load(path), "references/ghi-chu.md"), "tham khảo")

    def test_a_path_leading_outside_the_skill_is_refused(self):
        path = self.write("thu-nghiem")
        (self.base / "bi-mat.txt").write_text("đừng đọc", encoding="utf-8")
        with self.assertRaises(skills.SkillError):
            skills.reference(skills.load(path), "../../bi-mat.txt")

    def test_a_missing_reference_is_an_error_not_a_crash(self):
        with self.assertRaises(skills.SkillError):
            skills.reference(skills.load(self.write("thu-nghiem")), "references/khong-co.md")


class ToolsTests(FolderTests):
    def test_only_the_tools_the_skill_declared(self):
        skill = skills.load(self.write("thu-nghiem"))
        available = [{"name": "doc.read"}, {"name": "doc.replace"}, {"name": "doc.insert"}]
        self.assertEqual([t["name"] for t in skills.allowed_tools(skill, available)],
                         ["doc.read", "doc.insert"])

    def test_a_skill_declaring_no_tools_gets_none(self):
        skill = skills.load(self.write("thu-nghiem", GOOD.replace("tools: [doc.read, doc.insert]", "")))
        self.assertEqual(skills.allowed_tools(skill, [{"name": "doc.read"}]), [])


class PromptTests(FolderTests):
    def test_the_prompt_carries_the_body_and_the_question(self):
        skill = skills.load(self.write("thu-nghiem"))
        text = skills.prompt(skill, "soạn giúp tôi một công văn")
        self.assertIn("Làm việc A", text)
        self.assertIn("soạn giúp tôi một công văn", text)

    def test_a_network_permission_is_spelled_out_in_the_prompt(self):
        skill = skills.load(self.write("thu-nghiem", GOOD.replace("network: []", "network: [api.vidu.vn]")))
        self.assertIn("api.vidu.vn", skills.prompt(skill))


class BundledSkillsTests(unittest.TestCase):
    """Tám skill đi kèm bản 1.0 (ai-platform-design.md mục 9.2) phải nạp được và khai đúng."""

    def setUp(self):
        self.found, self.problems = skills.discover(ROOT / "skills")

    def test_all_eight_load_without_a_problem(self):
        self.assertEqual(self.problems, [])
        self.assertEqual(len(self.found), 8)

    def test_none_of_them_asks_for_network_or_scripts(self):
        for skill in self.found:
            self.assertEqual(skill["permissions"]["network"], [], skill["name"])
            self.assertFalse(skill["permissions"]["process"], skill["name"])

    def test_every_tool_they_declare_really_exists(self):
        from vn1x import doctools
        for skill in self.found:
            for tool in skill["tools"]:
                self.assertIn(tool, doctools.BY_NAME, f"{skill['name']} khai công cụ lạ: {tool}")

    def test_each_one_has_a_body_worth_loading(self):
        for skill in self.found:
            self.assertGreater(len(skills.body(skill)), 200, skill["name"])


if __name__ == "__main__":
    unittest.main()


class EachBundledSkillTests(unittest.TestCase):
    """Mỗi skill đi kèm phải tự đứng vững: có đủ phần, nói rõ giới hạn, và chỉ xin đúng công cụ nó cần.

    Không gọi mô hình thật nên không đo được chất lượng câu trả lời; ở đây đo những thứ đo được, và là những thứ
    hỏng âm thầm nhất khi ai đó sửa một SKILL.md.
    """

    @classmethod
    def setUpClass(cls):
        found, problems = skills.discover(Path(__file__).resolve().parent.parent / "skills")
        assert not problems, problems
        cls.found = {s["name"]: s for s in found}

    def test_there_are_eight_of_them(self):
        self.assertEqual(len(self.found), 8)

    def test_each_one_says_what_it_is_for_in_a_sentence(self):
        for name, skill in self.found.items():
            with self.subTest(name):
                description = skill["description"].strip()
                self.assertGreater(len(description), 30, "mô tả quá ngắn để mô hình chọn đúng skill")
                self.assertLess(len(description), 400, "mô tả quá dài, tốn ngữ cảnh của mọi lượt hỏi")
                self.assertTrue(description.endswith("."), "mô tả nên là một câu trọn vẹn")

    def test_each_body_is_substantial_and_has_at_least_a_heading(self):
        """Không đòi phải đánh số: skill viết lại câu chữ hợp với văn xuôi hơn là các bước 1-2-3.

        Chỉ đòi thân skill đủ dài để nói được điều gì, và có ít nhất một tiêu đề để mô hình bám vào.
        """
        for name, skill in self.found.items():
            with self.subTest(name):
                body = skills.body(skill)
                self.assertGreater(len(body), 200, "thân skill quá ngắn để hướng dẫn được việc gì")
                self.assertTrue(any(line.lstrip().startswith("#") for line in body.splitlines()),
                                "thân skill không có tiêu đề nào")

    def test_each_one_states_its_own_limit(self):
        """Skill nào cũng phải tự nói chỗ nó dừng lại; đó là thứ giữ cho mô hình không lấn sang việc của người."""
        marks = ("không", "chưa", "đừng", "tránh", "giới hạn")
        for name, skill in self.found.items():
            with self.subTest(name):
                body = skills.body(skill).casefold()
                self.assertTrue(any(word in body for word in marks),
                                "thân skill không nói chỗ nào nó dừng lại")

    def test_a_skill_that_talks_about_decree_thirty_asks_for_the_checker(self):
        for name, skill in self.found.items():
            with self.subTest(name):
                body = skills.body(skill).casefold()
                mentions = "nghị định 30" in body or "nđ30" in body
                if mentions and "kiểm" in body:
                    self.assertIn("doc.nd30_check", skill["tools"],
                                  "skill nói tới kiểm thể thức NĐ30 nhưng không xin công cụ kiểm")

    def test_none_of_them_asks_for_the_network_or_to_run_programs(self):
        for name, skill in self.found.items():
            with self.subTest(name):
                self.assertEqual(skill["permissions"]["network"], [])
                self.assertFalse(skill["permissions"]["process"])

    def test_each_one_names_the_app_it_belongs_to(self):
        for name, skill in self.found.items():
            with self.subTest(name):
                self.assertTrue(skill["apps"], "skill không nói nó dùng cho app nào")
                for app in skill["apps"]:
                    self.assertIn(app, ("doc", "sheet", "slide"))

    def test_the_prompt_of_each_one_carries_the_user_question(self):
        for name, skill in self.found.items():
            with self.subTest(name):
                self.assertIn("việc cần làm của tôi", skills.prompt(skill, "việc cần làm của tôi"))
